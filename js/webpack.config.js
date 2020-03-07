const webpack = require('webpack');
const resolve = require('path').resolve;
const CompressionPlugin = require('compression-webpack-plugin');

module.exports = {
    devtool: 'eval-source-map',
    entry: {
	bundle: __dirname + '/src/index.jsx',
	writer: __dirname + '/src/workers/writer.jsx'
    },
    output: {
	path: resolve('../py/ch2/web/static'),
	filename: '[name].js',
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
	}],
    },
    plugins: [new CompressionPlugin()],
};
