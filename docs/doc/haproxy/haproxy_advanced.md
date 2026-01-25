---
title: HAProxy — TLS y Escalado Avanzado
updated: 2026-01-25
---

# HAProxy — TLS y Escalado Avanzado

## Resumen
Prácticas para terminación TLS, reenvío de cabeceras y configuración para alta disponibilidad.

## TLS
- Usar certificados gestionados (Let's Encrypt / ACME) o certificados firmados internamente.
- TLS termination en el edge (frontend) y backend con re-encriptación si se requiere.

## Escalado
- Configurar `balance` y `option httpchk` para healthchecks.
- Usar Keepalived/VRRP para alta disponibilidad del proxy.

## Ejemplo de frontend

```haproxy
frontend http_front
  bind *:80
  bind *:443 ssl crt /etc/haproxy/certs/
  mode http
  default_backend app_back
```

---
