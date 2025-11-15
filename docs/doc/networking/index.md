# Networking

En esta sección encontrarás guías prácticas y concisas para desplegar y configurar soluciones de red y VPN.

- [NetBird: instalación y configuración básica](netbird.md)
- [Tailscale: instalación y configuración básica](tailscale.md)
- [ZeroTier: instalación y configuración básica](zerotier.md)
- [Resolución de problemas](troubleshooting.md)
- [Comparativa rápida: NetBird vs Tailscale vs ZeroTier](compare.md)

## Arquitecturas de las soluciones VPN

### NetBird - Arquitectura Mesh con Control Plane

```mermaid
graph TB
    subgraph "Control Plane (SaaS/Self-hosted)"
        CP[NetBird Management]
        CP --> DB[(Base de datos)]
        CP --> TURN[TURN Servers]
    end
    
    subgraph "Nodos"
        N1[Peer 1<br/>Linux/Windows/macOS]
        N2[Peer 2<br/>Servidor]
        N3[Peer 3<br/>Mobile]
    end
    
    CP -->|Políticas de acceso| N1
    CP -->|Políticas de acceso| N2
    CP -->|Políticas de acceso| N3
    
    N1 -->|WireGuard Mesh| N2
    N1 -->|WireGuard Mesh| N3
    N2 -->|WireGuard Mesh| N3
    
    style CP fill:#e1f5fe
    style N1 fill:#f3e5f5
    style N2 fill:#f3e5f5
    style N3 fill:#f3e5f5
```

### Tailscale - Arquitectura con Coordinación Central

```mermaid
graph TB
    subgraph "Tailscale SaaS"
        TS[Control Plane]
        TS --> AUTH[Autenticación SSO]
        TS --> DNS[MagicDNS]
    end
    
    subgraph "Nodos"
        D1[Device 1<br/>Tailscale Agent]
        D2[Device 2<br/>Subnet Router]
        D3[Device 3<br/>Exit Node]
    end
    
    TS -->|ACLs| D1
    TS -->|ACLs| D2
    TS -->|ACLs| D3
    
    D1 -->|WireGuard| D2
    D1 -->|WireGuard| D3
    D2 -->|WireGuard| D3
    
    D2 -->|Acceso LAN| LAN[(Red Local)]
    
    style TS fill:#e1f5fe
    style D1 fill:#f3e5f5
    style D2 fill:#f3e5f5
    style D3 fill:#f3e5f5
```

### ZeroTier - Arquitectura con Controlador Central

```mermaid
graph TB
    subgraph "Controller (SaaS/Self-hosted)"
        ZT[ZeroTier Controller]
        ZT --> NET[Redes Virtuales]
        ZT --> RULES[Flow Rules]
    end
    
    subgraph "Nodos"
        P1[Peer 1<br/>Planet/Moon/Leaf]
        P2[Peer 2<br/>Servidor]
        P3[Peer 3<br/>Cliente]
    end
    
    ZT -->|Configuración| P1
    ZT -->|Configuración| P2
    ZT -->|Configuración| P3
    
    P1 -->|ZeroTier Protocol| P2
    P1 -->|ZeroTier Protocol| P3
    P2 -->|ZeroTier Protocol| P3
    
    P2 -->|Acceso L2/L3| LAN[(Redes Físicas)]
    
    style ZT fill:#e1f5fe
    style P1 fill:#f3e5f5
    style P2 fill:#f3e5f5
    style P3 fill:#f3e5f5
```

## Videos tutoriales

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;">
  <iframe src="https://www.youtube.com/embed/eCXl09h7lqo" frameborder="0" allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe>
</div>

*Video: Redes VPN modernas - NetBird, Tailscale y ZeroTier comparados*
