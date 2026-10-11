---
title: "MTU/MSS Values"
description: Typical Maximum Transmission Unit values for different media (Ethernet, PPPoE, Jumbo Frames).
tags: ['networking']

updated: 2026-10-11
last_reviewed: 2026-10-11
difficulty: intermediate
category: Networking
status: published
estimated_time: 6 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# MTU/MSS Values

MTU (Maximum Transmission Unit) and MSS (Maximum Segment Size) are critical parameters in TCP/IP networks that affect the performance and efficiency of data transmission.

## Basic Concepts

### MTU (Maximum Transmission Unit)

The MTU is the maximum packet size that can be transmitted on a network interface without fragmentation.

**Basic formula:**
```
MTU = Payload + Headers
```

### MSS (Maximum Segment Size)

The MSS is the maximum amount of data in a TCP segment, excluding the TCP/IP headers.

**Relationship with MTU:**
```
MSS = MTU - (IP Header + TCP Header)
MSS = MTU - 40 bytes (IPv4) or 60 bytes (IPv6 with options)
```

## MTU Values by Technology

### Ethernet

| Standard | MTU | Notes |
|----------|-----|-------|
| Ethernet II | 1500 | Most common standard |
| IEEE 802.3 | 1492 | With LLC/SNAP |
| Jumbo Frames | 9000 | Large frames |
| Super Jumbo | 16000+ | For storage networks |

### WAN Technologies

| Technology | Typical MTU | Overhead | Notes |
|------------|------------|----------|-------|
| PPPoE | 1492 | 8 bytes | Common DSL |
| PPTP | 1460 | 40 bytes | Microsoft VPN |
| L2TP | 1460 | 40 bytes | Standard VPN |
| GRE | 1476 | 24 bytes | Tunneling |
| IPsec | 1380-1420 | 50-90 bytes | Encrypted VPN |
| MPLS | 1500 | Variable | Provider dependent |

### Wireless Technologies

| Technology | MTU | Notes |
|------------|-----|-------|
| Wi-Fi (802.11) | 1500 | Same as Ethernet |
| Wi-Fi (802.11n/ac) | 2304 | With aggregation |
| LTE/4G | 1428 | Carrier dependent |
| 5G | 1428+ | Higher in some deployments |

### Storage Technologies

| Technology | MTU | Use |
|------------|-----|-----|
| iSCSI | 9000 | Jumbo frames recommended |
| NFS | 9000 | Better performance |
| Fibre Channel over IP | 2400+ | Depends on FC |

## MSS Calculation

### IPv4

**Minimum headers:**
- IP Header: 20 bytes
- TCP Header: 20 bytes
- **Total overhead:** 40 bytes

```
MSS = MTU - 40
```

**Examples:**
- MTU 1500: MSS = 1460
- MTU 1492 (PPPoE): MSS = 1452
- MTU 9000 (Jumbo): MSS = 8960

### IPv6

**Minimum headers:**
- IPv6 Header: 40 bytes
- TCP Header: 20 bytes
- **Total overhead:** 60 bytes

```
MSS = MTU - 60
```

**With extension headers:**
- Fragment Header: +8 bytes
- Routing Header: +8-24 bytes
- Total can reach 100+ bytes

### TCP with Options

**Common options:**
- Timestamp: +12 bytes
- SACK: +variable
- Window Scaling: +4 bytes

**Effective MSS:**
```
MSS_Efectivo = MSS - Opciones_TCP
```

## System Configuration

### Linux

#### View the current MTU
```bash
ip link show dev eth0
ip addr show dev eth0
```

#### Set the MTU
```bash
# Temporary
ip link set dev eth0 mtu 9000

# Permanent (Ubuntu/Debian)
# /etc/network/interfaces
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    mtu 9000

# Permanent (systemd-networkd)
# /etc/systemd/network/10-eth0.network
[Match]
Name=eth0

[Network]
Address=192.168.1.100/24
MTUBytes=9000
```

