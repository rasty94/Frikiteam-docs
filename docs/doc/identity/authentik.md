---
tags:
  - identity
  - security
  - sso
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Gestión de Identidad
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Authentik

Una alternativa moderna y ligera a Keycloak, popular en entornos self-hosted.

## Ventajas sobre Keycloak

- Interfaz más intuitiva para usuarios finales.
- Consumo de recursos menor.
- Pipelines de autenticación muy flexibles (flows).

## Despliegue

Requiere Docker Compose con Redis y PostgreSQL.

```yaml
# Ver docker-compose.yml oficial en goauthentik.io
```

## Proxy Provider

Authentik puede actuar como proxy reverso para proteger aplicaciones que no soportan OIDC nativamente (similar a OAuth2-Proxy pero integrado).
