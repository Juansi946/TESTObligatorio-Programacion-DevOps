# Obligatorio Programación para DevOps

Banco Centralis: reporte de usuarios en Bash (ejercicio 1) y despliegue de la aplicación ServiceDesk en AWS con Python y Boto3 (ejercicio 2).

## Integrantes

| Nombre | Nº de estudiante |
|---|---|
| _COMPLETAR_ | _COMPLETAR_ |

## Estructura del repositorio

```
.
├── README.md                     documentación completa (este archivo)
├── .gitignore
├── docs/img/                     capturas de pantalla
├── ej1/
│   └── ej1_reporte_usuarios.sh   script de Bash
└── ej2/
    ├── requirements.txt          dependencias de Python (boto3)
    ├── config.py                 parámetros compartidos (región, nombres, tags, tamaños)
    ├── deploy.py                 despliega toda la infraestructura
    ├── destroy.py                borra todo lo que crea deploy.py
    ├── user_data_backend.sh      plantilla de arranque de la EC2 backend
    ├── user_data_frontend.sh     plantilla de arranque de la EC2 frontend
    └── artifacts/                (no se sube a Git) binario y estáticos de la app
```

---

# Ejercicio 1: reporte de usuarios (Bash)

## Descripción

`ej1_reporte_usuarios.sh` lee `/etc/passwd` y, por cada usuario, imprime separados por tabulador: nombre, UID, home, shell, si el home existe y es un directorio (`SI`/`NO`) y si el usuario es el propietario de ese home (`SI`/`NO`). Al final imprime la cantidad de usuarios listados.

## Requisitos

- Linux con Bash (probado en la familia Red Hat y en Ubuntu).
- Permiso de lectura sobre `/etc/passwd`.

## Modo de uso

```bash
chmod +x ej1/ej1_reporte_usuarios.sh
./ej1/ej1_reporte_usuarios.sh [-t] [-s] [-f] [Usuario]
```

| Modificador | Efecto |
|---|---|
| `-t` | Considera todos los usuarios. Sin `-t` se ignoran los de UID menor a 1000. |
| `-s` | Lista solo los usuarios cuya shell de login es `/bin/bash`. |
| `-f` | Lista solo los usuarios cuyo home existe y es un directorio. |
| `Usuario` | Analiza únicamente a ese usuario. |

Los modificadores se pueden combinar y pasar en cualquier orden, siempre antes del nombre de usuario.

Ejemplos:

```bash
./ej1/ej1_reporte_usuarios.sh                 # usuarios comunes (UID >= 1000)
./ej1/ej1_reporte_usuarios.sh -t              # todos los usuarios
./ej1/ej1_reporte_usuarios.sh -t -s -f root   # solo root, con las tres condiciones
```

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | Ejecución correcta |
| 1 | Modificador inválido |
| 2 | Cantidad de parámetros incorrecta |
| 3 | El nombre de usuario recibido es vacío |
| 4 | `/etc/passwd` no existe |
| 5 | No hay permiso de lectura sobre `/etc/passwd` |
| 6 | El usuario recibido no existe |
| 7 | `/etc/passwd` tiene una línea con un UID que no es un número |

## Captura de una ejecución exitosa

_COMPLETAR: pegar acá la captura de pantalla de una ejecución correcta (guardarla en `docs/img/` y enlazarla con `![ejecución exitosa](docs/img/ej1_ok.png)`)._

---

# Ejercicio 2: despliegue en AWS (Python + Boto3)

## Descripción

`deploy.py` despliega en AWS Academy Learner Lab la aplicación ServiceDesk (sistema de tickets): un frontend React servido por Nginx, una API en Go y una base PostgreSQL 16 en RDS. `destroy.py` elimina todo lo creado.

## Arquitectura

```
Internet --80--> EC2 frontend (Nginx) --8080--> EC2 backend (API Go) --5432--> RDS PostgreSQL 16
                       S3 (artefactos) ... SSM Parameter Store (contraseña de la base)
```

| Security group | Puerto | Origen permitido |
|---|---|---|
| `servicedesk-sg-frontend` | 80 | Internet (`0.0.0.0/0`) |
| `servicedesk-sg-backend` | 8080 | Solo el security group del frontend |
| `servicedesk-sg-rds` | 5432 | Solo el security group del backend |

