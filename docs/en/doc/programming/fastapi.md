---
title: "FastAPI"
description: "Packaging and deploying a FastAPI API: multi-stage Dockerfile, uvicorn/gunicorn workers, health endpoint for probes, reverse proxy, Quadlet and GitHub Actions CI."
keywords: "fastapi, uvicorn, gunicorn, dockerfile, multi-stage, healthcheck, traefik, haproxy, quadlet, github actions"
tags: ['programming', 'api']
updated: 2026-10-11
difficulty: advanced
estimated_time: 21 min
category: Development
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Python 3 and basic HTTP API concepts"
  - "[Docker](../docker/docker_base.md) or Podman"
  - "[Quadlets](../docker/quadlets.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# FastAPI

## The problem

The API works on your laptop with `uvicorn main:app --reload`. On the server the questions the tutorial never answered show up: how many processes? who restarts it if it dies? how does the load balancer know it is ready? why is the image 1 GB? why do the logs show the proxy IP instead of the client's?

FastAPI is a Python web framework for APIs built on type annotations, with validation (Pydantic), automatic OpenAPI docs and async support (Starlette). This page does not teach the framework: it covers how to **build, package and deploy** a FastAPI app on this site's infrastructure.

!!! note "What this covers and what it does not"
    We start from a minimal app and work around it: image, process, health, proxy, service and pipeline. For the programming model (dependencies, routers, schemas) use the [official documentation](https://fastapi.tiangolo.com/).

## 📋 Table of Contents

- [The minimal app](#the-minimal-app)
- [Application server: uvicorn and gunicorn](#application-server-uvicorn-and-gunicorn)
- [Multi-stage Dockerfile](#multi-stage-dockerfile)
- [Health endpoint and probes](#health-endpoint-and-probes)
- [Behind a reverse proxy](#behind-a-reverse-proxy)
- [Running it as a Quadlet](#running-it-as-a-quadlet)
- [Continuous integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## The minimal app

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
requirements.txt   # pinned dependencies (pip freeze or pip-compile)
app/main.py
Dockerfile
```

Pin versions in `requirements.txt` (or a lockfile): an image rebuilt with an unpinned `fastapi` is an image that changes by itself.

## Application server: uvicorn and gunicorn

FastAPI is an ASGI application; it needs a server. The usual options:

| Option | When | Command |
|---|---|---|
| **uvicorn alone** | One container per replica and the orchestrator scales (Kubernetes, several Quadlet units) | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **uvicorn with `--workers`** | A single machine or container and you want to use several cores | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| **gunicorn with uvicorn workers** | You want gunicorn's process manager (worker restarts, graceful timeout) | `gunicorn app.main:app -k uvicorn_worker.UvicornWorker -w 4 -b 0.0.0.0:8000` |

!!! warning "Version dependent"
    The `uvicorn.workers` module is deprecated and will be removed in a future release: the uvicorn documentation recommends the separate `uvicorn-worker` package (`pip install uvicorn-worker`, class `uvicorn_worker.UvicornWorker`). Check the current path for your version before hardcoding it in the Dockerfile.

How many workers: inside each worker the work is CPU-bound (the event loop is single-threaded), so more workers than cores rarely helps. Start with the number of cores assigned to the container and measure. If you orchestrate replicas (Kubernetes), **one worker per container** and scaling replicas is usually better: CPU and memory limits apply per container and are more predictable.

Each worker loads the whole app. With heavy models in memory (embeddings, ML) you multiply memory use by the number of workers.

## Multi-stage Dockerfile

The build stage installs dependencies (and compilers if needed); the final stage carries only the resolved virtual environment and the code.

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

Points to watch:

- **Same Python version** in both stages; the copied venv depends on the interpreter.
- **Layer order**: copy `requirements.txt` before the code so the dependency cache survives code changes.
- **`CMD` in exec form** (JSON list): uvicorn receives `SIGTERM` directly and shuts down cleanly. In shell form, the shell keeps the signal.
- **Non-root user**, no login shell. With a port above 1024 you need no privileges.
- The `3.12-slim` tag is an example: choose the Python version your stack supports and pin it. If a dependency compiles C extensions, the `builder` stage will need build packages and `runtime` the matching shared libraries.

More techniques (BuildKit cache, `.dockerignore`, image scanning) in [Docker Optimizations](../docker/docker_optimizations.md).

```bash
docker build -t miapi:dev .
docker run --rm -p 8000:8000 miapi:dev
curl -fsS http://localhost:8000/health
```

## Health endpoint and probes

A `/health` that always returns 200 only proves the process answers. Tell two questions apart:

| Probe | Question | What it should check | On failure |
|---|---|---|---|
| **Liveness** | Is the process alive? | Nothing external; only that the loop responds | The container is restarted |
| **Readiness** | Can it serve traffic? | Critical dependencies (database, cache) | Removed from the balancer, no restart |

```python
from fastapi import FastAPI, Response, status

app = FastAPI()


@app.get("/livez")
def livez():
    return {"status": "alive"}


@app.get("/readyz")
def readyz(response: Response):
    if not db_is_reachable():  # your real check
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded"}
    return {"status": "ready"}
```

Having liveness query the database is a classic mistake: if the database goes down, every container restarts in a loop and makes the incident worse. The details of `httpGet`, `initialDelaySeconds` and `startupProbe` are in [Kubernetes Probes](../kubernetes/probes.md).

For an image `HEALTHCHECK` without installing `curl` in a slim image, the standard library is enough:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/livez', timeout=2)" || exit 1
```

!!! note "OCI format and Podman"
    `HEALTHCHECK` is a Docker-format instruction. If you build with Podman in pure OCI format it is ignored; declare the healthcheck in the Quadlet (next sections) or build with `--format docker`.

## Behind a reverse proxy

In production the API does not face the world: a proxy that terminates TLS protects it. Three consequences for the app:

1. **Real client IP.** With no configuration, uvicorn sees the proxy IP. uvicorn reads `X-Forwarded-*` by default (`--proxy-headers`), but only from trusted IPs (by default `127.0.0.1` and `::1`); extend `--forwarded-allow-ips` to your proxies:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips="10.0.0.0/8"
```

   Do not use `*` unless the container is only reachable from the proxy: anyone could spoof their IP.

2. **Scheme and prefix.** If you publish under a path (`/api`), use `root_path` (a `FastAPI(...)` parameter or uvicorn's `--root-path`) so the OpenAPI docs generate correct URLs.
3. **Timeouts.** The proxy's must be larger than the app's; otherwise the client sees a 502/504 before the app answers.

Example with Traefik labels (see [Traefik](../traefik/traefik_base.md) for the provider and entrypoints):

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

With HAProxy (more in [HAProxy](../haproxy/haproxy_base.md)) the equivalent is a backend with active checks:

```haproxy
backend api
    option httpchk
    http-check send meth GET uri /readyz
    http-check expect status 200
    server api1 10.0.0.11:8000 check
    server api2 10.0.0.12:8000 check
```

## Running it as a Quadlet

With [Quadlets](../docker/quadlets.md) the container is a systemd service: restart, start ordering and logs in `journalctl`, no Compose.

```ini
# ~/.config/containers/systemd/miapi.container
[Unit]
Description=FastAPI API
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

`Notify=healthy` makes systemd consider the service started only when the healthcheck passes, so units that depend on it (`After=miapi.service`) wait for an API that is actually ready. Publishing on `127.0.0.1` forces traffic through the proxy. Remember `loginctl enable-linger` in rootless (see the Quadlets page). `Notify=healthy` depends on the Podman version: check `man podman-systemd.unit`. For classic system units, [systemd](../linux/systemd.md).

## Continuous integration

A workflow that builds the image on every push and publishes it to the GitHub registry when tagged. Details on triggers, caches and secrets are in [GitHub Actions](../cicd/github_actions.md).

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

!!! warning "Action versions"
    The `@v4`, `@v3` and `@v6` are examples: check the current major version of each action and consider pinning by SHA. Before the `push`, add a job that runs the tests (`pytest`) and starts the image against `/livez`.

Tag with the version (`v1.2.0`), not just `latest`: reproducibility and rollback depend on it.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Connection refused from outside the container | uvicorn listens on `127.0.0.1` (the default) | Start with `--host 0.0.0.0` |
| Logs show the proxy IP | `--forwarded-allow-ips` does not include the proxy IP (localhost only by default) | Extend it, limited to the proxy IPs |
| The container is slow to stop and ends with `SIGKILL` | `CMD` in shell form: the signal does not reach uvicorn | Use exec form (JSON list) |
| Restart loops when the database goes down | Liveness depends on external dependencies | Move those checks to readiness |
| Intermittent 502/504 at the proxy | Proxy timeout lower than the app's, or saturated workers | Align timeouts; review workers and latency |
| `/docs` breaks under `/api` | The proxy strips the prefix and the app does not know | Configure `root_path` |
| Image of hundreds of MB | Compilers and pip cache in the final image | Multi-stage and `--no-cache-dir` |
| `Unit not found` after creating the `.container` | Missing `daemon-reload` or a syntax error | `systemctl --user daemon-reload` and check the output |
| The service does not start after a server reboot | Rootless without *lingering* | `loginctl enable-linger $USER` |

## Best practices

- One image, one version: an immutable tag in production, never `latest`.
- Run as a non-root user, read-only filesystem if the app allows it.
- Configuration via environment variables or an env file, never inside the image; secrets outside the repository.
- Separate liveness and readiness; neither does expensive work.
- Listen on `127.0.0.1` and publish only through the proxy.
- Log to stdout/stderr and let `journalctl` or the log collector do the rest.
- Test the image in CI: a real start and a request to `/livez` before publishing.
- Measure before adding workers: more processes do not fix a blocking call inside an `async` route.

## References

- [FastAPI official documentation](https://fastapi.tiangolo.com/)
- [FastAPI: deployment](https://fastapi.tiangolo.com/deployment/)
- [uvicorn documentation](https://www.uvicorn.org/)
- [gunicorn documentation](https://docs.gunicorn.org/)
- [FastAPI on GitHub](https://github.com/tiangolo/fastapi)
- Related pages: [Quadlets](../docker/quadlets.md), [Docker Optimizations](../docker/docker_optimizations.md), [Kubernetes Probes](../kubernetes/probes.md), [Traefik](../traefik/traefik_base.md), [HAProxy](../haproxy/haproxy_base.md), [GitHub Actions](../cicd/github_actions.md)
