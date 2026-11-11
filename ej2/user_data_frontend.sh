#!/bin/bash
# User data de la EC2 frontend (Nginx + estáticos de React).
# Basado en el bloque "Frontend" del README de la app. deploy.py reemplaza los
# marcadores con forma __NOMBRE__ antes de lanzar la instancia.
set -euo pipefail

# 1) Descargar los estáticos desde el bucket privado
aws s3 cp "s3://__BUCKET__/web.tar.gz" /tmp/web.tar.gz --region __REGION__

# 2) Instalar Nginx y publicar los estáticos
dnf install -y nginx
install -d -m 0755 /var/www/servicedesk
tar -xzf /tmp/web.tar.gz -C /var/www/servicedesk
rm -f /etc/nginx/conf.d/*.conf

# 3) Virtual host: sirve React y manda /api/, /health y /docs al backend PRIVADO
cat > /etc/nginx/conf.d/servicedesk.conf <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/servicedesk;
    index index.html;
    client_max_body_size 12m;

    location /api/ {
        proxy_pass http://__IP_BACKEND__:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location = /health { proxy_pass http://__IP_BACKEND__:8080; }
    location /docs { proxy_pass http://__IP_BACKEND__:8080; }
    location / { try_files $uri $uri/ /index.html; }
}
EOF
nginx -t
systemctl enable --now nginx
touch /var/lib/servicedesk-frontend-ready
