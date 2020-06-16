# use --cache with buildkit to enable pip cache
from python:3.8.3-slim-buster
workdir /tmp
run apt-get update
run apt-get -y install \
    sqlite3 libsqlite3-dev \
    libpq-dev gcc \
    emacs
copy requirements.txt /tmp
run  \
    pip install --upgrade pip && \
    pip install wheel && \
    pip install -r requirements.txt
copy py /app
workdir /app    
run pip install .
expose 8000 8001
cmd ch2 --dev --base /data web service \
    --sqlite \
    --web-bind choochoo --jupyter-bind choochoo --proxy-bind 'localhost'
