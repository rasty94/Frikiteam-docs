# Comparativa rápida: NetBird vs Tailscale vs ZeroTier

## Diagrama de comparación visual

```mermaid
mindmap
  root((VPN Mesh<br/>Soluciones))
    NetBird
      Enfoque
        Control granular
        Self-hosted opcional
        Políticas avanzadas
      Arquitectura
        Control plane central
        WireGuard mesh
        TURN opcional
      Casos de uso
        Multi-sede
        Acceso condicional
        Zero-trust
    Tailscale
      Enfoque
        Simplicidad
        SaaS first
        SSO integrado
      Arquitectura
        Control plane SaaS
        WireGuard mesh
        MagicDNS
      Casos de uso
        Equipos remotos
        Desarrollo
        Acceso rápido
    ZeroTier
      Enfoque
        Redes virtuales
        L2/L3 flexible
        Controller opcional
      Arquitectura
        Controller central
        Protocolo propio
        Flow rules
      Casos de uso
        Laboratorios
        Redes híbridas
        SDN simple
```

## Tabla comparativa detallada

| Aspecto | NetBird | Tailscale | ZeroTier |
|---------|---------|-----------|----------|
| **Propósito** | VPN mesh con control de acceso granular | VPN mesh con SSO, enfoque simplicidad | Redes virtuales L2/L3 flexibles |
| **Instalación** | Script oficial, cliente `netbird` | Script oficial, servicio `tailscaled` | Script oficial, servicio `zerotier-one` |
| **Panel de control** | app.netbird.io o self-hosted | admin.tailscale.com (SaaS) | my.zerotier.com o controlador propio |
| **Rutas y LAN** | Políticas de acceso, rutas anunciadas | `--advertise-routes` + autorización | Managed routes por red |
| **ACLs/Políticas** | Políticas por grupos/peers | ACLs JSON centralizadas | Flow Rules a nivel de red |
| **DNS** | DNS por peer/red en panel | MagicDNS y nameservers | Asignación DNS por red |
| **Self-hosted** | Sí (control plane y TURN) | Limitado (Headscale alternativo) | Sí (controller) |
| **Casos típicos** | Acceso seguro entre sedes/servidores | Acceso entre dispositivos/equipos | Overlays L2/L3, laboratorios |

## Diagrama de flujo de decisión

```mermaid
flowchart TD
    A[¿Qué necesito?] --> B{¿Prioridad?}
    
    B -->|Control granular| C[NetBird]
    B -->|Simplicidad/SaaS| D[Tailscale]
    B -->|Flexibilidad L2/L3| E[ZeroTier]
    
    C --> F{¿Self-hosted?}
    D --> G{¿Presupuesto?}
    E --> H{¿Complejidad?}
    
    F -->|Sí| I[NetBird Self-hosted]
    F -->|No| J[NetBird SaaS]
    
    G -->|Gratuito| K[Tailscale Free]
    G -->|Pago| L[Tailscale Pro]
    
    H -->|Simple| M[ZeroTier Básico]
    H -->|Avanzado| N[ZeroTier Flow Rules]
    
    style A fill:#e1f5fe
    style C fill:#c8e6c9
    style D fill:#ffcdd2
    style E fill:#bbdefb
```

## Arquitecturas comparadas

### Modelo de Seguridad

```mermaid
graph TB
    subgraph "NetBird - Zero Trust"
        NB[NetBird]
        NB --> POL[Políticas Granulares]
        NB --> ACL[ACLs por Peer/Grupo]
        NB --> AUD[Auditoría]
    end
    
    subgraph "Tailscale - Confianza Implícita"
        TS[Tailscale]
        TS --> SSO[Autenticación SSO]
        TS --> ACL2[ACLs Simples]
        TS --> DNS2[MagicDNS]
    end
    
    subgraph "ZeroTier - Redes Virtuales"
        ZT[ZeroTier]
        ZT --> L2[L2/L3 Bridging]
        ZT --> RULES[Flow Rules]
        ZT --> VLAN[VLAN-like Networks]
    end
    
    style NB fill:#c8e6c9
    style TS fill:#ffcdd2
    style ZT fill:#bbdefb
```

- Propósito:
  - NetBird: VPN mesh con control de acceso granular y enfoque self-hosted opcional
  - Tailscale: VPN mesh con SSO, simplicity-first, gestión central SaaS
  - ZeroTier: redes virtuales L2/L3 flexibles con controlador SaaS o propio

- Instalación:
  - NetBird: script oficial, cliente `netbird`
  - Tailscale: script oficial, servicio `tailscaled`
  - ZeroTier: script oficial, servicio `zerotier-one`

- Control/Panel:
  - NetBird: app.netbird.io o self-hosted (control plane)
  - Tailscale: admin.tailscale.com (SaaS)
  - ZeroTier: my.zerotier.com o controlador propio

- Rutas y LAN access:
  - NetBird: rutas anunciadas desde panel; políticas de acceso
  - Tailscale: `--advertise-routes` + autorización en panel
  - ZeroTier: managed routes por red

- ACLs/Políticas:
  - NetBird: políticas de acceso por grupos/peers
  - Tailscale: ACLs JSON centralizadas
  - ZeroTier: Flow Rules a nivel de red

- DNS:
  - NetBird: DNS por peer/red en panel
  - Tailscale: MagicDNS y nameservers gestionados
  - ZeroTier: asignación de DNS por red

- Self-hosted:
  - NetBird: sí (control plane y TURN opcionales)
  - Tailscale: limitado (Headscale como alternativa no oficial)
  - ZeroTier: sí (controller)

- Casos de uso típicos:
  - NetBird: acceso seguro entre sedes y servidores con control granular
  - Tailscale: acceso rápido entre dispositivos y equipos con SSO
  - ZeroTier: overlays L2/L3, laboratorios y redes híbridas
