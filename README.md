# Obligatorio Programación para DevOps

Banco Centralis: reporte de usuarios en Bash (ejercicio 1) y despliegue de la aplicación de tickets ServiceDesk en AWS con Python y Boto3 (ejercicio 2).

## Integrantes

| Nombre | Nº de estudiante |
|---|---|
| _COMPLETAR_ | _COMPLETAR_ |
| _COMPLETAR_ | _COMPLETAR_ |

## Índice

1. [Ejercicio 1: reporte de usuarios (Bash)](#ejercicio-1-reporte-de-usuarios-bash)
2. [Ejercicio 2: despliegue en AWS (Python + Boto3)](#ejercicio-2-despliegue-en-aws-python--boto3)
3. [Uso de IA generativa](#uso-de-ia-generativa)
4. [Código completo de los scripts](#código-completo-de-los-scripts)

## Estructura del repositorio

```
.
├── README.md                       documentación completa (este archivo)
├── .gitignore                      deja afuera secretos y archivos de Python
├── docs/img/                       capturas de pantalla
├── ej1/
│   └── ej1_reporte_usuarios.sh     script de Bash
├── ej2/
│   └── deploy.py                   script de Python que hace todo el despliegue
└── artifacts/                      archivos de la aplicación, descargados del release de la cátedra
    ├── servicedesk                 backend (binario de la API)
    └── web.tar.gz                  frontend (archivos de React)
```

---

# Ejercicio 1: reporte de usuarios (Bash)

## Descripción

`ej1/ej1_reporte_usuarios.sh` lista los usuarios del sistema leyendo `/etc/passwd` (no usa el comando `id`). Por cada usuario imprime una línea con estos campos, separados por tabulador:

| Campo | Ejemplo |
|---|---|
| Nombre | `ana` |
| UID | `1000` |
| Directorio home | `/home/ana` |
| Shell de login | `/bin/bash` |
| ¿El home existe y es un directorio? | `SI` / `NO` |
| ¿El usuario es dueño de su home? | `SI` / `NO` |

Al final imprime el total: `1 usuario listado` o `N usuarios listados`.

## Requisitos

- Linux con Bash y los comandos básicos (`cut`, `grep`, `stat`). Probado en Ubuntu.
- Permiso de lectura sobre `/etc/passwd` (cualquier usuario lo tiene; no hace falta root).

## Modo de uso

```bash
chmod +x ej1/ej1_reporte_usuarios.sh
./ej1/ej1_reporte_usuarios.sh [-t] [-s] [-f] [Usuario]
```

| Opción | Qué hace |
|---|---|
| _(sin opciones)_ | Lista los usuarios con UID mayor o igual a 1000. |
| `-t` | Incluye también los usuarios con UID menor a 1000 (root y usuarios de sistema). |
| `-s` | Lista solo los usuarios con shell `/bin/bash`. |
| `-f` | Lista solo los usuarios cuyo home existe y es un directorio. |
| `Usuario` | Analiza solo ese usuario. Sin `-t` también se le aplica el filtro de UID. |

- Los modificadores se combinan entre sí: `-t -s -f` es lo mismo que `-tsf`.
- Van siempre **antes** del usuario. `ana -t` da error de cantidad de parámetros.

### Ejemplos

```bash
./ej1/ej1_reporte_usuarios.sh              # usuarios comunes
./ej1/ej1_reporte_usuarios.sh -t           # todos, incluido root
./ej1/ej1_reporte_usuarios.sh -s -f        # comunes, con bash y home válido
./ej1/ej1_reporte_usuarios.sh root         # 0 usuarios listados (UID 0 < 1000)
./ej1/ej1_reporte_usuarios.sh -t root      # solo root
```

Salida de `./ej1/ej1_reporte_usuarios.sh` con los usuarios del ejemplo de la letra:

```
ana	1000	/home/ana	/bin/bash	SI	SI
juan	1001	/home/juan	/bin/maligno	NO	NO
2 usuarios listados
```

## Códigos de salida

Los mensajes de error salen por la salida estándar de errores.

| Código | Significado |
|---|---|
| 0 | Ejecución correcta (también si no hay usuarios para listar) |
| 1 | Modificador inválido |
| 2 | Cantidad de parámetros incorrecta |
| 3 | Nombre de usuario vacío |
| 4 | `/etc/passwd` no existe |
| 5 | `/etc/passwd` no es un archivo regular |
| 6 | Sin permiso de lectura sobre `/etc/passwd` |
| 7 | El usuario no existe |
| 8 | `/etc/passwd` tiene un UID que no es numérico |

## Cómo funciona

1. **Modificadores:** se leen con `getopts`. Un modificador desconocido corta con código 1.
2. **Parámetros:** se cuentan *después* de sacar los modificadores (`shift $((OPTIND - 1))`); solo puede quedar el usuario.
3. **Validar `/etc/passwd`:** que exista, que sea un archivo regular, que se pueda leer y que todos los UID sean números. Se revisa todo antes de imprimir para no dejar una salida a medias.
4. **Validar el usuario:** si se pasó uno, tiene que estar en `/etc/passwd`.
5. **Recorrer los usuarios:** se aplican los filtros (usuario, UID, `-s`, `-f`) y se imprime la línea.
6. **Total:** cantidad de usuarios listados, en singular o plural.

Decisiones:

- **Dueño del home:** se compara el UID del dueño del directorio (`stat -L -c %u`) con el UID del usuario. Se compara por número y no por nombre porque dos usuarios pueden compartir UID. `-L` sigue los enlaces simbólicos, igual que `[ -d ]`.
- **Usuario existente:** se compara el nombre exacto con `=`, para que `ana` no coincida con `anabel`.
- **Líneas con espacios:** se recorre `/etc/passwd` con `IFS` en salto de línea, así un home con espacios no rompe la línea.

## Pruebas realizadas

| Caso | Resultado |
|---|---|
| `root` | `0 usuarios listados` |
| `-t root` | `root 0 /root /bin/bash SI SI` y `1 usuario listado` |
| `juan` (home inexistente, shell `/bin/maligno`) | `NO NO` |
| Home que existe pero es de otro usuario | `SI NO` |
| Home que es un archivo y no un directorio | `NO NO`, y no aparece con `-f` |
| Home con espacios en el nombre | Se lista bien |
| `-s` | No incluye `/usr/bin/bash` ni `/bin/maligno` |
| `-t -s -f` y `-tsf` | Mismo resultado |
| `-x` / `-tx` | Código 1 |
| `-t ana juan` / `ana -t` | Código 2 |
| `""` | Código 3 |
| `noexiste` | Código 7 |
| Ejecutado como usuario común (no root) | Mismo resultado |

## Captura de una ejecución exitosa

_COMPLETAR: guardar la captura en `docs/img/ej1_ok.png` y dejar esta línea:_ `![Ejecución exitosa del ejercicio 1](docs/img/ej1_ok.png)`

El código completo está al final, en [Código completo de los scripts](#código-completo-de-los-scripts).

---

# Ejercicio 2: despliegue en AWS (Python + Boto3)

## Descripción

`ej2/deploy.py` despliega en AWS (AWS Academy Learner Lab) la aplicación de tickets ServiceDesk que entregó el Banco Centralis. La aplicación tiene tres capas: un frontend React servido por Nginx, una API escrita en Go y una base de datos PostgreSQL 16.

Con un solo comando, el script crea toda la infraestructura, instala la aplicación en las instancias y comprueba que funcione de punta a punta. No hay que hacer nada a mano en la consola de AWS.

La aplicación se usa **tal cual la entrega la cátedra**: sus dos archivos compilados están en `artifacts/` sin modificar, y las instancias ejecutan los comandos de instalación de su README.

## Arquitectura

```
                 Internet
                    │  80/TCP
          ┌─────────▼──────────┐
          │  EC2 frontend      │  Nginx: sirve React y reenvía /api, /health y /docs
          └─────────┬──────────┘
                    │  8080/TCP (por IP privada)
          ┌─────────▼──────────┐
          │  EC2 backend       │  API en Go, corre como servicio de systemd
          └─────────┬──────────┘
                    │  5432/TCP (con TLS)
          ┌─────────▼──────────┐
          │  RDS PostgreSQL 16 │  sin IP pública
          └────────────────────┘

  S3 (privado):  archivos de la app que las instancias descargan al arrancar
  SSM:           configuración final y chequeos, sin SSH
```

Cada capa tiene su propio security group y solo acepta tráfico de la capa anterior:

| Security group | Puerto | Origen permitido |
|---|---|---|
| `servicedesk-sg-frontend-<sufijo>` | 80/TCP | Internet (`0.0.0.0/0`) |
| `servicedesk-sg-backend-<sufijo>` | 8080/TCP | Solo el security group del frontend |
| `servicedesk-sg-rds-<sufijo>` | 5432/TCP | Solo el security group del backend |

No se abre el puerto 22 en ningún grupo: los comandos dentro de las instancias se ejecutan por SSM.

`<sufijo>` son 8 caracteres aleatorios que el script genera en cada ejecución (ver [Ejecución](#ejecución)).

## Archivos de la aplicación

La aplicación solo necesita dos archivos, que se descargaron del release [`tsx-v1.0.0`](https://github.com/ORT-AII-ProgramacionDevOps/obligatorio/releases/tag/tsx-v1.0.0) de la cátedra y están en la carpeta `artifacts/` de este repositorio, sin modificar:

| Archivo | Para qué sirve |
|---|---|
| `artifacts/servicedesk` | Backend: binario de la API, donde está la lógica |
| `artifacts/web.tar.gz` | Frontend: la parte visual (React) |

Como están en el repositorio, alcanza con clonarlo para desplegar: no hay que descargar nada más. `deploy.py` los sube a un bucket S3 y cada instancia descarga el suyo al arrancar.

El *user data* de cada instancia (definido dentro de `deploy.py`) contiene los bloques "Backend" y "Frontend" de la sección *Comandos para Instalación en Amazon Linux* del README de la aplicación, **sin cambios** y con sus marcadores (`<ENDPOINT_RDS>`, `<IP_BACKEND>`…), que el script reemplaza antes de crear cada instancia. A esos bloques solo se les agrega:

- antes: la descarga del archivo desde S3, que el README da por hecha;
- después, en el backend: el archivo `servicedesk-backend-ready`, que espera el HealthCheck del README.

## Requisitos

| Requisito | Detalle |
|---|---|
| Sistema operativo | Linux. Los comandos están para Alma Linux / familia Red Hat (`dnf`) y también para Ubuntu (`apt`). |
| Python | 3.9 o superior, con `pip` y `venv`. Se probó con Python 3.13. |
| Boto3 | Se instala con `pip install boto3`. Se probó con Boto3 1.44. |
| AWS CLI | Versión 2. El script no la usa, pero sirve para cargar y comprobar las credenciales, borrar los recursos y diagnosticar problemas. |
| Git | Para clonar el repositorio. |
| Cuenta de AWS | AWS Academy Learner Lab iniciado. El script trabaja en la región `us-east-1` y usa el perfil de instancia `LabInstanceProfile` que trae el laboratorio. |

No hacen falta claves SSH, archivos `.pem` ni configurar nombres: el script genera nombres únicos solo.

## Instalación (una sola vez por máquina)

### 1. Instalar los paquetes del sistema

Alma Linux, Rocky o RHEL:

```bash
sudo dnf install -y python3 python3-pip git unzip
```

Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git unzip curl
```

### 2. Instalar la AWS CLI v2

Si `aws --version` ya muestra `aws-cli/2...`, saltear este paso. Si no, con el instalador oficial ([guía de AWS](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)):

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

Después, fijar la región por defecto (la usan los comandos de [Limpieza](#limpieza)):

```bash
aws configure set region us-east-1
```

### 3. Clonar el repositorio

El repositorio es privado: hay que tener acceso como colaborador. La forma más simple de autenticarse es la CLI de GitHub (`gh auth login`).

```bash
cd ~
git clone https://github.com/Juansi946/TESTObligatorio-Programacion-DevOps.git
```

Comprobar que llegaron los archivos de la aplicación (tienen que aparecer `servicedesk`, de unos 23 MB, y `web.tar.gz`):

```bash
ls -lh ~/TESTObligatorio-Programacion-DevOps/artifacts
```

### 4. Crear el entorno virtual e instalar Boto3

Desde la carpeta de este repositorio:

```bash
cd ~/TESTObligatorio-Programacion-DevOps
python3 -m venv .venv
source .venv/bin/activate
pip install boto3
python3 -c "import boto3; print(boto3.__version__)"     # tiene que imprimir una versión
```

- Con el entorno activo, el prompt empieza con `(.venv)`.
- **El entorno se activa por terminal.** En cada terminal nueva hay que volver a ejecutar `source .venv/bin/activate` desde la carpeta del repositorio. Si no, aparece el error `No module named 'boto3'`.
- El entorno virtual evita el error *externally-managed-environment* de `pip` y no mezcla paquetes con los del sistema. La carpeta `.venv/` está en `.gitignore`.

## Antes de cada ejecución

### 1. Iniciar el laboratorio y cargar las credenciales

1. En AWS Academy, entrar al Learner Lab y hacer clic en **Start Lab**. Esperar a que el círculo se ponga verde.
2. Hacer clic en **AWS Details** y, en *AWS CLI*, en **Show**.
3. Copiar el bloque **completo**: la línea `[default]` y las tres claves (`aws_access_key_id`, `aws_secret_access_key` y `aws_session_token`).
4. Pegarlo en `~/.aws/credentials`, reemplazando todo lo que hubiera. Por ejemplo, con `nano` (o `vi`):

   ```bash
   mkdir -p ~/.aws
   nano ~/.aws/credentials      # pegar, guardar con Ctrl+O y salir con Ctrl+X
   ```

5. Comprobar que funcionan:

   ```bash
   aws sts get-caller-identity     # tiene que devolver un JSON con UserId, Account y Arn
   ```

Las credenciales duran unas 4 horas y **cambian en cada sesión del laboratorio**: al iniciar una sesión nueva hay que repetir estos pasos.

### 2. Elegir la contraseña de la base de datos

La contraseña de la base no está en el código ni en el repositorio: la elige quien despliega, en el momento. Hay dos formas de pasarla, y cualquiera sirve:

- **Que el script la pida.** Si no se hace nada, al ejecutar `deploy.py` aparece `Contraseña para la base de datos:` y se escribe sin que se vea en pantalla.
- **Una variable de entorno**, útil para no tener que escribirla en cada ejecución:

  ```bash
  read -s -p "Contraseña para la base de datos: " RDS_ADMIN_PASSWORD && echo
  export RDS_ADMIN_PASSWORD
  ```

  `read -s` no muestra la contraseña y no la deja guardada en el historial de comandos, cosa que sí pasaría con `export RDS_ADMIN_PASSWORD='...'`. La variable solo existe en esa terminal.

Requisitos de la contraseña (el script los controla antes de crear nada):

- al menos 8 caracteres;
- sin `/`, `@`, `"`, `'`, `$`, `` ` ``, `\` ni espacios.

Ejemplo de contraseña válida: `ServiceDesk2026`.

## Ejecución

Con el entorno virtual activo, desde la carpeta de este repositorio:

```bash
python3 ej2/deploy.py
```

También funciona desde adentro de `ej2/` (`python3 deploy.py`).

- Antes de crear nada, comprueba que estén los dos archivos de `artifacts/` y que la contraseña sea válida.
- Tarda entre 15 y 20 minutos. La base de datos es lo más lento (5 a 10 minutos). No cerrar la terminal mientras corre.
- Al empezar, imprime el **sufijo** del despliegue. Todos los recursos lo llevan en el nombre y en el tag `Despliegue`. Anotarlo: sirve para borrarlos después.
- Al terminar, imprime la URL de la aplicación y la lista de recursos creados.

Salida resumida de una ejecución correcta:

```
Despliegue de ServiceDesk - Banco Centralis (región us-east-1)
Sufijo de este despliegue: 3f9a1c0b

=== Paso 1: archivos de la app y contraseña de la base ===
Archivos de la app encontrados: servicedesk, web.tar.gz
Contraseña válida (no se muestra por seguridad)

=== Paso 2: bucket S3 y artefactos ===
Bucket creado: servicedesk-artefactos-3f9a1c0b
...
=== Paso 7: ajuste final y chequeos ===
API (backend) responde: {"status":"ok"}
Nginx -> API responde: {"status":"ok"}
Web (/): OK
API + base (/api/v1/categories): OK

=== Despliegue terminado ===
Aplicación:    http://<IP_PUBLICA>
```

> **Cada ejecución crea un despliegue nuevo y completo**, con otro sufijo. Ejecutar el script dos veces deja dos copias corriendo y gasta el doble del presupuesto del laboratorio. Para volver a desplegar, primero borrar el anterior (ver [Limpieza](#limpieza)).

## Qué hace el script

| Paso | Qué hace | Por qué va en ese orden | Función |
|---|---|---|---|
| 1 | Comprueba que estén los dos archivos de `artifacts/` y toma la contraseña (variable de entorno o teclado) y la valida | Si algo faltara o la contraseña fuera inválida, se descubriría con recursos ya creados | `verificar_archivos_app`, `leer_password` |
| 2 | Crea el bucket S3 y sube los dos archivos de la app | El *user data* tiene un límite de 16 KB y el binario pesa 23 MB: las instancias lo descargan de S3 | `crear_bucket_y_subir_artefactos` |
| 3 | Crea los tres security groups y sus reglas encadenadas | Se pasan a las instancias y a la base al crearlas | `crear_security_groups` |
| 4 | Crea la RDS PostgreSQL 16 sin IP pública, espera a que esté disponible y obtiene el endpoint | El backend necesita el endpoint para conectarse | `crear_base_de_datos` |
| 5 | Obtiene la última AMI de Amazon Linux 2023, completa el *user data* del backend y lanza la EC2 backend | El frontend necesita la IP privada del backend para Nginx | `obtener_ami`, `armar_user_data`, `crear_instancia` |
| 6 | Completa el *user data* del frontend y lanza la EC2 frontend. Espera a que las dos instancias estén listas y obtiene la IP pública del frontend | El backend necesita la IP pública del frontend para CORS | `armar_user_data`, `crear_instancia` |
| 7 | Por SSM: completa `FRONTEND_ORIGIN` en el backend, reinicia la API y hace los chequeos | Es lo último que falta para que la aplicación quede funcionando | `configurar_backend`, `verificar_frontend`, `verificar_desde_internet` |

Qué hace cada instancia al arrancar (*user data*, con los comandos del README de la aplicación):

- **Backend:** descarga el binario desde S3, crea un usuario de sistema sin login, escribe `/opt/servicedesk/.env` (conexión TLS a RDS y un `JWT_SECRET` aleatorio) y deja la API corriendo como servicio de systemd. `FRONTEND_ORIGIN` queda con el marcador `<IP_FRONTEND>` hasta el paso 7.
- **Frontend:** descarga `web.tar.gz` desde S3, instala Nginx, publica los estáticos y configura el reenvío de `/api/`, `/health` y `/docs` a la IP privada del backend.

## Verificación

### Chequeos automáticos (paso 7)

El script termina con error si alguno falla:

| Chequeo | Qué comprueba |
|---|---|
| `API (backend) responde` | La API arrancó. Como se conecta a la base al iniciar y se cierra si no puede, también comprueba la conexión con RDS. |
| `Nginx -> API responde` | Nginx reenvía las peticiones al backend por la red privada. |
| `Web (/): OK` | La página se sirve por la IP pública, pasando por Internet y por el security group del puerto 80. |
| `API + base (/api/v1/categories): OK` | La cadena completa desde Internet: Nginx → API → RDS. |

### Prueba manual en el navegador

1. Abrir `http://<IP_PUBLICA>` escribiendo `http://` a mano. El sitio no tiene HTTPS: si el navegador cambia la dirección a `https://`, la página queda cargando.
2. Iniciar sesión con el administrador demo que crea la aplicación: `admin@servicedesk.local` / `admin123`.
3. Probar las funciones: crear un ticket, agregarle un comentario y un adjunto (PDF o PNG de hasta 10 MB), cambiarle el estado y ver la auditoría, crear una categoría y un usuario, y revisar `/reportes`.

Desde la terminal también se puede comprobar:

```bash
curl http://<IP_PUBLICA>/health      # {"status":"ok"}
```

## Seguridad

| Medida | Dónde |
|---|---|
| La contraseña de la base no está en el código ni en el repositorio: se toma de una variable de entorno o se pide sin mostrarla, y se valida antes de crear nada. | `deploy.py`, paso 1 |
| Tres security groups encadenados. Cada regla abre un solo puerto TCP. El backend y la base no son accesibles desde Internet. | `deploy.py`, paso 3 |
| Sin puerto 22 ni claves SSH: la administración y los chequeos van por SSM. | `deploy.py`, paso 7 |
| La base no tiene IP pública y la API se conecta con TLS (`sslmode=require`). | `deploy.py`, paso 4 y *user data* del backend |
| El bucket es privado: S3 bloquea el acceso público y cifra los objetos por defecto. Las instancias lo leen con el perfil `LabInstanceProfile`. | `deploy.py`, paso 2 |
| Las instancias exigen IMDSv2 para leer sus metadatos: Amazon Linux 2023 lo configura así por defecto. | `deploy.py`, pasos 5 y 6 |
| La API no corre como root: usa un usuario de sistema sin login, con un servicio de systemd restringido (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`). | *User data* del backend (README de la app) |
| `/opt/servicedesk/.env` tiene permisos `0600` y el `JWT_SECRET` se genera al azar en cada instancia. | *User data* del backend (README de la app) |
| El backend solo recibe tráfico a través de Nginx, por la IP privada. | *User data* del frontend (README de la app) |
| Las credenciales de AWS quedan en `~/.aws/credentials`, fuera del repositorio. `.gitignore` excluye `.env` y `*.pem`, y el repositorio es privado. | `.gitignore` |

Límites conocidos:

- **Sin HTTPS.** El laboratorio no ofrece dominio ni certificado, y la cátedra indicó que no hace falta.
- **La contraseña de la base viaja en el *user data* del backend**, igual que en el diseño del README de la aplicación. No está en el código ni en el repositorio, pero alguien con acceso a la consola de esa cuenta de AWS podría verla en la configuración de la instancia.
- **Usuarios demo.** La aplicación crea usuarios de prueba con la contraseña `admin123` y su API no tiene una forma de cambiarla. Es parte de la aplicación entregada.

## Limpieza

Los recursos **no se borran** al terminar la sesión del laboratorio, y la base de datos sigue consumiendo presupuesto. Para borrar un despliegue, usar el sufijo que imprimió `deploy.py`. El orden importa: cada recurso tiene que quedar libre antes de borrar el siguiente.

```bash
SUFIJO=3f9a1c0b     # reemplazar por el sufijo del despliegue

# 1. Terminar las dos instancias (libera los security groups del frontend y del backend)
IDS=$(aws ec2 describe-instances \
  --filters "Name=tag:Despliegue,Values=$SUFIJO" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query "Reservations[].Instances[].InstanceId" --output text)
aws ec2 terminate-instances --instance-ids $IDS
aws ec2 wait instance-terminated --instance-ids $IDS

# 2. Borrar la base de datos (tarda unos minutos; libera su security group)
aws rds delete-db-instance --db-instance-identifier "servicedesk-db-$SUFIJO" --skip-final-snapshot
aws rds wait db-instance-deleted --db-instance-identifier "servicedesk-db-$SUFIJO"

# 3. Borrar los security groups, del más interno al más externo
aws ec2 delete-security-group --group-name "servicedesk-sg-rds-$SUFIJO"
aws ec2 delete-security-group --group-name "servicedesk-sg-backend-$SUFIJO"
aws ec2 delete-security-group --group-name "servicedesk-sg-frontend-$SUFIJO"

# 4. Vaciar y borrar el bucket
aws s3 rb "s3://servicedesk-artefactos-$SUFIJO" --force
```

También se puede hacer desde la consola de AWS, en el mismo orden: EC2 (instancias), RDS, EC2 (security groups) y S3.

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'boto3'` | El entorno virtual no está activo en esa terminal, o Boto3 no se instaló. | Desde la carpeta del repositorio: `source .venv/bin/activate` y `pip install boto3`. |
| `error: externally-managed-environment` al usar `pip` | Se usó `pip` fuera del entorno virtual (pasa en Ubuntu y Debian recientes). | Crear y activar el entorno virtual ([Instalación, paso 4](#4-crear-el-entorno-virtual-e-instalar-boto3)). |
| `ERROR: no encuentro .../artifacts/...` | Falta alguno de los dos archivos en la copia local del repositorio. | Ejecutar `git status` y `git checkout -- artifacts` para recuperarlos. |
| `Unable to locate credentials` o `NoCredentialsError` | No existe `~/.aws/credentials` o está vacío. | Cargar las credenciales ([Antes de cada ejecución, paso 1](#1-iniciar-el-laboratorio-y-cargar-las-credenciales)). |
| `Error de AWS: ... ExpiredToken` o `InvalidClientTokenId` | Las credenciales vencieron (duran unas 4 horas) o son de una sesión anterior. | Copiar las credenciales nuevas del laboratorio a `~/.aws/credentials`. |
| `ERROR: la contraseña ...` | La contraseña no cumple los requisitos. | Elegir otra ([requisitos](#2-elegir-la-contraseña-de-la-base-de-datos)). |
| El navegador dice que no encuentra el sitio `http`, o la página queda cargando | La dirección quedó mal escrita (por ejemplo `http//IP`) o el navegador la cambió a `https://`. | Escribir `http://<IP_PUBLICA>` exacto, o probar en una ventana de incógnito. Para descartar el navegador: `curl http://<IP_PUBLICA>/health`. |
| `ERROR ejecutando comandos en i-...: Failed` en el paso 7 | Falló el *user data* o la aplicación no arrancó. | Ver abajo cómo revisar los logs. Después, borrar el despliegue ([Limpieza](#limpieza)) y volver a ejecutar. |
| `InvalidInstanceId` en el paso 7 | El agente de SSM de la instancia todavía no se había registrado. Es poco común. | Borrar el despliegue y volver a ejecutar. |

**Cómo revisar los logs de una instancia.** Con el *Session Manager plugin* de la AWS CLI instalado, se abre una terminal en la instancia sin SSH:

```bash
aws ssm start-session --target <ID_DE_LA_INSTANCIA>
sudo cat /var/log/cloud-init-output.log     # salida del user data
sudo journalctl -u servicedesk              # logs de la API (backend)
sudo systemctl status nginx                 # estado de Nginx (frontend)
```

Sin el plugin, se puede ver el final del arranque desde la máquina local:

```bash
aws ec2 get-console-output --instance-id <ID_DE_LA_INSTANCIA> --output text | tail -50
```

---

# Uso de IA generativa

_BORRADOR: revisar y completar con lo que realmente usaron (la letra exige declararlo)._

| Herramienta | Contexto de uso |
|---|---|
| Claude (Anthropic), en claude.ai | Planificación de los dos ejercicios, generación y revisión de código, revisión de que el código saliera del material del curso, redacción y corrección del README, y diagnóstico de errores durante las pruebas. |

Prompts principales:

1. _COMPLETAR_ (por ejemplo: pedido del plan de resolución del ejercicio 2 a partir de la letra y del README de la aplicación).
2. _COMPLETAR_ (por ejemplo: pedido de validar el código del ejercicio 2 contra los materiales de clase y la letra, y de ordenar los comentarios).
3. _COMPLETAR_ (por ejemplo: errores que aparecieron al probar el despliegue y cómo se resolvieron).

Qué se verificó a mano: _COMPLETAR_ (por ejemplo: despliegue completo en el Learner Lab, prueba de todas las funciones de la aplicación desde el navegador, casos de prueba del script de Bash).

---

# Código completo de los scripts

## ej1/ej1_reporte_usuarios.sh

```bash
#!/bin/bash
#
# ej1_reporte_usuarios.sh [-t] [-s] [-f] [Usuario]
#
# Lista los usuarios de /etc/passwd. Por cada uno muestra, separado por tab:
#   nombre  UID  home  shell  home_existe(SI/NO)  es_dueño(SI/NO)
#
# Modificadores (se pueden combinar, juntos o separados):
#   -t  incluye también los usuarios con UID < 1000
#   -s  solo usuarios con shell /bin/bash
#   -f  solo usuarios cuyo home existe y es un directorio
#
# Códigos de salida:
#   0  OK
#   1  modificador inválido
#   2  cantidad de parámetros incorrecta
#   3  nombre de usuario vacío
#   4  /etc/passwd no existe
#   5  /etc/passwd no es un archivo regular
#   6  sin permiso de lectura sobre /etc/passwd
#   7  el usuario no existe
#   8  hay un UID que no es numérico en /etc/passwd

# ===== Constantes =====
PASSWD=/etc/passwd
UID_MINIMO=1000
SHELL_BUSCADA=/bin/bash
SEP=$'\t'
SINTAXIS="Uso: $0 [-t] [-s] [-f] [Usuario]"

# ===== Funciones =====

# Devuelve 0 si el usuario ($1) está en /etc/passwd.
# Comparo con "=" y no con grep para que "ana" no matchee con "anabel".
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

# ===== Valores por defecto =====
todos=0          # -t
solo_bash=0      # -s
solo_home=0      # -f
usuario=""       # vacío = todos los usuarios

# ===== 1. Modificadores =====
# El ":" al inicio evita los mensajes propios de getopts;
# si llega una letra inválida queda en $OPTARG.
while getopts ":tsf" modificador
do
    case $modificador in
        t) todos=1 ;;
        s) solo_bash=1 ;;
        f) solo_home=1 ;;
        *) echo "Error: modificador inválido '-$OPTARG'. $SINTAXIS" >&2
           exit 1 ;;
    esac
done

# Saco los modificadores ya leídos; si vino usuario queda en $1
shift $((OPTIND - 1))

# ===== 2. Parámetros =====
# Se cuenta después de los modificadores: solo puede quedar el usuario
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

# ===== 3. Validar /etc/passwd =====
if [ ! -e "$PASSWD" ]
then
    echo "Error: el archivo $PASSWD no existe" >&2
    exit 4
fi

if [ ! -f "$PASSWD" ]
then
    echo "Error: $PASSWD no es un archivo regular" >&2
    exit 5
fi

if [ ! -r "$PASSWD" ]
then
    echo "Error: no hay permiso de lectura sobre $PASSWD" >&2
    exit 6
fi

# Reviso todos los UID antes de imprimir, para no dejar la salida a medias.
# Saco las líneas vacías, tomo el campo 3 y busco alguno que no sea número.
if grep -v "^$" "$PASSWD" | cut -d: -f3 | grep -qv "^[0-9][0-9]*$"
then
    echo "Error: $PASSWD tiene al menos una línea con un UID que no es un número" >&2
    exit 8
fi

# ===== 4. Validar el usuario =====
if [ -n "$usuario" ] && ! usuario_existe "$usuario"
then
    echo "Error: el usuario '$usuario' no existe" >&2
    exit 7
fi

# ===== 5. Recorrer los usuarios =====
# Campos: 1 nombre, 3 UID, 6 home, 7 shell.
# IFS en enter para recorrer línea por línea aunque haya espacios.
cantidad=0
IFS=$'\n'
for linea in $(cut -d: -f1,3,6,7 "$PASSWD")
do
    nombre=$(echo "$linea" | cut -d: -f1)
    uid=$(echo "$linea" | cut -d: -f2)
    home=$(echo "$linea" | cut -d: -f3)
    shell=$(echo "$linea" | cut -d: -f4)

    # Si se pidió un usuario, salteo los demás
    if [ -n "$usuario" ] && [ "$nombre" != "$usuario" ]
    then
        continue
    fi

    # Sin -t, salteo los UID < 1000
    if [ "$todos" -eq 0 ] && [ "$uid" -lt "$UID_MINIMO" ]
    then
        continue
    fi

    # Con -s, salteo los que no usan /bin/bash
    if [ "$solo_bash" -eq 1 ] && [ "$shell" != "$SHELL_BUSCADA" ]
    then
        continue
    fi

    # Home: ¿existe y es directorio? ¿el usuario es el dueño?
    home_ok=NO
    propietario=NO
    if [ -d "$home" ]
    then
        home_ok=SI
        # Comparo por UID y no por nombre (dos usuarios pueden compartir UID).
        # -L sigue los enlaces, igual que [ -d ].
        dueno_uid=$(stat -L -c %u "$home" 2>/dev/null)
        if [ "$dueno_uid" = "$uid" ]
        then
            propietario=SI
        fi
    fi

    # Con -f, salteo los que no tienen home válido
    if [ "$solo_home" -eq 1 ] && [ "$home_ok" = "NO" ]
    then
        continue
    fi

    echo "$nombre$SEP$uid$SEP$home$SEP$shell$SEP$home_ok$SEP$propietario"
    cantidad=$((cantidad + 1))
done

# ===== 6. Total =====
if [ "$cantidad" -eq 1 ]
then
    echo "1 usuario listado"
else
    echo "$cantidad usuarios listados"
fi

exit 0
```

## ej2/deploy.py

```python
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
# Uso:
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

# Tags que llevan todos los recursos
TAGS = [
    {'Key': 'Proyecto', 'Value': 'obligatorio-devops'},
    {'Key': 'Cliente', 'Value': 'banco-centralis'},
    {'Key': 'Ambiente', 'Value': 'produccion'},
    {'Key': 'Despliegue', 'Value': SUFIJO},
]

# Contraseña de la base
VARIABLE_PASSWORD = 'RDS_ADMIN_PASSWORD'

# Archivos de la app, en la carpeta artifacts/ de la raíz del repositorio.
# La ruta se arma desde la carpeta del script, así funciona desde cualquier carpeta.
CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CARPETA_ARTEFACTOS = os.path.join(CARPETA_SCRIPT, '..', 'artifacts')
ARTEFACTOS = [
    'servicedesk',           # backend: binario de la API
    'web.tar.gz',            # frontend: archivos de React
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
    for artefacto in ARTEFACTOS:
        ruta = os.path.join(CARPETA_ARTEFACTOS, artefacto)
        try:
            open(ruta).close()
        except FileNotFoundError:
            print(f"ERROR: no encuentro {ruta}")
            print("Revisá la carpeta artifacts/ del repositorio (ver README)")
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

    for artefacto in ARTEFACTOS:
        s3.upload_file(os.path.join(CARPETA_ARTEFACTOS, artefacto), BUCKET, artefacto)
        print(f"Subido: {artefacto}")


# Paso 3: security groups
def crear_security_group(nombre, descripcion):
    # Sin VpcId se crea en la VPC por defecto, la misma que usan EC2 y RDS
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
    # Abre un solo puerto TCP. origen puede ser un rango de IP (IpRanges)
    # o otro security group (UserIdGroupPairs).
    regla = {'IpProtocol': 'tcp', 'FromPort': puerto, 'ToPort': puerto}
    regla.update(origen)
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[regla])


def crear_security_groups():
    # Uno por capa. Solo el frontend recibe tráfico de Internet.
    sg_frontend = crear_security_group(SG_FRONTEND, 'HTTP publico hacia Nginx')
    sg_backend = crear_security_group(SG_BACKEND, 'API 8080 solo desde el frontend')
    sg_rds = crear_security_group(SG_RDS, 'PostgreSQL 5432 solo desde el backend')

    # Frontend: 80 abierto a todos
    agregar_regla(sg_frontend, 80, {'IpRanges': [{'CidrIp': '0.0.0.0/0'}]})
    # Backend: 8080 solo desde el frontend
    agregar_regla(sg_backend, 8080, {'UserIdGroupPairs': [{'GroupId': sg_frontend}]})
    # Base: 5432 solo desde el backend
    agregar_regla(sg_rds, 5432, {'UserIdGroupPairs': [{'GroupId': sg_backend}]})

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
        BackupRetentionPeriod=0,          # sin backups automáticos
        Tags=TAGS
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

    # Consulta el estado cada 5 segundos hasta que termine. No se usa el waiter
    # de SSM porque espera menos de 2 minutos y acá puede tardar más.
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
        f"curl --fail --silent --output /dev/null {url}/ && echo 'Web (/): OK'",
        f"curl --fail --silent --output /dev/null {url}/api/v1/categories && echo 'API + base (/api/v1/categories): OK'"
    ]
    salida = ejecutar_comandos(backend_id, comandos)
    print(salida.strip())


# Programa principal
def main():
    print(f"Despliegue de ServiceDesk - Banco Centralis (región {REGION})")
    # El sufijo identifica los recursos de esta ejecución (sirve para borrarlos)
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
    # La IP pública se asigna después de crearla, por eso se consulta ahora
    response = ec2.describe_instances(InstanceIds=[frontend_id])
    ip_frontend = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
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
```
