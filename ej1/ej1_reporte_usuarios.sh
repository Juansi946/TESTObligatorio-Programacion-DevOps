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
