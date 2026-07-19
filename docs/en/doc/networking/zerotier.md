---
title: "ZeroTier: installation and basic configuration"
description: "Documentation on zerotier: installation and basic configuration"
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

# ZeroTier: installation and basic configuration

> ZeroTier provides easy-to-deploy L2/L3 virtual networks between devices.

## ZeroTier architecture

```mermaid
graph TB
    subgraph "Controller"
        ZT[ZeroTier Controller<br/>my.zerotier.com]
        ZT --> NET[Virtual Networks<br/>Network IDs]
        ZT --> RULES[Flow Rules<br/>Traffic policies]
        ZT --> DNS[DNS Management]
    end
    
    subgraph "Nodes/Peers"
        P1[Planet<br/>Root Server]
        M1[Moon<br/>Distributed Controller]
        L1[Leaf 1<br/>End Client]
        L2[Leaf 2<br/>Server]
        GW[Gateway<br/>with routes]
    end
    
    ZT -->|Configuration| P1
    ZT -->|Configuration| M1
    ZT -->|Configuration| L1
    ZT -->|Configuration| L2
    ZT -->|Configuration| GW
    
    P1 -->|ZeroTier Protocol| M1
    P1 -->|ZeroTier Protocol| L1
    P1 -->|ZeroTier Protocol| L2
    P1 -->|ZeroTier Protocol| GW
    
    M1 -->|ZeroTier Protocol| L1
    M1 -->|ZeroTier Protocol| L2
    M1 -->|ZeroTier Protocol| GW
    
    L1 -->|ZeroTier Protocol| L2
    L1 -->|ZeroTier Protocol| GW
    L2 -->|ZeroTier Protocol| GW
    
    GW -->|L2/L3 Bridging| LAN[(Physical Networks)]
    
    style ZT fill:#e1f5fe
    style P1 fill:#fff3e0
    style M1 fill:#ffebee
    style L1 fill:#f3e5f5
    style L2 fill:#f3e5f5
    style GW fill:#e8f5e8
```

## Node hierarchy

```mermaid
flowchart TD
    A[Planets<br/>Root servers<br/>Stable and public] --> B[Moons<br/>Distributed<br/>controllers<br/>optional]
    B --> C[Leafs<br/>End clients<br/>User devices]
    
    D[Controller<br/>my.zerotier.com<br/>or self-hosted] --> E[Virtual Networks<br/>Network IDs]
    E --> F[Authorized<br/>members]
    
    style A fill:#fff3e0
    style B fill:#ffebee
    style C fill:#f3e5f5
    style D fill:#e1f5fe
```

## Requirements

- Debian/Ubuntu or equivalent with `curl` and `sudo`
- Access to `https://my.zerotier.com` or your own controller

## Installation

```bash
curl -s https://install.zerotier.com | sudo bash
```

Check the service:

```bash
sudo zerotier-cli -v
sudo systemctl status zerotier-one
```

## Join a network

1. Create a network at `my.zerotier.com` (take note of the Network ID)
2. On the host, join the network using that ID:

```bash
sudo zerotier-cli join <NETWORK_ID>
```

3. Authorize the member from the web console (Members → Authorize)

4. Verify the interface and connectivity:

```bash
ip -br a | grep zt
ping <peer_ip>
```

## Autostart and logs

```bash
sudo systemctl enable --now zerotier-one
journalctl -u zerotier-one -f
```

## Hardening and useful config

- Managed routes: define subnets on the network so ZeroTier installs them automatically on authorized members.
- Basic flow rules to restrict traffic, minimal example (only ICMP and TCP 22 between members):

```text
accept icmp;
accept tcp dport 22;
drop;
```

- MTU: if you see fragmentation, try tuning the MTU of the `zt*` interface (e.g. 2800-9001 depending on the environment).

### systemd override

```bash
sudo systemctl edit zerotier-one
```
Content:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Apply:

```bash
sudo systemctl daemon-reload
sudo systemctl restart zerotier-one
```

## Notes

- Configure managed routes and IP assignment from the web console
- Avoid subnet overlap with the local network

## Containerized examples (Docker)

### Connect your containers to the VPN

- Option 1 (host networking): ZeroTier with `--network host` creates a `zt*` interface on the host.
- Option 2 (sidecar): share the network namespace with your app:

```bash
docker run -d --name zerotier \
  --cap-add NET_ADMIN --device /dev/net/tun \
  -v zt_state:/var/lib/zerotier-one \
  --network container:myapp \
  zerotier:latest
```

- Option 3 (router container): enable NAT inside the ZeroTier container so a Docker network can reach the VPN (iptables MASQUERADE).
