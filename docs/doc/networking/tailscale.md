---
title: "Tailscale: instalación y configuración básica"
description: "Documentación sobre tailscale: instalación y configuración básica"
tags: ['networking']
updated: 2026-01-25
---

# Tailscale: instalación y configuración básica

> Tailscale crea una red mesh segura basada en WireGuard y autenticación SSO.

## Arquitectura de Tailscale

```mermaid
graph TB
    subgraph "Tailscale SaaS"
        TS[Control Plane<br/>admin.tailscale.com]
        TS --> AUTH[Autenticación SSO<br/>Google/Microsoft/etc]
        TS --> DNS[MagicDNS]
        TS --> ACL[ACL Engine]
    end
    
    subgraph "Nodos/Peers"
        D1[Device 1<br/>Laptop]
        D2[Device 2<br/>Server]
        D3[Device 3<br/>Mobile]
        SR[Subnet Router<br/>Gateway]
        EN[Exit Node<br/>VPN Gateway]
    end
    
    TS -->|ACLs| D1
    TS -->|ACLs| D2
    TS -->|ACLs| D3
    TS -->|ACLs| SR
    TS -->|ACLs| EN
    
    D1 -->|WireGuard| D2
    D1 -->|WireGuard| D3
    D1 -->|WireGuard| SR
    D1 -->|WireGuard| EN
    D2 -->|WireGuard| D3
    SR -->|WireGuard| EN
    
    SR -->|Acceso LAN| LAN[(Red Local)]
    EN -->|Internet| NET[Internet]
    
    style TS fill:#e1f5fe
    style D1 fill:#f3e5f5
    style D2 fill:#f3e5f5
    style D3 fill:#f3e5f5
    style SR fill:#fff3e0
    style EN fill:#ffebee
```

## Tipos de nodos en Tailscale

```mermaid
mindmap
  root((Tipos de Nodos<br/>Tailscale))
    Regular Node
      Conexión mesh
      Acceso peer-to-peer
      MagicDNS
      Sin privilegios especiales
    Subnet Router
      Anuncia rutas locales
      --advertise-routes
      Gateway para LAN
      Requiere autorización
    Exit Node
      --advertise-exit-node
      Gateway de internet
      Enruta todo el tráfico
      Configuración de ACLs
    App Connector
      Próximamente
      Conexión a servicios SaaS
      Sin exposición pública
```

## Requisitos

- Debian/Ubuntu o equivalente con `curl` y `sudo`
- Acceso a `https://login.tailscale.com`

## Instalación rápida

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Verifica servicio y versión:

```bash
tailscale version
sudo systemctl status tailscaled
```

## Autenticación y alta del nodo

```bash
sudo tailscale up
```

- Abre el enlace que aparece y autentícate
- En `admin.tailscale.com` autoriza el dispositivo si es necesario

## Comandos útiles

```bash
# Estado y IPs
tailscale status
ip -4 addr show tailscale0

# Habilitar al arranque
sudo systemctl enable --now tailscaled

# Salir/Desconectar
sudo tailscale down
```

## Hardening y opciones útiles

- ACLs (panel): define quién puede hablar con quién. Ejemplo mínimo (permitir a grupo admins todo):

```json
{
  "acls": [
    {"action": "accept", "src": ["group:admins"], "dst": ["*"]}
  ]
}
```

- DNS: habilita MagicDNS y define dominios de búsqueda; para fuerza DNS corporativo:

```bash
sudo tailscale up --accept-dns=true
```

- Subnet router (acceso a una LAN):

```bash
sudo tailscale up --advertise-routes=192.168.10.0/24
```
Autoriza la ruta en el panel.

### Override de systemd (asegurar red arriba)

```bash
sudo systemctl edit tailscaled
```
Contenido:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Aplica y reinicia:

```bash
sudo systemctl daemon-reload
sudo systemctl restart tailscaled
```

## Notas

- Evita conflictos con otras VPN WireGuard
- Revisa ACLs en el panel para controlar accesos

## Ejemplos con contenedores (Docker)

### Conectar tus contenedores a la VPN

- Opción 1 (userspace subnet router): expone puertos del contenedor Tailscale y usa `--advertise-exit-node`/`--advertise-routes` según necesidad.
- Opción 2 (namespace compartido/sidecar):

```bash
docker run -d --name tailscale \
  --cap-add NET_ADMIN --device /dev/net/tun \
  -v tailscale_state:/var/lib/tailscale \
  --network container:miapp \
  tailscale:latest
```

- Opción 3 (host networking): ejecutar Tailscale en el host o contenedor con `--network host` y el resto usa la red del host.
