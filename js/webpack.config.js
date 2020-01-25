const webpack = require('webpack');
const resolve = require('path').resolve;

const config = {
    devtool: 'eval-source-map',
    entry: __dirname + '/src/index.jsx',
    output: {
        path: resolve('../py/ch2/web/static'),
        filename: 'bundle.js',
        publicPath: 'static/'
    },
    resolve: {
        extensions: ['.js', '.jsx', '.css']
    },
    module: {
        rules: [{
            test: /\.jsx?/,
            loader: 'babel-loader',
            exclude: /node_modules/
        }, {
            test: /\.css$/,
            loader: 'style-loader!css-loader?modules'
        }]
    }
};

module.exports = config;
