---
title: IPv6 Addressing
description: IPv6 address structure, types (Link-Local, Global Unicast, Multicast), abbreviation rules, and migration patterns from IPv4.
draft: false
---

# IPv6 Addressing

IPv6 is the sixth-generation Internet protocol designed to replace IPv4. It provides a massive address space ($2^{128}$ addresses) and modern capabilities for the future of the Internet.

## Address Structure

### Basic Format

An IPv6 address has 128 bits, represented as 8 groups of 4 hexadecimal digits separated by colons:

```
2001:0db8:85a3:0000:0000:8a2e:0370:7334
```

### Abbreviation Rules

#### Rule 1: Omit Leading Zeros
Leading zeros in each group can be removed:

```
2001:db8:85a3:0:0:8a2e:370:7334
```

#### Rule 2: Compress Consecutive Zeros
One consecutive block of zeros can be replaced by `::` (only once per address):

```
2001:db8:85a3::8a2e:370:7334
```

#### Abbreviation Examples

| Full Address | Shortened | Notes |
|--------------|-----------|-------|
| 2001:0db8:0000:0000:0000:0000:0000:0001 | 2001:db8::1 | Loopback |
| 0000:0000:0000:0000:0000:0000:0000:0001 | ::1 | Short loopback |
| 0000:0000:0000:0000:0000:0000:0000:0000 | :: | Unspecified address |

## IPv6 Address Types

### 1. Unicast

Addresses that identify a single interface.

#### Global Unicast
- **Range:** 2000::/3
- **Use:** Public Internet
- **Example:** 2001:db8:85a3::8a2e:370:7334

Global Unicast structure:
```
| 3 bits | 13 bits | 32 bits | 16 bits | 64 bits |
| Prefix | TLA ID | Reserved | SLA ID | Interface ID |
```

#### Link-Local Unicast
- **Range:** fe80::/10
- **Use:** Communication on the same link
- **Example:** fe80::1%eth0
- **Autoconfiguration:** Generated automatically by hosts

#### Unique Local Unicast (ULA)
- **Range:** fc00::/7
- **Use:** Private local networks
- **Example:** fd12:3456:789a::1
- **Not routable on the Internet:** Similar to RFC 1918 in IPv4

### 2. Multicast

Addresses that identify multiple interfaces.

- **Range:** ff00::/8
- **Common groups:**
  - ff02::1 — All nodes on the link
  - ff02::2 — All routers on the link
  - ff05::2 — All OSPF routers
  - ff02::1:ffxx:xxxx — Solicited-node (neighbor solicitation)

### 3. Anycast

Addresses assigned to multiple interfaces where traffic is delivered to the nearest one.

- **Use:** Distributed services (DNS, NTP)
- **Syntax:** Indistinguishable from unicast

## Interface ID and EUI-64

### Generating an Interface ID

In IPv6, the lower 64 bits identify the interface. They can be generated in several ways.

#### EUI-64 (Extended Unique Identifier)
1. Take the MAC address (48 bits).
2. Insert ffff in the middle: `aa:bb:cc:ff:ff:dd:ee:ff`.
3. Flip the U/L bit of the first octet.

```python
def eui64_from_mac(mac):
    mac_parts = mac.split(':')
    eui64 = mac_parts[:3] + ['ff', 'ff'] + mac_parts[3:]
    first_byte = int(eui64[0], 16)
    first_byte ^= 0x02  # Flip U/L bit
    eui64[0] = f"{first_byte:02x}"
    return ':'.join(eui64)

print(eui64_from_mac("00:1B:44:11:3A:B7"))  # 021b:44ff:fe11:3ab7
```

#### Stateless Autoconfiguration (SLAAC)
- Hosts generate the Interface ID automatically.
- Based on MAC or random value for privacy.

## IPv6 Configuration

### Linux Commands

#### Show IPv6 addresses
```bash
ip -6 addr show
ip addr show dev eth0
```

#### Configure static address
```bash
ip addr add 2001:db8::1/64 dev eth0
```

#### Configure gateway
```bash
ip -6 route add default via 2001:db8::1 dev eth0
```

### Configure /etc/network/interfaces
```
iface eth0 inet6 static
    address 2001:db8:85a3::8a2e:370:7334
    netmask 64
    gateway 2001:db8:85a3::1
```

### Router Advertisements (RA)
Routers announce prefixes automatically:
```bash
# View received RAs
radvdump
```

## IPv4/IPv6 Migration

### Transition Techniques

#### Dual Stack
- Hosts have both IPv4 and IPv6 addresses.
- Applications choose the protocol.

#### Tunneling
- 6to4: `2002:ipv4_addr::/48`
- Teredo: Hosts behind IPv4 NAT
- ISATAP: Intra-site tunneling

#### Translation
- NAT64/DNS64: Protocol translation
- SIIT: Stateless IP/ICMP translation

### Configuration Examples

#### Dual Stack in Apache
```
Listen [::]:80
Listen 0.0.0.0:80
```

#### IPv6 in Docker
```yaml
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "80:80"
      - "[::]:80:80"  # IPv6
```

## IPv6 Security

### IPv6-Specific Considerations

- **Autoconfiguration:** Spoofing risk.
- **Extension Headers:** Possible fragmentation abuse.
- **Multicast:** Amplification vector.
- **Privacy Extensions:** Temporary addresses.

### Best Practices

- **Filtering:** Apply IPv6 ACLs.
- **Monitoring:** Use tools such as tcpdump.
- **Patching:** Keep systems updated.

### Diagnostic Tools

```bash
# IPv6 ping
ping6 2001:db8::1

# IPv6 traceroute
traceroute6 google.com

# Show IPv6 routes
ip -6 route show

# Show IPv6 neighbors
ip -6 neigh show
```

## References

- RFC 4291: IP Version 6 Addressing Architecture
- RFC 4862: IPv6 Stateless Address Autoconfiguration
- RFC 4941: Privacy Extensions for Stateless Address Autoconfiguration
- RFC 7343: An IPv6 Prefix for Overlay Routable Cryptographic Hash Identifiers (ORCHIDv2)
