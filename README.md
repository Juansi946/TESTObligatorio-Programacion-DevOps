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

Los modificadores se pueden combinar y pasar en cualquier orden, separados (`-t -s`) o juntos (`-ts`), siempre antes del nombre de usuario. Se procesan con `getopts`.

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

`deploy.py` despliega en AWS Academy Learner Lab la aplicación ServiceDesk (sistema de tickets): un frontend React servido por Nginx, una API en Go y una base PostgreSQL 16 en RDS.

## Arquitectura

```
Internet --80--> EC2 frontend (Nginx) --8080--> EC2 backend (API Go) --5432--> RDS PostgreSQL 16
                       S3 (artefactos que descargan las instancias)
```

| Security group | Puerto | Origen permitido |
|---|---|---|
| `servicedesk-sg-frontend` | 80 | Internet (`0.0.0.0/0`) |
| `servicedesk-sg-backend` | 8080 | Solo el security group del frontend |
| `servicedesk-sg-rds` | 5432 | Solo el security group del backend |

No se abre el puerto 22: los comandos se ejecutan en las instancias por SSM.

## Requisitos

- AWS Academy Learner Lab iniciado (región `us-east-1`, perfil `LabInstanceProfile`).
- **Python 3.9 o superior** y **pip** (el script se ejecutó con Python 3.13 y Boto3 1.44; cualquier Boto3 reciente sirve).
- **Boto3** (no es una librería estándar), **Git** y **AWS CLI**.

Instalación en Alma Linux / familia Red Hat:

```bash
sudo dnf install -y python3 python3-pip git
git clone <URL-del-repositorio> && cd <carpeta-del-repositorio>
pip install -r ej2/requirements.txt
```

Si pip se queja de un "entorno administrado externamente", agregar `--break-system-packages` o usar un entorno virtual:

```bash
python3 -m venv ~/venvs/devops && source ~/venvs/devops/bin/activate
pip install -r ej2/requirements.txt
```

En Ubuntu: `sudo apt install -y python3 python3-pip python3-venv git`.

La AWS CLI se instala siguiendo la guía oficial: <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>.

## Configuración previa

1. **Credenciales del lab.** En Learner Lab: *AWS Details → Show* y pegar el bloque completo en `~/.aws/credentials` (la primera vez se puede usar `aws configure`). Duran unas 4 horas y cambian en cada sesión. Comprobar que funcionan:

```bash
aws sts get-caller-identity     # debe devolver UserId, Account y Arn
```

2. **Artefactos de la app.** Descargar los archivos ya compilados de los *Releases* del repositorio de la aplicación y copiarlos a `ej2/artifacts/` (esa carpeta no se sube a Git por su tamaño):
   - `servicedesk` (binario de la API)
   - `web.tar.gz` (estáticos del frontend)
   - `docs/index.html` y `docs/openapi.yaml` (documentación que sirve `/docs`)

   Si los archivos descargados se llaman distinto, ajustar la lista `ARTEFACTOS` de `ej2/config.py`.
3. **Variable de entorno** con la contraseña de la base (no está en el código):

```bash
export RDS_ADMIN_PASSWORD='una-contraseña-segura'
```

   Requisitos de la contraseña: mínimo 8 caracteres y sin `/` `@` `"` `'` `$` `` ` `` `\` ni espacios. El script lo comprueba antes de crear nada.

No hace falta cambiar ningún nombre: el bucket, los security groups y la base llevan un sufijo aleatorio, así que no chocan con recursos existentes.

## Modo de uso

```bash
cd ej2
python3 deploy.py     # tarda unos 15 minutos (la base de datos es lo más lento)
```

Cada ejecución crea recursos nuevos con un sufijo distinto. Para empezar de cero hay que borrar a mano los anteriores desde la consola de AWS (ver *Pendientes de revisar*). Se puede ejecutar desde cualquier carpeta (`python3 ej2/deploy.py`).

## Qué hace el despliegue

| Paso | Qué hace | Función |
|---|---|---|
| 2 | Lee la contraseña de la base de la variable de entorno | `leer_password` |
| 3 | Crea el bucket S3 y sube los artefactos | `crear_bucket_y_subir_artefactos` |
| 4 | Crea los tres security groups y sus reglas encadenadas | `crear_security_groups` |
| 5 | Crea la RDS PostgreSQL 16 sin IP pública, espera a que esté disponible y obtiene el endpoint | `crear_base_de_datos` |
| 6 | Arma el user data de cada instancia reemplazando los marcadores `__NOMBRE__` | `armar_user_data` |
| 7 | Lanza la EC2 backend (descarga el binario, crea el servicio systemd y el `.env`) | `crear_instancia` |
| 8 | Lanza la EC2 frontend con la IP privada del backend (Nginx + estáticos) | `crear_instancia` |
| 9 | Por SSM: completa CORS con la IP del frontend, reinicia la API y verifica el `/health` del backend y de Nginx | `configurar_backend`, `verificar_frontend` |

## Verificación

Al terminar, el script imprime la URL pública. Se puede comprobar con:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<IP_FRONTEND>/    # 200
curl -s http://<IP_FRONTEND>/health
```

