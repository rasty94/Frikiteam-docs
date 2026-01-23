# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

# Cloud-native: GitOps con ArgoCD

Gestión del ciclo de vida de aplicaciones en Kubernetes mediante GitOps.

## Resumen

Despliegue automatizado y sincronización de estado desde repositorios Git.

## Instalación

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

## Patrones de Directorios

Recomendamos la estructura `apps/` base:

- `base/`: Manifiestos K8s puros.
- `overlays/`: Parches específicos por entorno (dev, prod).

## Referencias

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
