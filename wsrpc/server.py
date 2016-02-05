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
import sys

import jwt
import redis
import tornado
from tornado.escape import json_decode, json_encode
from tornado.websocket import WebSocketHandler


class RPCServer(WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)

        self.config = configparser.ConfigParser()
        self.logger = logging.getLogger('tornado.application')
        self.remote_functions = []
        self.user_id = None

        for method in dir(self):
            if method.endswith('__remote'):
                self.remote_functions.append(method)

        self.config.read('wsrpc.ini')

    #
    # Internal methods.
    #
    def _decode_token(self, encoded_token):
        if 'token' in self.config:
            algorithm = self.config.get('token', 'algorithm', fallback='HS256')
            try:
                # The key parameter is mandatory.
                key = self.config['token']['key']
            except KeyError:
                self._exit('The key parameter must be specified in the '
                           'configuration file')

            return jwt.decode(encoded_token, key, algorithm=algorithm)
        else:
            self._exit("The token section doesn't exist in the configuration "
                       "file")

    def _dismiss_request(self):
        self.logger.warning('Authentication request was dismissed')
        self.set_header('WWW-Authenticate', 'Token realm="wsrpc"')
        self.set_status(401)  # Unauthorized
        self.finish()

    def _exit(self, message):
        self.logger.error(message)
        sys.exit(1)

    def _open_redis_connection(self):
        if 'redis' in self.config:
            host = self.config.get('redis', 'host', fallback='localhost')
            port = self.config.get('redis', 'port', fallback='6379')
            redis_conn = redis.StrictRedis(host=host, port=port, db=0)
            try:
                connected = True if redis_conn.ping() else False
            except redis.exceptions.ConnectionError:
                connected = False

            if not connected:
                self._exit('wsrpc is not able to connect to Redis')

            return redis_conn
        else:
            self._exit("The redis section doesn't exist in the configuration "
                       "file")

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        try:
            encoded_token = args[0]
        except IndexError:  # The request doesn't contain a token.
            self._dismiss_request()
            return

        redis_conn = self._open_redis_connection()
        if redis_conn.exists(encoded_token):
            token = self._decode_token(encoded_token)
            self.user_id = token['user_id']
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
        function_name = parsed['function_name'] + '__remote'
        if function_name in self.remote_functions:
            method = getattr(self, function_name)
        else:
            ret['error'] = 'the {} function is ' \
                           'undefined'.format(parsed['function_name'])
            self.write_message(json_encode(ret))
            return

        # Checking if the number of actual arguments passed to a remote
        # procedure matches the number of formal parameters of the remote
        # procedure (except the self argument).
        if len(parsed['parameters_list']) == method.__code__.co_argcount - 1:
            result = method(*parsed['parameters_list'])
        else:
            ret['error'] = 'number of arguments mismatch in the {} ' \
                           'function call'.format(parsed['function_name'])
            self.write_message(json_encode(ret))
            return

        ret = {'result': result, 'marker': parsed['marker']}
        self.write_message(json_encode(ret))
