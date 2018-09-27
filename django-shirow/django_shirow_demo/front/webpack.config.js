const path = require('path');
const node_modules_dir = path.join(__dirname, 'node_modules');

module.exports = {
    context: __dirname + '/authentication/static',

    entry: './demo',

    output: {
        path: __dirname + '/authentication/static/bundles',
        publicPath: '/authentication/static/bundles',
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
