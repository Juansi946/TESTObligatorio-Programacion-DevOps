#!/usr/bin/env python3
# deploy.py
# Despliega ServiceDesk (la app de tickets del Banco Centralis) en AWS con Boto3.
#
#   Internet --80--> EC2 frontend (Nginx) --8080--> EC2 backend (API Go) --5432--> RDS PostgreSQL
#
# Los dos archivos de la app (descargados del release de la cátedra) están en
# la carpeta artifacts/ del repositorio. El script los sube a un bucket S3,
# desde donde cada instancia los descarga al arrancar.
#
# Uso (desde la raíz del repositorio):
#   python3 ej2/deploy.py
# La contraseña de la base sale de RDS_ADMIN_PASSWORD o, si no está, se pide por teclado.

import getpass
import os
import secrets
import time

import boto3
from botocore.exceptions import ClientError


# Configuración
# Todo lo que se puede ajustar está acá.

REGION = 'us-east-1'

# Sufijo aleatorio para que los nombres no choquen con recursos que ya existan
SUFIJO = secrets.token_hex(4)

# Contraseña de la base
VARIABLE_PASSWORD = 'RDS_ADMIN_PASSWORD'

# Archivos de la app, en la carpeta artifacts/ de la raíz del repositorio.
# Las rutas son relativas a esa raíz, que es desde donde se ejecuta el script.
ARTEFACTOS = [
    'artifacts/servicedesk',     # backend: binario de la API
    'artifacts/web.tar.gz',      # frontend: archivos de React
]

# S3
BUCKET = f'servicedesk-artefactos-{SUFIJO}'

# Security groups
SG_FRONTEND = f'servicedesk-sg-frontend-{SUFIJO}'
SG_BACKEND = f'servicedesk-sg-backend-{SUFIJO}'
SG_RDS = f'servicedesk-sg-rds-{SUFIJO}'

# RDS
DB_IDENTIFIER = f'servicedesk-db-{SUFIJO}'
DB_NAME = 'servicedesk'
DB_USER = 'servicedesk_admin'
DB_INSTANCE_CLASS = 'db.t3.micro'
DB_ENGINE = 'postgres'
DB_ENGINE_VERSION = '16'              # la app pide PostgreSQL 16
DB_STORAGE_GB = 20

# EC2
INSTANCE_TYPE = 't3.micro'
# Le da permiso a la instancia para usar SSM y leer el bucket
INSTANCE_PROFILE = 'LabInstanceProfile'
# Parámetro público de AWS con la última AMI de Amazon Linux 2023
AMI_PARAMETER = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
NOMBRE_BACKEND = f'servicedesk-backend-{SUFIJO}'
NOMBRE_FRONTEND = f'servicedesk-frontend-{SUFIJO}'


# User data de las instancias
# El bloque del medio de cada uno son los comandos del README de la app
# ("Comandos para Instalación en Amazon Linux"), con sus marcadores <...>.
# Antes se agrega la descarga desde S3, que el README da por hecha, y en el
# backend, después, el archivo que espera el chequeo final.
# Nota: en Python, \\n se escribe así para que en el script quede \n.

USER_DATA_BACKEND = '''#!/bin/bash
# Descarga del binario desde el bucket
aws s3 cp "s3://<BUCKET>/servicedesk" /tmp/servicedesk --region <REGION>

# Comandos del README de la app (Backend)
set -euo pipefail
useradd --system --home /opt/servicedesk --shell /sbin/nologin servicedesk || true
install -d -o servicedesk -g servicedesk -m 0750 /opt/servicedesk/uploads
install -o servicedesk -g servicedesk -m 0755 /tmp/servicedesk /opt/servicedesk/servicedesk
jwt_secret=$(openssl rand -hex 32)
printf '%s\\n' 'DATABASE_URL=host=<ENDPOINT_RDS> user=<RDS_USER> password=<RDS_PASSWORD> dbname=<RDS_DATABASE> port=5432 sslmode=require' "JWT_SECRET=$jwt_secret" 'PORT=8080' 'FRONTEND_ORIGIN=http://<IP_FRONTEND>' > /opt/servicedesk/.env
chown servicedesk:servicedesk /opt/servicedesk/.env
chmod 0600 /opt/servicedesk/.env
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

# Aviso de que terminó (lo espera el chequeo del backend)
touch /var/lib/servicedesk-backend-ready
'''