#### TCP MSS clamping
```bash
# View the current MSS
ip route show

# Configure MSS clamping
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1452
```

### Windows

#### View the MTU
```cmd
netsh interface ipv4 show interfaces
netsh interface ipv4 show subinterfaces
```

#### Set the MTU
```cmd
netsh interface ipv4 set subinterface "Ethernet" mtu=9000 store=persistent
```

#### PowerShell
```powershell
Get-NetAdapter | Select Name, MtuSize
Set-NetAdapterAdvancedProperty -Name "Ethernet" -RegistryKeyword "*MTU" -RegistryValue 9000
```

### Cisco IOS

```cisco
! View the MTU
show interfaces GigabitEthernet 0/0

! Set the MTU
interface GigabitEthernet 0/0
 mtu 9000
 ip mtu 9000  ! For IPv4
 ipv6 mtu 9000  ! For IPv6

! MSS clamping
ip tcp mss 1452
```

### Juniper JunOS

```junos
# View the MTU
show interfaces ge-0/0/0

# Set the MTU
set interfaces ge-0/0/0 mtu 9000

# MSS clamping
set security flow tcp-mss all-tcp mss 1452
```

## MTU Problems and Solutions

### Symptoms of a Low MTU

1. **Loss of large packets**
2. **Slow download performance**
3. **VPN problems**
4. **Fragmentation errors**

### Diagnosis

#### Test tools

```bash
# Ping with a specific size
ping -M do -s 1472 192.168.1.1  # 1500 - 28 = 1472

# Discover the path MTU
tracepath example.com

# MTR with MTU
mtr --mtu example.com
```

#### MTU discovery script

```bash
#!/bin/bash
# Discover the path MTU

TARGET=$1
MTU=1500

echo "Discovering path MTU to $TARGET..."

while [ $MTU -gt 0 ]; do
    if ping -M do -s $((MTU-28)) -c 1 $TARGET >/dev/null 2>&1; then
        echo "MTU path: $MTU"
        break
    fi
    MTU=$((MTU-10))
done
```

### Common Problems and Solutions

#### 1. PPPoE Overhead

**Problem:** MTU 1500 on a PPPoE link (actual MTU 1492)

**Solution:**
```bash
# Linux
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1452

# Router
ip tcp mss 1452
```

#### 2. VPN Overhead

**Problem:** IPSec/GRE adds overhead

**Solution:**
```bash
# Calculate the correct MSS
# For IPSec: MTU - 50-90 bytes
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1380
```

#### 3. Jumbo Frames

**Problem:** Not all devices support jumbo frames

**Solution:**
- Check compatibility on every device
- Use separate VLANs for jumbo frames
- Configure the MTU per interface

## Performance and Optimization

### Benefits of a High MTU

1. **Less overhead:** Fewer headers per byte of data
2. **Better throughput:** Fewer CPU interrupts
3. **Efficiency:** Better for large transfers

### Jumbo Frames in Practice

#### Recommended configuration

```bash
# File server
ip link set dev eth0 mtu 9000

# Check support
ethtool -i eth0  # View the driver
ethtool eth0     # View capabilities
```

#### Use cases

- **Storage:** iSCSI, NFS over Ethernet
- **Backup:** Large transfers
- **Virtualization:** Traffic between VMs
- **Data centers:** High-speed networks

### Security Considerations

#### Fragmentation and Security

- **PMTU Discovery:** Fragmentation attacks
- **ICMP blocking:** Can cause MTU problems
- **VPN:** MTU affects tunnel performance

#### Best Practices

1. **Monitoring:** Alerts on MTU changes
2. **Documentation:** Record the MTU per segment
3. **Testing:** Verify compatibility before changing
4. **Backup:** Rollback plan

## Reference Values

### MTU by Network Type

