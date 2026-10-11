---
title: "VLSM in Depth"
description: Guide to Variable Length Subnet Masking to optimize IP address usage.
tags: ['networking']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: intermediate
category: Networking
status: published
estimated_time: 4 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# VLSM (Variable Length Subnet Masking)

VLSM lets you create subnets of different sizes within a larger network, optimizing IP address usage by assigning exactly the number of addresses each subnet needs.

## Core Concepts

### What is VLSM?

VLSM is a technique that lets you subdivide a network into subnets of different sizes, unlike FLSM (Fixed Length Subnet Mask), which uses the same size for all subnets.

### Advantages

- **Efficiency:** Reduces IP address waste
- **Scalability:** Allows more flexible network designs
- **Optimization:** Adjusts subnet sizes to actual needs

## Design Methodology

### Step 1: Requirements

Identify the required subnets and their sizes:

| Subnet | Required Hosts | Needed Hosts* |
|--------|------------------|-------------------|
| Administration | 50 | 62 (/26) |
| Sales | 25 | 30 (/27) |
| Development | 12 | 14 (/28) |
| Servers | 5 | 6 (/29) |
| WAN links | 2 | 2 (/30) |

*Needed hosts = 2^(host bits) - 2

### Step 2: Sort by Size

Sort subnets from largest to smallest to optimize space:

1. Administration: 62 hosts (/26)
2. Sales: 30 hosts (/27)
3. Development: 14 hosts (/28)
4. Servers: 6 hosts (/29)
5. WAN Links: 2 hosts (/30)

### Step 3: Subnet Assignment

Start from the main network (example: 192.168.1.0/24)

#### Subnet 1: Administration (62 hosts, /26)
```
Network: 192.168.1.0/26
Range: 192.168.1.1 - 192.168.1.62
Broadcast: 192.168.1.63
Next available: 192.168.1.64
```

#### Subnet 2: Sales (30 hosts, /27)
```
Network: 192.168.1.64/27
Range: 192.168.1.65 - 192.168.1.94
Broadcast: 192.168.1.95
Next available: 192.168.1.96
```

#### Subnet 3: Development (14 hosts, /28)
```
Network: 192.168.1.96/28
Range: 192.168.1.97 - 192.168.1.110
Broadcast: 192.168.1.111
Next available: 192.168.1.112
```

#### Subnet 4: Servers (6 hosts, /29)
```
Network: 192.168.1.112/29
Range: 192.168.1.113 - 192.168.1.118
Broadcast: 192.168.1.119
Next available: 192.168.1.120
```

#### Subnet 5: WAN Links (2 hosts, /30)
```
Network: 192.168.1.120/30
Range: 192.168.1.121 - 192.168.1.122
Broadcast: 192.168.1.123
Next available: 192.168.1.124
```

## Subnet Calculation

### General Formula

For a network with base prefix `/N` and subnet with `/M`:

- **Borrowed bits:** M - N
- **Number of subnets:** 2^(M - N)
- **Hosts per subnet:** 2^(32 - M) - 2

### Calculation Tools

#### Python Script for VLSM
```python
import ipaddress

def calcular_vlsm(red_base, subredes):
    """
    Computes VLSM subnets
    red_base: string such as '192.168.1.0/24'
    subredes: list of (name, required_hosts) tuples
    """
    red = ipaddress.ip_network(red_base)
    subredes_ordenadas = sorted(subredes, key=lambda x: x[1], reverse=True)
    
    resultado = []
    direccion_actual = red.network_address
    
    for nombre, hosts_req in subredes_ordenadas:
        # Compute the required prefix
        bits_host = 0
        while (2 ** bits_host) - 2 < hosts_req:
            bits_host += 1
        
        prefijo = 32 - bits_host
        nueva_red = ipaddress.ip_network(f"{direccion_actual}/{prefijo}")
        
        resultado.append({
            'nombre': nombre,
            'red': nueva_red,
            'hosts': list(nueva_red.hosts())
        })
        
        # Next available address
        direccion_actual = nueva_red.broadcast_address + 1
    
    return resultado

# Usage example
subredes = [
    ('Administración', 50),
    ('Ventas', 25),
    ('Desarrollo', 12),
    ('Servidores', 5),
    ('WAN', 2)
]

resultado = calcular_vlsm('192.168.1.0/24', subredes)
for subred in resultado:
    print(f"{subred['nombre']}: {subred['red']}")
```

#### Linux Commands
```bash
# Use ipcalc to verify subnets
ipcalc 192.168.1.0/26

# Calculate ranges manually
echo "ibase=10; obase=2; 192" | bc  # Convert to binary
```

## Best Practices

### Efficient Design

1. **Sort correctly:** Always assign large subnets first
2. **Leave room:** Reserve ranges for future growth
3. **Document:** Keep network diagrams up to date
4. **Monitor usage:** Periodically review address utilization

### Security Considerations

- **Segmentation:** Use VLSM to separate security zones
- **Filtering:** Configure ACLs based on subnets
- **Monitoring:** Implement IP usage alerts

### Use Cases

#### Enterprise Networks
- Departments of different sizes
- Remote offices with varying requirements
- Segmentation by function (servers, users, guests)

#### Service Providers
- Assigning subnets to customers
- Optimizing limited IPv4 space
- Gradual migration to IPv6

## Limitations and Considerations

### Wasted Space
- Unused bits in small subnets
- Broadcast addresses consume addresses
- Reserved space for future growth

### Complexity
- Calculations more complex than FLSM
- Higher chance of human error
- Need for detailed documentation

### Migration
- Requires careful planning
- Possible service interruptions
- Updating network configurations

## References

- RFC 950: Internet Standard Subnetting Procedure
- RFC 1812: Requirements for IP Version 4 Routers
- Cisco Networking Academy: VLSM Concepts
