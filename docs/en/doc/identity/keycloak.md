# Keycloak: Identity Management

The de-facto open source standard for IAM (Identity and Access Management).

## Concepts

- **Realm:** Isolated user management space (e.g., "Frikiteam").
- **Client:** Application delegating authentication (e.g., Grafana, Proxmox).
- **Identity Provider (IdP):** External user source (Google, GitHub).

## Deployment (Docker)

```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:24.0.1 start-dev
```

## Generic OIDC Integration

1. Create client in Keycloak.
2. Get `Client ID` and `Client Secret`.
3. Configure Redirect URLs (`https://my-app.com/callback`).
