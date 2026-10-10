---
title: "VyOS (automation-first virtual router)"
description: "VyOS as a virtual router in a homelab or lab: deployment, base configuration with NAT and firewall, BGP/OSPF, commit/rollback and configuration as code."
keywords: "vyos, vrouter, bgp, ospf, nat, firewall, commit, rollback, ansible, gitops, homelab"
tags: ['networking', 'vrouter', 'automation']
updated: 2026-10-10
difficulty: advanced
estimated_time: 16 min
category: Networking
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Networking fundamentals"
  - "Basic virtualization knowledge"
  - "Dynamic routing concepts"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# VyOS (automation-first virtual router)

## The Problem

Your network grows: a couple of VLANs, a tunnel to another site, maybe a BGP neighbor. The current router is configured by clicking through a web interface and nobody knows what changed last Tuesday. If the virtual machine gets corrupted, rebuilding it means remembering dozens of screens.

VyOS attacks exactly that. It is a Linux-based network system (with FRR for dynamic routing) whose configuration is a text tree: you edit it in a session, it is validated, you confirm it with `commit` and you can export it as a list of `set` commands. That makes it a file that fits in Git, gets reviewed in a pull request and can be reapplied to a clean machine. The price is a learning curve: there is no graphical interface to guide you.

This page is the VyOS entry in the vRouter series; the criteria for choosing against OPNsense, pfSense and MikroTik CHR are in [vRouters: comparison](vrouters.md).

## 📋 Table of Contents