No se abre el puerto 22: la administración de las instancias se hace por SSM.

## Requisitos

- AWS Academy Learner Lab iniciado (región `us-east-1`, perfil `LabInstanceProfile`).
- Python 3 y pip, Git y AWS CLI. En la familia Red Hat:

```bash
sudo dnf install -y python3 python3-pip git
python3 -m venv ~/venvs/devops && source ~/venvs/devops/bin/activate
pip install -r ej2/requirements.txt
```

## Configuración previa

1. **Credenciales del lab.** En Learner Lab: *AWS Details → Show* y copiar el contenido a `~/.aws/credentials`. Cambian en cada sesión. Comprobar con `aws sts get-caller-identity`.
2. **Nombre del bucket.** Editar `BUCKET` en `ej2/config.py`: el nombre debe ser único en todo AWS.
3. **Artefactos de la app.** Copiar a `ej2/artifacts/` (no se suben a Git por su tamaño) los archivos del repositorio de la cátedra:
   - `servicedesk` (binario de la API)
   - `web.tar.gz` (estáticos del frontend)
   - `docs/index.html` y `docs/openapi.yaml` (documentación que sirve `/docs`)
4. **Variables de entorno** (las contraseñas no están en el código):

```bash
export RDS_ADMIN_PASSWORD='una-contraseña-segura'   # mínimo 8 caracteres, sin / @ comillas ni espacios
export APP_ADMIN_PASSWORD='...'                     # opcional: para probar el login del admin al final
```

## Modo de uso

```bash
cd ej2
python3 deploy.py     # tarda unos 15 minutos (la base de datos es lo más lento)
python3 destroy.py    # borra todo
```

`deploy.py` se puede volver a ejecutar: si un recurso ya existe, lo reutiliza.

## Qué hace el despliegue

| Paso | Qué hace | Función |
|---|---|---|
| 2 | Lee la contraseña de la base de la variable de entorno y la guarda cifrada en SSM Parameter Store | `guardar_password` |
| 3 | Crea el bucket S3, bloquea el acceso público, lo cifra y sube los artefactos | `crear_bucket_y_subir_artefactos` |
| 4 | Crea los tres security groups y sus reglas encadenadas | `crear_security_groups` |
| 5 | Crea la RDS PostgreSQL 16 sin IP pública y espera a que esté disponible | `crear_base_de_datos` |
| 6 | Arma el user data de cada instancia reemplazando los marcadores `__NOMBRE__` | `armar_user_data` |
| 7 | Lanza la EC2 backend (descarga el binario, crea el servicio systemd y el `.env`) | `crear_instancia` |
| 8 | Lanza la EC2 frontend con la IP privada del backend (Nginx + estáticos) | `crear_instancia` |
| 9 | Por SSM: completa CORS, reinicia la API y verifica backend, Nginx y la web por la IP pública | `configurar_backend`, `verificar_frontend`, `verificar_desde_internet` |

## Verificación

Al terminar, el script imprime la URL pública. Se puede comprobar con:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<IP_FRONTEND>/    # 200
curl -s http://<IP_FRONTEND>/health
```

En el navegador, abrir `http://<IP_FRONTEND>` (con `http://` explícito: no hay HTTPS). La documentación de la API está en `/docs`.

## Seguridad

