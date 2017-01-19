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

import logging
from functools import wraps

import jwt
import jwt.exceptions
import redis
import tornado
from tornado import gen
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.options import define, options
from tornado.platform.asyncio import to_asyncio_future
from tornado.websocket import WebSocketHandler

from shirow.request import Ret, Request

MOCK_TOKEN = 'mock_token'
MOCK_USER_ID = -1
TOKEN_PATTERN = r'([_\-\w\.]+)'

define('allow_mock_token',
       help="allow using '{}' instead of real token (for testing "
            "purposes only)".format(MOCK_TOKEN), default=False, type=bool)
define('config_file',
       help='load parameters from the specified configuration '
            'file', default='shirow.conf')
define('port',
       help='listen on a specific port', default=8888)
define('token_algorithm',
       help='specify the algorithm used to sign the token', default='HS256')
define('token_key',
       help='encrypt the token using the specified secret key', default=None)
define('redis_host',
       help='specify Redis host', default='localhost')
define('redis_port',
       help='specify Redis port', default=6379)


def remote(func):
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


class UndefinedMethod(Exception):
    """Exception raised when attempting to get a method which either does not
    exist or is not public."""
    pass


class RPCServer(WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)

        self.io_loop = IOLoop.current()
        self.logger = logging.getLogger('tornado.application')
        self.redis_conn = None
        self.user_id = None

    #
    # Internal methods.
    #
    @gen.coroutine
    def _call_remote_procedure(self, request, method_name, arguments_list):
        try:
            method = self._get_method(method_name)
        except UndefinedMethod:
            request.ret_error('the {} function is undefined'.
                              format(method_name))

        if self._check_number_of_args(method, arguments_list):
            future = to_asyncio_future(method(request, *arguments_list))
        else:
            request.ret_error('number of arguments mismatch in the {} '
                              'function call'.format(method_name))

        try:
            result = yield from future
            if result is not None:  # if the return statement was used
                request.ret(result)
        except Ret:
            pass
        except Exception:
            message = 'an error occurred while executing the function'
            self.logger.exception(message)
            request.ret_error(message)

    def _check_number_of_args(self, method, params):
        # Checking if the number of actual arguments passed to a remote
        # procedure matches the number of formal parameters of the remote
        # procedure (except self and request).
        min, max = method.arguments_range
        if (max - 2) >= len(params) >= (min - 2):
            return True

        return False

    def _decode_token(self, encoded_token):
        decoded = True
        try:
            token = jwt.decode(encoded_token, options.token_key,
                               algorithm=options.token_algorithm)
        except jwt.exceptions.DecodeError:
            token = {}
            decoded = False

        self.user_id = token.get('user_id', None)
        return decoded

    def _dismiss_request(self):
        self.logger.warning('Authentication request was dismissed')
        self.set_header('WWW-Authenticate', 'Token realm="shirow"')
        self.set_status(401)  # Unauthorized
        self.finish()

    def _fail_request(self, message):
        self.logger.error(message)
        self.set_status(500)  # Internal Server Error
        self.finish()

    def _get_token_key(self, user_id=None):
        if user_id is None:
            user_id = self.user_id

        return 'user:{}:token'.format(user_id)

    def _get_method(self, method_name):
        method = getattr(self, method_name, None)
        if method_name in dir(self) and hasattr(method, 'remote'):
            return method

        raise UndefinedMethod

    def _open_redis_connection(self):
        self.redis_conn = redis.StrictRedis(host=options.redis_host,
                                            port=options.redis_port, db=0)
        try:
            connected = True if self.redis_conn.ping() else False
        except redis.exceptions.ConnectionError:
            connected = False

        return connected

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

        if not self._open_redis_connection():
            self._fail_request('Shirow is not able to connect to Redis')
            return

        # Prepare mock token if needed
        if options.allow_mock_token and encoded_token == MOCK_TOKEN:
            payload = {'user_id': MOCK_USER_ID, 'ip': '127.0.0.1'}
            encoded_token = \
                jwt.encode(payload, options.token_key,
                           algorithm=options.token_algorithm).decode('utf8')

            key = self._get_token_key(MOCK_USER_ID)
            token_ttl = 15  # seconds
            self.redis_conn.setex(key, 60 * token_ttl, encoded_token)
            self.user_id = MOCK_USER_ID

        decoded_token = self._decode_token(encoded_token)
        if not decoded_token:
            self._fail_request('An error occurred while decoding the '
                               'following token: {}'.format(encoded_token))
            return

        key = self._get_token_key()
        if self.redis_conn.get(key) == encoded_token.encode('utf8'):
            # The WebSocket connection request must not contain any parameters.
            # The only parameter we needed has already been processed. Now we
            # have to get rid of it.
            args = ()
            WebSocketHandler.get(self, *args, **kwargs)
        else:
            self._dismiss_request()

    def create(self):
        pass

    def destroy(self):
        pass

    # Implementing the methods inherited from
    # tornado.websocket.WebSocketHandler

    def log_exception(self, typ, value, tb):
        """Logs uncaught exceptions. This overrides the method in
        WebSocketHandler not to log exceptions derived from Ret.
        """
        if not isinstance(value, Ret):
            WebSocketHandler.log_exception(self, typ, value, tb)

    def open(self):
        self.create()

    def on_close(self):
        self.destroy()

    @gen.coroutine
    def on_message(self, message):
        parsed = json_decode(message)

        def cb(response):
            self.write_message(response)

        request = Request(parsed['marker'], cb)

        method_name = parsed['function_name']
        params = parsed['parameters_list']

        try:
            yield self._call_remote_procedure(request, method_name, params)
        except Ret:
            pass
