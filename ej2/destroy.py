#!/usr/bin/env python3
# destroy.py
# Borra todo lo que crea deploy.py, en orden inverso a las dependencias.
#
# Uso (desde la carpeta ej2/):
#   python3 destroy.py

import boto3
from botocore.exceptions import ClientError

import config

s3 = boto3.client('s3', region_name=config.REGION)
ec2 = boto3.client('ec2', region_name=config.REGION)
rds = boto3.client('rds', region_name=config.REGION)
ssm = boto3.client('ssm', region_name=config.REGION)


def borrar_instancias():
    print("== EC2 ==")
    instances = ec2.describe_instances(Filters=[
        {'Name': 'tag:Name', 'Values': [config.NOMBRE_BACKEND, config.NOMBRE_FRONTEND]},
        {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
    ])
    ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            ids.append(instance['InstanceId'])
    if not ids:
        print("No hay instancias")
        return
    ec2.terminate_instances(InstanceIds=ids)
    print(f"Terminando {ids}...")
    ec2.get_waiter('instance_terminated').wait(InstanceIds=ids)


def borrar_base_de_datos():
    print("== RDS ==")
    try:
        rds.delete_db_instance(
            DBInstanceIdentifier=config.DB_IDENTIFIER,
            SkipFinalSnapshot=True,
            DeleteAutomatedBackups=True
        )
        print(f"Borrando {config.DB_IDENTIFIER} (varios minutos)...")
    except rds.exceptions.DBInstanceNotFoundFault:
        print("No hay base de datos")
        return
    except rds.exceptions.InvalidDBInstanceStateFault:
        print("La base ya se estaba borrando")
    rds.get_waiter('db_instance_deleted').wait(
        DBInstanceIdentifier=config.DB_IDENTIFIER,
        WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
    )


def borrar_security_groups():
    print("== Security groups ==")
    # Primero los que están referenciados por otros
    for nombre in [config.SG_RDS, config.SG_BACKEND, config.SG_FRONTEND]:
        try:
            response = ec2.describe_security_groups(GroupNames=[nombre])
            ec2.delete_security_group(GroupId=response['SecurityGroups'][0]['GroupId'])
            print(f"Borrado {nombre}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'InvalidGroup.NotFound':
                raise
            print(f"No existe {nombre}")


def borrar_bucket():
    print("== S3 ==")
    try:
        # Un bucket solo se puede borrar si está vacío
        response = s3.list_objects_v2(Bucket=config.BUCKET)
        if 'Contents' in response:
            for obj in response['Contents']:
                s3.delete_object(Bucket=config.BUCKET, Key=obj['Key'])
        s3.delete_bucket(Bucket=config.BUCKET)
        print(f"Borrado {config.BUCKET}")
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchBucket':
            raise
        print("No hay bucket")


def borrar_parametro():
    print("== SSM ==")
    try:
        ssm.delete_parameter(Name=config.PARAM_DB_PASSWORD)
        print(f"Borrado {config.PARAM_DB_PASSWORD}")
    except ssm.exceptions.ParameterNotFound:
        print("No hay parámetro")


def main():
    borrar_instancias()        # libera los security groups de frontend y backend
    borrar_base_de_datos()     # libera el security group de la base
    borrar_security_groups()
    borrar_bucket()
    borrar_parametro()
    print("Listo: no quedan recursos de ServiceDesk")


if __name__ == '__main__':
    try:
        main()
    except ClientError as e:
        print(f"Error de AWS: {e}")
        exit(1)
