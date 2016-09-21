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

import os
import reprlib
from select import PIPE_BUF

from tornado.escape import json_encode


PIPE_BUF_LEN = len(str(PIPE_BUF))


class Response:
    def __init__(self, data):
        self._data = data
        self._data_len = len(data)
        self._start = 0

    def __iter__(self):
        while True:
            buffer_size = self._data[self._start:self._start + PIPE_BUF_LEN]
            if not buffer_size:
                return

            size = int(buffer_size)
            start = self._start + PIPE_BUF_LEN
            end = start + size
            self._start = end
            yield self._data[start:end]

            if self._data_len == end:
                return

    def __repr__(self):
        return 'Response({})'.format(reprlib.repr(self._data))


class Ret(Exception):
    def __init__(self, value=None):
        super(Ret, self).__init__()
        self.value = value


class Request:
    def __init__(self, fd, marker):
        self._fd = fd
        self._marker = marker

    #
    # Internal methods
    #
    def _get_error_response(self, message):
        response = {
            'error': message,
            'marker': self._marker,
        }
        return json_encode(response)

    def _get_len(self, data):
        data_len = len(data)
        return str(data_len).zfill(PIPE_BUF_LEN)

    def _get_successful_response(self, result, eod=True):
        response = {
            'eod': 1 if eod else 0,
            'marker': self._marker,
            'result': result,
        }
        return json_encode(response)

    def _slice_up(self, data):
        for i in range(0, len(data), PIPE_BUF):
            yield data[0 + i:PIPE_BUF + i]

    def _write(self, response):
        data = self._get_len(response) + response
        slices = []
        if len(data) > PIPE_BUF:
            slices.append(data[:PIPE_BUF])

            for i in self._slice_up(data[PIPE_BUF:]):
                slices.append(self._get_len(i) + i)

            data = ''.join(slices)

        os.write(self._fd, data.encode('utf8'))

    #
    # User visible methods
    #
    def ret(self, value):
        """Causes a remote procedure to exit and return the specified value to
        the RPC client. The return statement can be used instead.
        """
        self._write(self._get_successful_response(value))
        raise Ret()

    def ret_and_continue(self, value):
        """Causes a remote procedure to return the specified value to the RPC
        client. Unlike ret, the method doesn't cause the procedure to exit.
        """
        self._write(self._get_successful_response(value, False))

    def ret_error(self, message):
        self._write(self._get_error_response(message))

