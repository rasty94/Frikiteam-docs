---
title: "Bash y APIs REST — curl, jq y scripts que no mienten"
description: "Consumir APIs REST desde Bash con curl y jq: manejo real de errores HTTP, paginación, reintentos con backoff, secretos fuera del script y un checker de servicios como ejemplo completo."
keywords: "bash, curl, jq, api rest, scripting, http, retry, backoff, monitorizacion, shell"
tags: [linux, bash, scripting, api]
updated: 2026-08-03
difficulty: intermediate
estimated_time: 18 min
category: Linux
status: published
last_reviewed: 2026-08-03
prerequisites:
  - "Bash básico"
  - "Nociones de HTTP (métodos, códigos de estado)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Bash y APIs REST — curl, jq y scripts que no mienten

## El problema

Tienes doce servicios repartidos entre Proxmox, un par de VPS y Kubernetes, y para saber cómo están abres doce pestañas. Escribes un script de dos líneas con `curl`, lo pones en cron, y durante tres semanas te dice que todo va bien. Luego descubres que llevaba tres semanas fallando: `curl` devolvió un 500, el script no miró el código de estado, `jq` no encontró el campo, imprimió `null` y salió con 0.

Un script que consulta APIs es fácil de escribir y sorprendentemente difícil de escribir **de forma que falle cuando debe fallar**. Esta página va sobre esa segunda parte.

## 📋 Tabla de Contenidos

