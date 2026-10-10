---
title: "Keycloak: Gestión de Identidad"
description: "Desplegar y operar Keycloak en infraestructura propia: PostgreSQL, reverse proxy, realms, clients OIDC, mappers, federación LDAP y copias de seguridad."
keywords: "keycloak, iam, sso, oidc, realm, client, mapper, ldap, reverse proxy, postgresql, backup"
tags: ['identity', 'cybersecurity']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 17 min
category: Gestión de Identidad
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Docker o Podman con Compose"
  - "Un reverse proxy con TLS ([Traefik](../traefik/traefik_base.md) o [HAProxy](../haproxy/haproxy_base.md))"
  - "Nociones de OIDC (ver [Autenticación y autorización](../cybersecurity/autenticacion_autorizacion.md))"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Keycloak: Gestión de Identidad

## El problema

Cada aplicación del laboratorio trae su propia base de usuarios: Grafana, Proxmox, Gitea, el registry. Dar de alta a una persona son seis formularios, darla de baja es acordarse de seis sitios, y nadie tiene MFA en todos. Peor: cuando alguien se va, una cuenta olvidada sigue viva meses.

Keycloak centraliza el login. Las aplicaciones delegan la autenticación vía OIDC o SAML, y el alta, la baja, el MFA y las políticas de contraseña viven en un solo sitio. A cambio, te conviertes en el operador del servicio del que depende todo lo demás: si Keycloak está caído, nadie entra. Esta página trata de desplegarlo para que eso no ocurra y de recuperarlo si ocurre.

!!! note "Qué cubre y qué no"
    Aquí: despliegue sobre contenedores, base de datos, reverse proxy, modelo de realms/clients y operación. Los conceptos generales de OIDC están en [Autenticación y autorización](../cybersecurity/autenticacion_autorizacion.md). Alternativas: [Authentik](authentik.md) (flows y forward auth) y [Dex](dex.md) (conector ligero para Kubernetes).

## 📋 Tabla de Contenidos

