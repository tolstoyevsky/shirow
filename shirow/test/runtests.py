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

import redis
from tornado import gen
from tornado.concurrent import Future
from tornado.escape import json_decode, json_encode
from tornado.options import options
from tornado.test.util import unittest
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application
from tornado.websocket import websocket_connect

from shirow.server import RPCServer, remote

# jwt.encode({'user_id': 1, 'ip': '127.0.0.1'}, 'secret', algorithm='HS256')
ENCODED_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.' \
                'eyJpcCI6IjEyNy4wLjAuMSIsInVzZXJfaWQiOjF9.' \
                'kYIAQYDjOiZpjExvXZaAgemi4xiisvPEzvXEemmAJLY'
TOKEN_KEY = 'secret'


class MockRPCServer(RPCServer):
    def initialize(self, close_future, compression_options=None):
        self.close_future = close_future
        self.compression_options = compression_options

    def get_compression_options(self):
        return self.compression_options

    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))

    @remote
    def add(self, a, b):
        return a + b

    @remote
    def div_by_zero(self):
        1 / 0

    @remote
    def echo(self, message):
        self.ret(message)

    @remote
    def say_hello(self, name='Shirow'):
        return 'Hello {}!'.format(name)

    @remote
    def return_more_than_one_value(self):
        self.ret_and_continue('spam')
        self.ret_and_continue('ham')
        self.ret_and_continue('eggs')


class WebSocketBaseTestCase(AsyncHTTPTestCase):
    @gen.coroutine
    def ws_connect(self, path, compression_options=None):
        ws = yield websocket_connect('ws://127.0.0.1:{}{}'.format(
            self.get_http_port(), path
        ), compression_options=compression_options)
        raise gen.Return(ws)

    @gen.coroutine
    def close(self, ws):
        """Close a websocket connection and wait for the server side.

        If we don't wait here, there are sometimes leak warnings in the
        tests.
        """
        ws.close()
        yield self.close_future


class RPCServerTest(WebSocketBaseTestCase):
    def get_app(self):
        self.close_future = Future()
        redis_conn = redis.StrictRedis(host='localhost', port=6379, db=0)
        redis_conn.set(ENCODED_TOKEN, '')
        options.token_key = TOKEN_KEY
        return Application([
            ('/rpc', MockRPCServer,
             dict(close_future=self.close_future)),
            ('/rpc/token/([\w\.]+)', MockRPCServer,
             dict(close_future=self.close_future)),
        ])

    def prepare_payload(self, procedure_name, parameters_list, marker):
        data = {
            'function_name': procedure_name,
            'parameters_list': parameters_list,
            'marker': marker
        }
        return json_encode(data)

    def test_tokenless_request(self):
        response = self.fetch('/rpc')
        self.assertEqual(response.code, 401)

    def test_passing_non_existent_token(self):
        response = self.fetch('/rpc/token/some.non.existent.token')
        self.assertEqual(response.code, 401)

    def test_using_none_token_key(self):
        options.token_key = None
        response = self.fetch('/rpc/token/{}'.format(ENCODED_TOKEN))
        self.assertEqual(response.code, 500)

    def test_using_wrong_token_key(self):
        options.token_key = 'wrong_' + TOKEN_KEY
        response = self.fetch('/rpc/token/{}'.format(ENCODED_TOKEN))
        self.assertEqual(response.code, 500)

    @gen_test
    def test_calling_existent_function(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        payload = self.prepare_payload('add', [1, 2], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {'result': 3, 'marker': 1})
        yield self.close(ws)

    @gen_test
    def test_calling_non_existent_function(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        payload = self.prepare_payload('non_existent_function', [], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'the non_existent_function function is undefined',
            'marker': 1
        })
        yield self.close(ws)

    @gen_test
    def test_mismatching_parameters(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        # less than is required
        payload = self.prepare_payload('add', [1], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'number of arguments mismatch in the add function call',
            'marker': 1
        })
        # more than is required
        payload = self.prepare_payload('add', [1, 3, 5], 2)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'number of arguments mismatch in the add function call',
            'marker': 2
        })
        yield self.close(ws)

    @gen_test
    def test_handling_errors_in_remote_procedures(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        payload = self.prepare_payload('div_by_zero', [], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'an error occurred while executing the function',
            'marker': 1
        })
        yield self.close(ws)

    @gen_test
    def test_default_parameters(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        payload = self.prepare_payload('say_hello', [], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello Shirow!',
            'marker': 1
        })
        payload = self.prepare_payload('say_hello', ['Norris'], 2)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello Norris!',
            'marker': 2
        })
        yield self.close(ws)

    @gen_test
    def test_using_ret_instead_of_return(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        payload = self.prepare_payload('echo', ['Hello!'], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello!',
            'marker': 1
        })
        yield self.close(ws)

    @gen_test
    def test_returning_more_than_one_value(self):
        ws = yield self.ws_connect('/rpc/token/{}'.format(ENCODED_TOKEN))
        payload = self.prepare_payload('return_more_than_one_value', [], 1)
        ws.write_message(payload)
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'spam',
            'next_frame': 1,
            'marker': 1
        })
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'ham',
            'next_frame': 1,
            'marker': 1
        })
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'eggs',
            'next_frame': 1,
            'marker': 1
        })
        response = yield ws.read_message()
        self.assertEqual(json_decode(response), {
            'result': '',
            'marker': 1
        })
        yield self.close(ws)


def main():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('shirow_test.log')
    logger.addHandler(handler)

    unittest.main()

if __name__ == '__main__':
    main()
