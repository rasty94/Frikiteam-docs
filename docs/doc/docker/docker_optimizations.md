---
title: Docker — Optimización y Buenas Prácticas
---

# Docker — Optimización y Buenas Prácticas

## Multi-stage build (ejemplo)

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

## Recomendaciones
- Usa imágenes base pequeñas (alpine, slim) cuando sea posible.
- Evita `ADD`/`COPY` innecesarios y reduce el tamaño final.
- Limpia cachés en la misma capa (`RUN apt-get update && apt-get install -y ... && apt-get clean && rm -rf /var/lib/apt/lists/*`).
- Evita ejecutar como `root`, crea y usa un usuario sin privilegios.
- Usa `docker scan` / `trivy` para escaneo de vulnerabilidades.

## Volúmenes y persistencia
- Usa volúmenes para datos persistentes y evita almacenar datos importantes dentro del layer de la imagen.

## Variables de entorno y secretos
- No incluyas secretos en la imagen ni en el `Dockerfile`.
- Usa `--env-file` o herramientas de secretos (HashiCorp Vault, Docker secrets, etc.)

## Caso práctico
- Añade un Dockerfile multi-stage, build y tag en CI, y publica la imagen a un registry.

---
