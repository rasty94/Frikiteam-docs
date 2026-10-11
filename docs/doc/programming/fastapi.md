---
title: "FastAPI"
description: "Empaquetar y desplegar una API FastAPI: Dockerfile multi-stage, uvicorn/gunicorn con workers, endpoint de health para probes, proxy inverso, Quadlet y CI con GitHub Actions."
keywords: "fastapi, uvicorn, gunicorn, dockerfile, multi-stage, healthcheck, traefik, haproxy, quadlet, github actions"
tags: ['programming', 'api']
updated: 2026-10-11
difficulty: advanced
estimated_time: 21 min
category: Desarrollo
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Python 3 y conceptos básicos de APIs HTTP"
  - "[Docker](../docker/docker_base.md) o Podman"
  - "[Quadlets](../docker/quadlets.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# FastAPI

## El problema

La API funciona en tu portátil con `uvicorn main:app --reload`. En el servidor aparecen las preguntas que el tutorial no contestaba: ¿cuántos procesos?, ¿quién la reinicia si cae?, ¿cómo sabe el balanceador que está lista?, ¿por qué la imagen pesa 1 GB?, ¿por qué los logs muestran la IP del proxy y no la del cliente?

FastAPI es un framework web para APIs en Python basado en las anotaciones de tipo, con validación (Pydantic), documentación OpenAPI automática y soporte asíncrono (Starlette). Esta página no enseña el framework: cubre cómo **construir, empaquetar y desplegar** una app FastAPI sobre la infraestructura de este sitio.

