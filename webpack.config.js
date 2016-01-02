const path = require('path');
const node_modules_dir = path.join(__dirname, 'node_modules');

module.exports = {
    context: __dirname + '/static',

    entry: './example',

    output: {
        path: __dirname + '/static/bundles',
        publicPath: '/static/bundles',
        filename: '[name].js',
    },

    devtool: 'cheap-source-map',

    resolve: {
        root: path.resolve('./static'),
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