USER_DATA_FRONTEND = '''#!/bin/bash
# Descarga del frontend desde el bucket
aws s3 cp "s3://<BUCKET>/web.tar.gz" /tmp/web.tar.gz --region <REGION>

# Comandos del README de la app (Frontend)
set -euo pipefail
dnf install -y nginx
install -d -m 0755 /var/www/servicedesk
tar -xzf /tmp/web.tar.gz -C /var/www/servicedesk
rm -f /etc/nginx/conf.d/*.conf
cat > /etc/nginx/conf.d/servicedesk.conf <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/servicedesk;
    index index.html;
    client_max_body_size 12m;

    location /api/ {
        proxy_pass http://<IP_BACKEND>:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location = /health { proxy_pass http://<IP_BACKEND>:8080; }
    location /docs { proxy_pass http://<IP_BACKEND>:8080; }
    location / { try_files $uri $uri/ /index.html; }
}
EOF
nginx -t
systemctl enable --now nginx
touch /var/lib/servicedesk-frontend-ready
'''


# Clientes de AWS, uno por servicio
s3 = boto3.client('s3', region_name=REGION)
ec2 = boto3.client('ec2', region_name=REGION)
rds = boto3.client('rds', region_name=REGION)
ssm = boto3.client('ssm', region_name=REGION)


def titulo(texto):
    # Encabezado para ver en pantalla en qué paso va
    print(f"\n=== {texto} ===")


# Paso 1: archivos de la app y contraseña de la base
def verificar_archivos_app():
    # Comprueba que estén los dos archivos antes de crear nada
    for ruta in ARTEFACTOS:
        try:
            open(ruta).close()
        except FileNotFoundError:
            print(f"ERROR: no encuentro {ruta}")
            print("Ejecutá el script desde la raíz del repositorio (ver README)")
            exit(1)
    print("Archivos de la app encontrados: " + ", ".join(ARTEFACTOS))


def leer_password():
    # Se busca en la variable de entorno; si no está, se pide sin mostrarla
    password = os.environ.get(VARIABLE_PASSWORD)
    if not password:
        password = getpass.getpass("Contraseña para la base de datos: ")

    # Se valida antes de crear nada, para no dejar recursos a medias.
    # RDS pide 8 caracteres o más y no acepta / @ " ni espacios.
    # ' $ ` \ tampoco, porque rompen el script de bash o el .env donde se escribe.
    if len(password) < 8:
        print("ERROR: la contraseña tiene que tener al menos 8 caracteres")
        exit(1)
    for caracter in password:
        if caracter in '/@"\' $`\\':
            print("ERROR: la contraseña no puede tener / @ \" ' $ ` \\ ni espacios")
            exit(1)
    print("Contraseña válida (no se muestra por seguridad)")
    return password


# Paso 2: bucket S3 con los archivos de la app
def crear_bucket_y_subir_artefactos():
    # El bucket queda privado; las instancias lo leen con LabInstanceProfile
    s3.create_bucket(Bucket=BUCKET)
    print(f"Bucket creado: {BUCKET}")

    for ruta in ARTEFACTOS:
        # En S3 se guarda solo con el nombre del archivo, sin la carpeta
        nombre = ruta.split('/')[-1]
        s3.upload_file(ruta, BUCKET, nombre)
        print(f"Subido: {nombre}")


# Paso 3: security groups
def crear_security_group(nombre, descripcion):
    # Sin VpcId se crea en la VPC por defecto, la misma que usan EC2 y RDS
    response = ec2.create_security_group(
        GroupName=nombre,
        Description=descripcion
    )
    sg_id = response['GroupId']
    print(f"Security group creado: {nombre} ({sg_id})")
    return sg_id


def crear_security_groups():
    # Uno por capa. Solo el frontend recibe tráfico de Internet.
    sg_frontend = crear_security_group(SG_FRONTEND, 'HTTP publico hacia Nginx')
    sg_backend = crear_security_group(SG_BACKEND, 'API 8080 solo desde el frontend')
    sg_rds = crear_security_group(SG_RDS, 'PostgreSQL 5432 solo desde el backend')

    # Frontend: 80 abierto a todos
    ec2.authorize_security_group_ingress(
        GroupId=sg_frontend,
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )
    # Backend: 8080 solo desde el security group del frontend
    ec2.authorize_security_group_ingress(
        GroupId=sg_backend,
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 8080,
            'ToPort': 8080,
            'UserIdGroupPairs': [{'GroupId': sg_frontend}]
        }]
    )
    # Base: 5432 solo desde el security group del backend
    ec2.authorize_security_group_ingress(
        GroupId=sg_rds,
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 5432,
            'ToPort': 5432,
            'UserIdGroupPairs': [{'GroupId': sg_backend}]
        }]
    )

    # El 22 no se abre: a las instancias se entra por SSM
    print("Reglas: 80 <- Internet | 8080 <- frontend | 5432 <- backend")
    return sg_frontend, sg_backend, sg_rds


