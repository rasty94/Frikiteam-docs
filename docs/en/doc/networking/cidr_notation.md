---
title: CIDR Notation
description: Detailed explanation of Classless Inter-Domain Routing notation and how to calculate IP ranges.
draft: false
---

# CIDR Notation

CIDR (Classless Inter-Domain Routing) notation is a method for assigning IP addresses and defining routes in IP networks. It replaces the fixed class system (A, B, C) with a more flexible prefix-based approach.

## Basic Concepts

### Syntax
A CIDR address is written as: `IP_address/prefix`

- **IP Address:** The network base address
- **Prefix:** Number of consecutive bits representing the network portion (0 to 32 for IPv4)

### Example
`192.168.1.0/24`

- Network: 192.168.1.0
- Netmask: 255.255.255.0
- Available hosts: 256 - 2 = 254 (excluding network and broadcast addresses)

## Range Calculation

### Converting Prefix to Netmask
The prefix indicates how many bits are for the network. Remaining bits are for hosts.

**Formula:** Netmask = 2^(32-prefix) - 1 in corresponding octets

### Common Prefix Table

| Prefix | Netmask | Hosts | Typical Use |
|---------|---------|-------|------------|
| /8 | 255.0.0.0 | 16M | Large organizations |
| /16 | 255.255.0.0 | 65K | Enterprise networks |
| /24 | 255.255.255.0 | 254 | LAN subnets |
| /25 | 255.255.255.128 | 126 | Small subnets |
| /26 | 255.255.255.192 | 62 | Very small subnets |
| /27 | 255.255.255.224 | 30 | Point-to-point subnets |
| /28 | 255.255.255.240 | 14 | Minimal subnets |
| /29 | 255.255.255.248 | 6 | Router subnets |
| /30 | 255.255.255.252 | 2 | Point-to-point links |
| /31 | 255.255.255.254 | 2* | Point-to-point links (RFC 3021) |
| /32 | 255.255.255.255 | 1 | Specific host |

*Note: /31 allows 2 hosts without broadcast, useful for point-to-point links.

### Manual Calculation

To calculate a CIDR network range:

1. **Convert IP to binary**
2. **Identify network and host bits**
3. **Calculate network address:** Bitwise AND with mask
4. **Calculate broadcast:** Bitwise OR with mask complement
5. **Host range:** From network+1 to broadcast-1

#### Example: 192.168.1.100/25

```
IP: 192.168.1.100 = 11000000.10101000.00000001.01100100
Mask /25: 11111111.11111111.11111111.10000000

Network: 192.168.1.0 (AND operation)
Broadcast: 192.168.1.127 (OR with ~mask)
Hosts: 192.168.1.1 - 192.168.1.126
```

## CIDR Advantages

- **Efficiency:** Better use of IP address space
- **Flexibility:** Subnets of any size
- **Aggregation:** Facilitates hierarchical routing
- **Scalability:** Reduces routing table sizes

## Practical Tools

### Online Calculators
- IP Calculator (ipleak.net)
- Subnet Calculator (subnet-calculator.com)

### Linux Commands
```bash
# Calculate subnets
ipcalc 192.168.1.0/24

# Show network information
ip route show
```

### Python Scripts
```python
import ipaddress

# Create network object
network = ipaddress.ip_network('192.168.1.0/24')

print(f"Network: {network.network_address}")
print(f"Broadcast: {network.broadcast_address}")
print(f"Hosts: {list(network.hosts())[:5]}...")  # First 5 hosts
```

## Common Use Cases

### Enterprise Subnets
- `/24` for small offices
- `/23` or `/22` for campuses
- `/16` for large corporate networks

### Cloud Computing
- AWS VPC: Typically `/16` or `/24`
- Subnets: `/24` to `/28` depending on needs

### VPN and Remote Access
- `/30` for point-to-point links
- `/24` for remote user networks

## Security Considerations

- **Filtering:** Ensure ACLs use CIDR notation
- **Monitoring:** Detect subnet changes
- **Documentation:** Keep network map updated

## References

- RFC 4632: Classless Inter-domain Routing (CIDR)
- RFC 1918: Address Allocation for Private Internets
- IANA IPv4 Address Space Registry
