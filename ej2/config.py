# config.py
# Parámetros compartidos por deploy.py y destroy.py.
# Todo lo que hay que cambiar para otra cuenta o entorno se cambia acá.

REGION = 'us-east-1'   # el Learner Lab trabaja en us-east-1

# Tags que se agregan a todos los recursos (identificar, filtrar, costos)
TAGS = [
    {'Key': 'Proyecto', 'Value': 'obligatorio-devops'},
    {'Key': 'Cliente', 'Value': 'banco-centralis'},
    {'Key': 'Ambiente', 'Value': 'produccion'},
]

# ---------- S3 ----------
# El nombre de un bucket es único en TODO AWS: cambialo por uno propio
BUCKET = 'servicedesk-artefactos-grupo-juan-2026'
CARPETA_ARTEFACTOS = 'artifacts'   # relativa a la carpeta ej2/ (está en .gitignore)
ARTEFACTOS = [
    'servicedesk',          # binario de la API (backend)
    'web.tar.gz',           # estáticos de React (frontend)
    'docs/index.html',      # documentación que sirve /docs
    'docs/openapi.yaml',
]

# ---------- Contraseña de la base ----------
# Se lee de esta variable de entorno (como en el ejercicio 9 de los Labs)
VARIABLE_PASSWORD = 'RDS_ADMIN_PASSWORD'
# y se guarda cifrada en SSM Parameter Store (como en el ejercicio 10)
PARAM_DB_PASSWORD = '/servicedesk/db/password'

# ---------- Security groups ----------
SG_FRONTEND = 'servicedesk-sg-frontend'
SG_BACKEND = 'servicedesk-sg-backend'
SG_RDS = 'servicedesk-sg-rds'

# ---------- RDS ----------
DB_IDENTIFIER = 'servicedesk-db'
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

# ---------- Verificación ----------
# Usuario administrador que crea la app al inicializar la base (README de la app).
# Su contraseña NO va en el código: se lee de esta variable de entorno.
ADMIN_EMAIL = 'admin@servicedesk.local'
VARIABLE_ADMIN_PASSWORD = 'APP_ADMIN_PASSWORD'