# Paso 4: base de datos RDS
def crear_base_de_datos(password, sg_rds):
    rds.create_db_instance(
        DBInstanceIdentifier=DB_IDENTIFIER,
        DBInstanceClass=DB_INSTANCE_CLASS,
        Engine=DB_ENGINE,
        EngineVersion=DB_ENGINE_VERSION,
        DBName=DB_NAME,                   # crea la base "servicedesk" adentro
        MasterUsername=DB_USER,
        MasterUserPassword=password,
        AllocatedStorage=DB_STORAGE_GB,
        VpcSecurityGroupIds=[sg_rds],
        PubliclyAccessible=False,         # sin IP pública
        BackupRetentionPeriod=0           # sin backups automáticos
    )
    print(f"Creando la base {DB_IDENTIFIER}...")

    # Espera a que esté disponible antes de seguir
    print("Esperando a que la base esté disponible (5 a 10 minutos)...")
    rds.get_waiter('db_instance_available').wait(DBInstanceIdentifier=DB_IDENTIFIER)

    # El endpoint recién existe cuando la base está disponible
    response = rds.describe_db_instances(DBInstanceIdentifier=DB_IDENTIFIER)
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    print(f"Base lista. Endpoint: {endpoint}")
    return endpoint


# Pasos 5 y 6: instancias EC2
def armar_user_data(plantilla, reemplazos):
    # Cambia cada marcador <NOMBRE> de la plantilla por su valor
    contenido = plantilla
    for marcador, valor in reemplazos.items():
        contenido = contenido.replace(marcador, valor)

    # AWS no acepta user data de más de 16 KB
    if len(contenido) > 16000:
        print("ERROR: el user data supera el límite de 16 KB")
        exit(1)
    return contenido


def obtener_ami():
    # Última AMI de Amazon Linux 2023, así no queda un ID fijo que después caduque
    parameter = ssm.get_parameter(Name=AMI_PARAMETER)
    return parameter['Parameter']['Value']


def crear_instancia(nombre, image_id, sg_id, user_data):
    response = ec2.run_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=INSTANCE_TYPE,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': INSTANCE_PROFILE},
        UserData=user_data,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': nombre}
                ]
            }
        ]
    )
    # Devuelve la instancia entera: de ahí salen el ID y la IP privada
    instancia = response['Instances'][0]
    print(f"Instancia {nombre} creada con ID: {instancia['InstanceId']}")
    return instancia


# Paso 7: ajuste final y chequeos por SSM
def ejecutar_comandos(instance_id, comandos):
    # Corre comandos de bash en la instancia por SSM (como root, sin SSH)
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': comandos}
    )
    command_id = response['Command']['CommandId']

    # Espera el resultado: consulta el estado hasta que el comando termine.
    # Primero espera 2 segundos, porque recién enviado el comando todavía no existe.
    time.sleep(2)
    while True:
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break
        time.sleep(2)

    if output['Status'] != 'Success':
        print(f"ERROR ejecutando comandos en {instance_id}: {output['Status']}")
        print(output['StandardOutputContent'])
        exit(1)
    return output['StandardOutputContent']


def configurar_backend(backend_id, ip_frontend):
    # Cuando se creó el backend todavía no había IP del frontend, así que
    # FRONTEND_ORIGIN quedó con el marcador. Acá se completa en el .env (CORS),
    # se reinicia la API y se prueba.
    comandos = [
        'set -e',
        # espera a que termine el user data, 10 minutos como máximo
        "timeout 600 bash -c 'while [ ! -f /var/lib/servicedesk-backend-ready ]; do sleep 5; done'",
        f"sed -i 's|^FRONTEND_ORIGIN=.*|FRONTEND_ORIGIN=http://{ip_frontend}|' /opt/servicedesk/.env",
        'systemctl restart servicedesk',
        # hasta 30 intentos, cada 2 segundos
        'for attempt in $(seq 1 30); do curl --fail --silent http://127.0.0.1:8080/health && exit 0; sleep 2; done; exit 1'
    ]
    salida = ejecutar_comandos(backend_id, comandos)
    # Si responde, también se conectó a la base: la API se cierra si no puede
    print(f"API (backend) responde: {salida.strip()}")


