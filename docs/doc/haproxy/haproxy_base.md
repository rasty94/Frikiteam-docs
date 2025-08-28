# HAProxy

Guía base de HAProxy: introducción, instalación y configuración mínima.

## Introducción

HAProxy es un balanceador de carga y proxy de alto rendimiento para TCP/HTTP.

## Instalación

- Debian/Ubuntu: `apt install haproxy`
- RHEL/CentOS/Rocky: `dnf install haproxy`

## Configuración mínima

Archivo principal: `/etc/haproxy/haproxy.cfg`.

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

## Comprobación

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

## Referencias

- Documentación oficial: https://www.haproxy.org/

## Instalación avanzada

- Habilitar y arrancar:

```bash
sudo systemctl enable --now haproxy
sudo systemctl status haproxy
```

- Recarga sin corte (hot reload):

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
```

## Terminación TLS (HTTPS)

Genera/instala un `fullchain.pem` y `privkey.pem` (por ejemplo de Let’s Encrypt) y referencia un `pem` combinado:

```bash
cat /etc/letsencrypt/live/tu-dominio/fullchain.pem \
    /etc/letsencrypt/live/tu-dominio/privkey.pem \
    | sudo tee /etc/haproxy/certs/tu-dominio.pem
```

Config en `frontend`:

```cfg
frontend https-in
  bind *:443 ssl crt /etc/haproxy/certs/tu-dominio.pem alpn h2,http/1.1
  http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
  redirect scheme https code 301 if !{ ssl_fc }
  default_backend app
```

Opcional: redirección 80→443

```cfg
frontend http-in
  bind *:80
  redirect scheme https code 301 if !{ ssl_fc }
```

## Health checks

Mejora la detección con `check` y paths HTTP:

```cfg
backend app
  option httpchk GET /healthz
  http-check expect status 200
  server app1 10.0.0.11:8080 check inter 3s fall 3 rise 2
  server app2 10.0.0.12:8080 check inter 3s fall 3 rise 2
```

## Sticky sessions (afinidad)

Por cookie insertada por el balanceador:

```cfg
backend app
  cookie SRV insert indirect nocache
  balance roundrobin
  server app1 10.0.0.11:8080 check cookie app1
  server app2 10.0.0.12:8080 check cookie app2
```

Por hash de IP del cliente (sin cookies):

```cfg
backend app
  balance hdr_ip(X-Forwarded-For)
```

## Métricas y panel de estado

```cfg
listen stats
  bind *:8404
  stats enable
  stats uri /
  stats refresh 10s
  stats auth admin:admin
```

## Logging

Activa logs en `global` y configura rsyslog:

```cfg
global
  log /dev/log local0
  log /dev/log local1 notice
```

En `/etc/rsyslog.d/49-haproxy.conf`:

```conf
if ($programname == 'haproxy') then /var/log/haproxy.log
& stop
```

## Buenas prácticas

- Valida la config antes de recargar: `haproxy -c -f ...`
- Usa `alpn h2,http/1.1` para mejor rendimiento en HTTPS.
- Ajusta timeouts según tus servicios y clientes.
