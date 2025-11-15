# HAProxy

Guía completa de HAProxy: balanceador de carga y proxy de alto rendimiento para TCP/HTTP.

## 📋 Tabla de Contenidos

- [Introducción](#introduccion)
- [Instalación](#instalacion)
- [Configuración Básica](#configuracion-basica)
- [Configuración Avanzada](#configuracion-avanzada)
- [Seguridad](#seguridad)
- [Monitoreo y Logging](#monitoreo-y-logging)
- [Casos de Uso](#casos-de-uso)
- [Diagramas](#diagramas)
- [Buenas Prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Introducción

HAProxy es un balanceador de carga y proxy de alto rendimiento para TCP/HTTP que proporciona:

- **Alto rendimiento**: Optimizado para manejar miles de conexiones simultáneas
- **Flexibilidad**: Soporte para HTTP/HTTPS y TCP genérico
- **Confiabilidad**: Health checks automáticos y failover
- **Seguridad**: Terminación TLS, rate limiting, y cabeceras de seguridad

## Instalación

### Instalación Básica

```bash
# Debian/Ubuntu
apt install haproxy

# RHEL/CentOS/Rocky
dnf install haproxy
```

### Instalación Avanzada

```bash
# Habilitar y arrancar
sudo systemctl enable --now haproxy
sudo systemctl status haproxy

# Recarga sin corte (hot reload)
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
```

## Configuración Básica

### Configuración Mínima

Archivo principal: `/etc/haproxy/haproxy.cfg`

```cfg
global
  log /dev/log local0
  maxconn 2048

defaults
  mode http
  timeout connect 5s
  timeout client  50s
  timeout server  50s

frontend http-in
  bind *:80
  default_backend app

backend app
  balance roundrobin
  server app1 10.0.0.11:8080 check
  server app2 10.0.0.12:8080 check
```

### Comprobación de Configuración

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

## Configuración Avanzada

### Terminación TLS (HTTPS)

1. **Generar certificado combinado**:
   ```bash
   cat /etc/letsencrypt/live/tu-dominio/fullchain.pem \
       /etc/letsencrypt/live/tu-dominio/privkey.pem \
       | sudo tee /etc/haproxy/certs/tu-dominio.pem
   ```

2. **Configurar frontend HTTPS**:
   ```cfg
   frontend https-in
     bind *:443 ssl crt /etc/haproxy/certs/tu-dominio.pem alpn h2,http/1.1
     http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
     redirect scheme https code 301 if !{ ssl_fc }
     default_backend app
   ```

3. **Redirección HTTP → HTTPS** (opcional):
   ```cfg
   frontend http-in
     bind *:80
     redirect scheme https code 301 if !{ ssl_fc }
   ```

### Health Checks Avanzados

```cfg
backend app
  option httpchk GET /healthz
  http-check expect status 200
  server app1 10.0.0.11:8080 check inter 3s fall 3 rise 2
  server app2 10.0.0.12:8080 check inter 3s fall 3 rise 2
```

### Sticky Sessions (Afinidad)

**Por cookie** (insertada por el balanceador):
```cfg
backend app
  cookie SRV insert indirect nocache
  balance roundrobin
  server app1 10.0.0.11:8080 check cookie app1
  server app2 10.0.0.12:8080 check cookie app2
```

**Por hash de IP** (sin cookies):
```cfg
backend app
  balance hdr_ip(X-Forwarded-For)
```

### Balanceo por Conexiones Mínimas

```cfg
backend app
  balance leastconn
  server app1 10.0.0.11:8080 check
  server app2 10.0.0.12:8080 check
```

### ACLs y Enrutado

```cfg
frontend https-in
  bind *:443 ssl crt /etc/haproxy/certs/tu-dominio.pem alpn h2,http/1.1
  acl is_api path_beg /api/
  acl is_admin hdr_beg(host) -i admin.
  use_backend api if is_api
  use_backend admin if is_admin
  default_backend app

backend api
  balance leastconn
  server api1 10.0.0.31:8080 check
  server api2 10.0.0.32:8080 check

backend admin
  balance roundrobin
  server adm1 10.0.0.41:8080 check
```

### Descubrimiento Dinámico

Útil con DNS SRV/round‑robin (consul, kubernetes headless services, etc.):

```cfg
backend app
  balance roundrobin
  resolvers dns
    nameserver google 8.8.8.8:53
  server-template srv 5 _app._tcp.example.local resolvers dns resolve-prefer ipv4 check
```

## Seguridad

### Cabeceras X-Forwarded-* y Seguridad

```cfg
frontend https-in
  bind *:443 ssl crt /etc/haproxy/certs/tu-dominio.pem alpn h2,http/1.1
  http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
  http-response set-header X-Content-Type-Options "nosniff"
  http-response set-header X-Frame-Options "SAMEORIGIN"
  http-response set-header Referrer-Policy "no-referrer-when-downgrade"
  http-response set-header Permissions-Policy "geolocation=(), microphone=()"
  default_backend app

backend app
  http-request set-header X-Forwarded-Proto https if { ssl_fc }
  http-request add-header X-Forwarded-Proto http if !{ ssl_fc }
  http-request set-header X-Forwarded-For %[src]
  http-request set-header X-Forwarded-Host %[req.hdr(Host)]
```

### Rate Limiting

```cfg
frontend https-in
  stick-table type ip size 1m expire 10m store gpc0,http_req_rate(10s)
  http-request track-sc0 src
  acl abuse sc0_http_req_rate gt 50
  http-request deny if abuse
  default_backend app
```

## Monitoreo y Logging

### Panel de Estado

```cfg
listen stats
  bind *:8404
  stats enable
  stats uri /
  stats refresh 10s
  stats auth admin:admin
```

### Configuración de Logs

**En HAProxy**:
```cfg
global
  log /dev/log local0
  log /dev/log local1 notice
```

**En rsyslog** (`/etc/rsyslog.d/49-haproxy.conf`):
```conf
if ($programname == 'haproxy') then /var/log/haproxy.log
& stop
```

## Casos de Uso

### Balanceo HTTP/HTTPS

Configuración estándar para aplicaciones web con terminación TLS.

### Balanceo TCP (Capa 4)

Para servicios no HTTP (bases de datos, TCP genérico):

```cfg
defaults
  mode tcp
  timeout connect 5s
  timeout client  50s
  timeout server  50s

frontend tcp-in
  bind *:5432
  default_backend db

backend db
  balance roundrobin
  server db1 10.0.0.21:5432 check
  server db2 10.0.0.22:5432 check
```

## Diagramas

### Flujo Básico de Balanceo HTTP

```mermaid
flowchart LR
  C[Cliente] -->|HTTP/HTTPS| H((HAProxy))
  H -->|Round Robin / LeastConn| A1[App 1]
  H --> A2[App 2]
```

### Terminación TLS y Cabeceras

```mermaid
sequenceDiagram
  participant U as Usuario
  participant H as HAProxy (443)
  participant S as Servidor App
  U->>H: HTTPS (TLS handshake)
  H-->>U: Certificado (ALPN h2/http1)
  H->>S: HTTP (X-Forwarded-For, X-Forwarded-Proto)
  S-->>H: Respuesta HTTP 200
  H-->>U: Respuesta HTTPS 200 (+ HSTS)
```

## Buenas Prácticas

- ✅ **Validar configuración** antes de recargar: `haproxy -c -f ...`
- ✅ **Usar ALPN** para mejor rendimiento en HTTPS: `alpn h2,http/1.1`
- ✅ **Ajustar timeouts** según tus servicios y clientes
- ✅ **Configurar health checks** apropiados para cada servicio
- ✅ **Implementar rate limiting** para proteger contra abuso
- ✅ **Usar sticky sessions** solo cuando sea necesario
- ✅ **Monitorear logs** y métricas regularmente

## Referencias

- **Documentación oficial**: https://www.haproxy.org/
- **Guía de configuración**: https://www.haproxy.org/download/2.8/doc/configuration.txt
- **Comunidad**: https://www.haproxy.org/community/
