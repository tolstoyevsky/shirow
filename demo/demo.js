import RPCClient from '../client/client.js';

var client = new RPCClient('ws://localhost:8888/rpc');

client.on('ready', function() {
    client.emit('get_packages_list', 1, 100).then(data => {
        console.log(data);
    });

    client.emit('get_packages_list', 2, 100).then(data => {
        console.log(data);
    });
});
