---
title: "Zero Trust in Practice"
date: 2026-01-25
updated: 2026-01-25
tags: [security, zero-trust, mtls, spiffe, opa, network-policies]
difficulty: intermediate
estimated_time: 6 min
category: Cybersecurity
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Zero Trust in Practice

Roll out strong identities, mTLS, least-privilege access control and continuous posture validation.

## Core Principles
- Identity first (workload identity with SPIFFE/SPIRE)
- End-to-end mTLS (service ↔ service)
- Least privilege (RBAC/ABAC, admission policies)
- Segmentation (NetworkPolicies, egress control)
- Continuous verification (scanning and posture)

## Service Identities (SPIFFE/SPIRE)

```bash
# Install SPIRE Server/Agent (official Helm chart)
helm repo add spiffe https://spiffe.github.io/helm-charts
helm install spire spiffe/spire -n spire --create-namespace

# Example of a SPIFFE ID issued to a deployment
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

## mTLS with a Service Mesh (Istio)

```yaml
# Strict mTLS policy in the "prod" namespace
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
# Least-privilege AuthorizationPolicy
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

## Network Segmentation

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

## Admission Policies (OPA Gatekeeper)

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

## Continuous Posture
- Scan images and manifests (Trivy, Checkov)
- Review RBAC periodically (rbacker/ rbac-police)
- Detect drift against a baseline (Kyverno policies in audit/enforce mode)

## Quick Checklist
- mTLS mandatory between services
- Workload identities (SPIFFE/SPIRE) issued and verified
- NetworkPolicies default to deny-all plus minimal rules
- Admission policies for labels, limits and image signatures
- Continuous image/manifest scanning and RBAC review
