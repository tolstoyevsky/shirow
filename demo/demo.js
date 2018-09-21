/*
 * Copyright 2016 Maxim Karpinskiy, Evgeny Golyshev. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

import RPCClient from '../client/client.js';

const token = 'mock_token'; // mock token (for testing only)
const client = new RPCClient('ws://localhost:8888/rpc/token/' + token);

client.on('ready', function () {
    $("#btn").click(function () {
        client.emit('say_hello', $("#inp").val()).then(data => {
            $("#res").text(data);
        });
    });
});