- Contraseñas fuera del código: variables de entorno y SSM Parameter Store (`SecureString`). La contraseña de la base no viaja escrita en el user data.
- Security groups encadenados: la base solo acepta tráfico del backend y el backend solo del frontend. Sin puerto 22.
- RDS sin IP pública y con el disco cifrado.
- Bucket S3 con acceso público bloqueado y cifrado.
- Instancias con IMDSv2 obligatorio y disco cifrado.
- La API corre con un usuario de sistema sin login, con `.env` en modo 0600 y servicio systemd endurecido (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`).
- Conexión a la base con TLS (`sslmode=require`) y `JWT_SECRET` aleatorio generado en el arranque.
- Nginx sin exponer su versión (`server_tokens off`).
- `.gitignore` excluye secretos y artefactos.

**Limitación:** el sitio se sirve por HTTP porque el laboratorio no ofrece dominio ni certificado.

## Limpieza

```bash
cd ej2 && python3 destroy.py
```

Termina las instancias, borra la base de datos, los security groups, el bucket (vaciándolo antes) y el parámetro de SSM. Se puede ejecutar aunque falten recursos.

## Troubleshooting

| Síntoma | Causa y solución |
|---|---|
| `ExpiredToken` / `Error de AWS` | Las credenciales del lab vencieron: copiar las nuevas a `~/.aws/credentials`. |
| `el nombre ... lo usa otra cuenta` | Cambiar `BUCKET` en `config.py`. |
| `definí la variable de entorno RDS_ADMIN_PASSWORD` | Exportar la variable antes de ejecutar. |
| `no existe artifacts/...` | Copiar los artefactos a `ej2/artifacts/`. |
| La web no abre justo al terminar | Esperar uno o dos minutos y usar `http://` explícito. |
| Con una base ya creada, la contraseña no coincide | Usar la misma contraseña de la primera vez o ejecutar `destroy.py`. |
| Aviso sobre `APP_ADMIN_PASSWORD` | Es opcional: sin ella se omite solo la prueba de login. |

---

# Uso de IA generativa

_COMPLETAR (la letra exige declararlo): herramienta(s) utilizada(s), contexto de uso, prompts principales y qué se verificó a mano._

---

# Código completo de los scripts

## ej1/ej1_reporte_usuarios.sh

```bash
#!/bin/bash
#
# ej1_reporte_usuarios.sh [-t] [-s] [-f] [Usuario]
#
# Lista información de los usuarios del sistema a partir de /etc/passwd.
# Por cada usuario muestra, separados por tabulador:
#   nombre  UID  home  shell  home_existe(SI/NO)  es_propietario(SI/NO)
#
# Modificadores (se pueden combinar y pasar en cualquier orden):
#   -t  considerar todos los usuarios (también los de UID < 1000)
#   -s  listar solo los usuarios cuya shell de login es /bin/bash
#   -f  listar solo los usuarios cuyo home existe y es un directorio
#
# Códigos de salida:
#   0  ejecución correcta
#   1  modificador inválido
#   2  cantidad de parámetros incorrecta
#   3  el nombre de usuario recibido es vacío
#   4  el archivo /etc/passwd no existe
#   5  no hay permiso de lectura sobre /etc/passwd
#   6  el usuario recibido no existe
#   7  /etc/passwd tiene una línea con un UID que no es un número

# ---------- Constantes ----------
PASSWD=/etc/passwd
UID_MINIMO=1000
SHELL_BUSCADA=/bin/bash
SEP=$'\t'
SINTAXIS="Uso: $0 [-t] [-s] [-f] [Usuario]"

# ---------- Funciones ----------

# Devuelve verdadero (0) si el usuario recibido como $1 existe en /etc/passwd.
# Compara el nombre exacto con "=" (no con una regex), así un nombre como
# "ana" no coincide con "anabel" y los caracteres especiales no molestan.
usuario_existe() {
    for nombre_passwd in $(cut -d: -f1 "$PASSWD")
    do
        if [ "$nombre_passwd" = "$1" ]
        then
            return 0
        fi
    done
    return 1
}

# ---------- Valores por defecto ----------
todos=0          # 1 si vino -t
solo_bash=0      # 1 si vino -s
solo_home=0      # 1 si vino -f
usuario=""       # vacío = analizar todos los usuarios

# ---------- Procesar los modificadores ----------
# Mientras el primer parámetro sea un modificador, se procesa y se "tacha"
# con shift. Al primer parámetro que no empieza con "-" se sale del while:
# ese tiene que ser el usuario.
while [ $# -gt 0 ]
do
    case "$1" in
        -t) todos=1 ;;
        -s) solo_bash=1 ;;
        -f) solo_home=1 ;;
        -*) echo "Error: modificador inválido '$1'. $SINTAXIS" >&2
            exit 1 ;;
        *)  break ;;
    esac
    shift
done

# Recién ahora se cuentan los parámetros: lo único que puede quedar es el usuario
if [ $# -gt 1 ]
then
    echo "Error: cantidad de parámetros incorrecta. $SINTAXIS" >&2
    exit 2
fi

if [ $# -eq 1 ]
then
    if [ -z "$1" ]
    then
        echo "Error: el nombre de usuario no puede ser vacío. $SINTAXIS" >&2
        exit 3
    fi
    usuario=$1
fi

# ---------- Validar el archivo /etc/passwd ----------
if [ ! -e "$PASSWD" ]
then
    echo "Error: el archivo $PASSWD no existe" >&2
    exit 4
fi

if [ ! -r "$PASSWD" ]
then
    echo "Error: no hay permiso de lectura sobre $PASSWD" >&2
    exit 5
fi

# ---------- Validar que el usuario exista ----------
if [ -n "$usuario" ] && ! usuario_existe "$usuario"
then
    echo "Error: el usuario '$usuario' no existe" >&2
    exit 6
fi

# ---------- Recorrer los usuarios ----------
# Se cortan ANTES del for los campos que interesan
# (1 = nombre, 3 = UID, 6 = home, 7 = shell) y se itera línea por línea.
cantidad=0
IFS=$'\n'
for linea in $(cut -d: -f1,3,6,7 "$PASSWD")
do
    nombre=$(echo "$linea" | cut -d: -f1)
    uid=$(echo "$linea" | cut -d: -f2)
    home=$(echo "$linea" | cut -d: -f3)
    shell=$(echo "$linea" | cut -d: -f4)

    if ! echo "$uid" | grep -q "^[0-9][0-9]*$"
    then
        echo "Error: el UID '$uid' del usuario '$nombre' en $PASSWD no es un número" >&2
        exit 7
    fi

    # Filtro 1: si se pidió un usuario, se saltean todos los demás
    if [ -n "$usuario" ] && [ "$nombre" != "$usuario" ]
    then
        continue
    fi

    # Filtro 2: sin -t, se ignoran los UID menores a 1000
    if [ "$todos" -eq 0 ] && [ "$uid" -lt "$UID_MINIMO" ]
    then
        continue
    fi

    # Filtro 3: con -s, solo los que tienen /bin/bash
    if [ "$solo_bash" -eq 1 ] && [ "$shell" != "$SHELL_BUSCADA" ]
    then
        continue
    fi

    # ¿El home existe y es un directorio? ¿El usuario es su dueño?
    home_ok=NO
    propietario=NO
    if [ -d "$home" ]
    then
        home_ok=SI
        # find con -maxdepth 0 mira solo el propio directorio (no entra);
        # -user lo muestra solo si su dueño es el usuario. Si no muestra
        # nada, el usuario no es el propietario.
        if [ -n "$(find "$home" -maxdepth 0 -user "$nombre" 2>/dev/null)" ]
        then
            propietario=SI
        fi
    fi

    # Filtro 4: con -f, solo los que tienen un home que existe y es directorio
    if [ "$solo_home" -eq 1 ] && [ "$home_ok" = "NO" ]
    then
        continue
    fi

    echo "$nombre$SEP$uid$SEP$home$SEP$shell$SEP$home_ok$SEP$propietario"
    cantidad=$((cantidad + 1))
done

# ---------- Resumen ----------
if [ "$cantidad" -eq 1 ]
then
    echo "1 usuario listado"
else
    echo "$cantidad usuarios listados"
fi

exit 0
```

## ej2/config.py

```python
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
```

## ej2/deploy.py

```python
#!/usr/bin/env python3
# deploy.py
# Despliega ServiceDesk (aplicación de tickets del Banco Centralis) en AWS usando Boto3.
#
#   Internet --80--> EC2 frontend (Nginx) --8080--> EC2 backend (API Go) --5432--> RDS PostgreSQL
#   S3 guarda los artefactos y SSM Parameter Store guarda la contraseña de la base.
#
# Uso (desde la carpeta ej2/):
#   export RDS_ADMIN_PASSWORD='una-contraseña-segura'
#   export APP_ADMIN_PASSWORD='...'    # opcional: para probar el login (ver README)
#   python3 deploy.py
#
# Se puede volver a ejecutar: si un recurso ya existe, lo reutiliza.

import os
import time

import boto3
from botocore.exceptions import ClientError

import config

# Un cliente por servicio
s3 = boto3.client('s3', region_name=config.REGION)
ec2 = boto3.client('ec2', region_name=config.REGION)
rds = boto3.client('rds', region_name=config.REGION)
ssm = boto3.client('ssm', region_name=config.REGION)


def paso(titulo):
    print(f"\n=== {titulo} ===")


# ----------------------------------------------------------------------
# Paso 2: contraseña de la base (ejercicios 9 y 10 de los Labs)
# ----------------------------------------------------------------------
def guardar_password():
    paso("Contraseña de la base de datos")
    # Igual que el ejercicio 9: la contraseña NO está en el código
    password = os.environ.get(config.VARIABLE_PASSWORD)
    if not password:
        print(f"ERROR: definí la variable de entorno {config.VARIABLE_PASSWORD} (ver README)")
        exit(1)
    if len(password) < 8:
        print("ERROR: la contraseña debe tener al menos 8 caracteres")
        exit(1)
    for caracter in password:
        if caracter in '/@"\' ':
            print("ERROR: la contraseña no puede tener / @ comillas ni espacios")
            exit(1)

    # Igual que el ejercicio 10, pero cifrada (SecureString). La EC2 backend
    # la lee de acá, así no viaja escrita en el user data.
    ssm.put_parameter(
        Name=config.PARAM_DB_PASSWORD,
        Value=password,
        Type='SecureString',
        Overwrite=True
    )
    print(f"Contraseña guardada cifrada en SSM: {config.PARAM_DB_PASSWORD}")
    return password


# ----------------------------------------------------------------------
# Paso 3: bucket S3 y artefactos (ejercicio 1)
# ----------------------------------------------------------------------
def crear_bucket_y_subir_artefactos():
    paso("S3: bucket y artefactos")
    try:
        s3.create_bucket(Bucket=config.BUCKET)
        print(f"Bucket creado: {config.BUCKET}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"El bucket {config.BUCKET} ya existe y es tuyo.")
        elif e.response['Error']['Code'] == 'BucketAlreadyExists':
            print(f"ERROR: el nombre {config.BUCKET} lo usa otra cuenta. Cambiá BUCKET en config.py")
            exit(1)
        else:
            raise

    # Seguridad: bloquear todo acceso público y cifrar los objetos
    s3.put_public_access_block(
        Bucket=config.BUCKET,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )
    s3.put_bucket_encryption(
        Bucket=config.BUCKET,
        ServerSideEncryptionConfiguration={
            'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
        }
    )

    for artefacto in config.ARTEFACTOS:
        ruta = config.CARPETA_ARTEFACTOS + '/' + artefacto
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
    try:
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
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
            response = ec2.describe_security_groups(GroupNames=[nombre])
            sg_id = response['SecurityGroups'][0]['GroupId']
            print(f"Security group ya existe: {nombre} ({sg_id})")
        else:
            raise
    return sg_id


def agregar_regla(sg_id, puerto, origen):
    # origen es {'IpRanges': [...]} o {'UserIdGroupPairs': [...]}
    regla = {'IpProtocol': 'tcp', 'FromPort': puerto, 'ToPort': puerto}
    regla.update(origen)
    try:
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[regla])
    except ClientError as e:
        if e.response['Error']['Code'] != 'InvalidPermission.Duplicate':
            raise


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
    try:
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
            StorageEncrypted=True,       # disco cifrado
            BackupRetentionPeriod=0,     # igual que el ejercicio 9 (sin backups automáticos en el lab)
            Tags=config.TAGS
        )
        print(f"Creando la base {config.DB_IDENTIFIER}...")
    except rds.exceptions.DBInstanceAlreadyExistsFault:
        print(f"La base {config.DB_IDENTIFIER} ya existe.")

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


def buscar_instancia(nombre):
    # Igual que el ejercicio 8: buscar por el tag Name (solo las que están vivas)
    instances = ec2.describe_instances(Filters=[
        {'Name': 'tag:Name', 'Values': [nombre]},
        {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
    ])
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            return instance
    return None


def crear_instancia(nombre, image_id, sg_id, user_data):
    existente = buscar_instancia(nombre)
    if existente:
        print(f"La instancia {nombre} ya existe: {existente['InstanceId']}")
        return existente['InstanceId'], existente['PrivateIpAddress']

    response = ec2.run_instances(
        ImageId=image_id,
        InstanceType=config.INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': config.INSTANCE_PROFILE},   # permisos para S3 y SSM
        UserData=user_data,
        # Seguridad: IMDSv2 obligatorio y disco cifrado
        MetadataOptions={'HttpTokens': 'required', 'HttpEndpoint': 'enabled'},
        BlockDeviceMappings=[{
            'DeviceName': '/dev/xvda',
            'Ebs': {'Encrypted': True, 'VolumeType': 'gp3', 'DeleteOnTermination': True}
        }],
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
    # El agente de SSM puede tardar un poco en registrarse: se reintenta
    for intento in range(10):
        try:
            response = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-RunShellScript',
                Parameters={'commands': comandos}
            )
            break
        except ClientError as e:
            if e.response['Error']['Code'] != 'InvalidInstanceId' or intento == 9:
                raise
            time.sleep(15)
    command_id = response['Command']['CommandId']

    # Igual que el ejercicio 6: preguntar hasta que termine
    while True:
        time.sleep(5)
        try:
            output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvocationDoesNotExist':
                continue   # todavía no se registró el comando
            raise
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


def verificar_desde_internet(backend_id, ip_frontend):
    # Desde la EC2 backend se entra a la IP PÚBLICA del frontend, o sea, por
    # Internet: prueba el puerto 80, Nginx, la API y la base (el login lee usuarios)
    paso("Verificación por la IP pública")
    url = f"http://{ip_frontend}"
    comandos = [
        'set -e',
        f"curl --fail --silent --output /dev/null {url}/ && echo 'Web: OK'",
        f"curl --fail --silent {url}/health && echo ' <- /health'"
    ]
    # La contraseña del admin tampoco va en el código (igual que la de la base)
    admin_password = os.environ.get(config.VARIABLE_ADMIN_PASSWORD)
    if admin_password:
        cuerpo = '{"email":"' + config.ADMIN_EMAIL + '","password":"' + admin_password + '"}'
        comandos.append(
            f"curl --fail --silent -X POST {url}/api/v1/auth/login -H 'Content-Type: application/json' "
            f"-d '{cuerpo}' | grep -q accessToken && echo 'Login API: OK'"
        )
    else:
        print(f"Aviso: definí {config.VARIABLE_ADMIN_PASSWORD} para probar también el login (ver README)")
    salida = ejecutar_comandos(backend_id, comandos)
    print(salida.strip())


# ----------------------------------------------------------------------
# Programa principal: el orden de los pasos
# ----------------------------------------------------------------------
def main():
    print(f"Despliegue de ServiceDesk - Banco Centralis ({config.REGION})")

    password = guardar_password()                                  # paso 2
    crear_bucket_y_subir_artefactos()                              # paso 3
    sg_frontend, sg_backend, sg_rds = crear_security_groups()      # paso 4
    endpoint = crear_base_de_datos(password, sg_rds)               # paso 5

    paso("Instancias EC2")
    image_id = obtener_ami()
    print(f"AMI obtenida desde SSM: {image_id}")

    # Pasos 6 y 7: primero el backend, porque el frontend necesita su IP privada
    user_data_backend = armar_user_data('user_data_backend.sh', {
        '__BUCKET__': config.BUCKET,
        '__REGION__': config.REGION,
        '__PARAM_DB_PASSWORD__': config.PARAM_DB_PASSWORD,
        '__ENDPOINT_RDS__': endpoint,
        '__RDS_USER__': config.DB_USER,
        '__RDS_DATABASE__': config.DB_NAME
    })
    backend_id, ip_backend = crear_instancia(config.NOMBRE_BACKEND, image_id, sg_backend, user_data_backend)
    print(f"IP privada del backend: {ip_backend}")

    # Pasos 6 y 8: el frontend, con la IP privada del backend
    user_data_frontend = armar_user_data('user_data_frontend.sh', {
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

    # Paso 9: CORS y chequeos
    configurar_backend(backend_id, ip_frontend)
    verificar_frontend(frontend_id)
    verificar_desde_internet(backend_id, ip_frontend)

    paso("Despliegue terminado")
    print(f"Aplicación:    http://{ip_frontend}")
    print(f"Documentación: http://{ip_frontend}/docs")
    print(f"Administrador: {config.ADMIN_EMAIL} (cambiar la contraseña después del primer ingreso)")


if __name__ == '__main__':
    try:
        main()
    except ClientError as e:
        print(f"Error de AWS: {e}")
        exit(1)
```

## ej2/destroy.py

```python
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
```

## ej2/user_data_backend.sh

```bash
#!/bin/bash
# User data de la EC2 backend (API Go).
# Basado en el bloque "Backend" del README de la app. deploy.py reemplaza los
# marcadores con forma __NOMBRE__ antes de lanzar la instancia.
set -euo pipefail

# 1) Descargar los artefactos desde el bucket privado (la instancia usa LabInstanceProfile)
aws s3 cp "s3://__BUCKET__/servicedesk" /tmp/servicedesk --region __REGION__
aws s3 cp "s3://__BUCKET__/docs/" /tmp/docs/ --recursive --region __REGION__

# 2) Leer la contraseña de RDS desde SSM Parameter Store.
#    Así la contraseña NO viaja escrita dentro del user data.
rds_password=$(aws ssm get-parameter --name "__PARAM_DB_PASSWORD__" --with-decryption \
    --query Parameter.Value --output text --region __REGION__)

# 3) Usuario de sistema sin login: la API no corre como root
useradd --system --home /opt/servicedesk --shell /sbin/nologin servicedesk || true
install -d -o servicedesk -g servicedesk -m 0750 /opt/servicedesk/uploads
install -o servicedesk -g servicedesk -m 0755 /tmp/servicedesk /opt/servicedesk/servicedesk
install -d -o servicedesk -g servicedesk -m 0755 /opt/servicedesk/docs
install -o servicedesk -g servicedesk -m 0644 /tmp/docs/index.html /tmp/docs/openapi.yaml /opt/servicedesk/docs/

# 4) Archivo de variables: JWT aleatorio y conexión TLS a RDS.
#    FRONTEND_ORIGIN queda pendiente: deploy.py lo completa por SSM cuando
#    el frontend ya tiene IP pública.
jwt_secret=$(openssl rand -hex 32)
printf '%s\n' \
    "DATABASE_URL=host=__ENDPOINT_RDS__ user=__RDS_USER__ password=${rds_password} dbname=__RDS_DATABASE__ port=5432 sslmode=require" \
    "JWT_SECRET=${jwt_secret}" \
    'PORT=8080' \
    'FRONTEND_ORIGIN=http://PENDIENTE' > /opt/servicedesk/.env
chown servicedesk:servicedesk /opt/servicedesk/.env
chmod 0600 /opt/servicedesk/.env

# 5) Servicio systemd
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

# 6) Limpieza y marca de "terminé" (el README la usa en el healthcheck pero no la crea)
rm -rf /tmp/servicedesk /tmp/docs
touch /var/lib/servicedesk-backend-ready
```

## ej2/user_data_frontend.sh

```bash
#!/bin/bash
# User data de la EC2 frontend (Nginx + estáticos de React).
# Basado en el bloque "Frontend" del README de la app. deploy.py reemplaza los
# marcadores con forma __NOMBRE__ antes de lanzar la instancia.
set -euo pipefail

# 1) Descargar los estáticos desde el bucket privado
aws s3 cp "s3://__BUCKET__/web.tar.gz" /tmp/web.tar.gz --region __REGION__

# 2) Instalar Nginx y publicar los estáticos
dnf install -y nginx
install -d -m 0755 /var/www/servicedesk
tar -xzf /tmp/web.tar.gz -C /var/www/servicedesk
rm -f /tmp/web.tar.gz
rm -f /etc/nginx/conf.d/*.conf

# 3) Virtual host: sirve React y manda /api/, /health y /docs al backend PRIVADO
cat > /etc/nginx/conf.d/servicedesk.conf <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/servicedesk;
    index index.html;
    client_max_body_size 12m;
    server_tokens off;

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
nginx -t
systemctl enable --now nginx
touch /var/lib/servicedesk-frontend-ready
```

