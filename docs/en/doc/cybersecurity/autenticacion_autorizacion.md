# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: "Autenticación y Autorización"
date: 2026-01-09
tags: [cybersecurity, authentication, authorization, ldap, oauth, keycloak]
draft: false
---

## Resumen

Esta guía explica protocolos y herramientas para autenticación y autorización en entornos empresariales: LDAP, OAuth2, SAML. Incluye integración con Keycloak/FreeIPA y ejemplos prácticos.

## Prerrequisitos

- Conocimientos básicos de protocolos web (HTTP, HTTPS).
- Familiaridad con conceptos de identidad (usuarios, roles, permisos).
- Acceso a un entorno de laboratorio (VM o contenedores).

## Protocolos Principales

### LDAP (Lightweight Directory Access Protocol)

Protocolo estándar para acceder a directorios de usuarios.

#### Características

- **Jerarquía:** Estructura de árbol (OU, Groups, Users).
- **Atributos:** Información de usuario (cn, uid, mail).
- **Operaciones:** Bind, Search, Add, Modify.

#### Ejemplo con OpenLDAP

```bash
# Instalar
sudo apt install slapd ldap-utils

# Configurar dominio
sudo dpkg-reconfigure slapd

# Añadir usuario
ldapadd -x -D cn=admin,dc=example,dc=com -W -f user.ldif
```

Archivo user.ldif:
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

Framework para autorización delegada, permite acceso limitado a recursos sin compartir credenciales.

#### Flujo Authorization Code

1. Cliente solicita autorización al servidor de auth.
2. Usuario se autentica y autoriza.
3. Servidor devuelve code.
4. Cliente intercambia code por access token.
5. Cliente usa token para acceder a recursos.

#### Ejemplo con curl

```bash
# Paso 1: Obtener code (manual en browser)
# https://auth.example.com/oauth/authorize?response_type=code&client_id=client123&redirect_uri=https://app.example.com/callback

# Paso 2: Intercambiar code por token
curl -X POST https://auth.example.com/oauth/token \
  -d 'grant_type=authorization_code&code=auth_code&redirect_uri=https://app.example.com/callback&client_id=client123&client_secret=secret'

# Respuesta: {"access_token":"token123","token_type":"Bearer"}
```

### SAML (Security Assertion Markup Language)

Protocolo XML para intercambio de información de autenticación y autorización.

#### Componentes

- **Identity Provider (IdP):** Autentica usuarios.
- **Service Provider (SP):** Proporciona servicios.
- **Assertions:** Información sobre autenticación/autorización.

#### Flujo Básico

1. Usuario accede a SP.
2. SP redirige a IdP.
3. Usuario se autentica en IdP.
4. IdP envía assertion SAML a SP.
5. SP valida assertion y permite acceso.

## Herramientas de Gestión de Identidad

### Keycloak

Servidor de identidad open-source, soporta OAuth2, SAML, LDAP.

#### Instalación con Docker

```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev
```

#### Configuración Básica

1. Acceder a http://localhost:8080
2. Crear realm
3. Configurar clientes (OAuth2 apps)
4. Crear usuarios y roles
5. Configurar identity providers (LDAP, Google, etc.)

#### Integración con Aplicación

```python
# Python con requests-oauthlib
from requests_oauthlib import OAuth2Session

client_id = 'myclient'
client_secret = 'secret'
redirect_uri = 'http://localhost:8080/callback'

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)
authorization_url, state = oauth.authorization_url('http://localhost:8080/realms/myrealm/protocol/openid-connect/auth')

# Redirigir usuario a authorization_url
```

### FreeIPA

Suite integrada para gestión de identidad (LDAP + Kerberos + DNS + CA).

#### Instalación

```bash
# En CentOS/RHEL
sudo yum install freeipa-server
sudo ipa-server-install
```

#### Uso

```bash
# Añadir usuario
ipa user-add jdoe --first=John --last=Doe

# Añadir host
ipa host-add myserver.example.com

# Configurar sudo rules
ipa sudorule-add mysudo
ipa sudorule-add-host mysudo --hosts=myserver.example.com
```

## Integración en Aplicaciones

### Kubernetes con OIDC

```yaml
# kubeconfig con OIDC
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

### Aplicación Web con JWT

```javascript
// Verificar token JWT
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

## Mejores Prácticas

- **Multi-Factor Authentication (MFA):** Siempre activar.
- **Principio de Least Privilege:** Roles mínimos.
- **Auditoría:** Logs de autenticación y autorización.
- **Certificados:** Usar HTTPS y certificados válidos.
- **Rotación:** Cambiar secrets periódicamente.

## Troubleshooting

```bash
# Verificar conectividad LDAP
ldapsearch -x -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -W

# Debug OAuth2
curl -v https://auth.example.com/.well-known/openid-configuration

# Logs de Keycloak
docker logs keycloak
```

## Referencias

- [LDAP RFC 4511](https://tools.ietf.org/rfc/rfc4511.txt)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/rfc/rfc6749.txt)
- [SAML Technical Overview](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [FreeIPA Documentation](https://www.freeipa.org/page/Documentation)