#!/bin/bash
# user_data_frontend.sh
# Arranque de la EC2 frontend (Nginx + React). Corre como root en el primer boot.
# Es una plantilla: deploy.py cambia los marcadores __NOMBRE__ por los valores reales.

# Corta el script ante cualquier error
set -euo pipefail

# 1. Descargar el frontend desde el bucket
aws s3 cp "s3://__BUCKET__/web.tar.gz" /tmp/web.tar.gz --region __REGION__

# 2. Instalar Nginx y dejar los archivos de React en su carpeta
dnf install -y nginx
install -d -m 0755 /var/www/servicedesk
tar -xzf /tmp/web.tar.gz -C /var/www/servicedesk
# Borra la configuración de ejemplo
rm -f /etc/nginx/conf.d/*.conf

# 3. Configuración de Nginx
# Sirve React y manda /api/, /health y /docs al backend por su IP privada.
# Cualquier otra ruta devuelve index.html para que la resuelva React.
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
# Valida la configuración y arranca Nginx
nginx -t
systemctl enable --now nginx

# 4. Aviso de que terminó (deploy.py espera este archivo)
touch /var/lib/servicedesk-frontend-ready