| Network Type | Recommended MTU | Notes |
|-------------|------------------|-------|
| Ethernet LAN | 1500 | Standard |
| Gigabit LAN | 1500-9000 | Jumbo if supported |
| PPPoE WAN | 1492 | PPPoE overhead |
| MPLS WAN | 1500 | Provider dependent |
| IPSec VPN | 1380-1420 | Encryption overhead |
| Wireless | 1500 | Same as Ethernet |
| Storage | 9000 | Jumbo frames |

### MSS by Scenario

| Scenario | MTU | MSS IPv4 | MSS IPv6 |
|-----------|-----|----------|----------|
| Standard Ethernet | 1500 | 1460 | 1440 |
| PPPoE | 1492 | 1452 | 1432 |
| IPSec tunnel | 1420 | 1380 | 1360 |
| PPTP | 1460 | 1420 | 1400 |
| Jumbo frames | 9000 | 8960 | 8940 |

## MTU on 25G, 40G and 100G networks

At these speeds the cost is not in the bandwidth alone but in the number of packets per second. At 100G with MTU 1500 you need on the order of 8 million packets per second (theoretical estimate, ignoring layer 2 overhead), and each packet consumes CPU. Raising the MTU reduces that number, but it is not the only way.

Offloads do much of this work in the NIC or the driver: TSO and GSO split large buffers into segments on transmit, and GRO and LRO merge received segments before handing them to the kernel. With offloads enabled the CPU handles far fewer packets even at MTU 1500, so do not assume jumbo frames are required to fill a 25G or 100G link.

### Jumbo end to end

A jumbo frame only works if **every** hop on the path uses the same MTU: NIC, bond, bridge (for example `vmbr` in Proxmox), VLAN subinterface and switch ports. A single hop at 1500 makes large packets get dropped (with the DF bit set) or fragmented. The typical symptom is a link that answers small pings but stalls on large transfers.

Check the MTU of each layer with `ip link show`:

```bash
ip link show dev bond0 | grep mtu
ip link show dev vmbr1 | grep mtu
ip link show dev bond0.100 | grep mtu
```

Then validate the end-to-end path with ping and DF set. In IPv4 the ICMP payload is MTU − 28 bytes (20 for IP and 8 for ICMP):

```bash
ping -M do -s 8972 -c 3 <ip_destino>   # MTU 9000 end to end
ping -M do -s 1472 -c 3 <ip_destino>   # MTU 1500
```

If the first fails and the second works, there is a hop that does not support jumbo frames.

### Where it is worth it

| Network | Jumbo | Reason |
|-----|-------|--------|
| Ceph (cluster network) | Recommended | Replication and recovery traffic between OSDs on a dedicated network |
| iSCSI or NFS on an isolated storage network | Recommended | Large blocks on a network you control end to end |
| Client or production network | Usually not | Clients, gateways and external equipment usually run at 1500; mixing MTUs causes hard-to-diagnose failures |

### Offloads and ring buffer

```bash
ethtool -k eth0 | grep -E 'segmentation-offload|receive-offload'   # TSO, GSO, GRO, LRO
ethtool -g eth0                                                    # ring buffer RX/TX: current and maximum
```

Before blaming the MTU for a CPU problem, check that TSO, GSO and GRO are `on`. The ring buffer sets how many packets can be queued during bursts; if the current value is far below the maximum, raising it may be worthwhile, but confirm it with the driver drop counters (`ethtool -S eth0`).

!!! warning
    Real gains depend on the NIC, the driver, the workload and the network path itself. There is no universal figure: measure with iperf3 before and after the change (same hosts, same number of connections, several runs) and also compare CPU usage. The methodology is in [benchmarks.md](benchmarks.md).

## References

- RFC 1191: Path MTU Discovery
- RFC 1981: Path MTU Discovery for IPv6
- RFC 2923: TCP Problems with Path MTU Discovery
- RFC 879: The TCP Maximum Segment Size and Related Topics
- IEEE 802.3: Ethernet Standards
