# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: Docker — Security and Scanning
---

# Docker — Security (Hardening, Secrets, and Scanning)

## Overview

Docker containers share the host kernel. This guide covers hardening strategies to reduce the attack surface.

## Key Security Principles

1. **Never store secrets** in Dockerfile or image layers
2. **Run as non-root** user inside container
3. **Scan images** for vulnerabilities regularly
4. **Sign images** for integrity verification
5. **Use read-only filesystems** when possible
6. **Limit capabilities** with seccomp and AppArmor

## Hardening: Best Practices

### Non-root User

```dockerfile
FROM alpine:3.19

RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser

COPY app /usr/local/bin/
RUN chown -R appuser:appgroup /usr/local/bin/app

USER appuser
ENTRYPOINT ["/usr/local/bin/app"]
```

### Read-only Root Filesystem

```dockerfile
FROM alpine:3.19
RUN mkdir -p /tmp /var/tmp && \
    chmod 1777 /tmp /var/tmp
USER 1000
WORKDIR /tmp
```

Deploy with:
```bash
docker run --read-only --tmpfs /tmp myimage
```

### Drop Unnecessary Capabilities

```dockerfile
FROM alpine:3.19
RUN setcap -r /usr/bin/chsh 2>/dev/null || true
USER 1000
```

Or at runtime:
```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myimage
```

## Secrets Management

### DON'T: Secrets in Dockerfile
```dockerfile
# ❌ BAD
RUN echo "password123" > /app/.env
```

### DO: Use Environment Files

```bash
# Create .env file locally (add to .gitignore!)
echo "DB_PASSWORD=secret123" > .env

# Pass to container
docker run --env-file .env myimage
```

### DO: Use External Secrets Management

**Docker Secrets (Swarm):**
```bash
echo "my-secret-data" | docker secret create my-secret -
docker service create --secret my-secret myimage
```

**Environment variables in deployment:**
```yaml
# Kubernetes
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  db-password: "secret123"
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: myimage
    envFrom:
    - secretRef:
        name: app-secrets
```

## Vulnerability Scanning

### Using Trivy (Recommended)

```bash
# Scan local image
trivy image myimage:latest

# Scan with severity filter
trivy image --severity CRITICAL,HIGH myimage:latest

# Output as JSON for CI integration
trivy image --format json --output report.json myimage:latest
```

### Using Docker Scan

```bash
# Requires Docker Desktop or Docker Scout subscription
docker scan myimage:latest
```

### In CI/CD Pipeline

```yaml
# GitHub Actions
- name: Scan Docker image
  run: |
    trivy image --severity HIGH,CRITICAL \
      --exit-code 1 \
      --no-progress \
      myregistry/myimage:${{ github.sha }}
```

## Supply Chain Security

### Image Signing (Docker Content Trust)

```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Push (automatically signs)
docker push myregistry/myimage:latest

# Verify signature
docker trust inspect --pretty myregistry/myimage:latest
```

### Registry Security

- Enable image scanning on push
- Require signed images for pulls
- Implement access controls (RBAC)
- Use HTTPS for all registry connections

## Supply Chain Best Practices

| Best Practice | Implementation |
|--------------|-----------------|
| **Minimal base images** | Use Alpine, Distroless |
| **Update regularly** | Schedule weekly image rebuilds |
| **Lock dependencies** | Use specific versions in Dockerfile |
| **Scan before push** | Run trivy in pre-commit hook |
| **SBOM generation** | Generate Software Bill of Materials |

## Common Vulnerabilities

| Vulnerability | Example | Mitigation |
|----------------|---------|-----------|
| **Exposed ports** | Port 22 SSH | Only expose needed ports |
| **Privilege escalation** | sudoers misconfiguration | Drop ALL capabilities |
| **Leaked secrets** | API keys in environment | Use secret management |
| **Outdated packages** | Old OpenSSL with CVE | Pin and update base images |

## Practical Hardened Dockerfile

```dockerfile
FROM alpine:3.19 AS base
RUN apk update && apk add --no-cache ca-certificates

FROM scratch
COPY --from=base /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser

COPY --chown=appuser:appgroup app /usr/local/bin/app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD ["/usr/local/bin/app", "--health-check"]

ENTRYPOINT ["/usr/local/bin/app"]
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Permission denied" running as non-root | File ownership wrong | Use `COPY --chown` in Dockerfile |
| "Read-only file system" errors | Logs can't be written | Create writable tmpfs: `--tmpfs /var/log` |
| Scan always finds CVEs | Outdated base image | Rebuild with latest base regularly |

## See Also

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/cis-benchmarks#docker)
- [Trivy Scanner](https://github.com/aquasecurity/trivy)
- [OWASP Container Security](https://owasp.org/www-project-container-security/)
