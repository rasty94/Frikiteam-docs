---
title: Kubernetes — Readiness y Liveness Probes
tags: ['kubernetes']
updated: 2026-10-11
difficulty: expert
category: Contenedores
status: published
estimated_time: 5 min
last_reviewed: 2026-10-11
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Docker básico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Kubernetes — Readiness y Liveness Probes

## Introducción

Kubernetes usa probes para monitorizar la salud de los contenedores y determinar si están listos para recibir tráfico:

- **`livenessProbe`**: determina si un contenedor está vivo. Si falla, Kubernetes reinicia el contenedor.
- **`readinessProbe`**: determina si un contenedor está listo para aceptar tráfico. Si falla, el contenedor se retira de los endpoints del servicio.

Ambas son cruciales para mantener la disponibilidad de la aplicación y habilitar la recuperación automática.

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
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
      timeoutSeconds: 3
      failureThreshold: 2
```

### Tipos de probe

- **httpGet**: realiza una petición HTTP GET contra el contenedor. Devuelve 200-399 en caso de éxito.
- **exec**: ejecuta un comando dentro del contenedor. El código de salida 0 significa éxito.
- **tcpSocket**: intenta una conexión TCP a un puerto. Es un éxito si la conexión se establece.

## Buenas prácticas

1. **Separa responsabilidades**: usa liveness para detectar deadlocks/crashes; usa readiness para comprobar dependencias.
2. **Ajusta bien los tiempos**:
   - `initialDelaySeconds`: espera antes del primer probe (permite que la app arranque)
   - `periodSeconds`: frecuencia de comprobación (30s es razonable)
   - `timeoutSeconds`: tiempo de espera de respuesta (típico 3-5s)
   - `failureThreshold`: número de fallos antes de actuar (3 es el valor por defecto)
3. **Usa readiness para rolling updates**: evita enviar tráfico a contenedores que aún están arrancando.
4. **Evita falsos positivos**: no dependas solo de endpoints /health; comprueba dependencias reales.

## Debugging

Comprueba el estado y los fallos de las probes:

```bash
# Ver eventos de las probes
kubectl describe pod <pod-name>

# Revisar logs de la aplicación en busca de errores de probe
kubectl logs -f <pod-name>

# Probar manualmente el endpoint de la probe
kubectl exec <pod-name> -- curl -v http://localhost:8080/health

# Ver eventos recientes
kubectl get events --sort-by='.lastTimestamp'
```

## Problemas comunes

| Problema | Causa | Solución |
|-------|-------|----------|
| El pod nunca se pone ready | Timeout de la probe demasiado corto | Aumentar `initialDelaySeconds` o `timeoutSeconds` |
| Los pods se reinician constantemente | Liveness probe demasiado agresiva | Aumentar `periodSeconds` o subir `failureThreshold` |
| Sigue llegando tráfico a un pod que falla | Readiness probe mal configurada | Verificar el endpoint de la readiness probe |
| CrashLoopBackOff | La aplicación crashea | Arreglar la aplicación, no las probes |

## Ver también

- [Documentación de Kubernetes: Configurar Liveness, Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

---

## Referencias

- [Documentación de Kubernetes: Configurar Liveness, Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
