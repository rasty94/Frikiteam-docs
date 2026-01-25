---
title: "Resolución de problemas (Networking)"
description: "Documentación sobre resolución de problemas (networking)"
tags: ['networking']
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Redes
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Fundamentos de redes"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Resolución de problemas (Networking)

## Conectividad entre peers no funciona

- Verifica que ambos peers estén en línea y autorizados
- Comprueba firewalls locales (ufw/nftables/iptables)
- Evita VPNs simultáneas que compitan por rutas/WireGuard

Comandos útiles:

```bash
ip -br a
ip r
ping <peer_ip>
traceroute <peer_ip>
```

## MTU y fragmentación

- Síntomas: SSH lento, cortes, paquetes grandes fallan
- Ajusta MTU en la interfaz de la VPN y/o en el bridge

```bash
sudo ip link set dev tailscale0 mtu 1280 || true
sudo ip link set dev ztXXXXXX mtu 1400 || true
```

## DNS

- Confirma que el resolutor activo sea el esperado (`resolvectl status`)
- Si usas DNS de la VPN, habilita la gestión de DNS en el cliente

## Rutas superpuestas

- Evita solapamiento de subredes entre LAN y VPN
- Revisa rutas anunciadas y prioridad de métricas

## systemd orden de arranque

- Asegura dependencia de `network-online.target` en el servicio de la VPN
- Usa `systemctl edit <service>` y añade:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```
