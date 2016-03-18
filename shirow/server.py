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
import logging
from functools import wraps

import jwt
import jwt.exceptions
import redis
import tornado
from tornado import gen
from tornado.escape import json_decode, json_encode
from tornado.options import define, options
from tornado.websocket import WebSocketHandler


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
        self.logger = logging.getLogger('tornado.application')
        self.redis_conn = None
        self.user_id = None

    #
    # Internal methods.
    #
    @gen.coroutine
    def _call_remote_procedure(self, func, *args, **kwargs):
        response = {'marker': kwargs.pop('marker')}
        try:
            response['result'] = yield func(*args)
        except Exception:
            message = 'an error occurred while executing the function'
            self.logger.exception(message)
            response = {'error': message}
        self.write_message(json_encode(response))

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

        if self.redis_conn.exists(encoded_token):
            if not self._decode_token(encoded_token):
                self._fail_request('An error occurred while decoding the '
                                   'following token: {}'.format(encoded_token))
                return

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

    def on_message(self, message):
        ret = {}
        parsed = json_decode(message)
        function_name = parsed['function_name']
        marker = parsed['marker']
        parameters_list = parsed['parameters_list']
        method = getattr(self, function_name, None)
        if function_name in dir(self) and hasattr(method, 'remote'):
            # Checking if the number of actual arguments passed to a remote
            # procedure matches the number of formal parameters of the remote
            # procedure (except the self argument).
            min, max = method.arguments_range
            if (max - 1) >= len(parameters_list) >= (min - 1):
                self._call_remote_procedure(method, *parameters_list,
                                            marker=marker)
            else:
                ret['error'] = 'number of arguments mismatch in the {} ' \
                               'function call'.format(function_name)
                self.write_message(json_encode(ret))
        else:
            ret['error'] = 'the {} function is ' \
                           'undefined'.format(parsed['function_name'])
            self.write_message(json_encode(ret))
            return
