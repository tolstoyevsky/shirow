#!/usr/bin/env python3

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

import os.path
import base64
import uuid

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.options import options

from shirow.server import RPCServer, remote


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r'/rpc/token/([\w\.]+)', RPCHandler),
        ]
        settings = dict(
            cookie_secret=base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            template_path=os.path.join(os.path.dirname(__file__), './'),
            static_path=os.path.join(os.path.dirname(__file__), './'),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


class RPCHandler(RPCServer):
    @remote
    def say_hello(self, _request, name):
        return 'Hello, {}!'.format(name if name else 'Anonymous')


def main():
    # Note that in this particular case the parameters specified in the
    # application configuration file can be overridden by the command-line
    # parameters.
    tornado.options.parse_config_file(options.config_file)
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
