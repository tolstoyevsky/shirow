var FirmwareBuild = FirmwareBuild || {};

(function(exports) {
    'use strict';

    exports.Events = function() {
        this.bind = function(ev, cb) {
            var callbacks = (this.callbacks || (this.callbacks = {}));
            (callbacks[ev] || (callbacks[ev] = [])).push(cb);
        };

        this.trigger = function(ev) {
            var args = [].slice.call(arguments)
              , callbacks = (this.callbacks || (this.callbacks = {}))
              , i = 0;

            if (typeof callbacks[ev] === 'undefined')
                return this;

            for (; i < callbacks[ev].length; i++)
                callbacks[ev][i].apply(this, args.slice(1));
        };
    };

    exports.RPCClient = function(ws_address) {
        var _callbacks_list = {}
          , _log
          , _opened = false
          , _register_callback
          , _request_number = 0
          , _rpc = new WebSocket(ws_address);

        _rpc.onopen = (event) => {
            _log('opened!');
            _opened = true;
            this.trigger('onready');
        };

        _rpc.onclose = function(event) {
            _log('closed!');
            _opened = false;
        };

        _rpc.onmessage = function(event) {
            var json = JSON.parse(event.data)

              , cb
              , n
              , result;

            if ('result' in json) {
                n = json['n'];
                result = json['result'];

                cb = _callbacks_list[n];
                cb(result);
                delete cb[n];
            } else
                throw json['error']
        }

        _log = function(message) {
            console.log(`RPCClient: ${message}`)
        };

        _register_callback = function(callback, n) {
            _callbacks_list[n] = callback;
        };

        this.exec = function(procedure_name, parameters_list, callback) {
            var data;
            if (_opened) {
                data = {
                    'function_name': procedure_name,
                    'parameters_list': parameters_list,
                    'n': _request_number
                };
                _rpc.send(JSON.stringify(data));

                _register_callback(callback, _request_number);
                _request_number++;
            } else
                _log('connection with the RPC server is not established!');
        };
    };

    exports.RPCClient.prototype = new exports.Events();
}(FirmwareBuild));
