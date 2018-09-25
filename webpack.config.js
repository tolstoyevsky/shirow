const path = require('path')
const nodeModulesDir = path.join(__dirname, 'node_modules')

module.exports = {
  context: path.join(__dirname, '/demo'),

  entry: './demo',

  output: {
    path: path.join(__dirname, '/demo/bundles'),
    publicPath: '/demo/bundles',
    filename: '[name].js'
  },

  devtool: 'cheap-source-map',

  resolve: {
    root: path.resolve('./demo'),
    modulesDirectories: [nodeModulesDir],
    extensions: ['', '.js']
  },

  resolveLoader: {
    modulesDirectories: [nodeModulesDir],
    moduleTemplates: ['*-loader', '*'],
    extensions: ['', '.js', '.css']
  },

  module: {
    loaders: [
      { test: /\.js$/, loader: 'babel?presets[]=es2015' }
    ]
  }
}
