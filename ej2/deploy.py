#!/usr/bin/env python3
# ======================================================================
# deploy.py - Ejercicio 2 del obligatorio de Programación para DevOps
# ======================================================================
# Despliego en AWS, con Boto3, la aplicación de tickets del Banco Centralis
# (ServiceDesk). La app tiene tres capas y cada una va en su propio recurso:
#
#   Internet --80--> EC2 frontend (Nginx) --8080--> EC2 backend (API Go) --5432--> RDS PostgreSQL
#
# El binario de la API pesa unos 23 MB y el user data tiene un límite de 16 KB,
# así que los archivos de la app los subo a un bucket S3 y cada instancia se
# los descarga al arrancar.
#
# El orden de los pasos importa: cada uno necesita algo que crea el anterior.
#   1. Contraseña de la base   la valido antes de crear cualquier recurso
#   2. Bucket S3               las instancias descargan de acá los artefactos
#   3. Security groups         van antes de las instancias para pasarlos al crearlas
#   4. Base de datos RDS       el backend necesita su endpoint
#   5. EC2 backend             el frontend necesita su IP privada
#   6. EC2 frontend            el backend necesita su IP pública (CORS)
#   7. Ajuste final y chequeos por SSM
#
# Uso (los detalles están en el README):
#   python3 ej2/deploy.py
# La contraseña de la base se toma de la variable de entorno RDS_ADMIN_PASSWORD
# y, si no está definida, el script la pide por teclado.

import getpass
import os
import secrets
import time

import boto3
from botocore.exceptions import ClientError


# ======================================================================
# Configuración
# ======================================================================
# Dejo todos los valores juntos acá arriba, como en los ejemplos de clase:
# si hay que cambiar algo (región, tamaños, nombres) se cambia solo acá.

REGION = 'us-east-1'                  # el Learner Lab trabaja en us-east-1

# Algunos nombres no se pueden repetir: el del bucket es único en todo AWS y
# los de los security groups y la base, dentro de la cuenta. Les agrego un
# sufijo aleatorio (lo sugirió el profe en la clase 21) para que la primera
# ejecución no choque con nada que ya exista, ni en mi cuenta ni en otra.
SUFIJO = secrets.token_hex(4)         # 8 caracteres hexadecimales, por ejemplo 3f9a1c0b

# Tags que pongo en todos los recursos para identificarlos y filtrarlos
TAGS = [
    {'Key': 'Proyecto', 'Value': 'obligatorio-devops'},
    {'Key': 'Cliente', 'Value': 'banco-centralis'},
    {'Key': 'Ambiente', 'Value': 'produccion'},
    {'Key': 'Despliegue', 'Value': SUFIJO},
]

# ---------- Contraseña de la base ----------
VARIABLE_PASSWORD = 'RDS_ADMIN_PASSWORD'   # variable de entorno donde la busco

# ---------- S3 ----------
BUCKET = f'servicedesk-artefactos-{SUFIJO}'
# Busco los archivos a partir de la carpeta donde está este script, así
# funciona aunque se ejecute desde otra carpeta (por ejemplo, la raíz del repo).
CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CARPETA_ARTEFACTOS = os.path.join(CARPETA_SCRIPT, 'artifacts')
ARTEFACTOS = [
    'servicedesk',           # binario de la API (backend)
    'web.tar.gz',            # archivos estáticos de React (frontend)
    'docs/index.html',       # página que muestra la documentación en /docs
    'docs/openapi.yaml',     # especificación de la API que lee esa página
]

# ---------- Security groups (uno por capa) ----------
SG_FRONTEND = f'servicedesk-sg-frontend-{SUFIJO}'
SG_BACKEND = f'servicedesk-sg-backend-{SUFIJO}'
SG_RDS = f'servicedesk-sg-rds-{SUFIJO}'

# ---------- RDS ----------
DB_IDENTIFIER = f'servicedesk-db-{SUFIJO}'
DB_NAME = 'servicedesk'
DB_USER = 'servicedesk_admin'
DB_INSTANCE_CLASS = 'db.t3.micro'
DB_ENGINE = 'postgres'
DB_ENGINE_VERSION = '16'              # el README de la app pide PostgreSQL 16
DB_STORAGE_GB = 20

