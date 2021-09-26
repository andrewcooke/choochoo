#!/bin/bash

rm -fr py/ch2/web/static/*.js*
rm -fr py/ch2/web/static/*.html
rm -fr py/ch2/web/static/*.png
rm -fr py/ch2/web/static/*.txt
rm -fr py/ch2/web/static/*.ico
pushd js >> /dev/null
npm install
npm run build
popd
cp -r js/build/* py/ch2/web/static
cp js/src/workers/writer.js py/ch2/web/static
touch py/ch2/web/static/__init__.py
touch py/ch2/web/static/static/__init__.py
touch py/ch2/web/static/static/js/__init__.py
