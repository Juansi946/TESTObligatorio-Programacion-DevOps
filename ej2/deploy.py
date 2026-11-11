#!/usr/bin/env python3
# deploy.py
# Despliega ServiceDesk (aplicación de tickets del Banco Centralis) en AWS usando Boto3.
#
#   Internet --80--> EC2 frontend (Nginx) --8080--> EC2 backend (API Go) --5432--> RDS PostgreSQL
#   S3 guarda los artefactos que descargan las instancias.
#
# Uso (desde la carpeta ej2/):
#   export RDS_ADMIN_PASSWORD='una-contraseña-segura'
#   python3 deploy.py
#
# Los nombres de bucket, security groups y base llevan un sufijo aleatorio
# (config.SUFIJO): la primera ejecución no choca con nombres ya usados.

import os
import time

import boto3
from botocore.exceptions import ClientError

import config

# Carpeta donde está este script: las plantillas y los artefactos se buscan acá,
# así funciona sin importar desde qué carpeta se ejecute.
CARPETA = os.path.dirname(os.path.abspath(__file__))

# Un cliente por servicio
s3 = boto3.client('s3', region_name=config.REGION)
ec2 = boto3.client('ec2', region_name=config.REGION)
rds = boto3.client('rds', region_name=config.REGION)
ssm = boto3.client('ssm', region_name=config.REGION)


def paso(titulo):
    print(f"\n=== {titulo} ===")


# ----------------------------------------------------------------------
# Paso 2: contraseña de la base (ejercicio 9 de los Labs)
# ----------------------------------------------------------------------
def leer_password():
    paso("Contraseña de la base de datos")
    # Igual que el ejercicio 9: la contraseña NO está en el código
    password = os.environ.get(config.VARIABLE_PASSWORD)
    if not password:
        print(f"ERROR: definí la variable de entorno {config.VARIABLE_PASSWORD} (ver README)")
        exit(1)
    # RDS rechaza contraseñas de menos de 8 caracteres y las que tienen / @ " o
    # espacios. Se evitan también ' $ ` \ porque la contraseña se escribe dentro
    # de un script de shell (user data). Se controla ahora, antes de crear nada.
    if len(password) < 8:
        print("ERROR: la contraseña debe tener al menos 8 caracteres")
        exit(1)
    for caracter in password:
        if caracter in '/@"\' $`\\':
            print("ERROR: la contraseña no puede tener / @ \" ' $ ` \\ ni espacios")
            exit(1)
    return password


# ----------------------------------------------------------------------
# Paso 3: bucket S3 y artefactos (ejercicio 1)
# ----------------------------------------------------------------------
def crear_bucket_y_subir_artefactos():
    paso("S3: bucket y artefactos")
    s3.create_bucket(Bucket=config.BUCKET)
    print(f"Bucket creado: {config.BUCKET}")

    for artefacto in config.ARTEFACTOS:
        ruta = os.path.join(CARPETA, config.CARPETA_ARTEFACTOS, artefacto)
        try:
            # upload_file(archivo local, bucket, nombre del objeto en S3)
            s3.upload_file(ruta, config.BUCKET, artefacto)
            print(f"Subido: {artefacto}")
        except FileNotFoundError:
            print(f"ERROR: no existe {ruta}. Copiá los artefactos de la app (ver README)")
            exit(1)


# ----------------------------------------------------------------------
# Paso 4: security groups (ejercicio 8 y Ejemplos/sg.py)
# ----------------------------------------------------------------------
def crear_security_group(nombre, descripcion):
    response = ec2.create_security_group(
        GroupName=nombre,
        Description=descripcion,
        TagSpecifications=[{
            'ResourceType': 'security-group',
            'Tags': [{'Key': 'Name', 'Value': nombre}] + config.TAGS
        }]
    )
    sg_id = response['GroupId']
    print(f"Security group creado: {nombre} ({sg_id})")
    return sg_id


def agregar_regla(sg_id, puerto, origen):
    # origen es {'IpRanges': [...]} o {'UserIdGroupPairs': [...]}
    regla = {'IpProtocol': 'tcp', 'FromPort': puerto, 'ToPort': puerto}
    regla.update(origen)
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[regla])


