# Authentik

A modern and lightweight alternative to Keycloak, very popular in self-hosted environments.

## Disadvantages vs Keycloak

- More intuitive interface for end users.
- Lower resource consumption.
- Highly flexible authentication pipelines (flows).

## Deployment

Requires Docker Compose with Redis and PostgreSQL.

```yaml
# See official docker-compose.yml at goauthentik.io
```

## Proxy Provider

Authentik can act as a reverse proxy to protect applications that do not natively support OIDC (similar to OAuth2-Proxy but integrated).
