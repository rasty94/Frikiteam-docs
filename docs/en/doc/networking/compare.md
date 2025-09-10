# Quick comparison: NetBird vs Tailscale vs ZeroTier

- Purpose:
  - NetBird: mesh VPN with granular access control, optional self-hosted
  - Tailscale: mesh VPN with SSO, simplicity-first, SaaS control plane
  - ZeroTier: flexible L2/L3 virtual networks, SaaS or self-hosted controller

- Installation:
  - NetBird: official script, `netbird` client
  - Tailscale: official script, `tailscaled` service
  - ZeroTier: official script, `zerotier-one` service

- Control/Console:
  - NetBird: app.netbird.io or self-hosted
  - Tailscale: admin.tailscale.com (SaaS)
  - ZeroTier: my.zerotier.com or own controller

- Routes / LAN access:
  - NetBird: advertised routes via dashboard; access policies
  - Tailscale: `--advertise-routes` + approval in console
  - ZeroTier: managed routes per network

- ACLs/Policies:
  - NetBird: access policies by groups/peers
  - Tailscale: centralized JSON ACLs
  - ZeroTier: Flow Rules per network

- DNS:
  - NetBird: per-peer/network DNS settings
  - Tailscale: MagicDNS and managed nameservers
  - ZeroTier: per-network DNS assignments

- Self-hosted:
  - NetBird: yes (control plane and TURN optional)
  - Tailscale: limited (Headscale alternative, community-maintained)
  - ZeroTier: yes (controller)

- Typical use cases:
  - NetBird: secure site-to-site and servers with fine-grained control
  - Tailscale: quick device/team connectivity with SSO
  - ZeroTier: L2/L3 overlays, labs and hybrid networks