def crear_security_groups():
    paso("Security groups")
    sg_frontend = crear_security_group(config.SG_FRONTEND, 'HTTP publico hacia Nginx')
    sg_backend = crear_security_group(config.SG_BACKEND, 'API 8080 solo desde el frontend')
    sg_rds = crear_security_group(config.SG_RDS, 'PostgreSQL 5432 solo desde el backend')

    # Frontend: puerto 80 abierto a todo el mundo (es el sitio público)
    agregar_regla(sg_frontend, 80, {'IpRanges': [{'CidrIp': '0.0.0.0/0'}]})
    # Backend: 8080 SOLO desde el security group del frontend
    agregar_regla(sg_backend, 8080, {'UserIdGroupPairs': [{'GroupId': sg_frontend}]})
    # Base: 5432 SOLO desde el security group del backend
    agregar_regla(sg_rds, 5432, {'UserIdGroupPairs': [{'GroupId': sg_backend}]})
    # No se abre el 22: para entrar a las instancias se usa SSM
    print("Reglas: 80 <- Internet | 8080 <- frontend | 5432 <- backend")
    return sg_frontend, sg_backend, sg_rds


# ----------------------------------------------------------------------
# Paso 5: base de datos RDS (ejercicio 9 y Ejemplos/rds.py)
# ----------------------------------------------------------------------
def crear_base_de_datos(password, sg_rds):
    paso("RDS PostgreSQL")
    rds.create_db_instance(
        DBInstanceIdentifier=config.DB_IDENTIFIER,
        DBInstanceClass=config.DB_INSTANCE_CLASS,
        Engine=config.DB_ENGINE,
        EngineVersion=config.DB_ENGINE_VERSION,
        DBName=config.DB_NAME,
        MasterUsername=config.DB_USER,
        MasterUserPassword=password,
        AllocatedStorage=config.DB_STORAGE_GB,
        VpcSecurityGroupIds=[sg_rds],
        PubliclyAccessible=False,    # sin IP pública: solo se llega desde la VPC
        BackupRetentionPeriod=0,     # igual que el ejercicio 9 (sin backups automáticos en el lab)
        Tags=config.TAGS
    )
    print(f"Creando la base {config.DB_IDENTIFIER}...")

    print("Esperando a que la base esté disponible (5 a 10 minutos)...")
    rds.get_waiter('db_instance_available').wait(
        DBInstanceIdentifier=config.DB_IDENTIFIER,
        WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
    )
    response = rds.describe_db_instances(DBInstanceIdentifier=config.DB_IDENTIFIER)
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    print(f"Base lista. Endpoint: {endpoint}")
    return endpoint


# ----------------------------------------------------------------------
# Pasos 6, 7 y 8: user data e instancias EC2 (ejercicios 7, 8 y 12)
# ----------------------------------------------------------------------
def armar_user_data(archivo, reemplazos):
    # Lee la plantilla y cambia cada marcador __ALGO__ por su valor
    contenido = open(archivo).read()
    for marcador, valor in reemplazos.items():
        contenido = contenido.replace(marcador, valor)
    if len(contenido) > 16000:
        print(f"ERROR: el user data de {archivo} supera el límite de 16 KB")
        exit(1)
    return contenido


def obtener_ami():
    # Igual que el ejercicio 12: última AMI de Amazon Linux 2023
    parameter = ssm.get_parameter(Name=config.AMI_PARAMETER)
    return parameter['Parameter']['Value']


def crear_instancia(nombre, image_id, sg_id, user_data):
    response = ec2.run_instances(
        ImageId=image_id,
        InstanceType=config.INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': config.INSTANCE_PROFILE},   # permisos para S3 y SSM
        UserData=user_data,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': nombre}] + config.TAGS
        }]
    )
    instance = response['Instances'][0]
    print(f"Instancia {nombre} creada con ID: {instance['InstanceId']}")
    return instance['InstanceId'], instance['PrivateIpAddress']