def verificar_frontend(frontend_id):
    # Pide /health a Nginx, que lo pasa al backend: prueba Nginx -> API
    comandos = [
        'set -e',
        "timeout 600 bash -c 'while [ ! -f /var/lib/servicedesk-frontend-ready ]; do sleep 5; done'",
        'curl --fail --silent http://127.0.0.1/health'
    ]
    salida = ejecutar_comandos(frontend_id, comandos)
    print(f"Nginx -> API responde: {salida.strip()}")


def verificar_desde_internet(backend_id, ip_frontend):
    # Entra por la IP pública del frontend, como un usuario.
    # Se corre desde el backend para no depender de tener curl en la máquina local.
    # "/" prueba la web; "/api/v1/categories" lee la base, así que prueba todo.
    url = f"http://{ip_frontend}"
    comandos = [
        'set -e',
        f"curl --fail --silent {url}/ > /dev/null && echo 'Web (/): OK'",
        f"curl --fail --silent {url}/api/v1/categories > /dev/null && echo 'API + base (/api/v1/categories): OK'"
    ]
    salida = ejecutar_comandos(backend_id, comandos)
    print(salida.strip())


# Programa principal
def main():
    print(f"Despliegue de ServiceDesk - Banco Centralis (región {REGION})")
    # El sufijo va en el nombre de todos los recursos de esta ejecución (sirve para borrarlos)
    print(f"Sufijo de este despliegue: {SUFIJO}")

    titulo("Paso 1: archivos de la app y contraseña de la base")
    verificar_archivos_app()
    password = leer_password()

    titulo("Paso 2: bucket S3 y artefactos")
    crear_bucket_y_subir_artefactos()

    titulo("Paso 3: security groups")
    sg_frontend, sg_backend, sg_rds = crear_security_groups()

    titulo("Paso 4: base de datos RDS PostgreSQL")
    endpoint = crear_base_de_datos(password, sg_rds)

    titulo("Paso 5: instancia EC2 del backend")
    image_id = obtener_ami()
    print(f"AMI obtenida desde SSM: {image_id}")
    # Va primero porque el frontend necesita su IP privada.
    # <IP_FRONTEND> no se reemplaza todavía: se completa en el paso 7.
    user_data_backend = armar_user_data(USER_DATA_BACKEND, {
        '<BUCKET>': BUCKET,
        '<REGION>': REGION,
        '<ENDPOINT_RDS>': endpoint,
        '<RDS_USER>': DB_USER,
        '<RDS_PASSWORD>': password,
        '<RDS_DATABASE>': DB_NAME
    })
    backend = crear_instancia(NOMBRE_BACKEND, image_id, sg_backend, user_data_backend)
    backend_id = backend['InstanceId']
    ip_backend = backend['PrivateIpAddress']
    print(f"IP privada del backend: {ip_backend}")

    titulo("Paso 6: instancia EC2 del frontend")
    user_data_frontend = armar_user_data(USER_DATA_FRONTEND, {
        '<BUCKET>': BUCKET,
        '<REGION>': REGION,
        '<IP_BACKEND>': ip_backend
    })
    frontend = crear_instancia(NOMBRE_FRONTEND, image_id, sg_frontend, user_data_frontend)
    frontend_id = frontend['InstanceId']

    # Espera a que las dos instancias pasen los chequeos de estado
    print("Esperando a que las instancias estén listas (unos minutos)...")
    ec2.get_waiter('instance_status_ok').wait(InstanceIds=[backend_id, frontend_id])
    # La IP pública se asigna después de crearla, por eso se consulta ahora,
    # buscando la instancia por su tag Name
    instances = ec2.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [NOMBRE_FRONTEND]}])
    ip_frontend = instances['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"IP pública del frontend: {ip_frontend}")

    titulo("Paso 7: ajuste final y chequeos")
    configurar_backend(backend_id, ip_frontend)
    verificar_frontend(frontend_id)
    verificar_desde_internet(backend_id, ip_frontend)

    titulo("Despliegue terminado")
    print(f"Aplicación:    http://{ip_frontend}")
    print("Abrir con http:// escrito a mano: el sitio no tiene HTTPS.")
    print(f"Recursos creados (todos con el sufijo {SUFIJO}):")
    print(f"  Bucket:          {BUCKET}")
    print(f"  Security groups: {sg_frontend} {sg_backend} {sg_rds}")
    print(f"  Base de datos:   {DB_IDENTIFIER}")
    print(f"  Instancias:      {backend_id} (backend) {frontend_id} (frontend)")


# Si AWS devuelve un error (credenciales vencidas, permisos...), se muestra
# y el script termina con código 1
if __name__ == '__main__':
    try:
        main()
    except ClientError as e:
        print(f"Error de AWS: {e}")
        exit(1)
