---
title: "NetBird: instalación y configuración básica"
description: "Documentación sobre netbird: instalación y configuración básica"
tags: ['networking']
updated: 2026-01-25
---

# NetBird: instalación y configuración básica

> NetBird es una solución de VPN mesh basada en WireGuard con control de acceso.

## Arquitectura de NetBird

```mermaid
graph TB
    subgraph "Control Plane"
        CP[NetBird Management<br/>app.netbird.io]
        CP --> DB[(Base de datos)]
        CP --> API[API REST]
        CP --> TURN[TURN Servers<br/>opcionales]
    end
    
    subgraph "Peers/Nodos"
        P1[Peer 1<br/>Servidor Linux]
        P2[Peer 2<br/>Desktop Windows]
        P3[Peer 3<br/>Mobile iOS]
        P4[Peer 4<br/>Gateway<br/>con rutas]
    end
    
    CP -->|Políticas de acceso| P1
    CP -->|Políticas de acceso| P2
    CP -->|Políticas de acceso| P3
    CP -->|Políticas de acceso| P4
    
    P1 -->|WireGuard Mesh| P2
    P1 -->|WireGuard Mesh| P3
    P1 -->|WireGuard Mesh| P4
    P2 -->|WireGuard Mesh| P3
    P2 -->|WireGuard Mesh| P4
    P3 -->|WireGuard Mesh| P4
    
    P4 -->|Acceso LAN| LAN[(Red Local<br/>192.168.1.0/24)]
    
    style CP fill:#e1f5fe
    style P1 fill:#f3e5f5
    style P2 fill:#f3e5f5
    style P3 fill:#f3e5f5
    style P4 fill:#fff3e0
```

## Flujo de conexión

```mermaid
sequenceDiagram
    participant U as Usuario
    participant P as Peer (Cliente)
    participant CP as Control Plane
    participant T as TURN Server
    
    P->>CP: Registro inicial (netbird up)
    CP-->>P: Enlace de autenticación
    U->>CP: Autenticación vía navegador
    CP-->>P: Credenciales WireGuard
    
    P->>CP: Solicitud de peers
    CP-->>P: Lista de peers autorizados
    
    P->>P: Establecer conexiones WireGuard
    P->>T: Usar TURN si NAT traversal falla
    
    Note over P: Conectado a la mesh VPN
```

## Requisitos

- Debian/Ubuntu o equivalente con `curl` y `sudo`
- Puertos salientes HTTP/HTTPS permitidos

## Instalación rápida (script oficial)

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sudo bash
```

Verifica servicio:

```bash
sudo systemctl status netbird
netbird --version
```

## Unirse a la red

1. Crea una cuenta/tenant en el panel (`https://app.netbird.io` o tu panel self-hosted)
2. Ejecuta el login y sigue el flujo del navegador:

```bash
netbird up
```

3. Verifica estado y peers:

```bash
netbird status
netbird peers
```

## Arranque y logs

```bash
sudo systemctl enable --now netbird
journalctl -u netbird -f
```

## Hardening y configuración útil

- ACLs básicas (panel):
  - Crea una política que permita tráfico solo entre grupos necesarios (ej. `role:admin` ↔ `role:infra`).
  - Deniega por defecto y permite por listas.
- DNS: configura DNS por peer o por red en el panel; en hosts Linux con `systemd-resolved` asegúrate de tenerlo activo:

```bash
sudo systemctl enable --now systemd-resolved
resolvectl status
```

- Rutas: usa rutas anunciadas en el panel para acceder a subredes detrás de un peer gateway.

### Override de systemd (orden de arranque)

```bash
sudo systemctl edit netbird
```
Contenido del drop-in:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Aplica cambios:

```bash
sudo systemctl daemon-reload
sudo systemctl restart netbird
```

## Notas

- NetBird usa WireGuard; evita conflictos con otras VPN activas
- Revisa políticas de acceso en el panel para permitir tráfico entre peers

## Ejemplos con contenedores (Docker)

### Conectar tus contenedores a la VPN

- Opción 1 (host networking): ejecutar NetBird en el host o en contenedor con `--network host`, y tus apps usan la pila del host.
- Opción 2 (sidecar namespace): comparte el namespace de red con tu app:

```bash
docker run -d --name netbird --cap-add NET_ADMIN --device /dev/net/tun \
  -v netbird_state:/var/lib/netbird --network container:miapp netbird:latest
```

- Opción 3 (red Docker dedicada): crea una red Docker y enruta a través del contenedor NetBird (requiere iptables/masquerade en el contenedor VPN).
