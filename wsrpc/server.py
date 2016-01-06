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

import tornado
from tornado.escape import json_decode, json_encode


class RPCServer(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, application, request,
                                                    **kwargs)
        self.remote_functions = []
        for method in dir(self):
            if method.endswith('__remote'):
                self.remote_functions.append(method)

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
