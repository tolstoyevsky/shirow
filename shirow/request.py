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

from tornado.escape import json_encode


class Ret(Exception):
    def __init__(self, value=None):
        super(Ret, self).__init__()
        self.value = value


class Request:
    def __init__(self, fd, marker):
        self._fd = fd
        self._history = []
        self._marker = marker

    def _get_response(self, result, next_frame=False):
        response = {'marker': self._marker, 'result': result}
        if next_frame:
            response['next_frame'] = 1
        return response

    def _write(self, response):
        json = json_encode(response)
        bytes_written = os.write(self._fd, json.encode('utf8'))
        self._history.append(bytes_written)

    def get_bytes_written(self):
        return self._history.pop()

    def ret(self, value):
        """Causes a remote procedure to exit and return the specified value to
        the RPC client. The return statement can be used instead.
        """
        self._write(self._get_response(value))
        raise Ret()

    def ret_and_continue(self, value):
        """Causes a remote procedure to return the specified value to the RPC
        client. Unlike ret, the method doesn't cause the procedure to exit.
        """
        self._write(self._get_response(value, True))

    def ret_error(self, message):
        response = {'marker': self._marker, 'error': message}
        self._write(response)

