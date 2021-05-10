# Copyright 2016-2020 Evgeny Golyshev. All Rights Reserved.
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

"""This module contains the Shirow tests. """

import datetime
import logging
import os
import pty
from asyncio import Future

import jwt
from tornado import gen
from tornado.escape import json_decode, json_encode
from tornado.ioloop import IOLoop
from tornado.options import options
from tornado.test.util import unittest
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application
from tornado.websocket import websocket_connect

from shirow.server import RPCServer, MOCK_TOKEN, TOKEN_PATTERN, remote

TOKEN_ALGORITHM_ENCODING = 'HS256'

TOKEN_KEY = 'secret'

USER_ID = 1

ENCODED_TOKEN = jwt.encode({'user_id': USER_ID, 'ip': '127.0.0.1'}, TOKEN_KEY,
                           algorithm=TOKEN_ALGORITHM_ENCODING).decode('utf8')

EXPIRED_ENCODED_TOKEN = jwt.encode(
    {'exp': datetime.datetime(1983, 2, 25).timestamp(), 'user_id': USER_ID, 'ip': '127.0.0.1'},
    TOKEN_KEY, algorithm=TOKEN_ALGORITHM_ENCODING
).decode('utf8')


def prepare_payload(procedure_name, parameters_list, marker):
    """Prepares a valid payload for use in the test cases. """

    data = {
        'function_name': procedure_name,
        'parameters_list': parameters_list,
        'marker': marker
    }
    return json_encode(data)


class MockRPCServer(RPCServer):  # pylint: disable=abstract-method
    """An RPC server based on Shirow used for the testing purposes. """

    def initialize(self, close_future, compression_options=None):
        self.close_future = close_future  # pylint: disable=attribute-defined-outside-init
        self.compression_options = compression_options  # pylint: disable=attribute-defined-outside-init

    def get_compression_options(self):
        return self.compression_options

    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))

    @remote
    async def add(self, _request, op_a, op_b):
        return op_a + op_b

    @remote
    async def div_by_zero(self, _request):
        1 / 0  # pylint: disable=pointless-statement

    @remote
    async def echo_via_ret_method(self, request, message):
        request.ret(message)

    @remote
    async def echo_via_return_statement(self, _request, message):
        return message

    @remote
    async def read_from_fd(self, request, master_fd):
        def handler(*_args, **_kwargs):
            res = os.read(master_fd, 65536)
            if res == b'qux\r\n':
                request.ret(res.decode('utf8'))

            request.ret_and_continue(res.decode('utf8'))

        self.io_loop.add_handler(master_fd, handler, self.io_loop.READ)

    @remote
    async def return_more_than_one_value(self, request):
        request.ret_and_continue('spam')
        request.ret_and_continue('ham')
        request.ret_and_continue('eggs')

    @remote
    async def say_hello(self, _request, name='Shirow'):
        return f'Hello {name}!'


class WebSocketBaseTestCase(AsyncHTTPTestCase):  # pylint: disable=abstract-method
    """A test case that starts up a WebSocket server. """

    def setUp(self):
        super().setUp()

        IOLoop.configure('tornado.platform.asyncio.AsyncIOLoop')
        self.io_loop = IOLoop.current()

    async def ws_connect(self, path, compression_options=None):
        ws_conn = await websocket_connect(f'ws://127.0.0.1:{self.get_http_port()}{path}',
                                          compression_options=compression_options)
        return ws_conn

    async def close(self, ws_conn):
        """Close a websocket connection and wait for the server side.

        If we don't wait here, there are sometimes leak warnings in the
        tests.
        """
        ws_conn.close()
        await self.close_future  # pylint: disable=no-member