1. [When to choose VyOS](#when-to-choose-vyos)
2. [Recommended deployment](#recommended-deployment)
3. [How you work: configure, commit, save](#how-you-work-configure-commit-save)
4. [Base configuration](#base-configuration)
5. [NAT and firewall](#nat-and-firewall)
6. [Dynamic routing](#dynamic-routing)
7. [Configuration as code](#configuration-as-code)
8. [Common risks](#common-risks)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)
11. [Operational checklist](#operational-checklist)
12. [References](#references)

## When to choose VyOS

- You need BGP/OSPF with declarative automation
- You want network config versioned as code
- Your operations rely on DevOps/NetOps pipelines
- You prefer a consistent CLI to a graphical interface, and you are fine with a router without panels or third-party plugins

If what you want is a firewall with a web interface and browsable rule lists, [OPNsense](vrouter_opnsense.md) or [pfSense](vrouter_pfsense.md) give you less friction. For environments where MikroTik tooling is already in place, see [MikroTik CHR](vrouter_mikrotik_chr.md).

## Recommended deployment

- 2+ vNICs depending on design
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disk: 8 GB+

A practical interface layout for a home lab:

| Interface | Use | Notes |
|---|---|---|
| `eth0` | WAN / uplink | DHCP or static IP from the provider |
| `eth1` | LAN or VLAN trunk | Internal addressing; `vif` subinterfaces for VLANs |
| `eth2` (optional) | Management | Administration network separate from data traffic |

On Proxmox, each vNIC connects to a different bridge (`vmbr0` towards the WAN, `vmbr1` towards the LAN). Use a paravirtualized network driver (VirtIO) and check that the LAN bridge has no gateway of its own competing with the router. The live installation image is used to install to disk with the `install image` command; rolling releases are published daily and stable ones require a subscription or your own build, so check which channel you use before depending on it in production.

## How you work: configure, commit, save

VyOS has two modes. The **operational** one (`show`, `ping`, `reboot`) changes nothing; the **configuration** one is opened with `configure` and works on a candidate copy:

```bash
configure
set system host-name vyos-lab
commit
save
exit
```

- `set` and `delete` modify the candidate.
- `commit` validates and applies the changes to the running system.
- `save` writes them to the boot file; without `save`, a reboot returns to the previous configuration.
- `compare` shows the difference between what you have and what is applied. Review it before every `commit`.
- `rollback` goes back to an earlier revision of the committed configuration.

For risky changes, `commit-confirm` applies the configuration and reverts it by itself if you do not confirm in time with `confirm`:

```bash
commit-confirm 5
confirm
```

It is the equivalent of "try this, and if I lose access, go back": your management network will thank you the first time you change the firewall over SSH.

## Base configuration

1. Define interfaces and addressing.
2. Harden SSH access and administrative accounts.
3. Configure firewall policies by zones.
4. Implement static or dynamic routing (FRR).
5. Automate backups and configuration validations.

Interfaces, default gateway and DNS:

```bash
configure
set interfaces ethernet eth0 address 'dhcp'
set interfaces ethernet eth1 address '192.168.10.1/24'
set interfaces ethernet eth1 description 'LAN'
set protocols static route 0.0.0.0/0 next-hop 203.0.113.1
set system name-server '1.1.1.1'
commit
save
```

If the WAN gets its address by DHCP, you do not need the default static route (it learns it from the server), and `203.0.113.1` here is just an example from the documentation range. If you have a WAN with a fixed IP, replace it with your provider's gateway.

The SSH service comes enabled in the standard installation, but you should pin the port and review the initial account:

```bash
set service ssh port '22'
```

Change the password of the `vyos` user created at installation and, when you can, replace it with a public key (`set system login user ... authentication`; check your version's documentation for the exact syntax). A DHCP server for the LAN and a DNS forwarder are configured with `set service dhcp-server` and `set service dns forwarding`, in the `service` tree; the syntax changed between versions, so check your version's guide before copying.

## NAT and firewall

A private LAN needs outbound NAT to reach the Internet. A masquerade rule on the WAN interface:

```bash
set nat source rule 100 outbound-interface name 'eth0'
set nat source rule 100 source address '192.168.10.0/24'
set nat source rule 100 translation address 'masquerade'
commit
save
```

!!! warning "Firewall syntax changed between 1.3 and 1.4"
    VyOS 1.4 reorganized the firewall: the old `firewall name <NAME>` tree applied to interfaces gave way to `firewall ipv4 input|forward|output` chains (and `ipv6`) with `filter` inside, and changes also reached NAT and some options (for example, `outbound-interface` now takes `name` or `group`). A 1.3 example pasted into 1.4 does not validate, and vice versa. Before copying anything, run `show version` and use the documentation for **that** version.

A minimal firewall for the router itself in 1.4 (traffic addressed to the router, `input` chain):

```bash
set firewall ipv4 input filter default-action 'drop'
set firewall ipv4 input filter rule 10 action 'accept'
set firewall ipv4 input filter rule 10 inbound-interface name 'eth1'
set firewall ipv4 input filter rule 10 protocol 'tcp'
set firewall ipv4 input filter rule 10 destination port '22'
commit
```

This allows SSH only from the LAN and drops the rest. **Do not apply it over SSH without `commit-confirm`**, and remember to add a rule for already established connections first, or the replies to what the router itself initiates (DNS, updates) will be lost. The connection-state option is written differently depending on the version; check the `state` reference for yours.

For traffic that crosses the router (LAN to Internet, LAN to LAN) the `forward` chain is used. In 1.3 the same idea was expressed with named rule sets applied to the interface, and there is also the zone-based model (`set firewall zone`) that the base configuration list recommends: you assign interfaces to zones and write what happens between each pair. For a homelab, two zones (internal and external) are enough.

## Dynamic routing

Dynamic routing is handled by FRR, integrated into the VyOS CLI. OSPF for an internal network:

```bash
set protocols ospf parameters router-id '10.255.0.1'
set protocols ospf area 0 network '192.168.10.0/24'
set protocols ospf interface eth1 passive
commit
```

`passive` avoids sending OSPF advertisements to interfaces where there is no other router. And BGP, for example for a peering with your provider or another lab:

```bash
set protocols bgp system-as-number '65001'
set protocols bgp neighbor 192.0.2.2 remote-as '65002'
set protocols bgp neighbor 192.0.2.2 address-family ipv4-unicast
set protocols bgp address-family ipv4-unicast network '192.168.10.0/24'
commit
```

The way of declaring the autonomous system changed between versions (there are releases where the AS is part of the `bgp` node itself instead of `system-as-number`), so verify with your version. To understand the AS number scheme, private ranges and basic concepts, read [ASN and BGP](asn_bgp.md). In a homelab, use AS numbers from the private range and always filter what you announce and what you accept using allowed prefixes, even with trusted neighbors.

Operational commands to check status:

```bash
show ip route
show ip ospf neighbor
show ip bgp summary
```

The last two show neighbor state; a session in `Established` (BGP) or `Full` (OSPF) is the healthy sign. The exact output depends on the version.

## Configuration as code

VyOS can export its configuration as a list of `set` commands, which makes versioning easier:

```bash
show configuration commands
```

The persistent file lives in `/config/config.boot`. With this, the GitOps flow is:

1. Store in a repository the dump of `show configuration commands` (or the `set` commands you maintain as the source of truth).
2. Changes through pull request and technical review; the diff is human-readable.
3. A job applies the changes to the router: the `vyos.vyos` Ansible collection includes modules for that, or you can run the commands with `configure` and `commit` from a script over SSH. Ansible is introduced in [Ansible base](../ansible/ansible_base.md).
4. After applying, the pipeline runs checks: neighbors in `Established`, expected routes, a `ping` through the gateway.

For backups, besides the repository, VyOS can archive each `commit` to a remote server (the `commit-archive` option of `system config-management`; check the exact syntax in your version). Also keep a VM snapshot before every major version upgrade.

!!! tip "The repository is the source of truth"
    If someone changes something by hand on the router, the next deployment overwrites or contradicts it. Decide a rule and stick to it: either Git rules and manual changes are discarded, or they are documented and brought into the repository.

## Common risks

- Manual changes outside the GitOps flow.
- Lack of pre-deployment validations.
- Not measuring convergence times on failures.
- Applying a firewall without `commit-confirm` over an SSH session and locking yourself out.
- Forgetting `save`: the configuration works until the next reboot.
- Mixing syntax from different versions when copying examples from the Internet.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `commit` fails with a validation error | Syntax from another version or nonexistent node | Check `show version` and that version's documentation; use `?` or tab to see valid options |
| After reboot, the configuration reverts to the previous one | `commit` was done but not `save` | Run `save` after confirming; consider automating it in the flow |
| The LAN does not reach the Internet | Missing source NAT or default route | Review the `nat source` rule and `show ip route` |
| You lose SSH access after a firewall change | The rule blocks your own session | Use `commit-confirm`; recover through the VM console |
| BGP neighbor stuck in `Active` or `Idle` | No TCP/179 connectivity, wrong AS or a filter | Check `ping`, the firewall rule towards the router, `remote-as` and the other end's configuration |
| OSPF neighbor does not reach `Full` | Inconsistent areas or network types, or different MTU | Verify area, network type and MTU on both sides |
| Low performance in the VM | Emulated network driver or insufficient vCPU | Use VirtIO, assign more vCPU and check load with `show system cpu` |
| The firewall rule has no effect | It is defined but not applied to a chain or interface | In 1.4 check the chain (`input`, `forward`, `output`); in 1.3, that the rule set is assigned to the interface |

## Best Practices

- Use templates and a Git repository for the configuration.
- Introduce changes through pull requests and technical review.
- Separate lab/pre-production/production environments when possible.
- Run periodic convergence and failover tests.
- Run `compare` before every `commit` and `commit-confirm` on risky remote changes.
- Record the VyOS version in your documentation and upgrade in the lab first; syntax changes between versions.
- Reserve a separate management interface reachable by console even if the firewall fails.
- If the router terminates tunnels, look at [WireGuard](../linux/wireguard.md) as a lightweight VPN option between sites.

## Operational checklist

- Is all critical configuration versioned?
- Is there a syntactic and functional validation pipeline?
- Have link/neighbor failure scenarios been tested?
- Are snapshots or backups ready for rollback?
- Was the last change saved with `save` and does it match the repository?
- Do you know which VyOS version is running and whether the documentation's syntax is its own?

## References

- [VyOS: official documentation](https://docs.vyos.io/)
- [vRouters: comparison](vrouters.md)
- [OPNsense](vrouter_opnsense.md)
- [pfSense](vrouter_pfsense.md)
- [MikroTik CHR](vrouter_mikrotik_chr.md)
- [ASN and BGP](asn_bgp.md)
- [WireGuard](../linux/wireguard.md)
- [Ansible base](../ansible/ansible_base.md)
