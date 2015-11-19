(function() {
    var client = new FirmwareBuild.RPCClient('ws://localhost:8888/rpc');

    client.bind('onready', function() {
        client.exec('get_packages_list', [1, 100], function(data) {
            console.log(data);
        });
        client.exec('get_packages_list', [2, 100], function(data) {
            console.log(data);
        });
    });
}());