---
title: "ICMP/ARP/NDP Protocols"
description: Key differences between IPv4 (ARP) and IPv6 (NDP) and ICMP message types for diagnostics.
tags: ['networking']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: advanced
category: Networking
status: published
estimated_time: 11 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# ICMP/ARP/NDP Protocols

The ICMP, ARP and NDP network protocols are fundamental to how IP works. ICMP provides diagnostics and error control, while ARP and NDP resolve layer 2 addresses to layer 3 addresses.

## ICMP (Internet Control Message Protocol)

### Main Function

ICMP carries control and error messages between IP devices. It is an integral part of the IP protocol and does not use ports like TCP/UDP.

### ICMP Message Types

#### Error Messages

| Type | Code | Description | Use |
|------|------|-------------|-----|
| 3 | 0 | Network Unreachable | Network not reachable |
| 3 | 1 | Host Unreachable | Host not reachable |
| 3 | 2 | Protocol Unreachable | Protocol not supported |
| 3 | 3 | Port Unreachable | Port not available |
| 3 | 4 | Fragmentation Needed | Fragmentation required |
| 11 | 0 | TTL Exceeded | Time to live exhausted |
| 12 | 0 | Parameter Problem | Parameter problem |

#### Informational Messages

| Type | Code | Description | Use |
|------|------|-------------|-----|
| 0 | 0 | Echo Reply | Ping reply |
| 8 | 0 | Echo Request | Ping request |
| 9 | 0 | Router Advertisement | Router announcement (rare) |
| 10 | 0 | Router Solicitation | Router solicitation |
| 13 | 0 | Timestamp Request | Timestamp request |
| 14 | 0 | Timestamp Reply | Timestamp reply |

### ICMP in Diagnostics

#### Ping (Echo Request/Reply)
```bash
# Basic ping
ping 192.168.1.1

# Ping with a specific size
ping -s 1472 192.168.1.1  # To detect MTU

# Continuous ping
ping -t 192.168.1.1
```

#### Traceroute (TTL Exceeded)
```bash
# Traceroute using ICMP
traceroute 8.8.8.8

# Windows tracert
tracert 8.8.8.8
```

### ICMPv6

IPv6 has ICMPv6 built in (not separate as in IPv4):

- **Error messages:** Similar to ICMPv4
- **Informational messages:** Includes NDP
- **Additional types:** Packet Too Big, Parameter Problem

## ARP (Address Resolution Protocol)

### Role in IPv4

ARP resolves layer 3 IP addresses to layer 2 MAC addresses. Essential for communication on Ethernet networks.

### ARP Process

1. **ARP Request:** Broadcast "Who has IP X?"
2. **ARP Reply:** Unicast "IP X is at MAC Y"
3. **Cache:** Stores the mapping for a limited time

### ARP Table

```bash
# Show ARP table
arp -a

# Show detailed ARP table
ip neigh show

# Clear a specific entry
arp -d 192.168.1.1

# Add a static entry
arp -s 192.168.1.1 aa:bb:cc:dd:ee:ff
```

### ARP Message Types

- **ARP Request (1):** Resolution request
- **ARP Reply (2):** Resolution reply
- **RARP Request (3):** Reverse ARP (obsolete)
- **RARP Reply (4):** Reverse ARP reply
- **ARP Announcement (8):** Gratuitous announcement (gratuitous ARP)

### Gratuitous ARP

A host announces its own IP/MAC without a prior request:

- **Use:** IP conflict detection
- **Failover:** Updating switch/cache entries
- **Clustering:** Notifying changes

```bash
# Send gratuitous ARP (Linux)
arping -U -I eth0 192.168.1.100
```

## NDP (Neighbor Discovery Protocol)

### Role in IPv6

NDP replaces ARP, ICMP Router Discovery and Redirect in IPv6. It uses ICMPv6 for all its functions.

### NDP Components

#### Neighbor Solicitation (NS) / Neighbor Advertisement (NA)

Equivalent to ARP Request/Reply:

- **NS:** Requests the MAC address of a neighbor
- **NA:** Replies with its own MAC address
- **ICMP type:** 135 (NS), 136 (NA)

```bash
# Show IPv6 neighbor table
ip -6 neigh show

# Solicit a neighbor manually
ndisc6 -n 2001:db8::1 eth0
```

#### Router Solicitation (RS) / Router Advertisement (RA)

Router discovery:

- **RS:** Requests router information (type 133)
- **RA:** Announces presence and configuration (type 134)

```bash
# Show RAs
radvdump

# Configure RA on the router
radvd -d  # Debug mode
```

#### Redirect

Similar to ICMP Redirect in IPv4 (type 137).

### DAD (Duplicate Address Detection)

Address conflict prevention:

1. Host sends NS with a tentative address
2. If it receives NA, the address is duplicated
3. If it receives no reply, the address is valid

## ARP vs NDP Comparison

| Aspect | ARP (IPv4) | NDP (IPv6) |
|---------|------------|------------|
| Protocol | Separate protocol | Part of ICMPv6 |
| Messages | ARP Request/Reply | NS/NA (ICMP 135/136) |
| Broadcast | Yes (ARP Request) | No (uses multicast) |
| Gratuitous | Yes | Unsolicited NA |
| Router Discovery | No (uses ICMP) | Yes (RS/RA) |
| DAD | No | Yes |
| Redirect | No (uses ICMP) | Yes |

## Security and Considerations

### Common Attacks

#### ARP Spoofing/Poisoning
- Attacker sends forged ARP replies
- Redirects traffic through their machine
- **Mitigation:** ARP inspection, certificates

#### ICMP Attacks
- **Smurf:** Amplification using broadcast
- **Ping of Death:** Oversized ICMP packets
- **Mitigation:** ICMP filtering, rate limiting

#### NDP Attacks
- **NDP Spoofing:** Similar to ARP poisoning
- **RA Spoofing:** Fake router advertisement
- **Mitigation:** RA Guard, DHCPv6 with authentication

### Best Practices

#### Secure Configuration
```bash
# Disable ICMP redirects (if not needed)
sysctl -w net.ipv4.conf.all.accept_redirects=0

# Rate limiting ICMP
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT
```

#### Monitoring
```bash
# Monitor ARP changes
arpwatch

# Detect ARP spoofing
arpspoof -i eth0 192.168.1.1 192.168.1.2
```

## Diagnostic Tools

### Wireshark Filters

```
# ARP
arp

# ICMP
icmp

# NDP
icmpv6.type == 135 || icmpv6.type == 136

# Router Advertisements
icmpv6.type == 134
```

### Monitoring Scripts

```python
import subprocess
import re

def get_arp_table():
    result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
    arp_entries = []
    
    for line in result.stdout.split('\n'):
        match = re.search(r'(\S+)\s+\(([\d.]+)\)\s+at\s+([\w:]+)', line)
        if match:
            arp_entries.append({
                'hostname': match.group(1),
                'ip': match.group(2),
                'mac': match.group(3)
            })
    
    return arp_entries

# Usage
arp_table = get_arp_table()
for entry in arp_table:
    print(f"{entry['ip']} -> {entry['mac']}")
```

## References

- RFC 792: Internet Control Message Protocol
- RFC 826: Ethernet Address Resolution Protocol
- RFC 4861: Neighbor Discovery for IP version 6 (IPv6)
- RFC 4862: IPv6 Stateless Address Autoconfiguration
