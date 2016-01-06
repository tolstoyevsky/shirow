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

import Events from 'cusdeb-utils';

class RPCClient extends Events {
    static get RETRIES_NUMBER() {
        return 5;
    }

    get RETRIES_NUMBER() {
        return this.constructor.RETRIES_NUMBER;
    }

    constructor(ws_host) {
        super();

        this._attempts = 0;
        this._call_number = 0;
        this._callbacks = {};
        this._queue = [];
        this._timeouts = {};
        this._ws_host = ws_host;

        this._connect();

        this.on('ready', () => {
            this._log('connection is established');
            this._queue.forEach((e) => {
                this._send(e);
            });

            this._queue.length = 0;
        });
    }

    /* Internal methods. */

    _log(msg, tracelog) {
        console[tracelog ? 'trace' : 'log'](`RPCClient: ${msg}`);
    }

    _register_callback(callback, marker) {
        this._callbacks[marker] = this._callbacks[marker] || [];
        this._callbacks[marker].push(callback);
    }

    _register_timeout(timeoutId, marker) {
        this._timeouts[marker] = timeoutId;
    }

    /**
    * will be executed either on message event or after timeout
    */
    _unregister(marker) {
        delete this._callbacks[marker];
        clearTimeout(this._timeouts[marker]);
    }

    _connect() {
        this._rpc = new WebSocket(this._ws_host);

        this._rpc.onopen = () => {
            this._attempts = 0;
            this._is_opened = true;
            this.trigger('ready');
        };

        this._rpc.onclose = () => {
            this._is_opened = false;

            if (this._attempts < this.RETRIES_NUMBER) {
                var delay = this._attempts * this._attempts;

                this._log(
                    `connection failed, retrying in ${delay} seconds.`,
                    true
                );

                setTimeout(() => {
                    this._connect();
                }, delay * 1000);

                this._attempts += 1;

            } else {
                this._log(
                    `connection failed after ${this.RETRIES_NUMBER} retries.`,
                    true
                );
            }
        };

        this._rpc.onmessage = (event) => {
            var json = JSON.parse(event.data);

            if (json.result) {
                let marker = json.marker;
                let result = json.result;
                let cbs = this._callbacks[marker];

                if (cbs) {
                    /* There can be more than one handler function. */
                    cbs.forEach((cb) => {
                        result = cb(result);
                    });
                }

                this._unregister(marker);
            } else {
                throw json.error
            }
        }
    }

    _send(data_str) {
        if (this._is_opened) {
            this._rpc.send(data_str);
        } else {
            this._queue.push(data_str);
        }
    }

    /* User visible methods. */

    emit(procedure_name, ...parameters_list) {
        var that = this;
        /*
         * The RPC client and server use so called markers to map a remote
         * procedure call with its return value. To call a remote procedure,
         * the RPC client sends to the RPC server the name of the procedure, a
         * list of its input parameters and the marker associated with it. When
         * the procedure is ready to return a result, the server sends to the
         * client the return value and the marker. Then, using the marker, the
         * client is able to call the corresponding handler function. The call
         * number is used as a marker.
         */
        var data = {
            'function_name': procedure_name,
            'parameters_list': parameters_list,
            'marker': this._call_number
        };
        var request_number = this._call_number;

        this._send(JSON.stringify(data));
        this._call_number += 1;

        return {
            then: function (callback) {
                that._register_callback(callback, request_number);
                return this;
            },
            timeout: function (time, callback) {
                let timeoutId = setTimeout(() => {
                    that._unregister(request_number);
                    return callback();
                }, time);
                that._register_timeout(timeoutId, request_number);
                return this;
            }
        };
    }
}

export default RPCClient;
