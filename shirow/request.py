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

"""This module contains the implementation of the entity called request. When
an RPC client connects to an RPC server and invokes one of the available remote
procedures, the request is passed to the remote procedure. The request is
necessary to allow the remote procedure to "find" its client when returning the
result.
"""

from tornado.escape import json_encode


class Ret(Exception):
    """Exception raised when a remote procedure returns a value via
    `Request.ret`.
    """

    def __init__(self, value=None):
        super().__init__()
        self.value = value


class Request:
    """Base class for requests.

    The instance of the class is passed as the first argument to a remote
    procedure before invoking it.
    """

    def __init__(self, marker, callback):
        self._callback = callback
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

    def _get_successful_response(self, result, eod=True):
        response = {
            'eod': 1 if eod else 0,
            'marker': self._marker,
            'result': result,
        }
        return json_encode(response)

    #
    # User visible methods
    #
    def ret(self, value):
        """Causes a remote procedure to exit and return the specified value to
        the RPC client. The return statement can be used instead.
        """
        self._callback(self._get_successful_response(value))
        raise Ret()

    def ret_and_continue(self, value):
        """Causes a remote procedure to return the specified value to the RPC
        client. Unlike ret, the method doesn't cause the procedure to exit.
        """
        self._callback(self._get_successful_response(value, False))

    def ret_error(self, message):
        """Causes a remote procedure to exit and inform the the client that an
        error occurred.
        """
        self._callback(self._get_error_response(message))
        raise Ret()
