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
