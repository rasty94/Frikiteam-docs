---
title: "ZeroTier: instalación y configuración básica"
description: "Documentación sobre zerotier: instalación y configuración básica"
tags: ['networking']
updated: 2026-01-25
difficulty: advanced
estimated_time: 3 min
category: Redes
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Fundamentos de redes"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# ZeroTier: instalación y configuración básica

> ZeroTier proporciona redes virtuales L2/L3 fáciles de desplegar entre dispositivos.

## Arquitectura de ZeroTier

```mermaid
graph TB
    subgraph "Controller"
        ZT[ZeroTier Controller<br/>my.zerotier.com]
        ZT --> NET[Redes Virtuales<br/>Network IDs]
        ZT --> RULES[Flow Rules<br/>Políticas de tráfico]
        ZT --> DNS[DNS Management]
    end
    
    subgraph "Nodos/Peers"
        P1[Planet<br/>Root Server]
        M1[Moon<br/>Controller Distribuido]
        L1[Leaf 1<br/>Cliente Final]
        L2[Leaf 2<br/>Servidor]
        GW[Gateway<br/>con rutas]
    end
    
    ZT -->|Configuración| P1
    ZT -->|Configuración| M1
    ZT -->|Configuración| L1
    ZT -->|Configuración| L2
    ZT -->|Configuración| GW
    
    P1 -->|Protocolo ZeroTier| M1
    P1 -->|Protocolo ZeroTier| L1
    P1 -->|Protocolo ZeroTier| L2
    P1 -->|Protocolo ZeroTier| GW
    
    M1 -->|Protocolo ZeroTier| L1
    M1 -->|Protocolo ZeroTier| L2
    M1 -->|Protocolo ZeroTier| GW
    
    L1 -->|Protocolo ZeroTier| L2
    L1 -->|Protocolo ZeroTier| GW
    L2 -->|Protocolo ZeroTier| GW
    
    GW -->|Bridging L2/L3| LAN[(Redes Físicas)]
    
    style ZT fill:#e1f5fe
    style P1 fill:#fff3e0
    style M1 fill:#ffebee
    style L1 fill:#f3e5f5
    style L2 fill:#f3e5f5
    style GW fill:#e8f5e8
```

## Jerarquía de nodos

```mermaid
flowchart TD
    A[Planets<br/>Servidores raíz<br/>Estables y públicos] --> B[Moons<br/>Controladores<br/>distribuidos<br/>opcionales]
    B --> C[Leafs<br/>Clientes finales<br/>Dispositivos usuarios]
    
    D[Controller<br/>my.zerotier.com<br/>o self-hosted] --> E[Redes Virtuales<br/>Network IDs]
    E --> F[Miembros<br/>autorizados]
    
    style A fill:#fff3e0
    style B fill:#ffebee
    style C fill:#f3e5f5
    style D fill:#e1f5fe
```

## Requisitos

- Debian/Ubuntu o equivalente con `curl` y `sudo`
- Acceso a `https://my.zerotier.com` o controlador propio

## Instalación

```bash
curl -s https://install.zerotier.com | sudo bash
```

Verifica servicio:

```bash
sudo zerotier-cli -v
sudo systemctl status zerotier-one
```

## Unirse a una red

1. Crea una red en `my.zerotier.com` (obtén el Network ID)
2. En el host, únete a la red con el ID:

```bash
sudo zerotier-cli join <NETWORK_ID>
```

3. Autoriza el miembro desde el panel (Members → Authorize)

4. Comprueba interfaz y conectividad:

```bash
ip -br a | grep zt
ping <peer_ip>
```

## Arranque y logs

```bash
sudo systemctl enable --now zerotier-one
journalctl -u zerotier-one -f
```

## Hardening y configuración útil

- Rutas gestionadas: define subredes en la red para que ZeroTier las instale automáticamente en los miembros autorizados.
- Reglas de flujo (Flow Rules) básicas para limitar tráfico, ejemplo mínimo (solo ICMP y TCP 22 entre miembros):

```text
accept icmp;
accept tcp dport 22;
drop;
```

- MTU: si ves fragmentación, prueba ajustar MTU de la interfaz `zt*` (ej. 2800-9001 según entorno).

### Override de systemd

```bash
sudo systemctl edit zerotier-one
```
Contenido:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Aplica:

```bash
sudo systemctl daemon-reload
sudo systemctl restart zerotier-one
```

## Notas

- Configura rutas administradas y asignación de IPs desde el panel
- Evita solapamiento de subredes con la red local

## Ejemplos con contenedores (Docker)

### Conectar tus contenedores a la VPN

- Opción 1 (host networking): ZeroTier con `--network host` crea interfaz `zt*` en el host.
- Opción 2 (sidecar): comparte namespace de red con tu app:

```bash
docker run -d --name zerotier \
  --cap-add NET_ADMIN --device /dev/net/tun \
  -v zt_state:/var/lib/zerotier-one \
  --network container:miapp \
  zerotier:latest
```

- Opción 3 (enrutador en contenedor): habilita NAT en el contenedor ZeroTier para que una red Docker alcance la VPN (iptables MASQUERADE).
