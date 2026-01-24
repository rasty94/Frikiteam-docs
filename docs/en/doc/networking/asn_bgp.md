---
title: ASN & BGP
description: Autonomous Systems, ASN ranges, BGP fundamentals, policies, security, and troubleshooting.
draft: false
---

# ASN & BGP

Autonomous Systems (AS) and the Border Gateway Protocol (BGP) are the backbone of interdomain routing on the Internet. This guide explains how global Internet routing works, how ASNs are assigned, and how to configure and secure BGP.

## Key Concepts

### What Is an Autonomous System (AS)?

An AS is a set of routers under a common technical administration that presents a single, consistent routing policy to the Internet.

**Characteristics:**
- **Unique number:** The ASN (Autonomous System Number).
- **Own policies:** Controls which routes are advertised and accepted.
- **Connectivity:** Interconnects with other ASes.
- **Scalability:** Divides the global Internet into manageable domains.

### Types of AS

#### Stub AS
- **Connectivity:** Single upstream provider.
- **Routes:** Receives full routes, advertises only its own prefixes.
- **Example:** Small company or local ISP.

#### Multihomed AS
- **Connectivity:** Multiple upstream providers.
- **Routes:** Receives routes from all, advertises its own prefixes.
- **Benefit:** Redundancy and better performance.

#### Transit AS
- **Function:** Provides transit for other ASes.
- **Routes:** Forwards learned routes to other peers.
- **Example:** Large Internet providers.

## Autonomous System Numbers (ASN)

### ASN Ranges

| Range | Type | Status |
|-------|------|--------|
| 1-64511 | Public ASN | Assigned by RIRs |
| 64512-65534 | Private ASN | Internal use |
| 65535 | Reserved | Do not use |
| 4200000000-4294967294 | 32-bit ASN | New assignments |

### ASN Allocation

#### By RIR (Regional Internet Registry)

| RIR | Region | ASN Range |
|-----|--------|-----------|
| ARIN | North America | 1-64511, 4-byte |
| RIPE | Europe/Middle East | 1-64511, 4-byte |
| APNIC | Asia/Pacific | 1-64511, 4-byte |
| LACNIC | Latin America | 1-64511, 4-byte |
| AFRINIC | Africa | 1-64511, 4-byte |

#### Requirements to Obtain an ASN

- **Justification:** Technical need (multihoming, unique policy).
- **Infrastructure:** Multiple connections.
- **Documentation:** Routing policies.
- **Contacts:** Up-to-date admin/tech contacts.

### Private ASNs

Private ASNs (64512-65534) are used for:

- **Internal iBGP:** Within an AS.
- **MPLS VPNs:** Customer VRFs.
- **Testing:** Labs and demos.

**Important:** They must not be advertised on the global Internet.

## BGP (Border Gateway Protocol)

### What Is BGP?

BGP is the standard routing protocol between ASes. It is a path-vector protocol using TCP for transport.

**Key characteristics:**
- **Current version:** BGP-4 (RFC 4271).
- **Port:** TCP 179.
- **Reliability:** Uses TCP delivery.
- **Scalability:** Handles hundreds of thousands of routes.

### BGP Flavors

#### eBGP (External BGP)
- **Use:** Between different ASes.
- **Next-hop:** Changes to the eBGP router.
- **AS Path:** Adds the local ASN.
- **Policies:** Typically stricter.

#### iBGP (Internal BGP)
- **Use:** Within the same AS.
- **Next-hop:** Preserved.
- **AS Path:** Unchanged.
- **Policies:** More flexible.

### BGP Messages

| Type | Description | Frequency |
|------|-------------|-----------|
| OPEN | Establishes BGP session | Once |
| UPDATE | Announces/withdraws routes | As needed |
| KEEPALIVE | Maintains session | Typically every 60s |
| NOTIFICATION | Errors/close | On error |

## Basic BGP Configuration

### Cisco IOS

```cisco
! Configure ASN and router ID
router bgp 65001
 bgp router-id 192.168.1.1

! eBGP neighbor
 neighbor 203.0.113.1 remote-as 65002
 neighbor 203.0.113.1 description Upstream Provider

! iBGP neighbor
 neighbor 192.168.2.1 remote-as 65001
 neighbor 192.168.2.1 update-source Loopback0

! Advertise networks
 network 192.168.1.0 mask 255.255.255.0
 network 203.0.113.0 mask 255.255.255.0
```

### Juniper JunOS

```junos
# Configure BGP
set routing-options autonomous-system 65001
set routing-options router-id 192.168.1.1

# eBGP group
set protocols bgp group upstream type external
set protocols bgp group upstream peer-as 65002
set protocols bgp group upstream neighbor 203.0.113.1

# iBGP group
set protocols bgp group internal type internal
set protocols bgp group internal local-address 192.168.1.1
set protocols bgp group internal neighbor 192.168.2.1

# Policies
set policy-options policy-statement export-routes term 1 from protocol direct
set policy-options policy-statement export-routes term 1 then accept
```

### Linux (BIRD)

```bird
router id 192.168.1.1;

protocol bgp upstream {
    local as 65001;
    neighbor 203.0.113.1 as 65002;
    export filter { accept; };
    import filter { accept; };
}

protocol bgp internal {
    local as 65001;
    neighbor 192.168.2.1;
    export filter { accept; };
    import filter { accept; };
}
```

## BGP Attributes

### Well-Known Mandatory

| Attribute | Description | Purpose |
|-----------|-------------|---------|
| AS_PATH | List of AS hops | Loop prevention |
| NEXT_HOP | Next-hop IP | Routing |
| ORIGIN | How the route was learned | Preference |

### Well-Known Discretionary

