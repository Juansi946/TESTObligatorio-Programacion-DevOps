#!/bin/bash
# User data de la EC2 backend (API Go).
# Basado en el bloque "Backend" del README de la app. deploy.py reemplaza los
# marcadores con forma __NOMBRE__ antes de lanzar la instancia.
set -euo pipefail

# 1) Descargar los artefactos desde el bucket privado (la instancia usa LabInstanceProfile)
aws s3 cp "s3://__BUCKET__/servicedesk" /tmp/servicedesk --region __REGION__
aws s3 cp "s3://__BUCKET__/docs/" /tmp/docs/ --recursive --region __REGION__

# 2) Usuario de sistema sin login: la API no corre como root
useradd --system --home /opt/servicedesk --shell /sbin/nologin servicedesk || true
install -d -o servicedesk -g servicedesk -m 0750 /opt/servicedesk/uploads
install -o servicedesk -g servicedesk -m 0755 /tmp/servicedesk /opt/servicedesk/servicedesk
install -d -o servicedesk -g servicedesk -m 0755 /opt/servicedesk/docs
install -o servicedesk -g servicedesk -m 0644 /tmp/docs/index.html /tmp/docs/openapi.yaml /opt/servicedesk/docs/

# 3) Archivo de variables: JWT aleatorio y conexión TLS a RDS.
#    FRONTEND_ORIGIN queda pendiente: deploy.py lo completa por SSM cuando
#    el frontend ya tiene IP pública.
jwt_secret=$(openssl rand -hex 32)
printf '%s\n' \
    "DATABASE_URL=host=__ENDPOINT_RDS__ user=__RDS_USER__ password=__RDS_PASSWORD__ dbname=__RDS_DATABASE__ port=5432 sslmode=require" \
    "JWT_SECRET=${jwt_secret}" \
    'PORT=8080' \
    'FRONTEND_ORIGIN=http://PENDIENTE' > /opt/servicedesk/.env
chown servicedesk:servicedesk /opt/servicedesk/.env
chmod 0600 /opt/servicedesk/.env

# 4) Servicio systemd
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

# 5) Marca de "terminé" (el README la usa en el healthcheck pero su bloque no la crea)
touch /var/lib/servicedesk-backend-ready
