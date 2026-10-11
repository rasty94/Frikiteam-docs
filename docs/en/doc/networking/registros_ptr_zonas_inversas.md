---
title: "PTR Records and Reverse Zones"
description: How reverse lookups (in-addr.arpa) work and their importance for IP reputation.
tags: ['networking']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: intermediate
category: Networking
status: published
estimated_time: 12 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# PTR Records and Reverse Zones

PTR (Pointer) records allow reverse resolution of IP addresses to domain names. They are crucial for email reputation, security and network diagnostics.

## Basic Concepts

### What is a Reverse Lookup?

Reverse resolution translates an IP address into a domain name:

- **Forward DNS:** `www.example.com` → `192.168.1.1`
- **Reverse DNS:** `192.168.1.1` → `www.example.com`

### PTR Records

- **Type:** PTR
- **Purpose:** Point to a domain name
- **Syntax:** `ip_address.in-addr.arpa. IN PTR domain_name.`

## Reverse Zone Structure

### in-addr.arpa Zone

For IPv4, reverse zones live under `in-addr.arpa`:

- **Structure:** Reversed IP + `.in-addr.arpa`
- **Example:** `192.168.1.1` → `1.1.168.192.in-addr.arpa`

### Zone Delegation

Reverse zones are delegated by octets:

- **/8:** Delegated to the RIRs (ARIN, RIPE, etc.)
- **/16:** ISP or large organization
- **/24:** Typical subnet

### Reverse Zone File

```bind
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
    2023120101 ; Serial
    3600       ; Refresh
    1800       ; Retry
    604800     ; Expire
    86400      ; Minimum TTL
)

@ IN NS ns1.example.com.
@ IN NS ns2.example.com.

; PTR records
1 IN PTR host1.example.com.
2 IN PTR host2.example.com.
10 IN PTR mail.example.com.
```

## Configuration on Different Servers

### BIND9

#### Zone file
```
zone "1.168.192.in-addr.arpa" {
    type master;
    file "/etc/bind/zones/db.192.168.1";
};
```

#### Reverse zone contents
```bind
$ORIGIN 1.168.192.in-addr.arpa.
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
    2023120101  ; Serial
    3H          ; Refresh
    1H          ; Retry
    1W          ; Expire
    1D          ; Minimum
)

    IN NS ns1.example.com.
    IN NS ns2.example.com.

1   IN PTR www.example.com.
2   IN PTR mail.example.com.
100 IN PTR dhcp-100.example.com.
```

### Windows DNS Server

1. **Create reverse zone:** DNS Manager → New Zone → Reverse Lookup Zone
2. **Type:** Primary zone
3. **Network:** 192.168.1.0/24
4. **Add PTR records:** Right-click → New Pointer (PTR)

### PowerDNS

```sql
-- Insert reverse zone
INSERT INTO domains (name, type) VALUES ('1.168.192.in-addr.arpa', 'MASTER');

-- Insert PTR records
INSERT INTO records (domain_id, name, type, content, ttl)
VALUES (
    (SELECT id FROM domains WHERE name='1.168.192.in-addr.arpa'),
    '1.1.168.192.in-addr.arpa',
    'PTR',
    'www.example.com',
    86400
);
```

## IPv6 Reverse DNS

### ip6.arpa Zone

For IPv6, `ip6.arpa` is used instead of `in-addr.arpa`.

#### Structure
- IPv6 address: `2001:db8:85a3::8a2e:370:7334`
- Reverse: `4.3.3.7.0.7.3.0.e.2.a.8.0.0.0.0.0.0.0.0.3.a.5.8.8.b.d.0.1.0.0.2.ip6.arpa`

#### Simplification
The address is expanded to its 32 hex digits and reversed nibble by nibble (4 bits); the zeros compressed by `::` count too:

```
2001:db8:85a3::8a2e:370:7334
↓
4.3.3.7.0.7.3.0.e.2.a.8.0.0.0.0.0.0.0.0.3.a.5.8.8.b.d.0.1.0.0.2.ip6.arpa
```

### IPv6 Reverse Configuration

```bind
$ORIGIN 3.a.5.8.8.b.d.0.1.0.0.2.ip6.arpa.
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
    2023120101
    3H
    1H
    1W
    1D
)

    IN NS ns1.example.com.

4.3.3.7.0.7.3.0.e.2.a.8.0.0.0.0.0.0.0.0 IN PTR www.example.com.
```

## Importance for Reputation

### Email Delivery

Email servers check PTR records to fight spam:

```bash
# Check PTR
dig -x 192.168.1.1

# Check SPF
dig TXT example.com

# Check DKIM
dig TXT dkim._domainkey.example.com
```

### Anti-spam Filters

- **Hotmail/Outlook:** Requires a valid PTR
- **Gmail:** Uses PTR as a reputation factor
- **Spamhaus:** Lists IPs without a valid PTR

### Best Practices

1. **PTR must resolve:** `host IP` must return a valid name
2. **Consistency:** PTR must match A/AAAA records
3. **Uniqueness:** An IP must have only one PTR
4. **Own domain:** Use your own subdomain (mail.example.com)

## Diagnosis and Troubleshooting

### Verification Tools

#### host command
```bash
host 192.168.1.1
# Should return: 192.168.1.1.in-addr.arpa domain name pointer mail.example.com
```

#### Dig
```bash
# PTR query
dig PTR 1.1.168.192.in-addr.arpa

# Simplified reverse query
dig -x 192.168.1.1
```

#### Nslookup
```bash
nslookup
> set type=PTR
> 1.1.168.192.in-addr.arpa
```

### Common Problems

#### 1. PTR not configured
```
;; ANSWER SECTION:
;; No answer
```

#### 2. Incorrect delegation
```
;; AUTHORITY SECTION:
1.168.192.in-addr.arpa. 86400 IN NS ns1.isp.com.
```

#### 3. Inconsistent TTL
A PTR with a TTL different from the A record can cause caching problems.

### Monitoring Scripts

```bash
#!/bin/bash
# Check PTR for an IP range

for i in {1..254}; do
    ip="192.168.1.$i"
    ptr=$(dig -x $ip +short)
    if [ -z "$ptr" ]; then
        echo "WARNING: No PTR for $ip"
    else
        echo "OK: $ip -> $ptr"
    fi
done
```

## Advanced Use Cases

### Load Balancing

PTR for load balancer IPs:

```
10 IN PTR lb1.example.com.
10 IN PTR lb2.example.com.  ; Not recommended - only one PTR per IP
```

### CDN and Shared Hosting

- **Problem:** Multiple domains on the same IP
- **Solution:** Generic PTR or subdomains

### VPN and Remote Access

PTR for dynamically assigned IPs:

```
100 IN PTR vpn-user-001.example.com.
101 IN PTR vpn-user-002.example.com.
```

## Security

### Considerations

- **Information leakage:** PTR can reveal internal structure
- **Spoofing:** DNS spoofing attacks affect PTR
- **Cache poisoning:** Attacks on DNS servers

### Security Best Practices

1. **DNSSEC:** Sign reverse zones
2. **Split DNS:** Separate internal and external zones
3. **Rate limiting:** Limit reverse queries
4. **Monitoring:** Alerts on PTR changes

## References

- RFC 1035: Domain Names - Implementation and Specification
- RFC 2317: Classless IN-ADDR.ARPA delegation
- RFC 3596: DNS Extensions to Support IP Version 6
- RFC 5855: Nameservers for IPv4 and IPv6 Reverse Zones
