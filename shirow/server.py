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

import configparser
import fcntl
import logging
import os
import select
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


define('config_file', default='wsrpc.conf', help='')
define('port', default=8888, help='listen on a specific port')
define('token_algorithm', default='HS256', help='')
define('token_key', default=None, help='')
define('redis_host', default='localhost', help='')
define('redis_port', default=6379, help='')


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


class RPCServer(WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)

        self.config = configparser.ConfigParser()
        self.io_loop = IOLoop.current()
        self.logger = logging.getLogger('tornado.application')
        self.redis_conn = None
        self.user_id = None

    #
    # Internal methods.
    #
    @gen.coroutine
    def _call_remote_procedure(self, request, method, arguments_list):
        result = None
        future = to_asyncio_future(method(request, *arguments_list))
        try:
            result = yield from future
        except Ret:
            pass
        except Exception:
            message = 'an error occurred while executing the function'
            request.ret_error(message)
            self.logger.exception(message)
        finally:
            if result is not None:
                request.ret(result)

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
        self.set_header('WWW-Authenticate', 'Token realm="wsrpc"')
        self.set_status(401)  # Unauthorized
        self.finish()

    def _fail_request(self, message):
        self.logger.error(message)
        self.set_status(500)  # Internal Server Error
        self.finish()

    def _open_redis_connection(self):
        self.redis_conn = redis.StrictRedis(host=options.redis_host,
                                            port=options.redis_port, db=0)
        try:
            connected = True if self.redis_conn.ping() else False
        except redis.exceptions.ConnectionError:
            connected = False

        return connected

    def _set_nonblocking(self, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

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
            self._fail_request('wsrpc is not able to connect to Redis')
            return

        decoded_token = self._decode_token(encoded_token)
        if not decoded_token:
            self._fail_request('An error occurred while decoding the '
                               'following token: {}'.format(encoded_token))
            return

        key = 'user:{}:token'.format(self.user_id)
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

    def open(self):
        self.create()

    def on_close(self):
        self.destroy()

    @gen.coroutine
    def on_message(self, message):
        read_end, write_end = os.pipe()
        self._set_nonblocking(read_end)
        self._set_nonblocking(write_end)

        parsed = json_decode(message)
        request = Request(write_end, parsed['marker'])

        def response_cb(*args, **kwargs):
            responses = os.read(read_end, select.PIPE_BUF)
            for _ in responses:
                self.write_message(request.get_response())

        self.io_loop.add_handler(read_end, response_cb, self.io_loop.READ)

        procedure_name = parsed['function_name']
        arguments_list = parsed['parameters_list']
        method = getattr(self, procedure_name, None)
        if procedure_name in dir(self) and hasattr(method, 'remote'):
            # Checking if the number of actual arguments passed to a remote
            # procedure matches the number of formal parameters of the remote
            # procedure (except self and request).
            min, max = method.arguments_range
            if (max - 2) >= len(arguments_list) >= (min - 2):
                self._call_remote_procedure(request, method, arguments_list)
            else:
                request.ret_error('number of arguments mismatch in the {} '
                                  'function call'.format(procedure_name))
        else:
            request.ret_error('the {} function is '
                              'undefined'.format(parsed['function_name']))
