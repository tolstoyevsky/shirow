const path = require('path');
const node_modules_dir = path.join(__dirname, 'node_modules');

module.exports = {
    context: __dirname + '/demo',

    entry: './demo',

    output: {
        path: __dirname + '/demo/bundles',
        publicPath: '/demo/bundles',
        filename: '[name].js',
    },

    devtool: 'cheap-source-map',

    resolve: {
        root: path.resolve('./demo'),
        modulesDirectories: [node_modules_dir],
        extensions: ['', '.js'],
    },

    resolveLoader: {
        modulesDirectories: [node_modules_dir],
        moduleTemplates: ['*-loader', '*'],
        extensions: ['', '.js', '.css']
    },

    module: {
        loaders: [
            { test: /\.js$/, loader: 'babel?presets[]=es2015' },
        ],
    }
};