class RPCServerTest(WebSocketBaseTestCase):
    """Tests various scenarios for an RPC server based on Shirow. """

    def get_app(self):
        self.close_future = Future()
        options.token_algorithm = TOKEN_ALGORITHM_ENCODING
        options.token_key = TOKEN_KEY
        return Application([
            ('/rpc', MockRPCServer,
             dict(close_future=self.close_future)),
            ('/rpc/token/' + TOKEN_PATTERN, MockRPCServer,
             dict(close_future=self.close_future)),
        ])

    def test_tokenless_request(self):
        response = self.fetch('/rpc')
        self.assertEqual(response.code, 401)

    def test_passing_expired_token(self):
        response = self.fetch(f'/rpc/token/{EXPIRED_ENCODED_TOKEN}')
        self.assertEqual(response.code, 401)

    def test_passing_non_existent_token(self):
        response = self.fetch('/rpc/token/some.non.existent.token')
        self.assertEqual(response.code, 401)

    def test_using_mock_token_key(self):
        options.allow_mock_token = True
        headers = {
            'Connection': 'Upgrade',
            'Upgrade': 'websocket'
        }
        response = self.fetch('/rpc/token/' + MOCK_TOKEN, headers=headers)
        self.assertEqual(response.code, 426)  # Upgrade Required

    def test_using_none_token_key(self):
        options.token_key = None
        response = self.fetch(f'/rpc/token/{ENCODED_TOKEN}')
        self.assertEqual(response.code, 500)

    def test_using_wrong_token_key(self):
        options.token_key = 'wrong_' + TOKEN_KEY
        response = self.fetch(f'/rpc/token/{ENCODED_TOKEN}')
        self.assertEqual(response.code, 401)  # decode error

    @gen_test
    async def test_using_ret_method_to_return_value(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        payload = prepare_payload('echo_via_ret_method', ['Hello!'], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello!',
            'marker': 1,
            'eod': 1,
        })
        await self.close(ws_conn)

    @gen_test
    async def test_using_return_statement_to_return_value(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        payload = prepare_payload('echo_via_return_statement', ['Hello!'], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello!',
            'marker': 1,
            'eod': 1,
        })
        await self.close(ws_conn)

    @gen_test
    async def test_calling_non_existent_function(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        payload = prepare_payload('non_existent_function', [], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'the non_existent_function function is undefined',
            'marker': 1
        })
        await self.close(ws_conn)

    @gen_test
    async def test_mismatching_parameters(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        # less than is required
        payload = prepare_payload('add', [1], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'number of arguments mismatch in the add function call',
            'marker': 1
        })
        # more than is required
        payload = prepare_payload('add', [1, 3, 5], 2)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'number of arguments mismatch in the add function call',
            'marker': 2
        })

        payload = prepare_payload('add', [1, 3], 3)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 4,
            'marker': 3,
            'eod': 1,
        })
        await self.close(ws_conn)

    @gen_test
    async def test_handling_errors_in_remote_procedures(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        payload = prepare_payload('div_by_zero', [], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'error': 'an error occurred while executing the function div_by_zero',
            'marker': 1
        })
        await self.close(ws_conn)

    @gen_test
    async def test_default_parameters(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        payload = prepare_payload('say_hello', [], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello Shirow!',
            'marker': 1,
            'eod': 1,
        })
        payload = prepare_payload('say_hello', ['Norris'], 2)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'Hello Norris!',
            'marker': 2,
            'eod': 1,
        })
        await self.close(ws_conn)

    @gen_test
    async def test_returning_more_than_one_value(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')
        payload = prepare_payload('return_more_than_one_value', [], 1)
        ws_conn.write_message(payload)
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'spam',
            'marker': 1,
            'eod': 0,
        })
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'ham',
            'marker': 1,
            'eod': 0,
        })
        response = await ws_conn.read_message()
        self.assertEqual(json_decode(response), {
            'result': 'eggs',
            'marker': 1,
            'eod': 0,
        })
        await self.close(ws_conn)

    @gen_test
    async def test_reading_from_fd(self):
        ws_conn = await self.ws_connect(f'/rpc/token/{ENCODED_TOKEN}')

        pid, master_fd = pty.fork()
        if pid == 0:  # child
            script = (
                'from time import sleep\n'
                'for i in ["foo", "bar", "baz", "qux"]: print(i); sleep(0.5)'
            )
            command_line = ['python3', '-c', script]
            os.execvp(command_line[0], command_line)
        else:  # parent
            payload = prepare_payload('read_from_fd', [master_fd], 1)
            ws_conn.write_message(payload)
            response = await ws_conn.read_message()
            self.assertEqual(json_decode(response), {
                'result': 'foo\r\n',
                'marker': 1,
                'eod': 0,
            })
            response = await ws_conn.read_message()
            self.assertEqual(json_decode(response), {
                'result': 'bar\r\n',
                'marker': 1,
                'eod': 0,
            })
            response = await ws_conn.read_message()
            self.assertEqual(json_decode(response), {
                'result': 'baz\r\n',
                'eod': 0,
                'marker': 1
            })
            response = await ws_conn.read_message()
            self.assertEqual(json_decode(response), {
                'result': 'qux\r\n',
                'marker': 1,
                'eod': 1,
            })

            await self.close(ws_conn)


def main():
    """The main entry point. """

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('shirow_test.log')
    logger.addHandler(handler)

    unittest.main()


if __name__ == '__main__':
    main()
