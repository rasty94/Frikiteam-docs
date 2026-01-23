---
title: Kubernetes — Readiness and Liveness Probes
---

# Kubernetes — Readiness and Liveness Probes

## Introduction

Kubernetes uses probes to monitor container health and determine readiness for traffic:

- **`livenessProbe`**: Determines if a container is alive. If it fails, Kubernetes restarts the container.
- **`readinessProbe`**: Determines if a container is ready to accept traffic. If it fails, the container is removed from service endpoints.

Both are crucial for maintaining application availability and enabling automated recovery.

## YAML Example

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

### Probe Types

- **httpGet**: Performs an HTTP GET request against the container. Returns 200-399 for success.
- **exec**: Executes a command inside the container. Exit code 0 means success.
- **tcpSocket**: Attempts a TCP connection to a port. Success if connection is established.

## Best Practices

1. **Separate concerns**: Use liveness for detecting deadlocks/crashes; use readiness for dependency checks.
2. **Tune timing carefully**:
   - `initialDelaySeconds`: Wait before first probe (allows app to start)
   - `periodSeconds`: How often to check (30s is reasonable)
   - `timeoutSeconds`: How long to wait for response (3-5s typical)
   - `failureThreshold`: Number of failures before action (3 is default)
3. **Use readiness for rolling updates**: Prevents traffic to containers still starting up.
4. **Avoid false positives**: Don't rely solely on /health endpoints; test real dependencies.

## Debugging

Check probe status and failures:

```bash
# View probe events
kubectl describe pod <pod-name>

# Check application logs for probe errors
kubectl logs -f <pod-name>

# Manually test the probe endpoint
kubectl exec <pod-name> -- curl -v http://localhost:8080/health

# View recent events
kubectl get events --sort-by='.lastTimestamp'
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Pod never becomes ready | Probe timeout too short | Increase `initialDelaySeconds` or `timeoutSeconds` |
| Pods restart constantly | Liveness probe too aggressive | Increase `periodSeconds` or raise `failureThreshold` |
| Traffic still sent to failing pod | Readiness probe misconfigured | Verify readiness probe endpoint |
| CrashLoopBackOff | Application crashes | Fix application, not probes |

## See Also

- [Kubernetes Documentation: Configure Liveness, Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

---
