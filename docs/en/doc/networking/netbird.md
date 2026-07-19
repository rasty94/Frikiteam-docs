---
title: "NetBird: basic installation and configuration"
description: "Documentation on netbird: basic installation and configuration"
tags: ['networking']
updated: 2025-11-15
difficulty: advanced
estimated_time: 3 min
category: Networking
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# NetBird: basic installation and configuration

> NetBird is a WireGuard-based mesh VPN solution with access control.

## NetBird architecture

```mermaid
graph TB
    subgraph "Control Plane"
        CP[NetBird Management<br/>app.netbird.io]
        CP --> DB[(Database)]
        CP --> API[REST API]
        CP --> TURN[TURN Servers<br/>optional]
    end
    
    subgraph "Peers/Nodes"
        P1[Peer 1<br/>Linux Server]
        P2[Peer 2<br/>Windows Desktop]
        P3[Peer 3<br/>Mobile iOS]
        P4[Peer 4<br/>Gateway<br/>with routes]
    end
    
    CP -->|Access policies| P1
    CP -->|Access policies| P2
    CP -->|Access policies| P3
    CP -->|Access policies| P4
    
    P1 -->|WireGuard Mesh| P2
    P1 -->|WireGuard Mesh| P3
    P1 -->|WireGuard Mesh| P4
    P2 -->|WireGuard Mesh| P3
    P2 -->|WireGuard Mesh| P4
    P3 -->|WireGuard Mesh| P4
    
    P4 -->|LAN access| LAN[(Local Network<br/>192.168.1.0/24)]
    
    style CP fill:#e1f5fe
    style P1 fill:#f3e5f5
    style P2 fill:#f3e5f5
    style P3 fill:#f3e5f5
    style P4 fill:#fff3e0
```

## Connection flow

```mermaid
sequenceDiagram
    participant U as User
    participant P as Peer (Client)
    participant CP as Control Plane
    participant T as TURN Server
    
    P->>CP: Initial registration (netbird up)
    CP-->>P: Authentication link
    U->>CP: Authentication via browser
    CP-->>P: WireGuard credentials
    
    P->>CP: Peer request
    CP-->>P: List of authorized peers
    
    P->>P: Establish WireGuard connections
    P->>T: Use TURN if NAT traversal fails
    
    Note over P: Connected to the VPN mesh
```

## Requirements

- Debian/Ubuntu or equivalent with `curl` and `sudo`
- Outbound HTTP/HTTPS ports allowed

## Quick installation (official script)

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sudo bash
```

Check the service:

```bash
sudo systemctl status netbird
netbird --version
```

## Joining the network

1. Create an account/tenant in the dashboard (`https://app.netbird.io` or your self-hosted dashboard)
2. Run the login and follow the browser flow:

```bash
netbird up
```

3. Check status and peers:

```bash
netbird status
netbird peers
```

## Startup and logs

```bash
sudo systemctl enable --now netbird
journalctl -u netbird -f
```

## Hardening and useful configuration

- Basic ACLs (dashboard):
  - Create a policy that only allows traffic between the groups you actually need (e.g. `role:admin` ↔ `role:infra`).
  - Deny by default and allow through explicit lists.
- DNS: configure per-peer or per-network DNS in the dashboard; on Linux hosts using `systemd-resolved`, make sure it is active:

```bash
sudo systemctl enable --now systemd-resolved
resolvectl status
```

- Routes: use advertised routes in the dashboard to reach subnets behind a gateway peer.

### systemd override (boot order)

```bash
sudo systemctl edit netbird
```
Drop-in content:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Apply the changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart netbird
```

## Notes

- NetBird relies on WireGuard; avoid conflicts with other active VPNs
- Review the access policies in the dashboard so traffic between peers is allowed

## Container examples (Docker)

### Connecting your containers to the VPN

- Option 1 (host networking): run NetBird on the host or in a container with `--network host`, so your apps use the host stack.
- Option 2 (sidecar namespace): share the network namespace with your app:

```bash
docker run -d --name netbird --cap-add NET_ADMIN --device /dev/net/tun \
  -v netbird_state:/var/lib/netbird --network container:myapp netbird:latest
```

- Option 3 (dedicated Docker network): create a Docker network and route through the NetBird container (requires iptables/masquerade inside the VPN container).