| Attribute | Description | Purpose |
|-----------|-------------|---------|
| LOCAL_PREF | Local preference | iBGP decision |
| ATOMIC_AGGREGATE | Indicates aggregation | Info |
| AGGREGATOR | Which router aggregated | Traceability |

### Optional

| Attribute | Type | Description |
|-----------|------|-------------|
| MULTI_EXIT_DISC (MED) | Optional Non-transitive | Inbound preference |
| COMMUNITY | Optional Transitive | Route tagging |
| ORIGINATOR_ID | Optional Non-transitive | iBGP loop prevention |
| CLUSTER_LIST | Optional Non-transitive | Route reflection |

## BGP Policy Tools

### Route Maps (Cisco)

```cisco
! Route map for filtering
route-map FILTER-OUT permit 10
 match ip address prefix-list MY-PREFIXES
 set community 65001:100

route-map FILTER-IN deny 10
 match as-path 666
route-map FILTER-IN permit 20

! Apply to neighbor
neighbor 203.0.113.1 route-map FILTER-IN in
neighbor 203.0.113.1 route-map FILTER-OUT out
```

### Prefix Lists

```cisco
ip prefix-list MY-NETWORKS permit 192.168.0.0/16
ip prefix-list MY-NETWORKS permit 203.0.113.0/24

neighbor 203.0.113.1 prefix-list MY-NETWORKS out
```

### AS Path Filtering

```cisco
ip as-path access-list 10 deny _666_
ip as-path access-list 10 permit .*

neighbor 203.0.113.1 filter-list 10 in
```

## BGP Communities

BGP communities tag routes to drive policies.

**Syntax:** `ASN:value`

#### Common Communities

| Community | Description | Use |
|-----------|-------------|-----|
| 65001:100 | Customer routes | Customer prefixes |
| 65001:200 | Peer routes | Settlement-free peers |
| 65001:666 | Blackhole | Discard traffic |
| 65535:65281 | No export | Do not export |
| 65535:65282 | No advertise | Do not advertise |

### Configuration

```cisco
route-map SET-COMMUNITY permit 10
 set community 65001:100

ip community-list 1 permit 65001:100

route-map FILTER-COMMUNITY permit 10
 match community 1
```

## BGP Troubleshooting

### Diagnostic Commands

#### Session status
```cisco
show ip bgp summary
show ip bgp neighbors
show ip bgp
```

#### Specific routes
```cisco
show ip bgp 192.168.1.0
show ip bgp regexp _65001_
```

#### Route attributes
```cisco
show ip bgp 192.168.1.0 | include Origin|AS Path|Next Hop
```

### Common Issues

#### 1) Session not established
```
* BGP neighbor state = Idle
```
**Causes:**
- IP connectivity broken.
- ACL blocking TCP 179.
- Duplicate router ID.

#### 2) Routes not received
```
* No routes received
```
**Causes:**
- Overly strict inbound filter.
- Missing `network` statement.
- Next-hop unreachable.

#### 3) Routes not selected as best
```
* Best path not selected
```
**Causes:**
- Lower LOCAL_PREF.
- Longer AS_PATH.
- Higher MED.

### Troubleshooting Helpers

#### Looking Glass
- **Route Views:** bgp.he.net
- **Traceroute with AS:** `traceroute -A`

#### Simple Monitoring Script

```bash
#!/bin/bash
BGP_NEIGHBOR="203.0.113.1"
STATE=$(vtysh -c "show ip bgp summary" | grep $BGP_NEIGHBOR | awk '{print $10}')

if [ "$STATE" != "Established" ]; then
    echo "ALERT: BGP with $BGP_NEIGHBOR is $STATE"
else
    echo "OK: BGP established with $BGP_NEIGHBOR"
fi
```

## BGP in Practice

### Peering

#### Internet Exchange Points (IXP)
Peering at IXPs enables direct interconnection.

- **AMS-IX:** Amsterdam
- **DE-CIX:** Frankfurt
- **LINX:** London
- **Equinix:** Global

#### Peering Config Example

```cisco
router bgp 65001
 neighbor 198.32.1.1 remote-as 65002
 neighbor 198.32.1.1 description Peer at IXP
 neighbor 198.32.1.1 route-map PEER-IN in
 neighbor 198.32.1.1 route-map PEER-OUT out
```

### Route Aggregation

Aggregation reduces the size of the global routing table.

```cisco
router bgp 65001
 aggregate-address 192.168.0.0 255.255.0.0 summary-only
```

### BGP FlowSpec

FlowSpec enables DDoS mitigation through BGP.

```cisco
router bgp 65001
 address-family ipv4 flowspec
  neighbor 203.0.113.1 activate
```

## BGP Security

### Threats

1. **Route hijacking:** Advertising prefixes you do not own.
2. **Blackholing:** Sending traffic to null.
3. **Prefix deaggregation:** Advertising more specific prefixes.
4. **AS path poisoning:** Manipulating AS_PATH.

### Protections

#### RPKI (Resource Public Key Infrastructure)

```cisco
router bgp 65001
 rpki server tcp 192.0.2.1 port 323 refresh 600
 rpki cache 192.0.2.1
```

#### BGPsec

BGPsec adds cryptographic signatures to BGP updates to prevent tampering.

### Security Best Practices

1. **Strict filtering:** Accept only valid prefixes.
2. **IRR validation:** Validate in route registries.
3. **Monitoring:** Alerts on route changes.
4. **Diversity:** Multiple upstream providers.

## References

- RFC 4271: A Border Gateway Protocol 4 (BGP-4)
- RFC 1997: BGP Communities Attribute
- RFC 6793: BGP Support for Four-Octet ASN Space
- RFC 6811: BGP Prefix Origin Validation
- RFC 8205: BGPsec Protocol Specification
