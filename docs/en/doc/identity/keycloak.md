---
title: "Keycloak: Identity Management"
description: "Deploy and operate Keycloak on your own infrastructure: PostgreSQL, reverse proxy, realms, OIDC clients, mappers, LDAP federation and backups."
keywords: "keycloak, iam, sso, oidc, realm, client, mapper, ldap, reverse proxy, postgresql, backup"
tags: ['identity', 'cybersecurity']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 17 min
category: Identity Management
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Docker or Podman with Compose"
  - "A reverse proxy with TLS ([Traefik](../traefik/traefik_base.md) or [HAProxy](../haproxy/haproxy_base.md))"
  - "OIDC basics (see [Authentication and authorization](../cybersecurity/autenticacion_autorizacion.md))"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Keycloak: Identity Management

## The problem

Every application in the lab ships its own user database: Grafana, Proxmox, Gitea, the registry. Onboarding a person means six forms, offboarding means remembering six places, and nobody has MFA everywhere. Worse: when someone leaves, a forgotten account stays alive for months.

Keycloak centralizes login. Applications delegate authentication through OIDC or SAML, and onboarding, offboarding, MFA and password policies live in one place. The price is that you become the operator of the service everything else depends on: if Keycloak is down, nobody gets in. This page is about deploying it so that does not happen, and recovering it if it does.

!!! note "What this covers and what it does not"
    Here: container deployment, database, reverse proxy, the realm/client model and operations. General OIDC concepts are in [Authentication and authorization](../cybersecurity/autenticacion_autorizacion.md). Alternatives: [Authentik](authentik.md) (flows and forward auth) and [Dex](dex.md) (lightweight connector for Kubernetes).

## 📋 Table of Contents