!!! note "Qué cubre y qué no"
    Se parte de una app mínima y se trabaja alrededor de ella: imagen, proceso, salud, proxy, servicio y pipeline. Para el modelo de programación (dependencias, routers, esquemas) usa la [documentación oficial](https://fastapi.tiangolo.com/).

## 📋 Tabla de Contenidos

- [La app mínima](#la-app-minima)
- [Servidor de aplicación: uvicorn y gunicorn](#servidor-de-aplicacion-uvicorn-y-gunicorn)
- [Dockerfile multi-stage](#dockerfile-multi-stage)
- [Endpoint de health y probes](#endpoint-de-health-y-probes)
- [Detrás de un proxy inverso](#detras-de-un-proxy-inverso)
- [Ejecutarlo como Quadlet](#ejecutarlo-como-quadlet)
- [Integración continua](#integracion-continua)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## La app mínima

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return {"status": "ok"}
```

```text
requirements.txt   # dependencias fijadas (pip freeze o pip-compile)
app/main.py
Dockerfile
```

Fija las versiones en `requirements.txt` (o en un lockfile): una imagen que se reconstruye con `fastapi` sin versión es una imagen que cambia sola.

## Servidor de aplicación: uvicorn y gunicorn

FastAPI es una aplicación ASGI; necesita un servidor. Las formas habituales:

| Opción | Cuándo | Comando |
|---|---|---|
| **uvicorn solo** | Un contenedor por réplica y el orquestador escala (Kubernetes, varias unidades Quadlet) | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **uvicorn con `--workers`** | Una sola máquina o contenedor y quieres aprovechar varios núcleos | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| **gunicorn con workers uvicorn** | Quieres el gestor de procesos de gunicorn (reinicio de workers, graceful timeout) | `gunicorn app.main:app -k uvicorn_worker.UvicornWorker -w 4 -b 0.0.0.0:8000` |

!!! warning "Dependiente de la versión"
    El módulo `uvicorn.workers` está deprecado y se eliminará en una versión futura: la documentación de uvicorn recomienda el paquete aparte `uvicorn-worker` (`pip install uvicorn-worker`, clase `uvicorn_worker.UvicornWorker`). Comprueba la ruta vigente en tu versión antes de fijarla en el Dockerfile.

Cuántos workers: el proceso es CPU-bound dentro de cada worker (el bucle de eventos es de un solo hilo), así que más workers que núcleos rara vez ayuda. Empieza con el número de núcleos asignados al contenedor y mide. Si orquestas réplicas (Kubernetes), suele ser mejor **un worker por contenedor** y escalar réplicas: los límites de CPU y memoria se aplican por contenedor y son más predecibles.

Cada worker carga la app entera. Con modelos pesados en memoria (embeddings, ML) multiplicas el consumo por el número de workers.

## Dockerfile multi-stage

La etapa de construcción instala dependencias (y compiladores si hacen falta); la final solo lleva el entorno virtual ya resuelto y el código.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home appuser
WORKDIR /srv
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Puntos a vigilar:

- **Misma versión de Python** en las dos etapas; el venv copiado depende del intérprete.
- **Orden de capas**: copia `requirements.txt` antes que el código para que la caché de dependencias sobreviva a los cambios de código.
- **`CMD` en formato exec** (lista JSON): uvicorn recibe `SIGTERM` directamente y se apaga limpio. En formato shell, el shell se queda con la señal.
- **Usuario no root**, sin shell de login. Si el puerto es mayor que 1024 no necesitas privilegios.
- La etiqueta `3.12-slim` es un ejemplo: elige la versión de Python que soporte tu stack y fíjala. Si alguna dependencia compila extensiones C, la etapa `builder` necesitará paquetes de compilación y la `runtime` las librerías compartidas correspondientes.

Más técnicas (caché de BuildKit, `.dockerignore`, escaneo de la imagen) en [Optimizaciones de Docker](../docker/docker_optimizations.md).

```bash
docker build -t miapi:dev .
docker run --rm -p 8000:8000 miapi:dev
curl -fsS http://localhost:8000/health
```

## Endpoint de health y probes

Un `/health` que siempre devuelve 200 solo demuestra que el proceso responde. Distingue dos preguntas:

| Probe | Pregunta | Qué debe comprobar | Si falla |
|---|---|---|---|
| **Liveness** | ¿Está vivo el proceso? | Nada externo; solo que el bucle responde | Se reinicia el contenedor |
| **Readiness** | ¿Puede atender tráfico? | Dependencias críticas (base de datos, caché) | Se saca del balanceador, sin reiniciar |

```python
from fastapi import FastAPI, Response, status

app = FastAPI()


@app.get("/livez")
def livez():
    return {"status": "alive"}


@app.get("/readyz")
def readyz(response: Response):
    if not db_is_reachable():  # tu comprobación real
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded"}
    return {"status": "ready"}
```

Que el liveness consulte la base de datos es un error clásico: si la base cae, todos los contenedores se reinician en bucle y empeoran el incidente. Los detalles de `httpGet`, `initialDelaySeconds` y `startupProbe` están en [Probes de Kubernetes](../kubernetes/probes.md).

Para un `HEALTHCHECK` de imagen sin instalar `curl` en una imagen slim, basta la librería estándar:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/livez', timeout=2)" || exit 1
```

!!! note "Formato OCI y Podman"
    `HEALTHCHECK` es una instrucción del formato Docker. Si construyes con Podman en formato OCI puro se ignora; declara el healthcheck en el Quadlet (sección siguiente) o construye con `--format docker`.

## Detrás de un proxy inverso

En producción la API no da la cara: la protege un proxy que termina TLS. Tres consecuencias para la app:

1. **IP real del cliente.** Sin configuración, uvicorn ve la IP del proxy. uvicorn lee `X-Forwarded-*` por defecto (`--proxy-headers`), pero solo de IPs de confianza (por defecto `127.0.0.1` y `::1`); amplía `--forwarded-allow-ips` a tus proxies:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips="10.0.0.0/8"
```

   No uses `*` salvo que el contenedor solo sea alcanzable desde el proxy: cualquiera podría falsear su IP.

2. **Esquema y prefijo.** Si publicas bajo una ruta (`/api`), usa `root_path` (parámetro de `FastAPI(...)` o `--root-path` de uvicorn) para que la documentación OpenAPI genere URLs correctas.
3. **Timeouts.** Los del proxy deben ser mayores que los de la app; si no, el cliente ve un 502/504 antes de que la app responda.

Ejemplo con etiquetas de Traefik (consulta [Traefik](../traefik/traefik_base.md) para el proveedor y los entrypoints):

```yaml
services:
  api:
    image: ghcr.io/ejemplo/miapi:1.0.0
    labels:
      - traefik.enable=true
      - traefik.http.routers.api.rule=Host(`api.example.com`)
      - traefik.http.routers.api.entrypoints=websecure
      - traefik.http.routers.api.tls=true
      - traefik.http.services.api.loadbalancer.server.port=8000
      - traefik.http.services.api.loadbalancer.healthcheck.path=/readyz
```

Con HAProxy (más en [HAProxy](../haproxy/haproxy_base.md)) el equivalente es un backend con comprobación activa:

```haproxy
backend api
    option httpchk
    http-check send meth GET uri /readyz
    http-check expect status 200
    server api1 10.0.0.11:8000 check
    server api2 10.0.0.12:8000 check
```

## Ejecutarlo como Quadlet

Con [Quadlets](../docker/quadlets.md) el contenedor es un servicio de systemd: reinicio, orden de arranque y logs en `journalctl`, sin Compose.

```ini
# ~/.config/containers/systemd/miapi.container
[Unit]
Description=API FastAPI
After=network-online.target
Wants=network-online.target

[Container]
Image=ghcr.io/ejemplo/miapi:1.0.0
PublishPort=127.0.0.1:8000:8000
EnvironmentFile=%h/.config/miapi/env
HealthCmd=python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez', timeout=2)"
HealthInterval=30s
HealthStartPeriod=10s
Notify=healthy
AutoUpdate=registry

[Service]
Restart=always
TimeoutStartSec=120

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user start miapi.service
journalctl --user -u miapi.service -f
```

`Notify=healthy` hace que systemd considere el servicio arrancado solo cuando el healthcheck pasa, de modo que las unidades que dependen de él (`After=miapi.service`) esperan a una API realmente lista. Publicar en `127.0.0.1` obliga a pasar por el proxy. Recuerda `loginctl enable-linger` en rootless (ver la página de Quadlets). `Notify=healthy` depende de la versión de Podman: compruébalo en `man podman-systemd.unit`. Para unidades de sistema clásicas, [systemd](../linux/systemd.md).

## Integración continua

Un workflow que construye la imagen en cada push y la publica en el registro de GitHub al etiquetar. Los detalles de triggers, cachés y secretos están en [GitHub Actions](../cicd/github_actions.md).

{% raw %}
```yaml
name: build-api
on:
  push:
    tags: ["v*"]

permissions:
  contents: read
  packages: write

jobs:
  image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```
{% endraw %}

!!! warning "Versiones de las acciones"
    Los `@v4`, `@v3` y `@v6` son ejemplos: comprueba la versión mayor vigente de cada acción y considera fijarla por SHA. Antes del `push`, añade un job que ejecute los tests (`pytest`) y el arranque de la imagen contra `/livez`.

Etiqueta con la versión (`v1.2.0`), no solo con `latest`: la reproducibilidad y el rollback dependen de ello.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Conexión rechazada desde fuera del contenedor | uvicorn escucha en `127.0.0.1` (valor por defecto) | Arrancar con `--host 0.0.0.0` |
| Los logs muestran la IP del proxy | `--forwarded-allow-ips` no incluye la IP del proxy (por defecto solo localhost) | Ampliarlo limitando a las IPs del proxy |
| El contenedor tarda en apagarse y acaba con `SIGKILL` | `CMD` en formato shell: la señal no llega a uvicorn | Usar formato exec (lista JSON) |
| Reinicios en bucle cuando cae la base de datos | Liveness depende de dependencias externas | Mover esas comprobaciones al readiness |
| 502/504 intermitentes en el proxy | Timeout del proxy menor que el de la app, o workers saturados | Alinear timeouts; revisar workers y latencia |
| La documentación `/docs` falla bajo `/api` | El proxy elimina el prefijo y la app no lo sabe | Configurar `root_path` |
| Imagen de cientos de MB | Compiladores y caché de pip en la imagen final | Multi-stage y `--no-cache-dir` |
| `Unit not found` tras crear el `.container` | Falta `daemon-reload` o hay error de sintaxis | `systemctl --user daemon-reload` y revisar la salida |
| El servicio no arranca tras reiniciar el servidor | Rootless sin *lingering* | `loginctl enable-linger $USER` |

## Buenas prácticas

- Una imagen, una versión: etiqueta inmutable en producción, nunca `latest`.
- Proceso como usuario no root, sistema de ficheros de solo lectura si la app lo permite.
- Configuración por variables de entorno o fichero de entorno, nunca dentro de la imagen; los secretos fuera del repositorio.
- Separa liveness y readiness; ninguna de las dos hace trabajo caro.
- Escucha en `127.0.0.1` y publica solo a través del proxy.
- Registra a stdout/stderr y deja que `journalctl` o el recolector de logs hagan el resto.
- Prueba la imagen en CI: arranque real y petición a `/livez` antes de publicar.
- Medir antes de subir workers: más procesos no arreglan una llamada bloqueante dentro de una ruta `async`.

## Referencias

- [Documentación oficial de FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI: despliegue](https://fastapi.tiangolo.com/deployment/)
- [Documentación de uvicorn](https://www.uvicorn.org/)
- [Documentación de gunicorn](https://docs.gunicorn.org/)
- [GitHub de FastAPI](https://github.com/tiangolo/fastapi)
- Páginas relacionadas: [Quadlets](../docker/quadlets.md), [Optimizaciones de Docker](../docker/docker_optimizations.md), [Probes de Kubernetes](../kubernetes/probes.md), [Traefik](../traefik/traefik_base.md), [HAProxy](../haproxy/haproxy_base.md), [GitHub Actions](../cicd/github_actions.md)
