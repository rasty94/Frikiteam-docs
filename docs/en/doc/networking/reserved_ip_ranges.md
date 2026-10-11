---
title: "Reserved IP Ranges"
description: Private (RFC 1918), documentation and reserved address blocks (CG-NAT, Loopback).
tags: ['networking']

updated: 2026-10-11
last_reviewed: 2026-10-11
difficulty: intermediate
category: Networking
status: published
estimated_time: 13 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# Reserved IP Ranges

Reserved IP addresses are address blocks that are not routed on the public Internet. They include private ranges, documentation ranges, loopback and other special uses defined by IANA and RFCs.

## Private Ranges (RFC 1918)

### Private Class A

| Range | CIDR Prefix | Available Hosts | Use |
|-------|-------------|-----------------|-----|
| 10.0.0.0 - 10.255.255.255 | 10.0.0.0/8 | 16,777,214 | Large corporate networks |

**Characteristics:**
- A single /8 block
- Largest private address space
- Common in large organizations
- Supports VLSM for subnetting

### Private Class B

| Range | CIDR Prefix | Available Hosts | Use |
|-------|-------------|-----------------|-----|
| 172.16.0.0 - 172.31.255.255 | 172.16.0.0/12 | 1,048,574 | Medium-sized networks |

**Characteristics:**
- 16 blocks of /16 each
- Balance between size and flexibility
- Common on university campuses
- Easy to remember and manage

### Private Class C

| Range | CIDR Prefix | Available Hosts | Use |
|-------|-------------|-----------------|-----|
| 192.168.0.0 - 192.168.255.255 | 192.168.0.0/16 | 65,534 | Small networks |

**Characteristics:**
- 256 blocks of /24 each
- Easiest to manage
- Common in homes and small offices
- Native support in home routers

## IANA Special Ranges

### Loopback (RFC 5735)

| Range | CIDR Prefix | Use |
|-------|-------------|-----|
| 127.0.0.0 - 127.255.255.255 | 127.0.0.0/8 | Local loopback interface |

**Details:**
- **127.0.0.1:** Standard loopback
- **127.0.0.0/8:** The whole range is reserved
- **Not routable:** Only reachable locally
- **Testing:** Used for testing local services

### Link-Local (RFC 3927)

| Range | CIDR Prefix | Use |
|-------|-------------|-----|
| 169.254.0.0 - 169.254.255.255 | 169.254.0.0/16 | Automatic autoconfiguration |

**Details:**
- **APIPA:** Automatic Private IP Addressing
- **Windows:** Assigned when DHCP fails
- **Zeroconf:** Used by Bonjour, Avahi
- **Not routable:** Local link only

### TEST-NET (RFC 5737)

| Range | CIDR Prefix | Use |
|-------|-------------|-----|
| 192.0.2.0 - 192.0.2.255 | 192.0.2.0/24 | Documentation and examples |
| 198.51.100.0 - 198.51.100.255 | 198.51.100.0/24 | Documentation and examples |
| 203.0.113.0 - 203.0.113.255 | 203.0.113.0/24 | Documentation and examples |

**Details:**
- **RFC 5737:** Ranges for documentation
- **Do not use in production:** Examples only
- **Books/Tutorials:** Common in technical documentation

## CGNAT (Carrier-Grade NAT) Ranges

### RFC 6598 (CGNAT)

| Range | CIDR Prefix | Use |
|-------|-------------|-----|
| 100.64.0.0 - 100.127.255.255 | 100.64.0.0/10 | Shared Address Space |

**Details:**
- **CGNAT:** Carrier-Grade Network Address Translation
- **ISPs:** Used by Internet service providers
- **RFC 6598:** Standard for shared address space
- **Not routable:** Only within carrier networks

### CGNAT Usage Examples

```
ISP Network:
- Public IPs: 203.0.113.0/24 (public range)
- CGNAT Pool: 100.64.0.0/16 (for customers)
- Customer 1: 100.64.1.1 (NAT to 203.0.113.10)
- Customer 2: 100.64.1.2 (NAT to 203.0.113.10)
```

## IANA Reserved Ranges

### IPv4 Special-Purpose Address Registry

| Range | CIDR Prefix | RFC | Purpose |
|-------|-------------|-----|---------|
| 0.0.0.0/8 | 0.0.0.0/8 | RFC 1122 | "This" network |
| 192.0.0.0/24 | 192.0.0.0/24 | RFC 5736 | IETF Protocol Assignments |
| 192.0.2.0/24 | 192.0.2.0/24 | RFC 5737 | TEST-NET-1 |
| 198.51.100.0/24 | 198.51.100.0/24 | RFC 5737 | TEST-NET-2 |
| 203.0.113.0/24 | 203.0.113.0/24 | RFC 5737 | TEST-NET-3 |
| 240.0.0.0/4 | 240.0.0.0/4 | RFC 1112 | Class E (experimental) |

### Ranges by Continent (RIRs)