- [La base que casi nadie pone](#la-base-que-casi-nadie-pone)
- [curl: separar cuerpo, estado y errores de red](#curl-separar-cuerpo-estado-y-errores-de-red)
- [jq: lo que se usa el 90% del tiempo](#jq-lo-que-se-usa-el-90-del-tiempo)
- [Autenticación y secretos](#autenticacion-y-secretos)
- [Reintentos y backoff](#reintentos-y-backoff)
- [Paginación](#paginacion)
- [Ejemplo completo: checker de servicios](#ejemplo-completo-checker-de-servicios)
- [Cuándo dejar Bash](#cuando-dejar-bash)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## La base que casi nadie pone

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
```

| Opción | Qué evita |
|---|---|
| `-e` | Que el script continúe tras un comando fallido |
| `-u` | Que una variable mal escrita se expanda a cadena vacía |
| `-o pipefail` | Que `cmd_que_falla \| jq .` devuelva el estado de `jq` (0) y oculte el fallo |
| `-E` | Que las funciones no hereden el `trap ERR` |

`pipefail` es el importante aquí: **toda** llamada a una API acaba en una tubería hacia `jq`. Sin él, el estado de salida que ves es el del último comando de la tubería, no el del que se rompió.

!!! warning "`set -e` no es una red de seguridad completa"
    No se dispara dentro de condicionales (`if`, `&&`, `||`) ni en sustituciones de comandos en ciertos contextos. Comprueba los estados que importan de forma explícita; `set -e` es el suelo, no el techo.

## curl: separar cuerpo, estado y errores de red

El fallo de base es tratar el cuerpo de la respuesta como si fuera el resultado. Hay tres cosas distintas: si la petición llegó, qué código devolvió y qué contenía.

```bash
api_get() {
    local url=$1
    local body status

    # -s silencia la barra de progreso, -S mantiene los errores visibles
    # --max-time evita el cuelgue indefinido
    # -w escribe el código HTTP al final del cuerpo, en una línea aparte
    if ! body=$(curl -sS --max-time 10 -w $'\n%{http_code}' "$url"); then
        echo "error de red al consultar $url" >&2
        return 1
    fi

    status=${body##*$'\n'}   # última línea
    body=${body%$'\n'*}      # todo lo anterior

    if [[ $status -lt 200 || $status -ge 300 ]]; then
        echo "HTTP $status en $url: $body" >&2
        return 1
    fi

    printf '%s' "$body"
}
```

Tres fallos distintos, tres tratamientos:

- **No hay respuesta** (DNS, timeout, conexión rechazada): `curl` sale distinto de 0. Sin `--max-time`, un servidor que acepta la conexión y no contesta cuelga tu cron para siempre.
- **Hay respuesta pero es un error** (4xx/5xx): `curl` sale 0 igualmente. Por eso hace falta `-w '%{http_code}'`. La alternativa `--fail` es más corta pero descarta el cuerpo, que es justo donde la API te explica qué has hecho mal.
- **Respuesta correcta**: ya puedes pasársela a `jq`.

## jq: lo que se usa el 90% del tiempo

```bash
# Un campo
jq -r '.status' <<<"$body"

# Campo anidado con valor por defecto si no existe
jq -r '.data.uptime // "desconocido"' <<<"$body"

# Filtrar y proyectar una lista
jq -r '.services[] | select(.state != "running") | .name' <<<"$body"

# Varios campos como columnas (TSV, seguro ante espacios)
jq -r '.items[] | [.name, .status, .updated] | @tsv' <<<"$body"

# Contar
jq '[.items[] | select(.healthy == false)] | length' <<<"$body"
```

`-r` (raw) quita las comillas de la salida. Sin él acabas con `"running"` incluyendo comillas y comparaciones que nunca casan — el bug más común y más tonto al usar `jq` desde Bash.

El operador `//` da valor por defecto solo si el resultado es `null` o `false`. Es la diferencia entre un informe que dice "desconocido" y uno que dice "null".

Para saber si un campo existe de verdad:

```bash
if jq -e '.data.token' >/dev/null <<<"$body"; then
    echo "hay token"
fi
```

`-e` fija el estado de salida según el resultado: 1 si es `null` o `false`, 4 si no hay salida. Es lo que convierte a `jq` en algo usable dentro de un `if`.

## Autenticación y secretos

```bash
# MAL: el token queda en el historial y en `ps` para cualquier usuario
curl -H "Authorization: Bearer sk-abc123" https://api.example.com/v1/status
```

Los argumentos de un proceso son públicos en `/proc/<pid>/cmdline`. Cualquier usuario del sistema puede leer ese token mientras el comando corre.

```bash
# BIEN: el token nunca aparece en la línea de comandos
: "${API_TOKEN:?falta API_TOKEN en el entorno}"

curl -sS --max-time 10 \
     -H "@/dev/stdin" \
     https://api.example.com/v1/status <<<"Authorization: Bearer $API_TOKEN"
```

Alternativa más limpia si la API acepta autenticación básica: un fichero `.netrc` con permisos 600.

```bash
# ~/.netrc (chmod 600)
machine api.example.com login usuario password contraseña
```

```bash
curl -sS --netrc https://api.example.com/v1/status
```

La sintaxis `${API_TOKEN:?mensaje}` aborta el script con un mensaje claro si la variable no está definida. Mejor que descubrirlo por un 401 tres pasos más adelante.

Para el fichero de entorno del servicio, ver [gestión de secretos](../cybersecurity/gestion_secretos.md).

## Reintentos y backoff

Un 503 o un timeout puntual no deberían despertar a nadie. Un 401 no se arregla reintentando.

```bash
api_get_retry() {
    local url=$1 max=${2:-4} intento=1 espera=2

    while :; do
        if api_get "$url"; then
            return 0
        fi
        if (( intento >= max )); then
            echo "agotados $max intentos para $url" >&2
            return 1
        fi
        echo "intento $intento fallido, reintentando en ${espera}s" >&2
        sleep "$espera"
        (( espera *= 2, intento++ ))
    done
}
```

2s, 4s, 8s: el backoff exponencial evita convertir un servicio con problemas en un servicio caído. Reintentar cada segundo es participar en el incidente.

!!! tip "curl reintenta solo"
    Para casos sencillos no hace falta el bucle:
    ```bash
    curl -sS --retry 4 --retry-delay 2 --retry-all-errors --max-time 10 "$url"
    ```
    `--retry-all-errors` es necesario porque por defecto `--retry` solo cubre errores transitorios y no los 5xx. Escribe el bucle solo cuando necesites lógica propia entre intentos.

## Paginación

Casi ninguna API devuelve todo de una vez. Dos patrones cubren casi todas:

```bash
# Por cursor (GitHub, Stripe): seguir hasta que no haya siguiente
cursor=""
while :; do
    body=$(api_get "https://api.example.com/items?limit=100${cursor:+&after=$cursor}")
    jq -r '.items[] | .name' <<<"$body"

    cursor=$(jq -r '.next_cursor // empty' <<<"$body")
    [[ -z $cursor ]] && break
done
```

`// empty` devuelve cadena vacía en vez de la palabra `null`, que es lo que hace que la condición de salida funcione.

```bash
# Por página: parar cuando la página venga vacía, no cuando creas que has terminado
pagina=1
while :; do
    body=$(api_get "https://api.example.com/items?page=$pagina&per_page=100")
    n=$(jq '.items | length' <<<"$body")
    (( n == 0 )) && break
    jq -r '.items[].name' <<<"$body"
    (( pagina++ ))
done
```

Pon siempre un tope (`(( pagina > 100 )) && break`): una API que devuelve siempre la misma página convierte tu script en un bucle infinito contra el servidor de otro.

## Ejemplo completo: checker de servicios

Junta todo lo anterior: lee endpoints de un fichero, los consulta en paralelo y sale con código distinto de 0 si algo falla — para que cron te avise de verdad.

{% raw %}

```bash
#!/usr/bin/env bash
# check-servicios.sh — estado de varios endpoints HTTP en una tabla
set -Eeuo pipefail

ENDPOINTS_FILE=${1:-/etc/check-servicios.list}   # una URL por línea, # para comentarios
TIMEOUT=${TIMEOUT:-5}

comprobar() {
    local url=$1 inicio fin ms code
    inicio=$(date +%s%3N)
    code=$(curl -so /dev/null -w '%{http_code}' --max-time "$TIMEOUT" "$url" 2>/dev/null) || code="000"
    fin=$(date +%s%3N)
    ms=$(( fin - inicio ))

    case $code in
        2*|3*) printf '%s\tOK\t%s\t%sms\n'    "$url" "$code" "$ms" ;;
        000)   printf '%s\tCAIDO\tsin-respuesta\t%sms\n' "$url" "$ms" ;;
        *)     printf '%s\tFALLO\t%s\t%sms\n' "$url" "$code" "$ms" ;;
    esac
}
export -f comprobar
export TIMEOUT

mapfile -t urls < <(grep -vE '^\s*(#|$)' "$ENDPOINTS_FILE")
(( ${#urls[@]} )) || { echo "no hay endpoints en $ENDPOINTS_FILE" >&2; exit 2; }

resultados=$(printf '%s\n' "${urls[@]}" | xargs -P 8 -I{} bash -c 'comprobar "$@"' _ {})
printf '%s\n' "$resultados" | sort | column -t -s $'\t'   # sort: xargs -P no garantiza el orden

# Estado de salida: 1 si algo no está OK — cron solo avisa cuando importa
# Ojo: $'\t' (comillas ANSI-C de Bash) produce un tabulador real.
# Con '\t' entre comillas simples, grep -E busca la letra "t" y nunca casa.
! grep -qE $'\t(FALLO|CAIDO)\t' <<<"$resultados"
```

{% endraw %}

```bash
# Autocomprobación mínima: el script debe fallar cuando un endpoint falla
printf 'https://httpbin.org/status/200\nhttps://httpbin.org/status/503\n' > /tmp/ep.list
./check-servicios.sh /tmp/ep.list && echo "MAL: debería haber salido con 1" || echo "OK: detecta el fallo"
```

`xargs -P 8` da paralelismo real: doce endpoints con timeout de 5 s tardan lo que el más lento, no la suma. La última línea es la clave — sin ella el script imprime una tabla preciosa y siempre sale con 0, que es exactamente el problema del principio.

## Cuándo dejar Bash

Bash es imbatible para pegar comandos y encadenar tuberías. Deja de serlo en cuanto aparece:

| Señal | Alternativa |
|---|---|
| Construir JSON complejo para enviarlo | `jq -n` aguanta bastante; más allá, Python |
| Estructuras de datos anidadas en memoria | Python con `requests` |
| Manejo de errores con reintentos por tipo, estado compartido | Python |
| Más de ~150 líneas | Python |
| Concurrencia más allá de `xargs -P` | Python (`asyncio`) o Go |

No es dogma: es que a partir de ahí escribes más código para sortear las limitaciones de Bash que para resolver el problema. Si ya tienes [FastAPI](../programming/fastapi.md) en el stack, el salto es corto.

Para lo verdaderamente sencillo, tampoco escribas nada: [Uptime Kuma](../monitoring/uptime_kuma.md) hace lo del ejemplo anterior con interfaz y notificaciones.

## Buenas prácticas

- **`set -Eeuo pipefail` en la primera línea.** Siempre.
- **Comprueba el código HTTP**, no solo que `curl` no explotara.
- **`--max-time` en cada llamada.** Un cron colgado no avisa de nada.
- **`jq -r` para salida a variables**, y `//` para valores por defecto.
- **Secretos por entorno o `.netrc`**, nunca en la línea de comandos.
- **Backoff exponencial y un número máximo de intentos.**
- **Sal con código distinto de 0 cuando algo falle.** Es lo único que hace que cron y tu monitorización se enteren.
- **Pasa `shellcheck`.** Encuentra en un segundo el 90% de lo que aquí se explica.

```bash
shellcheck check-servicios.sh
```

## Referencias

- [Manual de curl](https://curl.se/docs/manpage.html) · [jq manual](https://jqlang.github.io/jq/manual/)
- [ShellCheck](https://www.shellcheck.net/)
- [Recetas rápidas](../recipes.md) · [Systemd](systemd.md)
- [Uptime Kuma](../monitoring/uptime_kuma.md) · [Gestión de secretos](../cybersecurity/gestion_secretos.md)
