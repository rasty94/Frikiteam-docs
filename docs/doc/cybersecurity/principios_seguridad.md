---
title: "Principios de Seguridad"
date: 2026-01-09
tags: [cybersecurity, principles, defense-in-depth, zero-trust, least-privilege]
draft: false
---

## Resumen

Esta guía cubre principios fundamentales de seguridad aplicados a entornos DevOps e infraestructura moderna. Se enfoca en Defense in Depth, Zero Trust y Least Privilege, con ejemplos prácticos en Kubernetes y Docker.

## Prerrequisitos

- Conocimientos básicos de contenedores (Docker) y orquestación (Kubernetes).
- Entendimiento de conceptos de red y autenticación.

## Defense in Depth

### Concepto

Defense in Depth (DiD) es una estrategia de seguridad en capas: si una capa falla, otras la protegen. No depender de un solo control de seguridad.

### Aplicación en Infraestructura

- **Capa de Red:** Firewalls, VPNs, segmentación.
- **Capa de Host:** Hardening de OS, SELinux/AppArmor.
- **Capa de Aplicación:** Autenticación, encriptación.
- **Capa de Datos:** Encriptación at-rest y in-transit.

### Ejemplo en Kubernetes

- Red: Network Policies para aislar namespaces.
- Host: Pod Security Standards para restringir capabilities.
- App: RBAC para acceso a APIs.
- Datos: Secrets encriptados con KMS.

## Zero Trust

### Concepto

Zero Trust asume que ninguna entidad (usuario, dispositivo, aplicación) es confiable por defecto. Verificar todo acceso continuamente, sin confianza implícita.

### Principios clave

- **Verify explicitly:** Autenticar y autorizar cada request.
- **Least privilege access:** Solo acceso necesario.
- **Assume breach:** Monitorear y responder a anomalías.

### Aplicación en DevOps

- **Acceso a clusters:** Autenticación fuerte (OIDC, certificados), no IPs confiables.
- **Microservicios:** mTLS entre servicios.
- **CI/CD:** Pipelines que verifican integridad de artefactos.

### Ejemplo en Docker/K8s

- Usar Istio para service mesh con mTLS.
- Integrar OPA/Gatekeeper para políticas de acceso.
- Monitoreo con Falco para detectar accesos anómalos.

## Least Privilege

### Concepto

Least Privilege (PoLP) significa otorgar solo los permisos mínimos necesarios para realizar una tarea. Reduce el impacto de compromisos.

### Aplicación

- **Usuarios:** Roles específicos, no admin global.
- **Aplicaciones:** Capabilities limitadas en contenedores.
- **Redes:** Reglas de firewall restrictivas.

### Ejemplo en Kubernetes

- RBAC: Roles por namespace, no cluster-admin.
- Service Accounts: Con permisos mínimos para pods.
- Pod Security Context: No privileged containers.

## Implementación Práctica

### Checklist para Aplicar Principios

- [ ] Revisar arquitectura: Identificar capas y puntos de confianza.
- [ ] Configurar autenticación: OIDC/JWT en lugar de passwords.
- [ ] Aplicar segmentación: Namespaces en K8s, redes overlay.
- [ ] Monitorear: Logs y métricas de seguridad.
- [ ] Auditar regularmente: Revisar permisos y configs.

### Herramientas

- **Kubernetes:** RBAC, Network Policies, Pod Security Admission.
- **Docker:** User namespaces, seccomp profiles.
- **General:** OPA (Open Policy Agent) para políticas.

## Beneficios

- Mayor resiliencia a ataques.
- Reducción de superficie de ataque.
- Cumplimiento con estándares (NIST, ISO 27001).

## Referencias

- [NIST Zero Trust Architecture](https://csrc.nist.gov/publications/detail/sp/800-207/final)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Docker Security](https://docs.docker.com/engine/security/)