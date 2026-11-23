---
title: "MikroTik CHR (Cloud Hosted Router)"
description: "Deployment, licensing, RouterOS v7 baseline configuration, and hardening for MikroTik CHR in L3 routing and labs."
tags: ['networking', 'vrouter']
category: Networking
updated: 2026-11-23
last_reviewed: 2026-11-23
difficulty: advanced
status: published
estimated_time: 4 min
prerequisites:
  - "Networking fundamentals"
  - "Basic virtualization knowledge"
  - "Dynamic routing concepts"
---

# MikroTik CHR (Cloud Hosted Router)

## The problem

When you need a virtual router with advanced L3 capabilities (BGP, OSPF, VRF, WireGuard, or MPLS) on Proxmox, KVM, or a cloud provider, many commercial appliances either cost too much or demand heavy VMs. **MikroTik Cloud Hosted Router (CHR)** runs 64-bit RouterOS built specifically for hypervisors: it boots in seconds, uses minimal RAM, and exposes the same networking stack as physical MikroTik hardware.

## When to choose MikroTik CHR

- ISP/WISP scenarios, carrier-style labs, or multi-site interconnects with BGP/OSPF.
- Advanced routing policy requirements (VRF, Policy-Based Routing, GRE/WireGuard/IPsec tunnels).
- Teams already comfortable with RouterOS who want reproducible virtual topologies with a small footprint.

If you prioritize a guided web UI for perimeter firewalling and office segmentation, [OPNsense](vrouter_opnsense.md) or [pfSense](vrouter_pfsense.md) is usually a better fit.

## Recommended deployment and licensing

- **vNICs**: 2–4 `virtio` (or `vmxnet3` on ESXi) interfaces depending on topology, with a dedicated management interface where possible.
- **CPU and RAM**: 2+ vCPU, 512 MB–2 GB RAM (up to 4 GB if carrying full BGP tables).
- **Disk**: 2–8 GB (official CHR raw/qcow2 image; grow it if storing local logs).

CHR licensing caps **upload throughput per interface** rather than locking RouterOS features:

| CHR license | Per-interface upload cap | Typical use |
| --- | --- | --- |
| **Free** | 1 Mbps | Functional labs, BGP/OSPF testing |
| **P1** | 1 Gbps | Branch edge, VPN concentrator, labs with real traffic |
| **P10** | 10 Gbps | Virtualized core, high-capacity trunks |
| **P-Unlimited** | No license cap | Carriers and nodes with 25G/40G+ interfaces |

## RouterOS v7 baseline configuration

After importing the CHR disk into your hypervisor, the initial account is `admin` with an empty password (set it immediately on the console). A minimal hardened baseline with WAN (`ether1`) and LAN (`ether2`):

```text
# 1. Identity and admin password
/system/identity/set name=chr-edge-01
/user/set admin password="CHANGE-THIS-LONG-PASSWORD"

# 2. Addressing and default route
/ip/address/add address=203.0.113.10/24 interface=ether1 comment="WAN"
/ip/address/add address=10.10.20.1/24 interface=ether2 comment="LAN"
/ip/route/add dst-address=0.0.0.0/0 gateway=203.0.113.1

# 3. Disable unused management services and restrict SSH/WinBox to LAN
/ip/service/disable telnet,ftp,www,api,api-ssl
/ip/service/set ssh address=10.10.20.0/24
/ip/service/set winbox address=10.10.20.0/24

# 4. Minimal stateful firewall (input + forward)
/ip/firewall/filter/add chain=input connection-state=established,related action=accept
/ip/firewall/filter/add chain=input in-interface=ether2 action=accept comment="Allow LAN management"
/ip/firewall/filter/add chain=input action=drop comment="Drop everything else to router"

/ip/firewall/filter/add chain=forward connection-state=established,related action=accept
/ip/firewall/filter/add chain=forward connection-state=invalid action=drop
/ip/firewall/filter/add chain=forward in-interface=ether2 out-interface=ether1 action=accept
/ip/firewall/filter/add chain=forward action=drop comment="Drop everything else in forward"

# 5. Outbound NAT for LAN
/ip/firewall/nat/add chain=srcnat out-interface=ether1 action=masquerade
```

## Backups and rollback

Combine both backup formats before making routing changes or upgrading RouterOS:

```text
# Human-readable plain-text export (ideal for Git versioning and diffs)
/export file=chr-edge-01-base

# Full binary backup (only restorable on matching version/architecture)
/system/backup/save name=chr-edge-01-bin
```

Take a hypervisor VM snapshot as well before jumping RouterOS release trains.

## Good practices

- Separate management and data planes (dedicated VLAN or VRF) and restrict WinBox/SSH by source address.
- Document BGP/OSPF route filters and avoid advertising prefixes without explicit prefix lists.
- Evaluate **FastTrack** carefully: it speeds up forwarding significantly, but bypasses simple queues, IPsec, and parts of packet marking.
- Pin a tested RouterOS release across your fleet and validate upgrades on a cloned CHR before touching production.

## Common risks

- Leaving management services (`www`, `api`, `winbox`, `ssh`) reachable on the WAN interface.
- Forgetting that the **Free** tier caps each interface at 1 Mbps upload and mistaking it for a hypervisor bottleneck.
- Editing firewall rules remotely without enabling **Safe Mode** (`Ctrl+X` in console) and locking yourself out.

## Operational checklist

- Does the CHR license tier cover real upload throughput per interface?
- Are `telnet`, `ftp`, `www` disabled and `ssh`/`winbox` restricted to the management network?
- Are default-deny `input`/`forward` rules and anti-spoofing/bogon filters in place?
- Are CPU, pps, queues, and per-interface traffic monitored (SNMP or remote syslog)?
- Are plain-text exports and a tested version rollback path in place?

## References

- [MikroTik: Cloud Hosted Router (CHR)](https://help.mikrotik.com/docs/spaces/ROS/pages/18350234/Cloud+Hosted+Router+CHR)
- [MikroTik: Securing your router (RouterOS)](https://help.mikrotik.com/docs/spaces/ROS/pages/328353/Securing+your+router)
