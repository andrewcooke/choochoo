#!/bin/bash

# https://stackoverflow.com/a/49165016

PORT=8001

cat > nginx-startup.sh<<EOF

# https://trac.nginx.org/nginx/ticket/658
NAMESERVER=\`cat /etc/resolv.conf | grep "nameserver" | awk '{print \$2}' | tr '\n' ' '\`

cat > /etc/nginx/conf.d/proxy.conf <<EOF2
server {
  listen $PORT;
  location / {
      # https://stackoverflow.com/a/52319161
      resolver \$NAMESERVER valid=10s;
      proxy_pass http://ch2:$PORT;
      proxy_http_version 1.1;
      proxy_set_header Upgrade \\\$http_upgrade;
      proxy_set_header Connection 'upgrade';
      proxy_set_header Host \\\$host;
      proxy_cache_bypass \\\$http_upgrade;
  }
}
EOF2

echo '---------'
cat /etc/nginx/conf.d/proxy.conf
echo '---------'
nginx -g "daemon off;"
EOF

cat > dockerfile <<EOF
from nginx:1.19.0-alpine
workdir /
run rm /etc/nginx/conf.d/default.conf
copy ./nginx-startup.sh .
run chmod +x ./nginx-startup.sh
expose $PORT
cmd ./nginx-startup.sh
EOF
docker build --network=host --tag ngx -f dockerfile .

rm nginx-startup.sh
rm dockerfile
