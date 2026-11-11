# config.py
# Parámetros del despliegue (los usa deploy.py).
# Todo lo que hay que cambiar para otra cuenta o entorno se cambia acá.

import secrets

# Sufijo aleatorio: varios nombres de AWS no se pueden repetir (el bucket es único en
# TODO AWS), así que cada ejecución usa un nombre distinto y no choca con nadie.
SUFIJO = secrets.token_hex(4)

REGION = 'us-east-1'   # el Learner Lab trabaja en us-east-1

# Tags que se agregan a todos los recursos (identificar, filtrar, costos)
TAGS = [
    {'Key': 'Proyecto', 'Value': 'obligatorio-devops'},
    {'Key': 'Cliente', 'Value': 'banco-centralis'},
    {'Key': 'Ambiente', 'Value': 'produccion'},
]

# ---------- S3 ----------
# El nombre de un bucket es único en TODO AWS: por eso lleva el sufijo aleatorio
BUCKET = f'servicedesk-artefactos-{SUFIJO}'
CARPETA_ARTEFACTOS = 'artifacts'   # dentro de la carpeta ej2/ (está en .gitignore)
ARTEFACTOS = [
    'servicedesk',          # binario de la API (backend)
    'web.tar.gz',           # estáticos de React (frontend)
    'docs/index.html',      # documentación que sirve /docs
    'docs/openapi.yaml',
]

# ---------- Contraseña de la base ----------
# Se lee de esta variable de entorno (como en el ejercicio 9 de los Labs)
VARIABLE_PASSWORD = 'RDS_ADMIN_PASSWORD'

# ---------- Security groups ----------
SG_FRONTEND = f'servicedesk-sg-frontend-{SUFIJO}'
SG_BACKEND = f'servicedesk-sg-backend-{SUFIJO}'
SG_RDS = f'servicedesk-sg-rds-{SUFIJO}'

# ---------- RDS ----------
DB_IDENTIFIER = f'servicedesk-db-{SUFIJO}'
DB_NAME = 'servicedesk'
DB_USER = 'servicedesk_admin'
DB_INSTANCE_CLASS = 'db.t3.micro'
DB_ENGINE = 'postgres'
DB_ENGINE_VERSION = '16'          # el README de la app pide PostgreSQL 16
DB_STORAGE_GB = 20

# ---------- EC2 ----------
INSTANCE_TYPE = 't3.micro'
INSTANCE_PROFILE = 'LabInstanceProfile'   # perfil del rol LabRole (ejercicios 6 y 12)
# Parámetro público con la última AMI de Amazon Linux 2023 (ejercicio 12)
AMI_PARAMETER = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
NOMBRE_BACKEND = 'servicedesk-backend'
NOMBRE_FRONTEND = 'servicedesk-frontend'
