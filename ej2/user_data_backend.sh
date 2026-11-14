#!/bin/bash
# user_data_backend.sh
# Arranque de la EC2 backend (API en Go). Corre como root en el primer boot.
# Es una plantilla: deploy.py cambia los marcadores __NOMBRE__ por los valores reales.

# Corta el script ante cualquier error
set -euo pipefail

# 1. Descargar el binario y la documentación desde el bucket
aws s3 cp "s3://__BUCKET__/servicedesk" /tmp/servicedesk --region __REGION__
aws s3 cp "s3://__BUCKET__/docs/" /tmp/docs/ --recursive --region __REGION__

# 2. Usuario sin login para que la API no corra como root
useradd --system --home /opt/servicedesk --shell /sbin/nologin servicedesk || true
# Carpeta para los adjuntos de los tickets
install -d -o servicedesk -g servicedesk -m 0750 /opt/servicedesk/uploads
# Binario de la API
install -o servicedesk -g servicedesk -m 0755 /tmp/servicedesk /opt/servicedesk/servicedesk
# Archivos que muestra la API en /docs
install -d -o servicedesk -g servicedesk -m 0755 /opt/servicedesk/docs
install -o servicedesk -g servicedesk -m 0644 /tmp/docs/index.html /tmp/docs/openapi.yaml /opt/servicedesk/docs/

# 3. Variables de la API
# JWT_SECRET se genera al azar acá. FRONTEND_ORIGIN queda pendiente
# porque el frontend todavía no existe; después lo completa deploy.py.
jwt_secret=$(openssl rand -hex 32)
printf '%s\n' \
    "DATABASE_URL=host=__ENDPOINT_RDS__ user=__RDS_USER__ password=__RDS_PASSWORD__ dbname=__RDS_DATABASE__ port=5432 sslmode=require" \
    "JWT_SECRET=${jwt_secret}" \
    'PORT=8080' \
    'FRONTEND_ORIGIN=http://PENDIENTE' > /opt/servicedesk/.env
# Tiene secretos: solo lo lee el usuario del servicio
chown servicedesk:servicedesk /opt/servicedesk/.env
chmod 0600 /opt/servicedesk/.env

# 4. Servicio de systemd para la API, con permisos mínimos
cat > /etc/systemd/system/servicedesk.service <<'EOF'
[Unit]
Description=ServiceDesk API
After=network-online.target

[Service]
User=servicedesk
Group=servicedesk
WorkingDirectory=/opt/servicedesk
EnvironmentFile=/opt/servicedesk/.env
ExecStart=/opt/servicedesk/servicedesk
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/servicedesk/uploads

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now servicedesk

# 5. Aviso de que terminó (deploy.py espera este archivo)
touch /var/lib/servicedesk-backend-ready