# ---------- EC2 ----------
INSTANCE_TYPE = 't3.micro'
# Perfil del rol LabRole. Sin él la instancia no aparece en SSM ni puede
# leer el bucket (clase 21, ejercicios 6 y 12).
INSTANCE_PROFILE = 'LabInstanceProfile'
# Parámetro público con la última AMI de Amazon Linux 2023 (ejercicio 12)
AMI_PARAMETER = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
NOMBRE_BACKEND = f'servicedesk-backend-{SUFIJO}'
NOMBRE_FRONTEND = f'servicedesk-frontend-{SUFIJO}'
PLANTILLA_BACKEND = os.path.join(CARPETA_SCRIPT, 'user_data_backend.sh')
PLANTILLA_FRONTEND = os.path.join(CARPETA_SCRIPT, 'user_data_frontend.sh')


# ======================================================================
# Clientes de AWS
# ======================================================================
# Un cliente por servicio, con el nombre del servicio (clase 20). Les paso la
# región para no depender de cómo tenga configurada la AWS CLI quien lo ejecute.
s3 = boto3.client('s3', region_name=REGION)
ec2 = boto3.client('ec2', region_name=REGION)
rds = boto3.client('rds', region_name=REGION)
ssm = boto3.client('ssm', region_name=REGION)


def titulo(texto):
    # Imprime un encabezado para seguir en pantalla por qué paso va el despliegue
    print(f"\n=== {texto} ===")


# ======================================================================
# Paso 1: contraseña de la base de datos
# ======================================================================
def leer_password():
    # La contraseña nunca va escrita en el código. Primero la busco en una
    # variable de entorno, como en el ejercicio 9 de los Labs. Si no está,
    # la pido con getpass, que no la muestra en pantalla mientras se escribe
    # (las dos opciones las nombró el profe en la clase 21).
    password = os.environ.get(VARIABLE_PASSWORD)
    if not password:
        password = getpass.getpass("Contraseña para la base de datos: ")

    # La valido ahora, antes de crear nada: si RDS la rechaza recién en el
    # paso 4, ya habrían quedado creados el bucket y los security groups.
    # RDS pide al menos 8 caracteres y no acepta / @ " ni espacios. Además
    # descarto ' $ ` \ porque la contraseña termina escrita dentro de un
    # script de bash (el user data del backend) y ahí esos caracteres la romperían.
    if len(password) < 8:
        print("ERROR: la contraseña tiene que tener al menos 8 caracteres")
        exit(1)
    for caracter in password:
        if caracter in '/@"\' $`\\':
            print("ERROR: la contraseña no puede tener / @ \" ' $ ` \\ ni espacios")
            exit(1)
    print("Contraseña válida (no se muestra por seguridad)")
    return password


# ======================================================================
# Paso 2: bucket S3 con los artefactos de la app
# ======================================================================
def crear_bucket_y_subir_artefactos():
    # Igual que el ejercicio 1 de los Labs: creo el bucket y subo cada archivo
    # con upload_file(archivo local, bucket, nombre del objeto en S3).
    # El bucket queda privado: S3 bloquea el acceso público por defecto y las
    # instancias lo leen con los permisos de LabInstanceProfile.
    s3.create_bucket(Bucket=BUCKET)
    print(f"Bucket creado: {BUCKET}")

    for artefacto in ARTEFACTOS:
        ruta = os.path.join(CARPETA_ARTEFACTOS, artefacto)
        try:
            # Uso la misma ruta como nombre del objeto, así docs/ queda como
            # "carpeta" en S3 y el backend la descarga entera con un solo comando
            s3.upload_file(ruta, BUCKET, artefacto)
            print(f"Subido: {artefacto}")
        except FileNotFoundError:
            print(f"ERROR: no encuentro {ruta}. Revisá la carpeta ej2/artifacts (ver README)")
            exit(1)


# ======================================================================
# Paso 3: security groups encadenados
# ======================================================================
def crear_security_group(nombre, descripcion):
    # Igual que el ejercicio 8: Description es obligatoria. No paso VpcId, así
    # que el grupo se crea en la VPC por defecto, la misma que usan EC2 y RDS.
    response = ec2.create_security_group(
        GroupName=nombre,
        Description=descripcion,
        TagSpecifications=[{
            'ResourceType': 'security-group',
            'Tags': [{'Key': 'Name', 'Value': nombre}] + TAGS
        }]
    )
    sg_id = response['GroupId']
    print(f"Security group creado: {nombre} ({sg_id})")
    return sg_id


