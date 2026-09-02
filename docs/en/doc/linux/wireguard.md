---
title: "WireGuard VPN"
tags: ['linux', 'vpn', 'wireguard']
category: Linux
updated: 2025-12-07
difficulty: intermediate
status: published
estimated_time: 1 min
---

# WireGuard VPN

WireGuard is an extremely simple but fast and modern VPN.

## Installation

```bash
sudo apt install wireguard
```

## Key Generation

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

## Server Configuration (`/etc/wireguard/wg0.conf`)

```ini
[Interface]
Address = 10.100.0.1/24
SaveConfig = true
ListenPort = 51820
PrivateKey = <SERVER_PRIVATEKEY_CONTENT>

# Peer (Client)
[Peer]
PublicKey = <CLIENT_PUBLICKEY>
AllowedIPs = 10.100.0.2/32
```

## Start

```bash
wg-quick up wg0
systemctl enable wg-quick@wg0
```
