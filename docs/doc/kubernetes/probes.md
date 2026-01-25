---
title: Kubernetes — Readiness y Liveness Probes
updated: 2026-01-25
difficulty: expert
estimated_time: 1 min
category: Orquestación
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Docker básico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Kubernetes — Readiness y Liveness Probes

## Introducción
- `livenessProbe`: determina si el contenedor está vivo (si falla -> restart)
- `readinessProbe`: determina si el contenedor está listo para recibir tráfico

## Ejemplo YAML

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: myapp
    image: myapp:latest
    livenessProbe:
      httpGet:
        path: /health
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
```

## Buenas prácticas
- Diferencia entre `liveness` y `readiness` y no mezclar su propósito.
- Ajusta `initialDelaySeconds` y `periodSeconds` según el arranque de la aplicación.
- Recomendado usar `readinessPod` para rolling updates.

## Debugging
- Usa `kubectl describe pod <pod>` para ver los estados de las probes.
- Usa `kubectl logs -f <pod>` para revisar fallos en la app.

---
