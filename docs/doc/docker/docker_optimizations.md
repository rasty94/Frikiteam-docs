---
title: "Docker — Optimización y Buenas Prácticas"
description: "Reducir tiempo de build, tamaño y superficie de ataque de las imágenes Docker: multi-stage builds, minimización de capas, gestión de secretos, persistencia con volúmenes y un Dockerfile de producción de ejemplo."
keywords: "docker, optimización, multi-stage, dockerfile, capas, tamaño de imagen, secretos, volúmenes, buenas prácticas"
tags: ['docker']
updated: 2026-10-11
difficulty: expert
category: Contenedores
status: published
estimated_time: 5 min
last_reviewed: 2026-10-11
prerequisites: ["Conocimientos básicos de Docker y Dockerfile"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Docker — Optimización y Buenas Prácticas

Optimizar las imágenes Docker reduce el tiempo de build, el almacenamiento y el overhead en tiempo de ejecución, además de mejorar la seguridad.

## Multi-stage Builds

Los multi-stage builds permiten usar varias sentencias `FROM` en un mismo Dockerfile, conservando solo las capas finales en la imagen de producción.

```dockerfile
# Build stage
FROM golang:1.20-alpine AS build
WORKDIR /app
COPY . .
RUN go build -o /out/myapp

# Runtime stage
FROM alpine:3.19
COPY --from=build /out/myapp /usr/local/bin/myapp
USER 1000
ENTRYPOINT ["/usr/local/bin/myapp"]
```

**Beneficios:**
- Reduce el tamaño final de la imagen (100MB+ → 10-20MB en este ejemplo)
- Separa las herramientas de build de las dependencias de runtime
- Mejora la seguridad al excluir compiladores y paquetes de desarrollo

## Recomendaciones Generales

### Tamaño de Imagen y Capas

- **Usa imágenes base mínimas**: Alpine, Debian Slim o distroless cuando sea aplicable
- **Minimiza `COPY`/`ADD`**: copia solo los ficheros necesarios; usa `.dockerignore`
- **Limpia en la misma capa**:
  ```dockerfile
  RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*
  ```
- **Combina comandos `RUN`**: cada `RUN` crea una capa; menos capas = imágenes más pequeñas

### Seguridad

- **Nunca ejecutes como root**: crea un usuario sin privilegios
  ```dockerfile
  RUN useradd -m appuser
  USER appuser
  ```
- **Escanea vulnerabilidades**:
  ```bash
  docker scan myimage
  trivy image myimage
  ```
- **Mantén las imágenes actualizadas**: reconstruye regularmente con las últimas imágenes base

### Secretos y Configuración

- **Nunca incluyas secretos** en la imagen ni en el Dockerfile
- **Usa ficheros de entorno** para la configuración:
  ```bash
  docker run --env-file .env myimage
  ```
- **Usa herramientas de gestión de secretos**: HashiCorp Vault, Docker Secrets (Swarm), Kubernetes Secrets

### Persistencia de Datos

- **Usa volúmenes** para datos persistentes:
  ```bash
  docker run -v my-volume:/data myimage
  ```
- **Nunca almacenes datos críticos en las capas del contenedor**; son efímeras

## Consejos de Rendimiento

| Optimización | Impacto | Complejidad |
|--------------|--------|-----------|
| Multi-stage builds | Alto | Bajo |
| Cacheo de capas | Alto | Medio |
| Reducción de tamaño de imagen | Medio | Bajo |
| Escaneo de seguridad | Medio | Bajo |

## Ejemplo Práctico: Dockerfile Listo para Producción

```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /build
COPY go.* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app

# Runtime stage
FROM alpine:3.19
RUN apk add --no-cache ca-certificates
RUN adduser -D -u 1000 appuser
WORKDIR /app
COPY --from=builder /build/app .
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD wget --quiet --tries=1 --spider http://localhost:8080/health || exit 1
CMD ["./app"]
```

## Ver También

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)

## Referencias

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
