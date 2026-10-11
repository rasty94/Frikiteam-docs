---
title: "Cloud-native: GitOps con ArgoCD"
description: "GitOps declarativo para Kubernetes con ArgoCD: instalación, estructura de repositorio, Applications, sincronización, RBAC y resolución de problemas."
keywords: "argocd, gitops, kubernetes, ci-cd, kustomize, helm, sincronización, rbac"
tags: ['ci-cd', 'gitops', 'argocd', 'kubernetes']
updated: 2026-09-03
difficulty: beginner
estimated_time: 9 min
category: DevOps
status: published
last_reviewed: 2026-09-03
prerequisites: ["Ninguno"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Cloud-native: GitOps con ArgoCD

ArgoCD es una herramienta declarativa de entrega continua GitOps para Kubernetes. Sincroniza aplicaciones desde repositorios Git hacia tu clúster automáticamente.

## Resumen

**Principios de GitOps:**
- Infraestructura y aplicaciones definidas en Git
- Git es la única fuente de verdad
- La sincronización automatizada detecta y corrige el drift
- Rastro de auditoría completo a través del historial de Git

**Beneficios:**
- Gestión declarativa de aplicaciones
- Control de versiones para infraestructura
- Despliegues automatizados
- Rollbacks sencillos
- Mejor colaboración y cumplimiento

## Instalación

### Inicio rápido

```bash
# Crear el namespace
kubectl create namespace argocd

# Instalar ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Acceder a la UI (port-forward)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Obtener la contraseña de admin
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Visita `https://localhost:8080` con admin y la contraseña anterior.

### Usando Helm (recomendado para producción)

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -n argocd --create-namespace \
  --values values.yaml
```

## Estructura de Directorios (Recomendada)

Usa una separación clara entre los manifiestos base y los overlays específicos de cada entorno:

```
gitops-repo/
├── README.md
├── base/                    # Manifiestos base de Kubernetes
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/                # Parches específicos por entorno
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── replicas.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── replicas.yaml
│   └── prod/
│       ├── kustomization.yaml
│       ├── replicas.yaml
│       └── ingress.yaml
└── argocd-apps/            # Definiciones de Application de ArgoCD
    ├── app-dev.yaml
    ├── app-staging.yaml
    └── app-prod.yaml
```

## Creación de una Aplicación

### Creación manual vía UI

1. Ve a **Applications** → **+ NEW APP**
2. Rellena los detalles:
   - **Application name**: `my-app`
   - **Project**: `default`
   - **Repository URL**: `https://github.com/myorg/gitops-repo`
   - **Revision**: `main`
   - **Path**: `overlays/prod`
   - **Cluster URL**: `https://kubernetes.default.svc`
   - **Namespace**: `prod`
3. Haz clic en **CREATE**

### Usando el CRD Application (recomendado)

```yaml
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/gitops-repo
    targetRevision: main
    path: overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated:
      prune: true      # Elimina recursos que no estén en Git
      selfHeal: true   # Auto-sincroniza ante drift del clúster
    syncOptions:
    - CreateNamespace=true
```

Aplícalo con:
```bash
kubectl apply -f argocd-apps/app-prod.yaml
```

## Sincronización

### Sincronización manual
```bash
# Vía CLI
argocd app sync my-app

# Vía UI: haz clic en el botón "SYNC"
```

### Sincronización automática

```yaml
syncPolicy:
  automated:
    prune: true       # Auto-elimina recursos que no estén en Git
    selfHeal: true    # Auto-sincroniza cuando el clúster tiene drift
```

### Disparo por Webhook (más rápido que el polling)

GitHub → Settings → Webhooks → Add webhook:
- Payload URL: `https://argocd.example.com/api/webhook`
- Content type: `application/json`
- Trigger on: Push events

## Buenas Prácticas

1. **Separa los repos por función**:
   - Un repo para apps, otro para infraestructura
   - Permisos y flujos de CI/CD más limpios

2. **Usa Kustomize o Helm para los overlays**:
   ```yaml
   # kustomization.yaml
   bases:
   - ../../base
   patchesStrategicMerge:
   - replicas.yaml
   ```

3. **Implementa RBAC**:
   ```yaml
   apiVersion: v1
   kind: AppProject
   metadata:
     name: staging
   spec:
     sourceRepos:
     - 'https://github.com/myorg/*'
     destinations:
     - namespace: 'staging'
       server: https://kubernetes.default.svc
   ```

4. **Monitoriza el drift con notificaciones**:
   - Integración con Slack/Teams para fallos de sincronización
   - Alertas por email para intervenciones manuales

5. **Usa protección de ramas**:
   - Exige revisiones de PR antes de fusionar a main
   - Exige tests antes de desplegar

## Resolución de Problemas

| Problema | Causa | Solución |
|-------|-------|----------|
| App atascada en "Syncing" | Problemas de red o despliegues grandes | Revisa los logs de `argocd-application-controller` |
| "Repository not accessible" | Falta la clave SSH o las credenciales | Registra el repo con clave SSH en la UI |
| Los recursos no sincronizan | Path incorrecto o falta el namespace | Verifica el path de Git y el namespace en el spec |
| Drift detectado constantemente | Auto-sync desactivado | Activa `selfHeal: true` |

## Configuración Avanzada

### Múltiples Clústeres

```yaml
destinations:
- server: https://kubernetes.default.svc        # Clúster local
  namespace: prod
- server: https://staging-cluster.example.com   # Clúster remoto
  namespace: prod
```

### Notificaciones (ejemplo con Slack)

```bash
# Instalar la extensión de Notifications
kubectl apply -f https://raw.githubusercontent.com/argoproj-labs/argocd-notifications/release-1.0/manifests/install.yaml

# Configurar la integración con Slack (ver la documentación de ArgoCD)
```

## Ver También

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [GitOps Best Practices](https://opengitops.dev/)
- [Kustomize Documentation](https://kustomize.io/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
