---
title: "Authentication and Authorization"
tags: ['cybersecurity', 'identity']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: intermediate
category: Cybersecurity
status: published
estimated_time: 10 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Intermediate Linux"
---

## Summary

This guide explains protocols and tools for authentication and authorization in enterprise environments: LDAP, OAuth2, SAML. It includes integration with Keycloak/FreeIPA and practical examples.

## Prerequisites

- Basic knowledge of web protocols (HTTP, HTTPS).
- Familiarity with identity concepts (users, roles, permissions).
- Access to a lab environment (VM or containers).

## Core Protocols

### LDAP (Lightweight Directory Access Protocol)

Standard protocol for accessing user directories.

#### Characteristics

- **Hierarchy:** Tree structure (OU, Groups, Users).
- **Attributes:** User information (cn, uid, mail).
- **Operations:** Bind, Search, Add, Modify.

#### Example with OpenLDAP

```bash
# Install
sudo apt install slapd ldap-utils

# Configure domain
sudo dpkg-reconfigure slapd

# Add user
ldapadd -x -D cn=admin,dc=example,dc=com -W -f user.ldif
```

user.ldif file:
```
dn: uid=jdoe,ou=users,dc=example,dc=com
objectClass: inetOrgPerson
cn: John Doe
sn: Doe
uid: jdoe
mail: jdoe@example.com
userPassword: {SSHA}hashedpassword
```

### OAuth2

Framework for delegated authorization; it grants limited access to resources without sharing credentials.

#### Authorization Code Flow

1. Client requests authorization from the auth server.
2. User authenticates and grants authorization.
3. Server returns a code.
4. Client exchanges the code for an access token.
5. Client uses the token to access resources.

#### Example with curl

```bash
# Step 1: Get the code (manually in the browser)
# https://auth.example.com/oauth/authorize?response_type=code&client_id=client123&redirect_uri=https://app.example.com/callback

# Step 2: Exchange the code for a token
curl -X POST https://auth.example.com/oauth/token \
  -d 'grant_type=authorization_code&code=auth_code&redirect_uri=https://app.example.com/callback&client_id=client123&client_secret=secret'

# Response: {"access_token":"token123","token_type":"Bearer"}
```

### SAML (Security Assertion Markup Language)

XML protocol for exchanging authentication and authorization information.

#### Components

- **Identity Provider (IdP):** Authenticates users.
- **Service Provider (SP):** Provides services.
- **Assertions:** Information about authentication/authorization.

#### Basic Flow

1. User accesses the SP.
2. SP redirects to the IdP.
3. User authenticates at the IdP.
4. IdP sends a SAML assertion to the SP.
5. SP validates the assertion and grants access.

## Identity Management Tools

### Keycloak

Open-source identity server; supports OAuth2, SAML, LDAP.

#### Installation with Docker

```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev
```

#### Basic Configuration

1. Open http://localhost:8080
2. Create a realm
3. Configure clients (OAuth2 apps)
4. Create users and roles
5. Configure identity providers (LDAP, Google, etc.)

#### Integrating with an Application

```python
# Python with requests-oauthlib
from requests_oauthlib import OAuth2Session

client_id = 'myclient'
client_secret = 'secret'
redirect_uri = 'http://localhost:8080/callback'

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)
authorization_url, state = oauth.authorization_url('http://localhost:8080/realms/myrealm/protocol/openid-connect/auth')

# Redirect user to authorization_url
```

### FreeIPA

Integrated suite for identity management (LDAP + Kerberos + DNS + CA).

#### Installation

```bash
# On CentOS/RHEL
sudo yum install freeipa-server
sudo ipa-server-install
```

#### Usage

```bash
# Add user
ipa user-add jdoe --first=John --last=Doe

# Add host
ipa host-add myserver.example.com

# Configure sudo rules
ipa sudorule-add mysudo
ipa sudorule-add-host mysudo --hosts=myserver.example.com
```

## Application Integration

### Kubernetes with OIDC

```yaml
# kubeconfig with OIDC
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://k8s.example.com
contexts:
- context:
    cluster: kubernetes
    user: oidc
current-context: oidc
users:
- name: oidc
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: kubectl
      args:
      - oidc-login
      - get-token
      - --oidc-issuer-url=https://keycloak.example.com/realms/myrealm
      - --oidc-client-id=kubernetes
      - --oidc-client-secret=secret
```

### Web Application with JWT

```javascript
// Verify JWT token
const jwt = require('jsonwebtoken');

function verifyToken(req, res, next) {
  const token = req.headers['authorization'];
  if (!token) return res.status(403).send('Token required');

  jwt.verify(token, 'secretkey', (err, decoded) => {
    if (err) return res.status(401).send('Invalid token');
    req.user = decoded;
    next();
  });
}
```

## Best Practices

- **Multi-Factor Authentication (MFA):** Always enable.
- **Least Privilege principle:** Minimal roles.
- **Auditing:** Authentication and authorization logs.
- **Certificates:** Use HTTPS and valid certificates.
- **Rotation:** Change secrets periodically.

## Troubleshooting

```bash
# Verify LDAP connectivity
ldapsearch -x -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -W

# Debug OAuth2
curl -v https://auth.example.com/.well-known/openid-configuration

# Keycloak logs
docker logs keycloak
```

## References

- [LDAP RFC 4511](https://tools.ietf.org/rfc/rfc4511.txt)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/rfc/rfc6749.txt)
- [SAML Technical Overview](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [FreeIPA Documentation](https://www.freeipa.org/page/Documentation)
