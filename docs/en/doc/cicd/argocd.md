# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: Cloud-native GitOps with ArgoCD
---

# Cloud-native GitOps with ArgoCD

ArgoCD is a declarative, GitOps continuous delivery tool for Kubernetes. It synchronizes applications from Git repositories to your cluster automatically.

## Overview

**GitOps Principles:**
- Infrastructure and applications defined in Git
- Git is the single source of truth
- Automated synchronization detects and corrects drift
- Full audit trail through Git history

**Benefits:**
- Declarative application management
- Version control for infrastructure
- Automated deployments
- Easy rollbacks
- Better collaboration and compliance

## Installation

### Quick Start

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access the UI (port-forward)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Visit `https://localhost:8080` with admin and the password above.

### Using Helm (Recommended for Production)

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -n argocd --create-namespace \
  --values values.yaml
```

## Directory Structure (Recommended)

Use a clear separation between base manifests and environment-specific overlays:

```
gitops-repo/
├── README.md
├── base/                    # Base Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/                # Environment-specific patches
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
└── argocd-apps/            # ArgoCD Application definitions
    ├── app-dev.yaml
    ├── app-staging.yaml
    └── app-prod.yaml
```

## Creating an Application

### Manual Creation via UI

1. Navigate to **Applications** → **+ NEW APP**
2. Fill in details:
   - **Application name**: `my-app`
   - **Project**: `default`
   - **Repository URL**: `https://github.com/myorg/gitops-repo`
   - **Revision**: `main`
   - **Path**: `overlays/prod`
   - **Cluster URL**: `https://kubernetes.default.svc`
   - **Namespace**: `prod`
3. Click **CREATE**

### Using Application CRD (Recommended)

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
      prune: true      # Delete resources not in Git
      selfHeal: true   # Auto-sync on cluster drift
    syncOptions:
    - CreateNamespace=true
```

Apply with:
```bash
kubectl apply -f argocd-apps/app-prod.yaml
```

## Synchronization

### Manual Sync
```bash
# Via CLI
argocd app sync my-app

# Via UI: Click "SYNC" button
```

### Automatic Sync

```yaml
syncPolicy:
  automated:
    prune: true       # Auto-prune resources not in Git
    selfHeal: true    # Auto-sync when cluster drifts
```

### Webhook Trigger (Faster than Polling)

GitHub → Settings → Webhooks → Add webhook:
- Payload URL: `https://argocd.example.com/api/webhook`
- Content type: `application/json`
- Trigger on: Push events

## Best Practices

1. **Separate repos by concern**:
   - One repo for apps, one for infrastructure
   - Cleaner permissions and CI/CD workflows

2. **Use Kustomize or Helm for overlays**:
   ```yaml
   # kustomization.yaml
   bases:
   - ../../base
   patchesStrategicMerge:
   - replicas.yaml
   ```

3. **Implement RBAC**:
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

4. **Monitor drift with notifications**:
   - Slack/Teams integration for sync failures
   - Email alerts for manual interventions

5. **Use branch protection**:
   - Require PR reviews before merging to main
   - Enforce tests before deploy

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| App stuck in "Syncing" | Network issues or large deployments | Check `argocd-application-controller` logs |
| "Repository not accessible" | SSH key or credentials missing | Register repo with SSH key in UI |
| Resources not syncing | Path mismatch or missing namespace | Verify Git path and namespace in spec |
| Drift detected constantly | Auto-sync disabled | Enable `selfHeal: true` |

## Advanced Configuration

### Multiple Clusters

```yaml
destinations:
- server: https://kubernetes.default.svc        # Local cluster
  namespace: prod
- server: https://staging-cluster.example.com   # Remote cluster
  namespace: prod
```

### Notifications (Slack Example)

```bash
# Install Notifications extension
kubectl apply -f https://raw.githubusercontent.com/argoproj-labs/argocd-notifications/release-1.0/manifests/install.yaml

# Configure Slack integration (see ArgoCD docs)
```

## See Also

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [GitOps Best Practices](https://opengitops.dev/)
- [Kustomize Documentation](https://kustomize.io/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