def agregar_regla(sg_id, puerto, origen):
    # Un grupo recién creado es una "caja vacía" que no deja entrar nada.
    # Cada regla abre UN solo puerto TCP (FromPort y ToPort iguales).
    # origen es {'IpRanges': [...]} para permitir rangos de IP, o
    # {'UserIdGroupPairs': [...]} para permitir solo a otro security group.
    regla = {'IpProtocol': 'tcp', 'FromPort': puerto, 'ToPort': puerto}
    regla.update(origen)
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[regla])


def crear_security_groups():
    # Tres grupos, uno por capa (clase 21). Solo el frontend queda expuesto a
    # Internet; cada capa de atrás acepta tráfico únicamente de la anterior.
    sg_frontend = crear_security_group(SG_FRONTEND, 'HTTP publico hacia Nginx')
    sg_backend = crear_security_group(SG_BACKEND, 'API 8080 solo desde el frontend')
    sg_rds = crear_security_group(SG_RDS, 'PostgreSQL 5432 solo desde el backend')

    # Frontend: puerto 80 abierto a todo el mundo, porque es el sitio público
    agregar_regla(sg_frontend, 80, {'IpRanges': [{'CidrIp': '0.0.0.0/0'}]})
    # Backend: puerto 8080 SOLO desde el security group del frontend
    agregar_regla(sg_backend, 8080, {'UserIdGroupPairs': [{'GroupId': sg_frontend}]})
    # Base: puerto 5432 SOLO desde el security group del backend
    agregar_regla(sg_rds, 5432, {'UserIdGroupPairs': [{'GroupId': sg_backend}]})

    # No abro el 22 en ningún grupo: para entrar a las instancias uso SSM
    print("Reglas: 80 <- Internet | 8080 <- frontend | 5432 <- backend")
    return sg_frontend, sg_backend, sg_rds


# ======================================================================
# Paso 4: base de datos RDS PostgreSQL
# ======================================================================
def crear_base_de_datos(password, sg_rds):
    # Basado en el ejercicio 9 y en lo que vimos en la clase 21
    rds.create_db_instance(
        DBInstanceIdentifier=DB_IDENTIFIER,
        DBInstanceClass=DB_INSTANCE_CLASS,
        Engine=DB_ENGINE,
        EngineVersion=DB_ENGINE_VERSION,
        DBName=DB_NAME,                   # crea además la base "servicedesk" adentro
        MasterUsername=DB_USER,
        MasterUserPassword=password,
        AllocatedStorage=DB_STORAGE_GB,
        VpcSecurityGroupIds=[sg_rds],     # si no lo paso, queda con el grupo por defecto
        PubliclyAccessible=False,         # sin IP pública: solo se llega desde adentro de la VPC
        BackupRetentionPeriod=0,          # igual que el ejercicio 9: sin backups automáticos en el lab
        Tags=TAGS
    )
    print(f"Creando la base {DB_IDENTIFIER}...")

    # Python no espera solo: el waiter frena el script hasta que la base esté
    # disponible (clase 21). Tarda entre 5 y 10 minutos.
    print("Esperando a que la base esté disponible (5 a 10 minutos)...")
    rds.get_waiter('db_instance_available').wait(DBInstanceIdentifier=DB_IDENTIFIER)

    # El endpoint recién existe cuando la base está disponible
    response = rds.describe_db_instances(DBInstanceIdentifier=DB_IDENTIFIER)
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    print(f"Base lista. Endpoint: {endpoint}")
    return endpoint


# ======================================================================
# Pasos 5 y 6: instancias EC2 con user data
# ======================================================================
def armar_user_data(plantilla, reemplazos):
    # Leo la plantilla (como Ejemplos/rds.py lee su archivo) y cambio cada
    # marcador __NOMBRE__ por su valor real. Es lo mismo que pide el README de
    # la app con sus <MARCADORES>: "reemplazar y desplegar".
    contenido = open(plantilla).read()
    for marcador, valor in reemplazos.items():
        contenido = contenido.replace(marcador, valor)

    # El user data tiene un límite de 16 KB (clase 20). Lo controlo antes de
    # mandarlo para tener un error claro y no uno genérico de AWS.
    if len(contenido) > 16000:
        print(f"ERROR: el user data de {plantilla} supera el límite de 16 KB")
        exit(1)
    return contenido


