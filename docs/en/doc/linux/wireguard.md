---
title: "WireGuard VPN"
description: "WireGuard on your own infrastructure: keys, server and clients, routing and NAT, remote access versus site-to-site, operation with wg-quick and troubleshooting."
keywords: "wireguard, vpn, wg-quick, allowedips, persistentkeepalive, nat, site-to-site, homelab, mtu"
tags: ['linux', 'vpn', 'wireguard']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 17 min
category: Linux
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Linux with root access and systemd"
  - "IP addressing and basic routing"
  - "A server with a public IP or a forwarded UDP port"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# WireGuard VPN

## The Problem

You want to reach your Proxmox, Grafana or the NAS at home from outside without exposing any panel to the Internet. Classic VPNs (IPsec, OpenVPN) work, but they bring long configurations, negotiations with many parameters and a lot of code to audit. And when something fails, you do not know whether it is phase 1, phase 2 or the certificate.

WireGuard boils the problem down to the essentials: each end has a key pair, a list of allowed peers and one more network interface. It lives in the Linux kernel, the configuration file fits on one screen and there is no session state to debug. In exchange, it **does not solve** key distribution, addressing or routing for you: you decide those, and that is where almost every failure comes from.

!!! note "What this covers and what it does not"
    This page covers WireGuard "by hand" with `wg` and `wg-quick`: the building block. If you would rather have a control plane manage keys and NAT traversal, see [Tailscale](../networking/tailscale.md) or [NetBird](../networking/netbird.md); the comparison is in [VPN overlay: comparison](../networking/vpn_overlay_comparison.md).

## 📋 Table of Contents

