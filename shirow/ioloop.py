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

"""Utility code intended to simplify initializing the event loop. """

import asyncio

from tornado.platform.asyncio import AsyncIOMainLoop


class Singleton(type):
    """Metaclass which helps to create singletons. """
    instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.instances:
            singleton = super(Singleton, cls)
            cls.instances[cls] = singleton.__call__(*args, **kwargs)

        return cls.instances[cls]


class IOLoop(metaclass=Singleton):  # pylint: disable=too-few-public-methods
    """A singleton intended to create the event loop based on the AsyncIO Event
    Loop.
    """

    def __init__(self):
        self._io_loop = None
        AsyncIOMainLoop().install()

    def start(self, app, port):
        """Starts the event loop. """

        app.listen(port)
        self._io_loop = asyncio.get_event_loop()
        self._io_loop.run_forever()