def obtener_ami():
    # Igual que el ejercicio 12: pido a SSM la última AMI de Amazon Linux 2023,
    # así no dejo escrito un ID de AMI que con el tiempo deja de existir
    parameter = ssm.get_parameter(Name=AMI_PARAMETER)
    return parameter['Parameter']['Value']


def crear_instancia(nombre, image_id, sg_id, user_data):
    # run_instances como en los ejercicios 6, 7 y 12: le paso el security group
    # de su capa, el perfil del lab, el user data y el tag Name en la creación
    response = ec2.run_instances(
        ImageId=image_id,
        InstanceType=INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': INSTANCE_PROFILE},
        UserData=user_data,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': nombre}] + TAGS
        }]
    )
    # Devuelvo el diccionario de la instancia: de ahí saco el ID y la IP privada
    instancia = response['Instances'][0]
    print(f"Instancia {nombre} creada con ID: {instancia['InstanceId']}")
    return instancia


# ======================================================================
# Paso 7: ajuste final y chequeos por SSM
# ======================================================================
def ejecutar_comandos(instance_id, comandos):
    # Mando una lista de comandos de bash a la instancia por SSM, sin SSH
    # (ejercicios 6 y 12). Los comandos corren como root.
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': comandos}
    )
    command_id = response['Command']['CommandId']

    # Igual que el ejercicio 6: pregunto el estado cada 5 segundos hasta que
    # termine. No uso el waiter command_executed porque espera como mucho
    # unos 100 segundos y la espera del user data puede ser más larga.
    while True:
        time.sleep(5)
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break

    if output['Status'] != 'Success':
        print(f"ERROR ejecutando comandos en {instance_id}: {output['Status']}")
        print(output['StandardErrorContent'])
        exit(1)
    return output['StandardOutputContent']


def configurar_backend(backend_id, ip_frontend):
    # El backend arrancó con FRONTEND_ORIGIN pendiente, porque cuando lo creé
    # el frontend todavía no existía. El README de la app dice que ese valor
    # "puede actualizarse después mediante SSM": eso hago acá. Después corro
    # el HealthCheck del backend que trae el mismo README.
    comandos = [
        'set -e',
        # espero a que el user data termine (como máximo 10 minutos)
        "timeout 600 bash -c 'while [ ! -f /var/lib/servicedesk-backend-ready ]; do sleep 5; done'",
        # completo FRONTEND_ORIGIN (CORS) con la IP pública del frontend
        f"sed -i 's|^FRONTEND_ORIGIN=.*|FRONTEND_ORIGIN=http://{ip_frontend}|' /opt/servicedesk/.env",
        # reinicio la API para que tome el valor nuevo
        'systemctl restart servicedesk',
        # healthcheck del README: hasta 30 intentos, uno cada 2 segundos
        'for attempt in $(seq 1 30); do curl --fail --silent http://127.0.0.1:8080/health && exit 0; sleep 2; done; exit 1'
    ]
    salida = ejecutar_comandos(backend_id, comandos)
    # Si la API responde es porque también se conectó a la base: el proceso
    # se conecta a RDS al arrancar y, si no puede, se cierra.
    print(f"API (backend) responde: {salida.strip()}")


def verificar_frontend(frontend_id):
    # HealthCheck del frontend del README de la app: pide /health a Nginx, que
    # lo reenvía al backend. Así pruebo la cadena Nginx -> API, no solo el puerto 80.
    comandos = [
        'set -e',
        "timeout 600 bash -c 'while [ ! -f /var/lib/servicedesk-frontend-ready ]; do sleep 5; done'",
        'curl --fail --silent http://127.0.0.1/health'
    ]
    salida = ejecutar_comandos(frontend_id, comandos)
    print(f"Nginx -> API responde: {salida.strip()}")


