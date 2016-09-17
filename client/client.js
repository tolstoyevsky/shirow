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

const RETRIES_NUMBER = 5;

class Shirow extends Events {
    constructor(ws_host) {
        super();

        if (typeof ws_host !== 'string' || !ws_host.startsWith('ws')) {
            throw new Error('The ws_host parameter must be started with the ws:// or wss:// URI scheme.');
        }

        this._attempts = 0;
        this._cached_res = {};
        this._call_number = 0;
        this._callbacks = {};
        this._do_not_reconnect = false;
        this._errors = {};
        this._queue = [];
        this._timeouts = {};
        this._ws_host = ws_host;

        this._connect();

        this.on('ready', () => {
            this._log('connection is established');
            this._queue.forEach(e => this._send(e));
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

    _register_error(fn, marker) {
        this._errors[marker] = fn;
    }

    /**
    * will be executed either on message event or after timeout
    */
    _unregister(marker) {
        delete this._callbacks[marker];
        delete this._errors[marker];
        clearTimeout(this._timeouts[marker]);
        delete this._timeouts[marker];
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

            if (this._do_not_reconnect) {
                return;
            }

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

        this._shirow.onmessage = event => this._onmessage(JSON.parse(event.data));
    }

    _onmessage(json = {}) {
        let marker = json.marker;

        if (json.result) {
            let result = json.result;
            let cbs = this._callbacks[marker];

            if (cbs) {
                /* There can be more than one handler function. */
                cbs.forEach(cb => {
                    result = cb(result);
                });
            }
        } else {
            if (typeof this._errors[marker] === 'function') {
                this._errors[marker](json.error);
            } else {
                console.error(json.error);
            }
        }

        if (json.eod === 1) {
            this._unregister(marker);
        }
    }

    _reconnect() {
        if (this._attempts < RETRIES_NUMBER) {
            let delay = this._attempts * this._attempts;

            this._log(
                `connection failed, retrying in ${delay} seconds.`,
                true
            );

            setTimeout(() => this._connect(), delay * 1000);

            this._attempts += 1;

        } else {
            this._log(
                `connection failed after ${RETRIES_NUMBER} retries.`,
                true
            );
        }
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

    _emit(procedure_name, force=false, ...parameters_list) {
        let that = this;
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
        let data = {
            'function_name': procedure_name,
            'parameters_list': parameters_list
        };
        let request_number = this._call_number;
        let cache_key = JSON.stringify(data);

        data.marker = request_number;
        data = JSON.stringify(data);

        // when force is set to true we don't cache the result
        if (force) {
            this._send(data);
        } else {
            if (!this._cached_res[cache_key]) {
                this._send(data);
            } else {
                setTimeout(() => {
                    this._onmessage({
                        result: this._cached_res[cache_key],
                        marker: request_number
                    });
                });
            }
        }

        this._call_number += 1;

        return {
            then: function (fn) {
                let callback = function (res) {
                    if (!force) {
                        that._cached_res[cache_key] = res;
                    }

                    return fn(res);
                };
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
            },
            catch: function (fn) {
                that._register_error(fn, request_number);
                return this;
            },
        };
    }

    /* User visible methods. */

    disconnect() {
        if (!this._shirow) {
            return;
        }

        this._do_not_reconnect = true;
        this._shirow.close();
    }

    emit(procedure_name, ...parameters_list) {
        return this._emit(procedure_name, false, ...parameters_list);
    }

    emitForce(procedure_name, ...parameters_list) {
        return this._emit(procedure_name, true, ...parameters_list);
    }
}

export default Shirow;
