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
        this._callbacks = {};
        this._queue = [];
        this._request_number = 0;
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

    _register_callback(callback, n) {
        this._callbacks[n] = this._callbacks[n] || [];
        this._callbacks[n].push(callback);
    }

    _register_timeout(timeoutId, n) {
        this._timeouts[n] = timeoutId;
    }

    /**
    * will be executed either on message event or after timeout
    */
    _unregister(n) {
        delete this._callbacks[n];
        clearTimeout(this._timeouts[n]);
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
                let n = json.n;
                let result = json.result;
                let cbs = this._callbacks[n];

                if (cbs) {
                    cbs.forEach((cb) => {
                        result = cb(result);
                    });
                }

                this._unregister(n);
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
        var data = {
            'function_name': procedure_name,
            'parameters_list': parameters_list,
            'n': this._request_number
        };
        var request_number = this._request_number;

        this._send(JSON.stringify(data));
        this._request_number += 1;

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