def verificar_desde_internet(backend_id, ip_frontend):
    # Último chequeo, como lo haría un usuario: entro por la IP PÚBLICA del
    # frontend, o sea, pasando por Internet y por el security group del 80.
    # Lo lanzo desde la instancia backend (por SSM) para no depender de que
    # quien ejecuta el script tenga curl instalado.
    #   - "/" devuelve la página de React (prueba Nginx y los estáticos).
    #   - "/api/v1/categories" es un endpoint público de la API que lee la
    #     base, así que prueba la cadena completa: Nginx -> API -> RDS.
    url = f"http://{ip_frontend}"
    comandos = [
        'set -e',
        f"curl --fail --silent --output /dev/null {url}/ && echo 'Web (/): OK'",
        f"curl --fail --silent --output /dev/null {url}/api/v1/categories && echo 'API + base (/api/v1/categories): OK'"
    ]
    salida = ejecutar_comandos(backend_id, comandos)
    print(salida.strip())


# ======================================================================
# Programa principal: los pasos en orden
# ======================================================================
def main():
    print(f"Despliegue de ServiceDesk - Banco Centralis (región {REGION})")
    # Muestro el sufijo porque identifica todos los recursos de esta ejecución
    # (sirve para encontrarlos y borrarlos después, ver README)
    print(f"Sufijo de este despliegue: {SUFIJO}")

    titulo("Paso 1: contraseña de la base de datos")
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
    # Primero el backend, porque el frontend necesita su IP privada para Nginx
    user_data_backend = armar_user_data(PLANTILLA_BACKEND, {
        '__BUCKET__': BUCKET,
        '__REGION__': REGION,
        '__ENDPOINT_RDS__': endpoint,
        '__RDS_USER__': DB_USER,
        '__RDS_PASSWORD__': password,
        '__RDS_DATABASE__': DB_NAME
    })
    backend = crear_instancia(NOMBRE_BACKEND, image_id, sg_backend, user_data_backend)
    backend_id = backend['InstanceId']
    ip_backend = backend['PrivateIpAddress']
    print(f"IP privada del backend: {ip_backend}")

    titulo("Paso 6: instancia EC2 del frontend")
    user_data_frontend = armar_user_data(PLANTILLA_FRONTEND, {
        '__BUCKET__': BUCKET,
        '__REGION__': REGION,
        '__IP_BACKEND__': ip_backend
    })
    frontend = crear_instancia(NOMBRE_FRONTEND, image_id, sg_frontend, user_data_frontend)
    frontend_id = frontend['InstanceId']

    # Igual que los ejercicios 6 y 12: espero a que las dos instancias pasen
    # los chequeos de estado. Un solo waiter puede esperar varias a la vez.
    print("Esperando a que las instancias estén listas (unos minutos)...")
    ec2.get_waiter('instance_status_ok').wait(InstanceIds=[backend_id, frontend_id])
    # La IP pública no viene en la respuesta de run_instances (se asigna
    # después), por eso la consulto ahora con describe_instances
    response = ec2.describe_instances(InstanceIds=[frontend_id])
    ip_frontend = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"IP pública del frontend: {ip_frontend}")

    titulo("Paso 7: ajuste final y chequeos")
    configurar_backend(backend_id, ip_frontend)
    verificar_frontend(frontend_id)
    verificar_desde_internet(backend_id, ip_frontend)

    titulo("Despliegue terminado")
    print(f"Aplicación:    http://{ip_frontend}")
    print(f"Documentación: http://{ip_frontend}/docs")
    print("Abrir con http:// escrito a mano: el sitio no tiene HTTPS.")
    print(f"Recursos creados (todos con el sufijo {SUFIJO}):")
    print(f"  Bucket:          {BUCKET}")
    print(f"  Security groups: {sg_frontend} {sg_backend} {sg_rds}")
    print(f"  Base de datos:   {DB_IDENTIFIER}")
    print(f"  Instancias:      {backend_id} (backend) {frontend_id} (frontend)")


# Solo ejecuto main() si corro el archivo directamente (ejercicio 3 de los Labs).
# Si AWS devuelve un error (credenciales vencidas, permisos, límites del lab),
# lo muestro y termino con código 1, igual que el ejercicio 1.
if __name__ == '__main__':
    try:
        main()
    except ClientError as e:
        print(f"Error de AWS: {e}")
        exit(1)
