# Comparativa rápida: NetBird vs Tailscale vs ZeroTier

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
