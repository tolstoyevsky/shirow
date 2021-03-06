# Copyright 2018-2020 Evgeny Golyshev. All Rights Reserved.
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


def check_number_of_args(method, params):
    """Checks if the number of actual arguments passed to a remote procedure
    matches the number of formal parameters of the remote procedure (except
    self and request).
    """

    min_args, max_args = method.arguments_range
    if (max_args - 2) >= len(params) >= (min_args - 2):
        return True

    return False