- [Conceptos](#conceptos)
- [Despliegue de desarrollo](#despliegue-de-desarrollo)
- [Despliegue de producción](#despliegue-de-produccion)
- [Detrás de un reverse proxy](#detras-de-un-reverse-proxy)
- [Realms y usuarios](#realms-y-usuarios)
- [Integración OIDC](#integracion-oidc)
- [Mappers, roles y grupos](#mappers-roles-y-grupos)
- [Federación LDAP y proveedores externos](#federacion-ldap-y-proveedores-externos)
- [Backup y recuperación](#backup-y-recuperacion)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Conceptos

- **Realm:** espacio aislado de usuarios, roles, clients y configuración (ej. `frikiteam`). Los usuarios de un realm no existen en otro.
- **Client:** aplicación que delega autenticación (Grafana, Proxmox, tu API).
- **Identity Provider (IdP):** origen de usuarios externo al realm (Google, GitHub, otro Keycloak).
- **User federation:** directorio del que Keycloak lee o sincroniza usuarios (LDAP, Active Directory).
- **Mapper:** regla que decide qué datos del usuario viajan como claims en el token.
- **Realm `master`:** reservado para administrar Keycloak. No pongas ahí a los usuarios de tus aplicaciones.

Desde la versión 17 Keycloak corre sobre Quarkus. Los artículos antiguos hablan de WildFly, del prefijo `/auth` en las URLs y de `standalone.xml`; nada de eso aplica ya.

## Despliegue de desarrollo

`start-dev` arranca con base de datos embebida, HTTP sin TLS y caches deshabilitadas. Sirve para probar un client en cinco minutos y para nada más.

```bash
docker run --rm -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=cambia-esto \
  quay.io/keycloak/keycloak:<versión> start-dev
```

!!! warning "Dependiente de la versión"
    Las variables del administrador inicial han cambiado entre versiones: las antiguas son `KEYCLOAK_ADMIN` y `KEYCLOAK_ADMIN_PASSWORD`; las versiones recientes introducen `KC_BOOTSTRAP_ADMIN_USERNAME` y `KC_BOOTSTRAP_ADMIN_PASSWORD`. Comprueba cuáles acepta la versión que fijes en la guía de contenedores de su documentación.

## Despliegue de producción

El comando `start` exige base de datos externa, hostname y TLS (o declarar que el TLS lo termina un proxy). Un `compose.yaml` mínimo con PostgreSQL:

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
    image: quay.io/keycloak/keycloak:<versión>
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
      KC_HOSTNAME: https://sso.ejemplo.com
      KC_HTTP_ENABLED: "true"
      KC_PROXY_HEADERS: xforwarded
      KC_HEALTH_ENABLED: "true"
    ports:
      - "127.0.0.1:8080:8080"
```

Los secretos van en un `.env` junto al compose, con permisos `600` y fuera de git. El puerto solo escucha en `127.0.0.1`: lo expone el reverse proxy, nunca el host.

Keycloak distingue opciones de *build* y de *runtime*. Cambiar `KC_DB` o activar `KC_HEALTH_ENABLED` implica reconstruir la configuración optimizada. Con la imagen oficial, `start` lo hace en cada arranque y tarda; para arranques rápidos se ejecuta `kc.sh build` en un Dockerfile propio y luego `kc.sh start --optimized`.

!!! warning "Dependiente de la versión"
    `KC_HOSTNAME` aceptaba antes solo el nombre de host y se acompañaba de otras opciones (`KC_HOSTNAME_STRICT`, `KC_HOSTNAME_URL`); las versiones recientes aceptan la URL completa y reorganizan estas opciones. El puerto y la ruta de los endpoints de salud también han cambiado entre versiones (en las recientes viven en un puerto de gestión separado). Verifica ambos en la documentación de tu versión.

Para ejecutarlo como servicio de systemd en lugar de Compose, ver [Quadlets](../docker/quadlets.md).

## Detrás de un reverse proxy

Keycloak construye las URLs que devuelve (redirect URIs, endpoints del discovery, cookies) a partir de lo que cree que es su dirección pública. Si no sabe que hay un proxy delante, genera URLs `http://` internas y el login falla con redirecciones rotas.

Tres piezas tienen que casar:

1. `KC_HOSTNAME` apunta a la URL pública (`https://sso.ejemplo.com`).
2. `KC_PROXY_HEADERS=xforwarded` (o `forwarded`) le dice que confíe en las cabeceras `X-Forwarded-*` del proxy. En versiones anteriores la opción equivalente era `KC_PROXY=edge`.
3. El proxy debe enviar `X-Forwarded-For`, `X-Forwarded-Proto` y `X-Forwarded-Host`.

Con Traefik basta una etiqueta de router y el puerto del servicio; Traefik añade las cabeceras `X-Forwarded-*` por defecto. Ver [Traefik](../traefik/traefik_base.md).

```yaml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.keycloak.rule=Host(`sso.ejemplo.com`)"
      - "traefik.http.routers.keycloak.tls=true"
      - "traefik.http.services.keycloak.loadbalancer.server.port=8080"
```

Con HAProxy hay que declararlas explícitamente con `http-request set-header`. Ver [HAProxy](../haproxy/haproxy_base.md).

!!! warning "No expongas la consola de administración"
    El realm `master` y la consola `/admin` no deberían ser accesibles desde Internet. Filtra por IP o red de gestión en el proxy y deja a los usuarios solo la ruta `/realms/`. Si `KC_PROXY_HEADERS` confía en cabeceras que cualquier cliente puede falsificar, un atacante puede suplantar IP y esquema: el proxy debe sobrescribirlas, no reenviarlas.

## Realms y usuarios

Un realm por frontera de confianza, no por aplicación. Para un laboratorio, normalmente uno (`frikiteam`) y el `master` solo para administrar.

1. Entra en la consola con el administrador inicial y crea el realm.
2. Crea un usuario administrador personal dentro de `master` con MFA y deja de usar la cuenta inicial.
3. En *Authentication* activa la política de contraseñas y, en el flujo de login, el segundo factor (OTP o passkeys, según versión).
4. Define roles de realm (`admin`, `viewer`) y agrúpalos en *Groups* para asignar permisos a personas por pertenencia.
5. En *Realm settings* configura el servidor SMTP: sin correo no funcionan la recuperación de contraseña ni la verificación de email.

## Integración OIDC

Cada aplicación se registra como *client* del realm.

1. En el realm, *Clients → Create client*, protocolo OpenID Connect y un `Client ID` estable (`grafana`).
2. Para aplicaciones con backend, activa *Client authentication* (client confidencial) y copia el `Client Secret` de la pestaña *Credentials*. Para SPAs y apps móviles, client público con PKCE.
3. Configura *Valid redirect URIs* con la URL exacta del callback (`https://grafana.ejemplo.com/login/generic_oauth`). Evita comodines: un `*` en redirect URIs permite robar códigos de autorización.
4. La aplicación necesita solo la URL del discovery, de la que obtiene el resto de endpoints:

```text
https://sso.ejemplo.com/realms/frikiteam/.well-known/openid-configuration
```

El flujo es el de authorization code: la aplicación redirige al usuario a Keycloak, este autentica, devuelve un código a la redirect URI y la aplicación lo cambia por tokens contra el endpoint de tokens. La aplicación nunca ve la contraseña.

Ejemplo para Grafana, en variables de entorno (los nombres son los de la sección `auth.generic_oauth` de Grafana):

```bash
GF_AUTH_GENERIC_OAUTH_ENABLED=true
GF_AUTH_GENERIC_OAUTH_NAME=Keycloak
GF_AUTH_GENERIC_OAUTH_CLIENT_ID=grafana
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET=${GRAFANA_CLIENT_SECRET}
GF_AUTH_GENERIC_OAUTH_SCOPES="openid profile email"
GF_AUTH_GENERIC_OAUTH_AUTH_URL=https://sso.ejemplo.com/realms/frikiteam/protocol/openid-connect/auth
GF_AUTH_GENERIC_OAUTH_TOKEN_URL=https://sso.ejemplo.com/realms/frikiteam/protocol/openid-connect/token
GF_AUTH_GENERIC_OAUTH_API_URL=https://sso.ejemplo.com/realms/frikiteam/protocol/openid-connect/userinfo
```

Para aplicaciones sin soporte OIDC propio, un proxy que haga la autenticación delante (forward auth) es la salida; [Authentik](authentik.md) lo trae integrado.

## Mappers, roles y grupos

Los tokens llevan claims. Lo que la aplicación recibe depende de los *mappers* del client o de los *client scopes* asociados.

- **Roles:** los roles de realm van en el claim `realm_access.roles` del token de acceso. Los roles propios de un client van en `resource_access.<client>.roles`.
- **Grupos:** no se incluyen por defecto. Añade un mapper de tipo *Group Membership* al client scope para recibir un claim `groups`.
- **Atributos de usuario:** un mapper *User Attribute* copia un atributo arbitrario a un claim.
- **Audiencia:** si una API rechaza el token por `aud` incorrecto, añade un mapper de audiencia al client que lo emite.

Usa el cliente de pruebas de la consola (*Client scopes → Evaluate*) para ver exactamente qué claims recibiría una aplicación para un usuario concreto, sin tener que depurar desde la aplicación.

Mapea roles de Keycloak a roles de la aplicación en la aplicación, no al revés: así cambiar de IdP no obliga a rehacer los permisos.

## Federación LDAP y proveedores externos

Si ya tienes un directorio (OpenLDAP, FreeIPA, Active Directory), Keycloak puede consultarlo sin migrar usuarios.

- **User federation → LDAP:** indicas la URL del servidor, el DN base de usuarios y una cuenta de lectura. Keycloak autentica contra el directorio, y puede importar los usuarios a su base de datos al primer login o sincronizarlos periódicamente.
- **Modo de edición:** *READ_ONLY* es el más seguro; Keycloak nunca escribe en tu directorio.
- **Mappers LDAP:** equivalentes a los anteriores, mapean atributos (`mail`, `cn`) y grupos del directorio a atributos y grupos de Keycloak.
- **Conexión:** usa `ldaps://` o StartTLS; el bind de servicio viaja con contraseña.

Para login social o corporativo, *Identity providers* permite delegar en Google, GitHub u otro OIDC. El usuario se crea en el realm al primer acceso y puedes decidir qué mappers aplicar. Deja una cuenta local de emergencia: si el IdP externo cae, necesitas poder entrar.

## Backup y recuperación

El estado de Keycloak está casi entero en PostgreSQL: realms, usuarios, clients, secretos y sesiones. El contenedor de Keycloak no guarda nada que importe.

```bash
# Volcado consistente de la base de datos
docker compose exec -T postgres pg_dump -U keycloak keycloak | gzip > keycloak-$(date +%F).sql.gz

# Restauración sobre una base vacía
gunzip -c keycloak-2026-10-10.sql.gz | docker compose exec -T postgres psql -U keycloak keycloak
```

Copia el volcado fuera del host (ver [Restic y Borg](../backups/restic_borg.md)). Además, `kc.sh export` puede volcar la configuración de un realm a ficheros JSON, útil para versionar la configuración o clonar un entorno, pero no sustituye al volcado de la base de datos: por defecto no es una copia completa de sesiones ni de todos los secretos.

!!! warning "Actualiza con copia previa"
    Keycloak migra el esquema de la base de datos en el primer arranque de una versión nueva, y esa migración no es reversible. Haz el volcado antes de cambiar la etiqueta de la imagen, sube de una versión mayor cada vez y lee las notas de actualización de la versión destino.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Tras el login, redirección a `http://...` interno o a `localhost` | Keycloak no conoce su URL pública o no confía en el proxy | Revisar `KC_HOSTNAME` y `KC_PROXY_HEADERS`; comprobar que el proxy envía `X-Forwarded-*` |
| `Invalid parameter: redirect_uri` | La URI del callback no coincide exactamente con *Valid redirect URIs* | Copiar la URI exacta del error al client; esquema, host y ruta deben coincidir |
| `Invalid token issuer` en la API o aplicación | La app valida contra una URL de Keycloak distinta de la que firma (interna vs. pública) | Hacer que la app use el mismo hostname público que `KC_HOSTNAME` |
| El arranque falla al conectar con la base de datos | PostgreSQL aún no está listo o `KC_DB_URL` es incorrecta | `depends_on` con `service_healthy`; revisar host, puerto y credenciales |
| La consola carga sin estilos o en blanco | Recursos bloqueados por el proxy o cabeceras mal reescritas | Revisar el proxy y que no filtre rutas `/resources/` |
| Los tokens no incluyen `groups` | No hay mapper de pertenencia a grupos en el client scope | Añadir un mapper *Group Membership* y asignar el scope al client |
| Usuarios de LDAP no pueden entrar | Bind DN incorrecto, filtro de usuarios o certificado de `ldaps://` no confiable | Usar *Test authentication* en la configuración de la federación; revisar los logs |
| Tras actualizar, el arranque falla en migración | Salto de varias versiones mayores o base de datos inconsistente | Restaurar el volcado previo y actualizar versión mayor a versión mayor |

## Buenas prácticas

- Fija la etiqueta de la imagen a una versión concreta; nunca `latest` en un servicio del que depende todo el login.
- Un PostgreSQL dedicado para Keycloak, con backup probado de restauración, no solo de volcado.
- Sirve siempre por TLS y no publiques el puerto 8080 más allá de `127.0.0.1` o de la red del proxy.
- Restringe la consola de administración por red y exige MFA a los administradores.
- Un client por aplicación, con redirect URIs exactas y secretos distintos; rota el secreto si se filtra.
- No uses el realm `master` para usuarios de aplicaciones.
- Monitoriza el endpoint de salud (con [Uptime Kuma](../monitoring/uptime_kuma.md) o el [stack de observabilidad](../monitoring/observability_stack.md)); un SSO caído se nota tarde.
- Mantén una cuenta de emergencia local fuera del flujo federado y documenta cómo recuperarla.

## Referencias

- [Documentación oficial de Keycloak](https://www.keycloak.org/documentation)
- [Guía de contenedores de Keycloak](https://www.keycloak.org/server/containers)
- [Configuración de reverse proxy en Keycloak](https://www.keycloak.org/server/reverseproxy)
- [Authentik](authentik.md) y [Dex](dex.md), alternativas dentro del sitio
- [Autenticación y autorización](../cybersecurity/autenticacion_autorizacion.md)