!!! note "Private ranges do not depend on the RIR"
    The five regional registries (ARIN, RIPE NCC, APNIC, LACNIC and AFRINIC) hand out **public** address space. The RFC 1918 private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) are not assigned by any RIR: they are the same worldwide and anyone can use them inside their own network without requesting them.


## IPv6 Reserved Ranges

### Unique Local Addresses (ULA)

| Range | Prefix | RFC | Use |
|-------|--------|-----|-----|
| fc00::/7 | fc00::/7 | RFC 4193 | Unique local addresses |

**Details:**
- **fc00::/8:** Assigned by LIRs
- **fd00::/8:** Locally generated
- **Not routable:** Within the site only

### Link-Local Unicast

| Range | Prefix | RFC | Use |
|-------|--------|-----|-----|
| fe80::/10 | fe80::/10 | RFC 4291 | Link-local |

**Details:**
- **fe80::/64:** Per interface
- **Autoconfiguration:** SLAAC
- **Not routable:** Local link only

### Multicast

| Range | Prefix | RFC | Use |
|-------|--------|-----|-----|
| ff00::/8 | ff00::/8 | RFC 4291 | Multicast addresses |

**Important groups:**
- **ff02::1:** All nodes
- **ff02::2:** All routers
- **ff05::2:** All OSPF routers

## Device Configuration

### Cisco Router (IOS)

```cisco
! Configure interface with a private IP
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
 no shutdown

! Configure NAT for Internet access
ip nat inside source list 1 interface GigabitEthernet0/1 overload
access-list 1 permit 192.168.1.0 0.0.0.255

! Configure DHCP for clients
ip dhcp pool LAN
 network 192.168.1.0 255.255.255.0
 default-router 192.168.1.1
 dns-server 8.8.8.8
```

### Linux (netplan)

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
```

### Windows (PowerShell)

```powershell
# Configure a private IP
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.1.100 -PrefixLength 24 -DefaultGateway 192.168.1.1

# Configure DNS
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses ("8.8.8.8","1.1.1.1")
```

## Security Considerations

### Risks of Private Ranges

1. **IP conflicts:** Multiple networks using the same range
2. **Accidental routing:** Insufficient filtering
3. **Internal attacks:** Without proper segmentation

### Best Practices

#### Network Segmentation

```bash
# Linux - Create VLANs
ip link add link eth0 name eth0.10 type vlan id 10
ip addr add 192.168.10.1/24 dev eth0.10

# Firewall rules
iptables -A FORWARD -s 192.168.1.0/24 -d 192.168.2.0/24 -j DROP
```

#### Range Monitoring

```bash
#!/bin/bash
# Scan the private network for devices

NETWORK="192.168.1.0/24"

echo "Scanning $NETWORK..."
nmap -sn $NETWORK | grep "Nmap scan report" | awk '{print $5}' > hosts.txt

echo "Hosts found:"
cat hosts.txt
```

### VPN and Private Ranges

#### OpenVPN with private ranges

```openvpn
server 10.8.0.0 255.255.255.0
push "route 192.168.1.0 255.255.255.0"
```

#### WireGuard

```wg
[Interface]
Address = 10.0.0.1/24
PrivateKey = ...

[Peer]
AllowedIPs = 10.0.0.2/32, 192.168.1.0/24
```

## Troubleshooting

### Common Problems

#### 1. IP Conflict
```
# Check IPs in use
arp -a
nmap -sn 192.168.1.0/24
```

#### 2. No connectivity
```
# Check IP configuration
ip addr show
ip route show

# Test connectivity
ping 192.168.1.1
traceroute 8.8.8.8
```

#### 3. DNS not working
```
# Check DNS servers
cat /etc/resolv.conf
nslookup google.com
```

### Diagnostic Tools

```bash
# View the ARP table
arp -n

# View routes
ip route

# View interfaces
ip link show

# Connectivity test
mtr 8.8.8.8

# View network processes
netstat -tlnp
ss -tlnp
```

## References

- [RFC 1918: Address Allocation for Private Internets](https://www.rfc-editor.org/rfc/rfc1918)
- [RFC 3927: Dynamic Configuration of IPv4 Link-Local Addresses](https://www.rfc-editor.org/rfc/rfc3927)
- [RFC 4193: Unique Local IPv6 Unicast Addresses](https://www.rfc-editor.org/rfc/rfc4193)
- [RFC 5735: Special Use IPv4 Addresses (obsoleted by RFC 6890)](https://www.rfc-editor.org/rfc/rfc5735)
- [RFC 5737: IPv4 Address Blocks Reserved for Documentation](https://www.rfc-editor.org/rfc/rfc5737)
- [RFC 6598: IANA-Reserved IPv4 Prefix for Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598)
- [IANA IPv4 Special-Purpose Address Registry](https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml)
- [IANA IPv6 Special-Purpose Address Registry](https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml)
- [RFC 6890: Special-purpose address registries](https://www.rfc-editor.org/rfc/rfc6890)
