---
title: DNSSEC
description: DNS Security Extensions to authenticate DNS data, avoid cache poisoning, and prove non-existence.
draft: false
---

# DNSSEC (Domain Name System Security Extensions)

DNSSEC extends DNS with origin authentication, data integrity, and authenticated denial of existence, preventing cache-poisoning attacks.

## Why DNSSEC?

Traditional DNS lacks:

- **Authentication:** Verify the response comes from an authorized server.
- **Integrity:** Ensure data has not been modified.
- **Authenticated denial:** Prove that a name does not exist.

DNSSEC solves this with public-key cryptography.

## Core Components

- **ZSK (Zone Signing Key):** Signs zone records (shorter rotation).
- **KSK (Key Signing Key):** Signs ZSK and DS records (rotates less frequently).
- **DS (Delegation Signer):** Hash of the KSK published in the parent zone to chain trust.

## How DNSSEC Validation Works

1. **DNS query:** Client asks for `www.example.com`.
2. **Signed response:** Server returns RRsets plus `RRSIG`.
3. **Chain validation:**
   - Validate `RRSIG` using public key in `DNSKEY`.
   - Validate `DS` in the parent zone.
   - Follow the chain of trust to the root.
4. **Outcome:** Authenticated data or validation failure.

## DNSSEC Record Types

| Record | Purpose | Description |
|--------|---------|-------------|
| DNSKEY | Public keys | Contains public ZSK and KSK |
| RRSIG | Signatures | Signatures over RRsets |
| NSEC | Denial of existence | Lists next existing name |
| NSEC3 | Denial of existence | Hashed version of NSEC |
| DS | Delegation Signer | Links parent and child zones |
| CDS/CDNSKEY | Key change automation | Automates DS updates |

## Enabling DNSSEC in BIND9

### 1) Generate Keys
```bash
mkdir -p /etc/bind/keys/example.com

dnssec-keygen -a RSASHA256 -b 2048 -n ZONE -f KSK example.com  # KSK
dnssec-keygen -a RSASHA256 -b 1024 -n ZONE example.com         # ZSK
```

### 2) Sign the Zone
```bash
dnssec-signzone -o example.com -k Kexample.com.+008+12345 example.com Kexample.com.+008+67890

dnssec-verify example.com.signed
```

### 3) named.conf
```bind
zone "example.com" {
    type master;
    file "/etc/bind/zones/example.com.signed";
    key-directory "/etc/bind/keys/example.com";
};
```

### 4) Publish the DS Record
```bash
dnssec-dsfromkey Kexample.com.+008+12345
# Publish DS with the registrar
```

### Automation Example
```bash
#!/bin/bash
ZONE="example.com"
ZONEDIR="/etc/bind/zones"
KEYDIR="/etc/bind/keys/$ZONE"

# Sign zone
DNSKEY=$(ls $KEYDIR/K${ZONE}.+008+*.key | head -n1 | xargs -I{} basename {} .key)
dnssec-signzone -o $ZONE -d $ZONEDIR -k $KEYDIR/$DNSKEY $ZONEDIR/$ZONE

# Reload
rndc reload $ZONE
```

## Validating on the Client Side

### Resolver Configuration

- **/etc/resolv.conf**
```
nameserver 8.8.8.8  # Google (DNSSEC capable)
nameserver 1.1.1.1  # Cloudflare (DNSSEC capable)
```

- **BIND local resolver**
```bind
options {
    dnssec-enable yes;
    dnssec-validation yes;
};
```

- **Unbound**
```unbound
server:
    do-dnssec: yes
    trust-anchor-file: "/etc/unbound/root.key"
```

### Validation Checks
```bash
dig @8.8.8.8 www.dnssec-failed.org +dnssec
dig example.com DNSKEY +dnssec
dig example.com A +dnssec
```

## NSEC vs NSEC3

- **NSEC:** Lists the next existing name; simple and efficient but allows zone enumeration.
- **NSEC3:** Uses hashed names; prevents easy enumeration with extra overhead.

```text
www.example.com. NSEC mail.example.com. A RRSIG NSEC
7P5G...example.com. NSEC3 1 0 10 SALT NEXT-HASHED-NAME
```

## Key Rotation

### ZSK Rotation
1. Generate new ZSK.
2. Publish alongside the old one and sign.
3. Wait for TTL to expire.
4. Remove old ZSK.

### KSK Rotation
1. Generate new KSK.
2. Create and publish the new DS.
3. Wait for DS propagation.
4. Remove old KSK.

## Monitoring and Troubleshooting

### Diagnostic Commands
```bash
dnssec-verify example.com.signed
dig @127.0.0.1 example.com A +dnssec
drill -D example.com
```

### Simple Health Script
```bash
#!/bin/bash
DOMAIN="example.com"
DNSSEC_OK=0

if dig $DOMAIN DNSKEY +short | grep -q "DNSKEY"; then
    echo "✓ DNSKEY present"; DNSSEC_OK=$((DNSSEC_OK+1)); else echo "✗ Missing DNSKEY"; fi
if dig $DOMAIN A +dnssec | grep -q "RRSIG"; then
    echo "✓ RRSIG present"; DNSSEC_OK=$((DNSSEC_OK+1)); else echo "✗ Missing RRSIG"; fi
if dig $DOMAIN DS +short | grep -q "DS"; then
    echo "✓ DS present"; DNSSEC_OK=$((DNSSEC_OK+1)); else echo "✗ Missing DS"; fi

if [ $DNSSEC_OK -eq 3 ]; then
    echo "✓ DNSSEC OK"
else
    echo "✗ DNSSEC issues detected"
fi
```

### Common Problems
- **SERVFAIL:** Validation error; check keys and signatures.
- **Missing DS:** Not published at registrar; publish DS.
- **Expired signatures:** RRSIG expired; resign the zone.
- **Serial mismatch:** Serial not incremented before signing.

## Practical Use Cases

- **Public domains:** Protect against cache poisoning.
- **Corporate networks:** Internal DNSSEC for AD/LDAP.
- **Cloud services:** Route 53 and Cloudflare provide managed DNSSEC.

## Best Practices

1. Start with a subdomain to test.
2. Automate key rollover.
3. Monitor validation errors.
4. Document recovery procedures.

## Performance Considerations

- **Overhead:** Responses are larger (~20-30%).
- **Latency:** Extra validation lookups.
- **CPU:** Cryptographic cost on authoritative servers.

## References

- RFC 4033: DNS Security Introduction and Requirements
- RFC 4034: Resource Records for the DNS Security Extensions
- RFC 4035: Protocol Modifications for the DNS Security Extensions
- RFC 5155: DNS Security (DNSSEC) Hashed Authenticated Denial of Existence
- RFC 6781: DNSSEC Operational Practices, Version 2
