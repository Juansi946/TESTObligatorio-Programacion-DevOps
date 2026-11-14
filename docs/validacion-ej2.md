# Validación del ejercicio 2 (Python + Boto3)

Revisión del 13/11/2026 sobre el código del repo de pruebas (`TESTObligatorio-Programacion-DevOps`, commit `86f291e`). Fuentes contra las que se validó: letra del obligatorio, clases 9, 10, 20, 21 y 22, notas del curso, PDFs py-1 a py-7, repo `Labs` (ejemplos y 12 ejercicios resueltos) y README de la app (`tsx/`).

Marcas: ✅ sale tal cual del material · 🟡 adaptación o dato de la documentación oficial, con su justificación.

## 1. Qué cambió respecto del repo de pruebas

| Cambio | Motivo |
|---|---|
| `config.py` se unió al principio de `deploy.py` | Importar un módulo propio (`import config`) no aparece en ningún material. Los Labs ponen las constantes arriba del script (`ejercicio3.py`, `Ejemplos/ec2+sg+tag.py`). Además ahora hay un solo script para leer y defender. |
| `WaiterConfig` sacado del waiter de RDS | Los valores que tenía (30 s y 60 intentos) son los que el waiter ya usa por defecto. Queda igual a la clase 21. |
| Si no está `RDS_ADMIN_PASSWORD`, la pide con `getpass` | La clase 21 nombra "pedirla con `input()` (o `getpass`)" como alternativa válida. Evita el error de la variable que no existe en esa terminal. |
| Pasos renumerados del 1 al 7 y títulos impresos desde `main()` | Antes arrancaban en "Paso 2" y la numeración no coincidía con la del README. |
| `crear_instancia` devuelve el diccionario de la instancia | Se navega la respuesta como en la clase 20 (`['InstanceId']`, `['PrivateIpAddress']`) y desaparece la variable `ip_privada_frontend`, que no se usaba. |
| Nuevo chequeo `verificar_desde_internet` | La letra pide "hacer los chequeos necesarios" de web y API. `/api/v1/categories` es público y lee la base, así que prueba Internet → Nginx → API → RDS sin contraseñas. |
| Tag `Despliegue = <sufijo>` y sufijo también en el nombre de las EC2 | Permite encontrar y borrar todo lo de una ejecución (sección Limpieza del README). |
| Resumen final con todos los recursos creados | Mismo motivo. |
| `ej2/artifacts/` pasa a estar en el repo | Ver sección 4. |
| Comentarios reescritos en primera persona, por pasos | Pedido explícito. Cada bloque dice qué hace, por qué y de qué ejercicio o clase sale. |

## 2. Trazabilidad del código

### deploy.py

