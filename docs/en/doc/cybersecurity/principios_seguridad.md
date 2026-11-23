---
title: "Security Principles"
description: "Defense in Depth, Zero Trust and Least Privilege applied to real infrastructure, with concrete examples in Docker and Kubernetes."
tags: ['cybersecurity', 'best-practices', 'hardening', 'zero-trust']

updated: 2026-11-23
last_reviewed: 2026-11-23
difficulty: intermediate
category: Cybersecurity
status: published
estimated_time: 2 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Intermediate Linux"
---

## The problem

Betting the security of a platform on a single perimeter firewall or a strong password works right up until that one layer fails. When a misconfiguration or service vulnerability hits, the blast radius depends on how many barriers sit behind it. Here we walk through the three principles that keep a small incident from turning into a full compromise — Defense in Depth, Zero Trust and Least Privilege — applied to Docker and Kubernetes.

## Prerequisites

- Basic knowledge of containers (Docker) and orchestration (Kubernetes).
- Understanding of networking and authentication concepts.

## Defense in Depth

### Concept

Defense in Depth (DiD) is a layered security strategy: if one layer fails, others protect the system. Do not rely on a single security control.

### Application in Infrastructure

- **Network Layer:** Firewalls, VPNs, segmentation.
- **Host Layer:** OS hardening, SELinux/AppArmor.
- **Application Layer:** Authentication, encryption.
- **Data Layer:** Encryption at rest and in transit.

### Example in Kubernetes

- Network: Network Policies to isolate namespaces.
- Host: Pod Security Standards to restrict capabilities.
- App: RBAC for API access.
- Data: Secrets encrypted with KMS.

## Zero Trust

### Concept

Zero Trust assumes that no entity (user, device, application) is trusted by default. Verify all access continuously, with no implicit trust.

### Key Principles

- **Verify explicitly:** Authenticate and authorize every request.
- **Least privilege access:** Only the access that is needed.
- **Assume breach:** Monitor and respond to anomalies.

### Application in DevOps

- **Cluster access:** Strong authentication (OIDC, certificates), not trusted IPs.
- **Microservices:** mTLS between services.
- **CI/CD:** Pipelines that verify artifact integrity.

### Example in Docker/K8s

- Use Istio for service mesh with mTLS.
- Integrate OPA/Gatekeeper for access policies.
- Monitor with Falco to detect anomalous access.

## Least Privilege

### Concept

Least Privilege (PoLP) means granting only the minimum permissions needed to perform a task. It reduces the impact of compromises.

### Application

- **Users:** Specific roles, not global admin.
- **Applications:** Limited capabilities in containers.
- **Networks:** Restrictive firewall rules.

### Example in Kubernetes

- RBAC: Roles per namespace, not cluster-admin.
- Service Accounts: Minimal permissions for pods.
- Pod Security Context: No privileged containers.

## Practical Implementation

### Checklist for Applying Principles

- [ ] Review architecture: Identify layers and trust points.
- [ ] Configure authentication: OIDC/JWT instead of passwords.
- [ ] Apply segmentation: Namespaces in K8s, overlay networks.
- [ ] Monitor: Security logs and metrics.
- [ ] Audit regularly: Review permissions and configs.

### Tools

- **Kubernetes:** RBAC, Network Policies, Pod Security Admission.
- **Docker:** User namespaces, seccomp profiles.
- **General:** OPA (Open Policy Agent) for policies.

## Benefits

- Greater resilience to attacks.
- Reduced attack surface.
- Compliance with standards (NIST, ISO 27001).

## References

- [NIST Zero Trust Architecture](https://csrc.nist.gov/publications/detail/sp/800-207/final)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Docker Security](https://docs.docker.com/engine/security/)
