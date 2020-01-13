#!/bin/bash

# https://www.valentinog.com/blog/babel/
# https://itnext.io/a-template-for-creating-a-full-stack-web-application-with-flask-npm-webpack-and-reactjs-be2294b111bd

# clean directory
rm -fr js
mkdir js
pushd js

# npm manages the js packages
npm init -y

# webpack builds a single file for loading in the browser
npm i webpack --save-dev
npm i webpack-cli --save-dev
sed -ie '$d' package.json
sed -ie '$d' package.json
cat >> package.json << EOF
  },
  "scripts": {
    "build": "webpack --mode production"
  }
}
EOF

# babel transcompiles jsx to js
npm i @babel/core babel-loader @babel/preset-env @babel/preset-react --save-dev
cat > .babelrc << EOF
{
  "presets": ["@babel/preset-env", "@babel/preset-react"]
}
EOF

# tell webpack to call bable
cat > webpack.config.js << EOF
module.exports = {
  module: {
    rules: [
      {
	test: /\.(js|jsx)$/,
	exclude: /node_modules/,
	use: {
	  loader: "babel-loader"
	}
      }
    ]
  }
};
EOF

# react is the js library we will use on the client
npm i react react-dom --save-dev

