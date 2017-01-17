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

import asyncio

from tornado import gen
from tornado.ioloop import IOLoop


class SubProcProtocol(asyncio.SubprocessProtocol):
    def __init__(self, exit_future):
        self.exit_future = exit_future
        self.output = bytearray()

    def pipe_data_received(self, fd, data):
        self.output.extend(data)

    def process_exited(self):
        self.exit_future.set_result(True)


@gen.coroutine
def run(command_line):
    loop = IOLoop.current().asyncio_loop
    exit_future = asyncio.Future(loop=loop)

    # Create the subprocess controlled by the protocol SubProcProtocol,
    # redirect the standard output into a pipe
    proc = loop.subprocess_exec(lambda: SubProcProtocol(exit_future),
                                *command_line,
                                stdin=None, stderr=None)
    transport, protocol = yield from proc

    # Wait for the subprocess exit using the process_exited() method
    # of the protocol
    yield from exit_future

    transport.close()  # close the stdout pipe

    return bytes(protocol.output)
