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

class Shirow extends Events {
    static get RETRIES_NUMBER() {
        return 5;
    }

    get RETRIES_NUMBER() {
        return this.constructor.RETRIES_NUMBER;
    }

    constructor(ws_host) {
        super();

        if (typeof ws_host !== 'string' || !ws_host.startsWith('ws')) {
            throw new Error('The ws_host parameter must be started with the ws:// or wss:// URI scheme.');
        }

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
        console[tracelog ? 'trace' : 'log'](`Shirow: ${msg}`);
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
        this._shirow = new WebSocket(this._ws_host);

        this._shirow.onopen = () => {
            this._attempts = 0;
            this._is_opened = true;
            this.trigger('ready');
        };

        this._shirow.onclose = () => {
            this._is_opened = false;

            /*
             * The WebSocket API doesn't provide any way to get response
             * headers. Thus, at the first attempt to reconnect to the RPC
             * server we have to send a simple HTTP GET request in order to
             * diagnose a problem.
             */
            if (this._attempts === 0) {
                this._diagnose(
                    this._reconnect.bind(this),
                    () => this._log('Authorization attempt failed')
                );
            } else {
                this._reconnect();
            }
        };

        this._shirow.onmessage = (event) => {
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
                throw json.error;
            }
        };
    }

    _reconnect() {
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
    }

    /*
     * Allows closing connection manually. It can be useful for debugging
     * purposes.
     */
    _disconnect() {
        if (!this._shirow) {
            return;
        }

        this._shirow.close();
    }

    _send(data_str) {
        if (this._is_opened) {
            this._shirow.send(data_str);
        } else {
            this._queue.push(data_str);
        }
    }

    _diagnose(success, failure) {
        if (this._is_diagnosed) {
            /*
             * It means that the diagnosing has been made before and the
             * current token is valid, but after a while connection was broken.
             */
            return success();
        }

        /*
         * Note that if the wss:// URI scheme is used, we will get https after
         * replacement.
         */
        let http_host = this._ws_host.replace(/^ws/, 'http');
        let xhr = new XMLHttpRequest();
        xhr.open('GET', http_host);

        success = success || function () {};
        failure = failure || function () {};

        xhr.onreadystatechange = () => {
            if (xhr.readyState === 4) {
                if (xhr.status === 401) {
                    failure();
                } else {
                    this._is_diagnosed = true;
                    success();
                }
            }
        };

        xhr.send();
    }

    /* User visible methods. */

    emit(procedure_name, ...parameters_list) {
        var that = this;
        /*
         * The Shirow client and server use so called markers to map a remote
         * procedure call with its return value. To call a remote procedure,
         * the Shirow client sends to the Shirow server the name of the procedure, a
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

export default Shirow;