| Construcción | Fuente | |
|---|---|---|
| `#!/usr/bin/env python3` | Clase 14 (shebang) | ✅ |
| `import os`, `os.environ.get(...)` | Labs ej9 | ✅ |
| `import time`, `time.sleep` | Labs ej6, ej12 | ✅ |
| `import getpass` / `getpass.getpass` | Clase 21 (formas de no hardcodear la contraseña) | ✅ |
| `import secrets`, `secrets.token_hex(4)` | Clase 21 (sufijo aleatorio para nombres únicos) | ✅ |
| `from botocore.exceptions import ClientError` | Labs ej1 | ✅ |
| Constantes en mayúscula arriba del script | Labs ej3, `Ejemplos/ec2+sg+tag.py`, `Ejemplos/rds.py` | ✅ |
| `os.path.dirname(os.path.abspath(__file__))`, `os.path.join` | Documentación de Python. Justificación: clase 21 ("nada de rutas fijas", el profe lo ejecuta en su máquina); permite correrlo desde la raíz del repo o desde `ej2/`. | 🟡 |
| `boto3.client('s3', region_name=REGION)` | Clase 20 (un cliente por servicio), `Ejemplos/ec2+sg+tag.py` (`region_name`) | ✅ |
| f-strings | Clase 16, clase 21 | ✅ |
| `len(...)`, `for caracter in password`, `if caracter in '...'` | py-2, py-3, py-4 | ✅ |
| `exit(1)` | Labs ej1 | ✅ |
| `s3.create_bucket(Bucket=...)` | Labs ej1, clase 20 | ✅ |
| `s3.upload_file(ruta, bucket, key)` + `except FileNotFoundError` | Labs ej1, clase 20 | ✅ |
| `ec2.create_security_group(GroupName, Description)` | Labs ej8, clase 20 | ✅ |
| `TagSpecifications` en `create_security_group` | Labs ej12 lo usa en `run_instances`; en security groups es documentación de Boto3 | 🟡 |
| `regla.update(origen)` | Clase 16 (`update` de diccionarios) | ✅ |
| `authorize_security_group_ingress` con `IpRanges` y `UserIdGroupPairs` | Clase 20, clase 21 (código igual), `Ejemplos/sg.py` | ✅ |
| `rds.create_db_instance(...)` con `Engine='postgres'` y `VpcSecurityGroupIds` | Clase 21 | ✅ |
| `EngineVersion` | `Ejemplos/rds.py` | ✅ |
| `PubliclyAccessible=False` | `Ejemplos/rds.py` y Labs ej9 lo usan en `True`; `False` por seguridad (clases 20 y 21: la base no se expone) | ✅ |
| `BackupRetentionPeriod=0` | Labs ej9 | ✅ |
| `Tags=TAGS` en `create_db_instance` | Clase 20 (tags para identificar y controlar costos); el parámetro es de la documentación | 🟡 |
| `rds.get_waiter('db_instance_available').wait(...)` | Clase 21 | ✅ |
| `describe_db_instances(...)['DBInstances'][0]['Endpoint']['Address']` | Clase 21, `Ejemplos/rds.py` | ✅ |
| `open(plantilla).read()` | `Ejemplos/rds.py` | ✅ |
| `.items()` en un `for`, `.replace(...)` | Clase 16, py-4 | ✅ |
| Límite de 16 KB del user data | Clase 20, clase 21 | ✅ |
| AMI desde `ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/...')` | Labs ej12 | ✅ |
| `run_instances` con `SecurityGroupIds`, `IamInstanceProfile`, `UserData`, `TagSpecifications` | `Ejemplos/ec2+sg+tag.py`, Labs ej6, ej7, ej12 | ✅ |
| `response['Instances'][0]['PrivateIpAddress']` | Clase 20 (navegar la respuesta; cada instancia tiene IP privada y pública). La clave es de la documentación | 🟡 |
| `ec2.get_waiter('instance_status_ok').wait(InstanceIds=[a, b])` | Labs ej6, ej12; clase 21 (un waiter con varias instancias) | ✅ |
| `describe_instances(...)['Reservations'][0]['Instances'][0]['PublicIpAddress']` | Labs ej8 (`describe_instances`); la clave es de la documentación | 🟡 |
| `ssm.send_command(DocumentName='AWS-RunShellScript', Parameters={'commands': [...]})` | Labs ej6, ej12, clase 21 | ✅ |
| `while True` + `get_command_invocation` + estados `Success/Failed/Cancelled/TimedOut` | Labs ej6, ej12 | ✅ |
| No usar el waiter `command_executed` | Su espera máxima es de unos 100 s (5 s × 20) y la espera del user data puede ser más larga | ✅ (decisión) |
| `if __name__ == '__main__':` | Labs ej3 | ✅ |
| `try: main() except ClientError as e:` | Labs ej1 | ✅ |

### Comandos de bash dentro de deploy.py (por SSM)

| Comando | Fuente | |
|---|---|---|
| Espera del archivo `-ready`, `systemctl restart servicedesk`, bucle `curl --fail` al `/health` | README de la app (HealthCheck) | ✅ |
| `timeout 600` alrededor de la espera | Agregado: el README espera sin límite | 🟡 |
| `sed -i 's|^FRONTEND_ORIGIN=...|...|'` | Clase 5 (`sed 's/patrón/reemplazo/'`); README de la app ("`IP_FRONTEND` puede actualizarse después mediante SSM") | ✅ |
| `curl ... /api/v1/categories` | README de la app (endpoints y ejemplos `curl`) | ✅ |

