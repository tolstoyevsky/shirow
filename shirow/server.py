# Copyright 2016 Evgeny Golyshev. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module provides an RPC framework the primary goal of which is to
simplify creating microservices using Tornado.
"""

import logging
from functools import wraps

import jwt
import jwt.exceptions
import tornado
from jwt.exceptions import DecodeError
from tornado import gen
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.options import define, options
from tornado.platform.asyncio import to_asyncio_future
from tornado.websocket import WebSocketHandler

from shirow.exceptions import CouldNotDecodeToken, UndefinedMethod
from shirow.request import Ret, Request
from shirow.util import check_number_of_args

MOCK_TOKEN = 'mock_token'
MOCK_USER_ID = 1
TOKEN_PATTERN = r'([_\-\w\.]+)'

define('allow_mock_token',
       help=f"allow using '{MOCK_TOKEN}' instead of real token (for testing "
            f"purposes only)", default=False, type=bool)
define('config_file',
       help='load parameters from the specified configuration '
            'file', default='shirow.conf')
define('port',
       help='listen on a specific port', default=8888)
define('token_algorithm',
       help='specify the algorithm used to sign the token', default='HS256')
define('token_key',
       help='encrypt the token using the specified secret key', default=None)


def remote(func):
    """Decorator to mark some of the methods of RPC servers as remote. The
    decorated methods can be considered as a part of the public interface,
    since they are accessible from the client side.
    """

    @wraps(func)
    @gen.coroutine
    def wrapper(self, *args, **kwargs):
        args += tuple(kwargs.values())
        return func(self, *args)

    try:
        defaults_number = len(func.__defaults__)
    # If there are no default arguments func.__defaults__ is None.
    except TypeError:
        defaults_number = 0

    arguments_number = func.__code__.co_argcount
    wrapper.arguments_range = (
        arguments_number - defaults_number,  # min
        arguments_number  # max
    )
    wrapper.remote = True

    return wrapper


class RPCServer(WebSocketHandler):  # pylint: disable=abstract-method
    """Base class for RPC servers. """

    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)

        self.io_loop = IOLoop.current()
        self.logger = logging.getLogger('tornado.application')
        self.user_id = None

    #
    # Internal methods.
    #
    @gen.coroutine
    def _call_remote_procedure(self, request, method_name, arguments_list):
        try:
            method = self._get_method(method_name)
        except UndefinedMethod:
            request.ret_error(f'the {method_name} function is undefined')

        if check_number_of_args(method, arguments_list):
            future = to_asyncio_future(method(request, *arguments_list))
        else:
            request.ret_error(f'number of arguments mismatch in the {method_name} function call')

        try:
            result = yield from future
            if result is not None:  # if the return statement was used
                request.ret(result)
        except Ret:
            pass
        except Exception:  # pylint: disable=broad-except
            message = 'an error occurred while executing the function'
            self.logger.exception(message)
            request.ret_error(message)

    def _decode_token(self, encoded_token):
        try:
            token = jwt.decode(encoded_token, options.token_key,
                               algorithms=[options.token_algorithm])
        except DecodeError:
            raise CouldNotDecodeToken

        self.user_id = token['user_id']

    def _dismiss_request(self):
        self.logger.warning('Authentication request was dismissed')
        self.set_header('WWW-Authenticate', 'Token realm="shirow"')
        self.set_status(401)  # Unauthorized
        self.finish()

    def _fail_request(self, message):
        self.logger.error(message)
        self.set_status(500)  # Internal Server Error
        self.finish()

    def _get_method(self, method_name):
        method = getattr(self, method_name, None)
        if method_name in dir(self) and hasattr(method, 'remote'):
            return method

        raise UndefinedMethod

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        try:
            encoded_token = args[0]
        except IndexError:  # The request doesn't contain a token.
            self._dismiss_request()
            return

        if options.token_key is None:
            self._fail_request('A token key must be specified either in the '
                               'configuration file or on the command line')
            return

        if options.allow_mock_token and encoded_token == MOCK_TOKEN:
            self.user_id = MOCK_USER_ID
        else:
            try:
                self._decode_token(encoded_token)
            except CouldNotDecodeToken:
                self._dismiss_request()
                return

        if self.user_id:
            # The WebSocket connection request must not contain any parameters.
            # The only parameter we needed has already been processed. Now we
            # have to get rid of it.
            args = ()
            WebSocketHandler.get(self, *args, **kwargs)
        else:
            self._dismiss_request()

    def create(self):
        """Invoked when a connection to the RPC server is established. """

    def destroy(self):
        """Invoked when a connection to the RPC server is terminated. """

    # Implementing the methods inherited from
    # tornado.websocket.WebSocketHandler

    def log_exception(self, typ, value, tb):
        """Logs uncaught exceptions. This overrides the method in
        WebSocketHandler not to log exceptions derived from Ret.
        """
        if not isinstance(value, Ret):
            WebSocketHandler.log_exception(self, typ, value, tb)

    def open(self, *args, **kwargs):
        self.create()

    def on_close(self):
        self.destroy()

    @gen.coroutine
    def on_message(self, message):
        parsed = json_decode(message)

        def callback(response):
            self.write_message(response)

        request = Request(parsed['marker'], callback)

        method_name = parsed['function_name']
        params = parsed['parameters_list']

        try:
            yield self._call_remote_procedure(request, method_name, params)
        except Ret:
            pass