En el navegador, abrir `http://<IP_FRONTEND>` (con `http://` explícito: no hay HTTPS). La documentación de la API está en `/docs`.

## Seguridad

- La contraseña de la base no está en el código: se lee de una variable de entorno.
- Security groups encadenados: la base solo acepta tráfico del backend y el backend solo del frontend. Sin puerto 22.
- La RDS no tiene IP pública.
- La API corre con un usuario de sistema sin login, con el `.env` en modo 0600 y un servicio systemd restringido (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`).
- Conexión a la base con TLS (`sslmode=require`) y `JWT_SECRET` aleatorio generado en el arranque.
- `.gitignore` excluye secretos y artefactos.

**Limitación:** el sitio se sirve por HTTP porque el laboratorio no ofrece dominio ni certificado.

## Troubleshooting

| Síntoma | Causa y solución |
|---|---|
| `ExpiredToken` / `Error de AWS` | Las credenciales del lab vencieron: copiar las nuevas a `~/.aws/credentials`. |
| `definí la variable de entorno RDS_ADMIN_PASSWORD` | Exportar la variable antes de ejecutar. |
| `no existe .../artifacts/...` | Copiar los artefactos a `ej2/artifacts/` (ver Configuración previa). |
| El despliegue falla a mitad de camino | Entrar a la instancia sin SSH: `aws ssm start-session --target <id-instancia>` (requiere el *Session Manager plugin* de la AWS CLI) y mirar `sudo journalctl -u servicedesk` (backend), `sudo systemctl status nginx` (frontend) y `sudo cat /var/log/cloud-init-output.log` (user data). En la sesión hay que usar `sudo`. |
| La web no abre justo al terminar | Esperar uno o dos minutos y usar `http://` explícito. |
| `ya existe` / recurso duplicado al volver a ejecutar | Borrar a mano los recursos creados antes (instancias, RDS, security groups, bucket). |

---

# Pendientes de revisar

- **Medidas de seguridad adicionales** (la letra pide aplicar las medidas de seguridad disponibles y no las detalla). Quedaron afuera y hay que revisar si corresponde sumarlas: contraseña de la base en SSM Parameter Store como `SecureString` en vez de en el user data, cifrado del bucket S3, de la RDS y de los discos de las instancias, IMDSv2 obligatorio en las EC2, bloqueo de acceso público del bucket y `server_tokens off` en Nginx.
- **Script de limpieza.** No hay `destroy.py`; los recursos se borran a mano desde la consola. La RDS sigue corriendo con el laboratorio apagado y consume presupuesto.
- **Re-ejecución.** `deploy.py` no reutiliza recursos: cada corrida crea todo de nuevo con otro sufijo. Si se ejecuta varias veces se acumulan instancias y bases.
- Confirmar con la cátedra que la base es PostgreSQL 16 (README de la app) y no MySQL.
- Confirmar que los nombres de los artefactos de los *Releases* coinciden con `ARTEFACTOS` en `config.py` y de dónde sale la carpeta `docs/`.
- Probar el despliegue completo en AWS: el `EngineVersion='16'`, el `aws s3 cp` dentro del user data y los permisos de `LabRole` no se verificaron todavía.

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
```

## ej2/deploy.py

```python
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
rm -f /etc/nginx/conf.d/*.conf

# 3) Virtual host: sirve React y manda /api/, /health y /docs al backend PRIVADO
cat > /etc/nginx/conf.d/servicedesk.conf <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/servicedesk;
    index index.html;
    client_max_body_size 12m;

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

