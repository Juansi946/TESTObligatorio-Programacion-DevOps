#!/bin/bash
#
# ej1_reporte_usuarios.sh [-t] [-s] [-f] [Usuario]
#
# Lista información de los usuarios del sistema a partir de /etc/passwd.
# Por cada usuario muestra, separados por tabulador:
#   nombre  UID  home  shell  home_existe(SI/NO)  es_propietario(SI/NO)
#
# Modificadores (se pueden combinar, juntos o separados, en cualquier orden):
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
#   5  /etc/passwd no es un archivo regular
#   6  no hay permiso de lectura sobre /etc/passwd
#   7  el usuario recibido no existe
#   8  /etc/passwd tiene una línea con un UID que no es un número

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
# getopts recorre los modificadores en cualquier orden y acepta tanto
# "-t -s" como "-ts". El ":" inicial de ":tsf" hace que getopts no imprima
# sus propios errores: ante un modificador desconocido devuelve "?" y deja
# la letra en $OPTARG, así el mensaje lo arma el script.
# getopts se detiene en el primer parámetro que no empieza con "-": ese
# tiene que ser el usuario.
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

# OPTIND quedó apuntando al primer parámetro que no es modificador.
# Con shift se descartan los modificadores ya procesados, así el usuario
# (si vino) queda en $1.
shift $((OPTIND - 1))

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

# Existe, pero tiene que ser un archivo regular (no un directorio, etc.)
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

# Antes de imprimir nada se revisa que todos los UID sean números, así un
# archivo corrupto no deja una salida a medias. Se ignoran las líneas
# vacías; de las demás se toma el campo 3 (UID) y grep -qv busca alguno que
# NO sea solo dígitos (un UID vacío también cuenta como inválido).
if grep -v "^$" "$PASSWD" | cut -d: -f3 | grep -qv "^[0-9][0-9]*$"
then
    echo "Error: $PASSWD tiene al menos una línea con un UID que no es un número" >&2
    exit 8
fi

# ---------- Validar que el usuario exista ----------
if [ -n "$usuario" ] && ! usuario_existe "$usuario"
then
    echo "Error: el usuario '$usuario' no existe" >&2
    exit 7
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
        # stat -c %u devuelve el UID del dueño del directorio y se compara
        # con el UID del usuario leído de /etc/passwd. Se compara el número
        # y no el nombre porque Linux registra al dueño por UID: si dos
        # usuarios comparten UID, el nombre que muestra ls sería el de
        # otro. -L hace que stat siga los enlaces simbólicos, igual que
        # [ -d ], para mirar el dueño del directorio real y no del enlace.
        dueno_uid=$(stat -L -c %u "$home" 2>/dev/null)
        if [ "$dueno_uid" = "$uid" ]
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
