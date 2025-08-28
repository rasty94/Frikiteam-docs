# HAProxy

Basic guide to HAProxy: introduction, installation and minimal configuration.

## Introduction

HAProxy is a high‑performance load balancer and TCP/HTTP proxy.

## Installation

- Debian/Ubuntu: `apt install haproxy`
- RHEL/CentOS/Rocky: `dnf install haproxy`

## Minimal configuration

Main file: `/etc/haproxy/haproxy.cfg`.

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

## Check

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

## References

- Official docs: https://www.haproxy.org/

## Advanced installation

- Enable and start:

```bash
sudo systemctl enable --now haproxy
sudo systemctl status haproxy
```

- Zero‑downtime reload:

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
```

## TLS termination (HTTPS)

Create/install `fullchain.pem` and `privkey.pem` (e.g. Let’s Encrypt) and generate a combined `pem`:

```bash
cat /etc/letsencrypt/live/your-domain/fullchain.pem \
    /etc/letsencrypt/live/your-domain/privkey.pem \
    | sudo tee /etc/haproxy/certs/your-domain.pem
```

Config in `frontend`:

```cfg
frontend https-in
  bind *:443 ssl crt /etc/haproxy/certs/your-domain.pem alpn h2,http/1.1
  http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
  redirect scheme https code 301 if !{ ssl_fc }
  default_backend app
```

Optional: redirect 80→443

```cfg
frontend http-in
  bind *:80
  redirect scheme https code 301 if !{ ssl_fc }
```

## Health checks

Improve detection with `check` and HTTP paths:

```cfg
backend app
  option httpchk GET /healthz
  http-check expect status 200
  server app1 10.0.0.11:8080 check inter 3s fall 3 rise 2
  server app2 10.0.0.12:8080 check inter 3s fall 3 rise 2
```

## Sticky sessions (affinity)

Cookie‑based stickiness inserted by the balancer:

```cfg
backend app
  cookie SRV insert indirect nocache
  balance roundrobin
  server app1 10.0.0.11:8080 check cookie app1
  server app2 10.0.0.12:8080 check cookie app2
```

Client IP hash (no cookies):

```cfg
backend app
  balance hdr_ip(X-Forwarded-For)
```

## Metrics and stats page

```cfg
listen stats
  bind *:8404
  stats enable
  stats uri /
  stats refresh 10s
  stats auth admin:admin
```

## Logging

Enable logs in `global` and configure rsyslog:

```cfg
global
  log /dev/log local0
  log /dev/log local1 notice
```

In `/etc/rsyslog.d/49-haproxy.conf`:

```conf
if ($programname == 'haproxy') then /var/log/haproxy.log
& stop
```

## Best practices

- Validate config before reload: `haproxy -c -f ...`
- Use `alpn h2,http/1.1` for better HTTPS performance.
- Tune timeouts according to your services and clients.
