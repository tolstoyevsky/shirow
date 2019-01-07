# Copyright 2018 Evgeny Golyshev. All Rights Reserved.
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

"""Miscellaneous utility functions. """

from subprocess import PIPE

from tornado import gen
from tornado.process import Subprocess


@gen.coroutine
def execute_async(command_line, env=None):
    """Executes the specified command line asynchronously. """

    process = Subprocess(command_line, env=env, stdout=PIPE, stderr=PIPE)
    ret = yield process.wait_for_exit(raise_error=False)
    out, err = process.stdout.read(), process.stderr.read()  # pylint: disable=no-member
    process.stdout.close()
    process.stderr.close()
    return ret, out, err
