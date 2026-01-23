---
title: Docker — Optimization and Best Practices
---

# Docker — Optimization and Best Practices

Optimizing Docker images reduces build time, storage, and runtime overhead while improving security.

## Multi-stage Builds

Multi-stage builds allow you to use multiple `FROM` statements in a single Dockerfile, keeping only the final layers in the production image.

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

**Benefits:**
- Reduces final image size (100MB+ → 10-20MB in this example)
- Separates build tools from runtime dependencies
- Improves security by excluding compilers and dev packages

## General Recommendations

### Image Size and Layers

- **Use minimal base images**: Alpine, Debian Slim, or distroless where applicable
- **Minimize `COPY`/`ADD`**: Only copy necessary files; use `.dockerignore`
- **Clean in the same layer**: 
  ```dockerfile
  RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*
  ```
- **Combine RUN commands**: Each `RUN` creates a layer; fewer layers = smaller images

### Security

- **Never run as root**: Create an unprivileged user
  ```dockerfile
  RUN useradd -m appuser
  USER appuser
  ```
- **Scan for vulnerabilities**:
  ```bash
  docker scan myimage
  trivy image myimage
  ```
- **Keep images updated**: Regularly rebuild with latest base images

### Secrets and Configuration

- **Never include secrets** in the image or Dockerfile
- **Use environment files** for configuration:
  ```bash
  docker run --env-file .env myimage
  ```
- **Use secret management tools**: HashiCorp Vault, Docker Secrets (Swarm), Kubernetes Secrets

### Data Persistence

- **Use volumes** for persistent data:
  ```bash
  docker run -v my-volume:/data myimage
  ```
- **Never store critical data in container layers**; they're ephemeral

## Performance Tips

| Optimization | Impact | Complexity |
|--------------|--------|-----------|
| Multi-stage builds | High | Low |
| Layer caching | High | Medium |
| Image size reduction | Medium | Low |
| Security scanning | Medium | Low |

## Practical Example: Production-Ready Dockerfile

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

## See Also

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