# ----------------------------------------------------------------------
# Paso 9: comandos por SSM (ejercicios 6 y 12)
# ----------------------------------------------------------------------
def ejecutar_comandos(instance_id, comandos):
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': comandos}
    )
    command_id = response['Command']['CommandId']

    # Igual que el ejercicio 6: preguntar hasta que termine
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
    paso("Backend: CORS y healthcheck")
    comandos = [
        'set -e',
        # esperar a que termine el user data (máximo 10 minutos)
        "timeout 600 bash -c 'while [ ! -f /var/lib/servicedesk-backend-ready ]; do sleep 5; done'",
        # completar FRONTEND_ORIGIN con la IP pública del frontend
        f"sed -i 's|^FRONTEND_ORIGIN=.*|FRONTEND_ORIGIN=http://{ip_frontend}|' /opt/servicedesk/.env",
        'systemctl restart servicedesk',
        # healthcheck del README de la app
        'for attempt in $(seq 1 30); do curl --fail --silent http://127.0.0.1:8080/health && exit 0; sleep 2; done; exit 1'
    ]
    salida = ejecutar_comandos(backend_id, comandos)
    print(f"API responde: {salida.strip()}")


def verificar_frontend(frontend_id):
    paso("Frontend: healthcheck Nginx -> backend")
    comandos = [
        'set -e',
        "timeout 600 bash -c 'while [ ! -f /var/lib/servicedesk-frontend-ready ]; do sleep 5; done'",
        'curl --fail --silent http://127.0.0.1/health'
    ]
    salida = ejecutar_comandos(frontend_id, comandos)
    print(f"Nginx -> API responde: {salida.strip()}")


# ----------------------------------------------------------------------
# Programa principal: el orden de los pasos
# ----------------------------------------------------------------------
def main():
    print(f"Despliegue de ServiceDesk - Banco Centralis ({config.REGION})")

    password = leer_password()                                     # paso 2
    crear_bucket_y_subir_artefactos()                              # paso 3
    sg_frontend, sg_backend, sg_rds = crear_security_groups()      # paso 4
    endpoint = crear_base_de_datos(password, sg_rds)               # paso 5

    paso("Instancias EC2")
    image_id = obtener_ami()
    print(f"AMI obtenida desde SSM: {image_id}")

    # Pasos 6 y 7: primero el backend, porque el frontend necesita su IP privada
    user_data_backend = armar_user_data(os.path.join(CARPETA, 'user_data_backend.sh'), {
        '__BUCKET__': config.BUCKET,
        '__REGION__': config.REGION,
        '__ENDPOINT_RDS__': endpoint,
        '__RDS_USER__': config.DB_USER,
        '__RDS_PASSWORD__': password,
        '__RDS_DATABASE__': config.DB_NAME
    })
    backend_id, ip_backend = crear_instancia(config.NOMBRE_BACKEND, image_id, sg_backend, user_data_backend)
    print(f"IP privada del backend: {ip_backend}")

    # Pasos 6 y 8: el frontend, con la IP privada del backend
    user_data_frontend = armar_user_data(os.path.join(CARPETA, 'user_data_frontend.sh'), {
        '__BUCKET__': config.BUCKET,
        '__REGION__': config.REGION,
        '__IP_BACKEND__': ip_backend
    })
    frontend_id, ip_privada_frontend = crear_instancia(config.NOMBRE_FRONTEND, image_id, sg_frontend, user_data_frontend)

    # Igual que los ejercicios 6 y 12: esperar a que pasen los chequeos de estado
    print("Esperando a que las instancias estén listas (unos minutos)...")
    ec2.get_waiter('instance_status_ok').wait(InstanceIds=[backend_id, frontend_id])
    response = ec2.describe_instances(InstanceIds=[frontend_id])
    ip_frontend = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"IP pública del frontend: {ip_frontend}")

    # Paso 9: CORS y chequeos (los del README de la app)
    configurar_backend(backend_id, ip_frontend)
    verificar_frontend(frontend_id)

    paso("Despliegue terminado")
    print(f"Aplicación:    http://{ip_frontend}")
    print(f"Documentación: http://{ip_frontend}/docs")


if __name__ == '__main__':
    try:
        main()
    except ClientError as e:
        print(f"Error de AWS: {e}")
        exit(1)
