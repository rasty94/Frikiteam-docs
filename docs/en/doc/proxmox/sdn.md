---
title: Proxmox — Software-Defined Networking (SDN)
---

# Proxmox — Software-Defined Networking

Advanced networking configuration using software-defined networking in Proxmox VE.

## Overview

Proxmox SDN allows you to implement virtual networks using VXLAN and EVPN for multi-tenant segmentation, isolation, and dynamic network management.

**Key Benefits:**
- Multi-tenant network isolation
- Dynamic network provisioning
- Overlay networks independent of physical topology
- Native Kubernetes network integration

## Prerequisites

- Proxmox VE 8.1 or higher
- Package `libpve-network-perl` installed
- Jumbo frames (MTU 9000) support on physical switch (recommended)
- All cluster nodes must be interconnected with sufficient bandwidth

## Architecture

```
┌─────────────────────────────────┐
│   Virtual Networks (SDN)        │
│  ┌──────────────────────────┐   │
│  │ VXLAN Zone (vnnet0)      │   │
│  │ - VMs on different nodes │   │
│  │ - Encapsulated traffic   │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
           │
    ┌──────┴──────┐
    │  EVPN       │  (Optional: Advanced routing)
    │  Routing    │
    └─────────────┘
```

## Configuration Steps

### 1. Create VXLAN Zone

Navigate to: **Node → SDN → Zones → Add → VXLAN**

Settings:
- **Zone ID**: `vnnet0` (identifier)
- **VNI**: Start ID for VXLAN networks (e.g., 1000)
- **Peers**: IP addresses of other Proxmox nodes
- **MTU**: 9000 (if jumbo frames supported)

Example configuration:
```
Zone ID: vnnet0
VNI: 1000
Peers: 10.1.1.1, 10.1.1.2, 10.1.1.3
Mtu: 9000
```

### 2. Create Virtual Network

Navigate to: **SDN → Vnets → Add**

Settings:
- **VNet ID**: `net0`
- **Zone**: `vnnet0`
- **VLANs**: Leave empty (handled by zone)
- **Subnets**: Define IP ranges (e.g., 10.100.0.0/24)

### 3. Create Subnet (Optional)

Navigate to: **SDN → Subnets → Add**

Settings:
- **Subnet**: `10.100.0.0/24`
- **Gateway**: `10.100.0.1` (optional)
- **SNAT**: Enable for external routing

### 4. Apply Configuration

Click: **Apply** to activate SDN configuration

Proxmox will:
- Configure VXLAN encapsulation
- Distribute configuration to cluster nodes
- Create required network interfaces

## Using SDN Networks

### Create VM with SDN Network

1. **New VM → Hardware → Network Device**
2. Select: Bridge `vnet0` (your SDN virtual network)
3. Use VLAN tag (optional): Leave blank for SDN handling

### Example: Assigning IP to VM

Inside VM (assuming Linux):
```bash
# DHCP (if subnet has DHCP enabled)
dhclient eth0

# Static IP
ip addr add 10.100.0.50/24 dev eth0
ip route add default via 10.100.0.1
```

## Monitoring

### Check VXLAN Status

```bash
# On Proxmox node
ip link show

# Check active VXLAN interfaces
ip link show type vxlan

# View VXLAN forwarding database
bridge fdb show dev vxlan100

# Monitor traffic
tcpdump -i vxlan100 -n
```

### Verify Connectivity

From VM to another VM on different node:
```bash
ping 10.100.0.51  # Another VM on SDN network
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| VXLAN interfaces down | MTU mismatch | Set MTU 9000 on physical interfaces and SDN |
| VMs can't ping each other | Zone not applied | Click "Apply" in SDN interface |
| High latency | VXLAN overhead | Use dedicated network for VXLAN traffic |
| Traffic not encapsulated | Peers not reachable | Verify IP connectivity between nodes |

## Performance Tips

1. **Use dedicated network interface** for VXLAN traffic (separate from management)
2. **Enable jumbo frames** (MTU 9000) for better throughput
3. **Monitor encapsulation overhead**: VXLAN adds ~50 bytes per packet
4. **Use EVPN for advanced routing** in large deployments

## Advanced: EVPN Routing

For dynamic route distribution between zones (requires additional configuration):

```
Zone: vnnet0 (VXLAN)
+ EVPN Routing
= Automatic MAC/ARP learning
```

Not covered in this guide; see official Proxmox documentation.

## See Also

- [Proxmox SDN Documentation](https://pve.proxmox.com/wiki/Software_Defined_Network)
- [VXLAN RFC 7348](https://tools.ietf.org/html/rfc7348)
- [EVPN Best Practices](https://www.cisco.com/c/en/us/support/docs/mpls/evpn/)