### user_data_backend.sh y user_data_frontend.sh

| Parte | Fuente | |
|---|---|---|
| Bloques "Backend" y "Frontend" (usuario sin login, `.env` 0600, JWT con `openssl rand`, TLS, unidad systemd, Nginx) | README de la app, sin cambios | ✅ |
| `#!/bin/bash` | Labs ej7 | ✅ |
| `aws s3 cp` de los artefactos | Clases 20 y 21 dicen que la instancia los descarga de S3; el comando es de la documentación de la AWS CLI. Probado en el lab el 11/11 | 🟡 |
| Copia de `docs/` a `/opt/servicedesk/docs` | `main.go` de la app sirve `/docs` leyendo `docs/index.html` desde su carpeta de trabajo | 🟡 |
| `touch /var/lib/servicedesk-backend-ready` | El README de la app la usa en su HealthCheck pero su bloque no la crea | 🟡 |

## 3. Requisitos de la letra

| Requisito | Estado |
|---|---|
| Script de Python con Boto3 que automatiza el despliegue | ✅ `ej2/deploy.py` |
| Aplicación 100 % funcional (web y API) y chequeos para corroborarlo | ✅ 4 chequeos automáticos + prueba manual documentada. **Falta volver a correrlo en AWS con esta versión.** |
| Todas las medidas de seguridad disponibles | ✅ Contraseña fuera del código, 3 SG encadenados, sin 22, RDS privada con TLS, bucket privado, IMDSv2, API sin root, `.env` 0600. Límites declarados en el README. |
| Cambios trazables en un repositorio privado de GitHub | ✅ El repo final es privado. ⚠️ El repo de pruebas es **público** y tiene todo el código. |
| README con descripción, requisitos, modo de uso | ✅ |
| README con configuraciones necesarias y archivos auxiliares | ✅ |
| README con el código entero de todos los scripts | ✅ Generado desde los archivos; regenerarlo si se cambia el código. |
| Códigos `.sh` y `.py` dentro del repositorio | ✅ |
| Commits por integrante y uso de ramas | Pendiente: lo hacen ustedes al subirlo. |
| Uso de IA declarado (herramientas y contexto) | Borrador en el README; completar. |
| Sin cambios después del 2/12 a las 21:00 | Pendiente. |

## 4. ¿Se pueden subir los archivos de la app al repo?

Sí. Nada en la letra ni en las clases lo prohíbe:

- **Letra:** el README debe documentar "configuraciones necesarias, archivos auxiliares". El límite de 40 MB es del zip que se sube a Gestión (el PDF), no del repositorio.
- **Clase 9:** lo que nunca se sube son secretos (`.env`, tokens, claves). Los artefactos no lo son: son la app compilada que entrega la cátedra, igual para todos los grupos.
- **Clase 21:** el profe ejecuta el código en su máquina y "tiene que andar en la primera corrida". Cada paso manual (descargar, crear la carpeta, buscar `docs/`) es un punto de falla; la clase 20 avisa que cada error que encuentra resta puntos.
- **GitHub:** acepta archivos de hasta 100 MB; el binario pesa 23 MB.
- **El repo de la app** también versiona esos artefactos (su workflow los commitea en `tsx/artifacts`).

Por eso se sacó `ej2/artifacts/` del `.gitignore`, y el problema de la carpeta que no existía desaparece.

## 5. Pendientes

1. Correr de cero esta versión en el lab (clonar, seguir el README) antes de subirla al repo final.
2. Poner **privado** (o borrar) el repo `TESTObligatorio-Programacion-DevOps`: es público y tiene la solución completa.
3. Subir los cambios al repo final con commits de los dos integrantes, en ramas.
4. Completar integrantes, captura del ej1 y la sección de uso de IA.
