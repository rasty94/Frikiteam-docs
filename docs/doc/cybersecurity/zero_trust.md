---
title: "Zero Trust en Práctica"
date: 2026-01-25
updated: 2026-01-25
tags: [security, zero-trust, mtls, spiffe, opa, network-policies]
difficulty: intermediate
estimated_time: 6 min
category: Ciberseguridad
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Zero Trust en Práctica

Implementa identidades fuertes, mTLS, control de acceso mínimo y validación continua de postura.

## Principios Clave
- Identidad primero (workload identity con SPIFFE/SPIRE)
- mTLS extremo a extremo (servicio ↔ servicio)
- Menor privilegio (RBAC/ABAC, políticas de admisión)
- Segmentación (NetworkPolicies, control de egress)
- Verificación continua (escaneo y postura)

## Identidades de Servicio (SPIFFE/SPIRE)

```bash
# Instalar SPIRE Server/Agent (Helm chart oficial)
helm repo add spiffe https://spiffe.github.io/helm-charts
helm install spire spiffe/spire -n spire --create-namespace

# Ejemplo de SPIFFE ID emitido a un deployment
kubectl apply -f - <<'EOF'
apiVersion: spire.spiffe.io/v1alpha1
kind: SpiffeID
metadata:
  name: api-frontend
  namespace: default
spec:
  spiffeId: spiffe://example.org/ns/default/sa/api-frontend
  parentId: spiffe://example.org/spire/server
  selector:
    matchLabels:
      app: api-frontend
EOF
```

## mTLS con Service Mesh (Istio)

```yaml
# Política mTLS estricta en namespace "prod"
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: prod
spec:
  mtls:
    mode: STRICT
```

```yaml
# AuthorizationPolicy de menor privilegio
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend-to-api
  namespace: prod
spec:
  selector:
    matchLabels:
      app: api
  rules:
  - from:
    - source:
        principals: ["spiffe://example.org/ns/prod/sa/frontend"]
    to:
    - operation:
        ports: ["8080"]
```

## Segmentación de Red

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

## Políticas de Admisión (OPA Gatekeeper)

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequireLabels
metadata:
  name: require-owner-tier
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  parameters:
    labels: ["owner", "tier"]
```

## Postura Continua
- Escaneo de imágenes y manifiestos (Trivy, Checkov)
- Revisiones periódicas de RBAC (rbacker/ rbac-police)
- Detección de drift y baseline (Kyverno policies en modo audit/enforce)

## Checklist Rápido
- mTLS obligatorio entre servicios
- Identidades workload (SPIFFE/SPIRE) emitidas y verificadas
- NetworkPolicies por defecto deny-all + reglas mínimas
- Políticas de admisión para etiquetas, límites y firma de imágenes
- Escaneo continuo de imágenes/manifiestos y revisión de RBAC