- [Concepts](#concepts)
- [Development deployment](#development-deployment)
- [Production deployment](#production-deployment)
- [Behind a reverse proxy](#behind-a-reverse-proxy)
- [Realms and users](#realms-and-users)
- [OIDC integration](#oidc-integration)
- [Mappers, roles and groups](#mappers-roles-and-groups)
- [LDAP federation and external providers](#ldap-federation-and-external-providers)
- [Backup and recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Concepts

- **Realm:** isolated space of users, roles, clients and configuration (e.g. `frikiteam`). Users in one realm do not exist in another.
- **Client:** application that delegates authentication (Grafana, Proxmox, your API).
- **Identity Provider (IdP):** user source external to the realm (Google, GitHub, another Keycloak).
- **User federation:** directory Keycloak reads or syncs users from (LDAP, Active Directory).
- **Mapper:** rule that decides which user data travels as claims in the token.
- **`master` realm:** reserved for administering Keycloak. Do not put your application users there.

Since version 17 Keycloak runs on Quarkus. Older articles mention WildFly, the `/auth` URL prefix and `standalone.xml`; none of that applies anymore.

## Development deployment

`start-dev` starts with an embedded database, plain HTTP and caches disabled. It is good for trying a client in five minutes and for nothing else.

```bash
docker run --rm -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=change-this \
  quay.io/keycloak/keycloak:<version> start-dev
```

!!! warning "Version dependent"
    The initial administrator variables have changed between versions: the older ones are `KEYCLOAK_ADMIN` and `KEYCLOAK_ADMIN_PASSWORD`; recent versions introduce `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD`. Check which ones the version you pin accepts in the container guide of its documentation.

## Production deployment

The `start` command requires an external database, a hostname and TLS (or a declaration that a proxy terminates TLS). A minimal `compose.yaml` with PostgreSQL:

```yaml
services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${KC_DB_PASSWORD}
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak -d keycloak"]
      interval: 10s
      retries: 5

  keycloak:
    image: quay.io/keycloak/keycloak:<version>
    restart: unless-stopped
    command: start
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KC_DB_PASSWORD}
      KC_HOSTNAME: https://sso.example.com
      KC_HTTP_ENABLED: "true"
      KC_PROXY_HEADERS: xforwarded
      KC_HEALTH_ENABLED: "true"
    ports:
      - "127.0.0.1:8080:8080"
```

Secrets go in a `.env` next to the compose file, with `600` permissions and out of git. The port only listens on `127.0.0.1`: the reverse proxy exposes it, never the host.

Keycloak distinguishes *build* options from *runtime* options. Changing `KC_DB` or enabling `KC_HEALTH_ENABLED` means rebuilding the optimized configuration. With the official image, `start` does it on every boot and is slow; for fast starts you run `kc.sh build` in your own Dockerfile and then `kc.sh start --optimized`.

!!! warning "Version dependent"
    `KC_HOSTNAME` used to accept only the host name and was combined with other options (`KC_HOSTNAME_STRICT`, `KC_HOSTNAME_URL`); recent versions accept the full URL and reorganize these options. The port and path of the health endpoints have also changed between versions (recent ones use a separate management port). Verify both in the documentation of your version.

To run it as a systemd service instead of Compose, see [Quadlets](../docker/quadlets.md).

## Behind a reverse proxy

Keycloak builds the URLs it returns (redirect URIs, discovery endpoints, cookies) from what it believes its public address is. If it does not know a proxy sits in front, it generates internal `http://` URLs and login fails with broken redirects.

Three pieces must line up:

1. `KC_HOSTNAME` points to the public URL (`https://sso.example.com`).
2. `KC_PROXY_HEADERS=xforwarded` (or `forwarded`) tells it to trust the proxy's `X-Forwarded-*` headers. In earlier versions the equivalent option was `KC_PROXY=edge`.
3. The proxy must send `X-Forwarded-For`, `X-Forwarded-Proto` and `X-Forwarded-Host`.

With Traefik a router label and the service port are enough; Traefik adds the `X-Forwarded-*` headers by default. See [Traefik](../traefik/traefik_base.md).

```yaml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.keycloak.rule=Host(`sso.example.com`)"
      - "traefik.http.routers.keycloak.tls=true"
      - "traefik.http.services.keycloak.loadbalancer.server.port=8080"
```

With HAProxy you must declare them explicitly with `http-request set-header`. See [HAProxy](../haproxy/haproxy_base.md).

!!! warning "Do not expose the admin console"
    The `master` realm and the `/admin` console should not be reachable from the Internet. Filter by IP or management network in the proxy and leave users only the `/realms/` path. If `KC_PROXY_HEADERS` trusts headers any client can forge, an attacker can spoof IP and scheme: the proxy must overwrite them, not forward them.

## Realms and users

One realm per trust boundary, not per application. For a lab, usually one (`frikiteam`) and `master` only for administration.

1. Log into the console with the initial administrator and create the realm.
2. Create a personal administrator user inside `master` with MFA and stop using the initial account.
3. Under *Authentication* enable the password policy and, in the login flow, the second factor (OTP or passkeys, depending on version).
4. Define realm roles (`admin`, `viewer`) and group them under *Groups* so permissions are assigned to people by membership.
5. Under *Realm settings* configure the SMTP server: without mail, password recovery and email verification do not work.

## OIDC integration

Each application registers as a *client* of the realm.

1. In the realm, *Clients → Create client*, OpenID Connect protocol and a stable `Client ID` (`grafana`).
2. For applications with a backend, enable *Client authentication* (confidential client) and copy the `Client Secret` from the *Credentials* tab. For SPAs and mobile apps, a public client with PKCE.
3. Set *Valid redirect URIs* to the exact callback URL (`https://grafana.example.com/login/generic_oauth`). Avoid wildcards: a `*` in redirect URIs allows authorization codes to be stolen.
4. The application only needs the discovery URL, from which it gets the other endpoints:

```text
https://sso.example.com/realms/frikiteam/.well-known/openid-configuration
```

The flow is authorization code: the application redirects the user to Keycloak, which authenticates them, returns a code to the redirect URI, and the application exchanges it for tokens at the token endpoint. The application never sees the password.

Example for Grafana, as environment variables (the names are those of Grafana's `auth.generic_oauth` section):

```bash
GF_AUTH_GENERIC_OAUTH_ENABLED=true
GF_AUTH_GENERIC_OAUTH_NAME=Keycloak
GF_AUTH_GENERIC_OAUTH_CLIENT_ID=grafana
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET=${GRAFANA_CLIENT_SECRET}
GF_AUTH_GENERIC_OAUTH_SCOPES="openid profile email"
GF_AUTH_GENERIC_OAUTH_AUTH_URL=https://sso.example.com/realms/frikiteam/protocol/openid-connect/auth
GF_AUTH_GENERIC_OAUTH_TOKEN_URL=https://sso.example.com/realms/frikiteam/protocol/openid-connect/token
GF_AUTH_GENERIC_OAUTH_API_URL=https://sso.example.com/realms/frikiteam/protocol/openid-connect/userinfo
```

For applications without native OIDC support, a proxy that authenticates in front (forward auth) is the way out; [Authentik](authentik.md) has it built in.

## Mappers, roles and groups

Tokens carry claims. What the application receives depends on the *mappers* of the client or its associated *client scopes*.

- **Roles:** realm roles go in the `realm_access.roles` claim of the access token. A client's own roles go in `resource_access.<client>.roles`.
- **Groups:** not included by default. Add a *Group Membership* mapper to the client scope to receive a `groups` claim.
- **User attributes:** a *User Attribute* mapper copies an arbitrary attribute into a claim.
- **Audience:** if an API rejects the token because of a wrong `aud`, add an audience mapper to the client that issues it.

Use the console's test tool (*Client scopes → Evaluate*) to see exactly which claims an application would receive for a given user, without debugging from the application.

Map Keycloak roles to application roles in the application, not the other way round: that way changing IdP does not force you to redo permissions.

## LDAP federation and external providers

If you already have a directory (OpenLDAP, FreeIPA, Active Directory), Keycloak can query it without migrating users.

- **User federation → LDAP:** you give the server URL, the users base DN and a read account. Keycloak authenticates against the directory, and can import users into its database at first login or sync them periodically.
- **Edit mode:** *READ_ONLY* is the safest; Keycloak never writes to your directory.
- **LDAP mappers:** equivalent to the ones above, they map directory attributes (`mail`, `cn`) and groups to Keycloak attributes and groups.
- **Connection:** use `ldaps://` or StartTLS; the service bind travels with a password.

For social or corporate login, *Identity providers* lets you delegate to Google, GitHub or another OIDC. The user is created in the realm on first access and you decide which mappers apply. Keep a local emergency account: if the external IdP goes down, you need to be able to get in.

## Backup and recovery

Almost all of Keycloak's state is in PostgreSQL: realms, users, clients, secrets and sessions. The Keycloak container stores nothing that matters.

```bash
# Consistent database dump
docker compose exec -T postgres pg_dump -U keycloak keycloak | gzip > keycloak-$(date +%F).sql.gz

# Restore onto an empty database
gunzip -c keycloak-2026-10-10.sql.gz | docker compose exec -T postgres psql -U keycloak keycloak
```

Copy the dump off the host (see [Restic and Borg](../backups/restic_borg.md)). In addition, `kc.sh export` can dump a realm's configuration to JSON files, useful for versioning configuration or cloning an environment, but it does not replace the database dump: by default it is not a full copy of sessions or of every secret.

!!! warning "Upgrade with a prior backup"
    Keycloak migrates the database schema on the first boot of a new version, and that migration is not reversible. Take the dump before changing the image tag, upgrade one major version at a time and read the upgrade notes of the target version.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| After login, redirect to an internal `http://...` or to `localhost` | Keycloak does not know its public URL or does not trust the proxy | Check `KC_HOSTNAME` and `KC_PROXY_HEADERS`; verify the proxy sends `X-Forwarded-*` |
| `Invalid parameter: redirect_uri` | The callback URI does not exactly match *Valid redirect URIs* | Copy the exact URI from the error into the client; scheme, host and path must match |
| `Invalid token issuer` in the API or application | The app validates against a Keycloak URL different from the one signing (internal vs. public) | Make the app use the same public hostname as `KC_HOSTNAME` |
| Startup fails connecting to the database | PostgreSQL is not ready yet or `KC_DB_URL` is wrong | `depends_on` with `service_healthy`; check host, port and credentials |
| The console loads unstyled or blank | Resources blocked by the proxy or badly rewritten headers | Check the proxy and that it does not filter `/resources/` paths |
| Tokens do not include `groups` | No group membership mapper in the client scope | Add a *Group Membership* mapper and assign the scope to the client |
| LDAP users cannot log in | Wrong bind DN, user filter or untrusted `ldaps://` certificate | Use *Test authentication* in the federation settings; check the logs |
| After upgrading, startup fails in migration | Jump of several major versions or inconsistent database | Restore the previous dump and upgrade one major version at a time |

## Best practices

- Pin the image tag to a specific version; never `latest` on a service all login depends on.
- A dedicated PostgreSQL for Keycloak, with a restore-tested backup, not just a dump.
- Always serve over TLS and do not publish port 8080 beyond `127.0.0.1` or the proxy network.
- Restrict the admin console by network and require MFA for administrators.
- One client per application, with exact redirect URIs and distinct secrets; rotate the secret if it leaks.
- Do not use the `master` realm for application users.
- Monitor the health endpoint (with [Uptime Kuma](../monitoring/uptime_kuma.md) or the [observability stack](../monitoring/observability_stack.md)); a dead SSO is noticed late.
- Keep a local emergency account outside the federated flow and document how to recover it.

## References

- [Keycloak official documentation](https://www.keycloak.org/documentation)
- [Keycloak container guide](https://www.keycloak.org/server/containers)
- [Keycloak reverse proxy configuration](https://www.keycloak.org/server/reverseproxy)
- [Authentik](authentik.md) and [Dex](dex.md), alternatives within the site
- [Authentication and authorization](../cybersecurity/autenticacion_autorizacion.md)
