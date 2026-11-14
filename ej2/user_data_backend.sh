#!/bin/bash
# ======================================================================
# user_data_backend.sh - arranque de la EC2 backend (API en Go)
# ======================================================================
# Es una plantilla: deploy.py reemplaza los marcadores __NOMBRE__ con los
# valores reales (bucket, región, endpoint de RDS, usuario, contraseña y
# nombre de la base) y manda el resultado como user data. AWS lo ejecuta
# como root, una sola vez, en el primer arranque de la instancia.
#
# Los pasos 2 a 4 son el bloque "Backend" del README de la app. Lo que
# agregué yo: la descarga desde S3 (paso 1), la copia de docs/ y la marca
# final (paso 5), que el README usa en su HealthCheck pero no crea.

# Si un comando falla, si uso una variable sin definir o si falla algo
# dentro de un pipe, el script se detiene (explicado en el README de la app)
set -euo pipefail

# ---------- 1. Descargar los artefactos desde el bucket ----------
# El bucket es privado. La instancia puede leerlo porque la creo con
# LabInstanceProfile, y la AWS CLI ya viene instalada en Amazon Linux 2023.
aws s3 cp "s3://__BUCKET__/servicedesk" /tmp/servicedesk --region __REGION__
aws s3 cp "s3://__BUCKET__/docs/" /tmp/docs/ --recursive --region __REGION__

# ---------- 2. Usuario del servicio y archivos ----------
# Creo un usuario de sistema sin login: la API no corre como root.
useradd --system --home /opt/servicedesk --shell /sbin/nologin servicedesk || true
# Carpeta de adjuntos de los tickets (solo el usuario del servicio puede entrar)
install -d -o servicedesk -g servicedesk -m 0750 /opt/servicedesk/uploads
# Binario de la API, con permiso de ejecución
install -o servicedesk -g servicedesk -m 0755 /tmp/servicedesk /opt/servicedesk/servicedesk
# La API sirve /docs leyendo docs/index.html y docs/openapi.yaml desde su
# carpeta de trabajo, por eso los copio a /opt/servicedesk/docs
install -d -o servicedesk -g servicedesk -m 0755 /opt/servicedesk/docs
install -o servicedesk -g servicedesk -m 0644 /tmp/docs/index.html /tmp/docs/openapi.yaml /opt/servicedesk/docs/

# ---------- 3. Variables de la API (/opt/servicedesk/.env) ----------
# - DATABASE_URL: conexión a RDS con TLS (sslmode=require).
# - JWT_SECRET: lo genero acá con openssl, así es aleatorio y no queda
#   escrito en ningún archivo del repositorio.
# - FRONTEND_ORIGIN: todavía no sé la IP pública del frontend (se crea
#   después), así que dejo PENDIENTE y deploy.py lo completa por SSM.
jwt_secret=$(openssl rand -hex 32)
printf '%s\n' \
    "DATABASE_URL=host=__ENDPOINT_RDS__ user=__RDS_USER__ password=__RDS_PASSWORD__ dbname=__RDS_DATABASE__ port=5432 sslmode=require" \
    "JWT_SECRET=${jwt_secret}" \
    'PORT=8080' \
    'FRONTEND_ORIGIN=http://PENDIENTE' > /opt/servicedesk/.env
# Solo el usuario del servicio puede leer el archivo, porque tiene secretos
chown servicedesk:servicedesk /opt/servicedesk/.env
chmod 0600 /opt/servicedesk/.env

# ---------- 4. Servicio systemd ----------
# La unidad carga el .env, ejecuta la API con el usuario servicedesk, la
# reinicia si se cae y la deja con permisos mínimos: sin escalar privilegios,
# con /tmp propio y con el disco en solo lectura salvo la carpeta uploads/.
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
# Registro la unidad nueva, la habilito para cada arranque y la inicio ya
systemctl daemon-reload
systemctl enable --now servicedesk

# ---------- 5. Marca de "terminé" ----------
# deploy.py espera a que exista este archivo antes de hacer los chequeos
touch /var/lib/servicedesk-backend-ready
