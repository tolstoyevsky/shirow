/*
 * Copyright 2016 Maxim Karpinskiy <karpinski20@gmail.com>
 * Copyright 2016 Denis Mosolov <denismosolov@gmail.com>
 * Copyright 2016 Evgeny Golyshev <eugulixes@gmail.com>
 * Copyright 2020 Denis Gavrilyuk <karpa4o4@gmail.com>
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

const RETRIES_NUMBER = 5;

class Events {
    constructor () {
        this._callbacks = {};
    }

    on (ev, cb) {
        const callbacks = this._callbacks;

        if (!callbacks[ev]) {
            callbacks[ev] = [];
        }

        callbacks[ev].push(cb);
    }

    trigger (ev) {
        const args = Array.from(arguments);
        const callbacks = this._callbacks || (this._callbacks = {});

        if (typeof callbacks[ev] === 'undefined') {
            return this;
        }

        for (let i = 0; i < callbacks[ev].length; i++) {
            callbacks[ev][i].apply(this, args.slice(1));
        }
    }
}

class Shirow extends Events {
    constructor (wsHost) {
        super();

        if (typeof wsHost !== 'string' || !wsHost.startsWith('ws')) {
            throw new Error('The wsHost parameter must be started with the ws:// or wss:// URI scheme.');
        }

        this._attempts = 0;
        this._cached_res = {};
        this._call_number = 0;
        this._callbacks = {};
        this._do_not_reconnect = false;
        this._errors = {};
        this._queue = [];
        this._timeouts = {};
        this._ws_host = wsHost;

        this._connect();

        this.on('ready', () => {
            this._log('connection is established');
            this._queue.forEach(e => this._send(e));
            this._queue.length = 0;
        });
    }

    /* Internal methods. */

    _log (msg, tracelog) {
        console[tracelog ? 'trace' : 'log'](`Shirow: ${msg}`);
    }

    _registerCallback (callback, marker) {
        this._callbacks[marker] = this._callbacks[marker] || [];
        this._callbacks[marker].push(callback);
    }

    _registerTimeout (timeoutId, marker) {
        this._timeouts[marker] = timeoutId;
    }

    _registerError (fn, marker) {
        this._errors[marker] = fn;
    }

    /**
    * will be executed either on message event or after timeout
    */
    _unregister (marker) {
        delete this._callbacks[marker];
        delete this._errors[marker];
        clearTimeout(this._timeouts[marker]);
        delete this._timeouts[marker];
    }

    _connect () {
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

        this._shirow.onerror = () => {
            this.trigger('error');
        };

        this._shirow.onmessage = event => this._onmessage(JSON.parse(event.data));
    }

    _onmessage (json = {}) {
        const marker = json.marker;

        if (typeof json.result !== 'undefined') {
            let result = json.result;
            const cbs = this._callbacks[marker];

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

    _reconnect () {
        if (this._attempts < RETRIES_NUMBER) {
            const delay = this._attempts * this._attempts;

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

    _send (dataStr) {
        if (this._is_opened) {
            this._shirow.send(dataStr);
        } else {
            this._queue.push(dataStr);
        }
    }

    _diagnose (success, failure) {
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
        const httpHost = this._ws_host.replace(/^ws/, 'http');
        const xhr = new XMLHttpRequest();
        xhr.open('GET', httpHost);

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

    _emit (procedureName, force = false, ...parametersList) {
        const that = this;
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
            function_name: procedureName,
            parameters_list: parametersList
        };
        const requestNumber = this._call_number;
        const cacheKey = JSON.stringify(data);

        data.marker = requestNumber;
        data = JSON.stringify(data);

        // when force is set to true we don't cache the result
        if (force) {
            this._send(data);
        } else {
            if (!this._cached_res[cacheKey]) {
                this._send(data);
            } else {
                setTimeout(() => {
                    this._onmessage({
                        result: this._cached_res[cacheKey],
                        marker: requestNumber,
                        // all cached responses must be end of data
                        eod: 1
                    });
                });
            }
        }

        this._call_number += 1;

        return {
            then: function (fn) {
                const callback = function (res) {
                    if (!force) {
                        that._cached_res[cacheKey] = res;
                    }

                    return fn(res);
                };
                that._registerCallback(callback, requestNumber);
                return this;
            },
            timeout: function (time, callback) {
                const timeoutId = setTimeout(() => {
                    that._unregister(requestNumber);
                    return callback();
                }, time);
                that._registerTimeout(timeoutId, requestNumber);
                return this;
            },
            catch: function (fn) {
                that._registerError(fn, requestNumber);
                return this;
            }
        };
    }

    /* User visible methods. */

    disconnect () {
        if (!this._shirow) {
            return;
        }

        this._do_not_reconnect = true;
        this._shirow.close();
    }

    emit (procedureName, ...parametersList) {
        return this._emit(procedureName, false, ...parametersList);
    }

    emitForce (procedureName, ...parametersList) {
        return this._emit(procedureName, true, ...parametersList);
    }
}

export default Shirow;
