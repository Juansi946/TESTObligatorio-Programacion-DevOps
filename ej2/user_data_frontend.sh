#!/bin/bash
# ======================================================================
# user_data_frontend.sh - arranque de la EC2 frontend (Nginx + React)
# ======================================================================
# Es una plantilla: deploy.py reemplaza los marcadores __NOMBRE__ (bucket,
# región e IP privada del backend) y manda el resultado como user data.
# AWS lo ejecuta como root, una sola vez, en el primer arranque.
#
# Los pasos 2 y 3 son el bloque "Frontend" del README de la app. Lo que
# agregué yo es la descarga desde S3 (paso 1).

# Si un comando falla, si uso una variable sin definir o si falla algo
# dentro de un pipe, el script se detiene
set -euo pipefail

# ---------- 1. Descargar los estáticos desde el bucket ----------
aws s3 cp "s3://__BUCKET__/web.tar.gz" /tmp/web.tar.gz --region __REGION__

# ---------- 2. Instalar Nginx y publicar los estáticos ----------
# Amazon Linux usa dnf. -y para que no pida confirmación (nadie la puede dar).
dnf install -y nginx
install -d -m 0755 /var/www/servicedesk
tar -xzf /tmp/web.tar.gz -C /var/www/servicedesk
# Borro cualquier configuración de ejemplo para que no compita con la mía
rm -f /etc/nginx/conf.d/*.conf

# ---------- 3. Configuración de Nginx ----------
# - Sirve los archivos de React y, para cualquier ruta que no sea un archivo
#   (/tickets, /equipo...), devuelve index.html para que React la resuelva.
# - Reenvía /api/, /health y /docs a la API, por la IP PRIVADA del backend.
#   Por eso el 8080 no está abierto a Internet: solo el frontend llega ahí.
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
# Valido la sintaxis antes de iniciar, y dejo Nginx habilitado e iniciado
nginx -t
systemctl enable --now nginx

# ---------- 4. Marca de "terminé" ----------
# deploy.py espera a que exista este archivo antes de hacer el chequeo
touch /var/lib/servicedesk-frontend-ready
