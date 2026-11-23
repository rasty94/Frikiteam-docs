---
title: "OPNsense (virtual router/firewall)"
description: "Virtualized deployment, VirtIO tuning, VLAN segmentation, CARP high availability, and day-2 operations for OPNsense."
tags: ['networking', 'cybersecurity', 'vrouter']
category: Networking
updated: 2026-11-23
last_reviewed: 2026-11-23
difficulty: intermediate
status: published
estimated_time: 4 min
prerequisites:
  - "Networking fundamentals"
  - "Basic virtualization knowledge"
---

# OPNsense (virtual router/firewall)

## The problem

Maintaining a perimeter firewall with hand-written `nftables` works until you have to segment ten VLANs, manage WireGuard/IPsec VPNs, audit rules across a team, and patch without dropping traffic. **OPNsense** (built on FreeBSD) covers that layer with a clear web UI, predictable release cycles, and built-in high availability via CARP.

## When to choose OPNsense

- You need a clear, auditable web GUI for day-to-day firewall operations.
- You want VLAN segmentation, VPNs (WireGuard/OpenVPN/IPsec), local DNS (Unbound), and optional IDS/proxy in a single appliance.
- You want a predictable update cadence (two major releases per year) without proprietary hardware lock-in.

If you need pure carrier-style L3 routing (complex BGP, MPLS, minimal footprint), see [MikroTik CHR](vrouter_mikrotik_chr.md).

## Recommended hypervisor deployment (Proxmox / KVM)

- **vNICs**: at least 2 `virtio` interfaces (`vtnet0` for WAN and `vtnet1` for LAN; add a dedicated `SYNC` interface for HA).
- **CPU and RAM**: 2 vCPU minimum, 4 GB RAM (official minimum 3 GB; 8 GB+ if enabling Suricata IDS/IPS or Zenarmor).
- **Disk**: 40 GB+ SSD (official "reasonable" recommendation), ideally on **ZFS** for Boot Environments during upgrades.

### Critical VirtIO tuning on FreeBSD

When running OPNsense on KVM/Proxmox with `virtio` NICs, hardware-offloaded checksums often break traffic between VMs or across the host bridge. Under **Interfaces → Settings**, check all three offload disable options:

- **Disable hardware checksum offload**
- **Disable hardware TCP segmentation offload (TSO)**
- **Disable hardware large receive offload (LRO)**

Apply the settings and reboot the VM so all `vtnet` interfaces come up cleanly.

## Step-by-step baseline setup

1. **Assign interfaces** on the console (`vtnet0` = WAN, `vtnet1` = LAN) and set the LAN management IP.
2. **Harden access**: change the `root` password, create a named admin user, keep the web GUI off WAN, and enable two-factor authentication (TOTP) under **System → Access → Servers**.
3. **Configure WAN and LAN**: block private networks (RFC1918) and bogons on WAN (when WAN is public) and set up LAN DHCP/DNS (Unbound).
4. **Segment with VLANs**: create VLANs under **Interfaces → Other Types → VLAN** on the LAN trunk and enforce explicit inter-VLAN rules (deny by default between segments).
5. **Tighten firewall rules**: keep the *anti-lockout* rule on LAN; replace broad `any any` rules on server or IoT VLANs with explicit port and destination rules.

## High availability, backups, and upgrades

- **High availability (HA)**: two OPNsense nodes sharing **CARP** virtual IPs on WAN/LAN, state synchronization (`pfsync`) over a dedicated interface, and XMLRPC config replication from primary to secondary.
- **Configuration backup (`config.xml`)**: exportable from **System → Configuration → Backups** (or automated to Nextcloud/Git). The entire configuration lives in that single XML file.
- **Safe upgrades**: before a major upgrade, download `config.xml`, take a hypervisor VM snapshot, and keep console access handy in case an interface name or plugin changes.

## Good practices

- Segment networks with VLANs (management, servers, users, guest/IoT) and use **Aliases** to group hosts and ports cleanly.
- Export `config.xml` before critical changes and keep copies off the firewall.
- Keep firmware and plugins updated in maintenance windows and avoid installing unused plugins.
- Enable logging on deny rules and forward logs via syslog to your observability stack.

## Common risks

- Leaving permissive `any any` rules on internal VLANs, defeating the purpose of segmentation.
- Forgetting to disable hardware checksum/TSO/LRO offloading on `virtio` NICs, causing intermittent drops or stalled TCP sessions.
- Skipping MTU/MSS clamping on PPPoE, WireGuard, or IPsec tunnels (leading to half-loaded pages).
- Undocumented NAT port forwards or third-party plugins blocking major upgrades.

## Operational checklist

- Are WAN and LAN on separate interfaces with no overlap and no management access from WAN?
- Are checksum offload, TSO, and LRO disabled on VirtIO deployments?
- Is a recent, tested `config.xml` backup stored off the firewall?
- Are gateway latency, packet loss, CARP state, and state table usage monitored?
- Is there a rollback path (VM snapshot or ZFS Boot Environment)?

## References

- [OPNsense: hardware requirements](https://docs.opnsense.org/manual/hardware.html)
- [OPNsense: two-factor authentication](https://docs.opnsense.org/manual/how-tos/two_factor.html)
- [OPNsense: High Availability (CARP)](https://docs.opnsense.org/manual/hacarp.html)