1. [How it works](#how-it-works)
2. [Installation](#installation)
3. [Key generation](#key-generation)
4. [Server](#server-etcwireguardwg0conf)
5. [Client](#client)
6. [Routing and NAT](#routing-and-nat)
7. [Firewall](#firewall)
8. [Startup and operation](#startup-and-operation)
9. [Site-to-site](#site-to-site)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)
12. [References](#references)

## How it works

WireGuard does not distinguish between "server" and "client": everyone is a peer. What we call the server is the peer with a reachable IP or port, and therefore the one that receives the initial connection.

- **Keys**: each peer has a private key (which never leaves the machine) and a public key (which is handed to the others). There is no CA and no certificates.
- **Cryptokey routing**: `AllowedIPs` does two things at once. When sending, it decides which peer a packet goes to based on its destination. When receiving, it drops any decrypted packet whose source is not in that peer's list.
- **UDP and silent**: it uses a single UDP port and does not answer packets from anyone it does not know, so a scan sees nothing.
- **Roaming**: a peer's `Endpoint` updates itself from the latest authenticated packet that arrives, so a laptop that moves from wifi to 4G stays connected.

!!! warning "AllowedIPs is not just a filter"
    It is also the tunnel's routing table. Putting `0.0.0.0/0` on a client sends all its traffic through the VPN; putting it on two peers of the same end makes only one of them receive it.

## Installation

On current Debian and Ubuntu, support is in the kernel and the package provides the tools:

```bash
sudo apt install wireguard
```

The package installs `wg` (inspection and live tuning) and `wg-quick` (brings the interface up by reading a file). On a very old kernel the module may not be available; check your distribution's official documentation.

## Key generation

Generate each key pair on the machine that will use it, with restrictive permissions:

```bash
umask 077
wg genkey | tee privatekey | wg pubkey > publickey
```

`umask 077` keeps the private key from being readable by other users. To add an extra symmetric layer (resistance to future quantum computer attacks, according to the project's documentation) you can generate a preshared key for each pair of peers:

```bash
wg genpsk > preshared_srv_laptop
```

That key is declared with `PresharedKey` on both ends and is optional.

## Server (`/etc/wireguard/wg0.conf`)

```ini
[Interface]
Address = 10.100.0.1/24
ListenPort = 51820
PrivateKey = <CONTENIDO_DE_PRIVATEKEY_SERVIDOR>

# Peer: portátil
[Peer]
PublicKey = <PUBLICKEY_DEL_CLIENTE>
AllowedIPs = 10.100.0.2/32

# Peer: móvil
[Peer]
PublicKey = <PUBLICKEY_DEL_MOVIL>
AllowedIPs = 10.100.0.3/32
```

Each client gets a `/32` inside the tunnel network (`10.100.0.0/24`). That network must differ from any LAN your clients will be on: if the laptop is on a `192.168.1.0/24` wifi and so is your home, the routes collide.

!!! warning "SaveConfig = true rewrites the file"
    The previous version of this page used `SaveConfig = true`. With it, `wg-quick` dumps the in-memory configuration to the file when the interface goes down, and **discards your comments and any manual edits made while it was up**. For a file you maintain by hand or in Git, leave it disabled.

The file contains the private key: permissions `600` and owned by root.

```bash
sudo chmod 600 /etc/wireguard/wg0.conf
```

## Client

```ini
[Interface]
Address = 10.100.0.2/24
PrivateKey = <CONTENIDO_DE_PRIVATEKEY_CLIENTE>
DNS = 10.100.0.1

[Peer]
PublicKey = <PUBLICKEY_DEL_SERVIDOR>
Endpoint = vpn.example.com:51820
AllowedIPs = 10.100.0.0/24, 192.168.10.0/24
PersistentKeepalive = 25
```

- **Split tunnel** (the one above): only traffic to the tunnel network and the home LAN `192.168.10.0/24` goes through the VPN; the rest goes out directly. It is the recommended setup for access to internal services.
- **Full tunnel**: change `AllowedIPs` to `0.0.0.0/0, ::/0` and all traffic goes through the server. It requires NAT on the server (next section) and a decision about DNS.
- `DNS` is only interpreted by `wg-quick`, which uses `resolvconf` or `systemd-resolved` to apply it. If your system has neither, the line can make startup fail.
- `PersistentKeepalive = 25` sends a packet every 25 seconds. It is needed if the client is behind NAT and the server must be able to reach it without the client having sent anything first. Without it, the NAT entry expires and the tunnel looks down in one direction.

## Routing and NAT

For clients to reach the LAN behind the server, the server must forward packets. Enable it persistently:

```bash
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl --system
```

If the LAN has no return route to `10.100.0.0/24` (because the WireGuard server is not its gateway), add NAT so LAN devices see connections as originating from the server. With `iptables`, in the server's `[Interface]` section:

```ini
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

`%i` is replaced by `wg-quick` with the interface name (`wg0`) and `eth0` must be your real outbound interface. If you already have a forwarding policy in nftables, write the equivalent rules there instead of mixing both worlds.

!!! tip "The best route is the return route"
    NAT works, but it hides the real source in LAN logs. If you can add a static route `10.100.0.0/24` towards the WireGuard server on your router, you do not need MASQUERADE and you keep traceability.

## Firewall

The server only needs one port open: `51820/udp` on the host firewall and, if there is a router in front, a forward of the same port to it. Example nftables rules are in [nftables and fail2ban](../cybersecurity/nftables_fail2ban.md). You should:

- Accept `udp dport 51820` from any source on the public interface.
- Allow on the `wg0` interface only what you want to expose to clients; being authenticated does not mean they should reach everything.
- If the server is a virtual router, the [vRouters](../networking/vrouters.md) comparison helps decide where to place the endpoint.

## Startup and operation

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

`wg-quick@wg0` is the unit that reads `/etc/wireguard/wg0.conf` at boot. To stop or restart:

```bash
sudo wg-quick down wg0
sudo systemctl restart wg-quick@wg0
```

To see live status:

```bash
sudo wg show
```

The output lists the interface with its public key and port, and below it each peer with its `endpoint`, `allowed ips`, time since the last handshake and bytes transferred. A peer that has never completed a handshake does not show that line: it is the most direct sign that traffic is not arriving or the keys do not match.

### Changes without dropping the tunnel

To add a peer on the fly, without restarting the interface:

```bash
sudo wg set wg0 peer <PUBLICKEY_NUEVO> allowed-ips 10.100.0.4/32
```

That is not saved to the file (except with `SaveConfig`), so add it to `wg0.conf` too. If you edit the file and want to apply it without tearing down existing connections, `wg-quick strip` produces the configuration without `wg-quick`-specific directives and `wg syncconf` applies it:

```bash
sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'
```

`syncconf` only applies what `wg` understands (private key, port, peers and their `AllowedIPs`, `Endpoint`, etc.); it does not touch `Address`, routes or `PostUp`. If you change those, bring the interface down and up.

### Revoking access

Removing the `[Peer]` block and applying the change is enough: without its public key in the list, the peer cannot talk to the server. There are no revocation lists because there are no certificates. Rotate the keys of a lost device by generating a new pair and replacing it.

## Site-to-site

To join two sites (home and a VPS, or two labs), both sides are server and client at once. Each side declares the remote LAN in `AllowedIPs`:

```ini
# Sede A (LAN 192.168.10.0/24, túnel 10.100.0.1)
[Interface]
Address = 10.100.0.1/30
ListenPort = 51820
PrivateKey = <CLAVE_PRIVADA_A>

[Peer]
PublicKey = <CLAVE_PUBLICA_B>
Endpoint = sedeb.example.com:51820
AllowedIPs = 10.100.0.2/32, 192.168.20.0/24
PersistentKeepalive = 25
```

Site B is the mirror image, with `192.168.10.0/24` in its `AllowedIPs`. Devices on each LAN need their gateway to know the remote network is behind the WireGuard end (a static route, or the end being the gateway). For topologies with more than two sites, a full mesh by hand scales poorly; consider a control plane like [Tailscale](../networking/tailscale.md) or [NetBird](../networking/netbird.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `wg show` shows no *latest handshake* line | UDP is not arriving (closed port, NAT without forward) or the keys do not match | Check the `51820/udp` forward; verify the public key declared on each side is the other's |
| Handshake succeeds but there is no traffic | `AllowedIPs` does not include the source or destination IP | Review `AllowedIPs` on both ends; remember it filters on receive |
| The client reaches the server but not the LAN | `ip_forward` missing or the LAN does not know the return route | Enable forwarding; add a static route or NAT |
| The tunnel works from client to server but not the other way | Client behind NAT without keepalive | Add `PersistentKeepalive = 25` on the client |
| Hung connections with large pages or SSH that freezes | MTU: encapsulation reduces the usable size | Lower `MTU` in `[Interface]`; if you do not set it, `wg-quick` derives it from the interface of the route to the `Endpoint` (or the default route) |
| `wg-quick up` fails with a DNS or resolvconf error | `DNS` line without `resolvconf` or `systemd-resolved` | Install one of them or remove `DNS` and configure the resolver by hand |
| After `down`, changes and comments in `wg0.conf` are lost | `SaveConfig = true` | Disable it and manage the file by hand or with Git |
| Two clients with the same `AllowedIPs` and only one works | Each IP can belong to only one peer | Assign a unique `/32` per client |
| Works at home but not on a corporate network | The network blocks non-standard outbound UDP | Try a more common port such as `443/udp` |

To see why a packet does not get in, `tcpdump -ni eth0 udp port 51820` on the server confirms whether datagrams arrive; the content is encrypted, but it is enough to tell whether the problem is network or keys.

## Best Practices

- One key pair per device, never shared; that way you revoke one without touching the rest.
- Minimal `AllowedIPs`: the client's `/32` on the server and only the necessary networks on the client.
- Private keys with `600` permissions, outside repositories and unencrypted backups. If you version `wg0.conf`, use a secrets manager and templates, not the key in the clear.
- Reserve your own tunnel range (`10.100.0.0/24` here) that does not overlap with any known LAN.
- Document the table of IPs assigned to each peer; it is the only "user database" that exists.
- Expose only the UDP port and control what incoming traffic from `wg0` can reach with the firewall.
- Monitor each peer's last handshake (`wg show wg0 latest-handshakes`) to detect down peers.
- For large fleets or complex NAT traversal, consider a control layer on top before multiplying files by hand.

## References

- [WireGuard: official documentation](https://www.wireguard.com/)
- [wg(8) and wg-quick(8)](https://man7.org/linux/man-pages/man8/wg.8.html)
- [Tailscale](../networking/tailscale.md)
- [NetBird](../networking/netbird.md)
- [VPN overlay: comparison](../networking/vpn_overlay_comparison.md)
- [nftables and fail2ban](../cybersecurity/nftables_fail2ban.md)
- [vRouters: comparison](../networking/vrouters.md)
