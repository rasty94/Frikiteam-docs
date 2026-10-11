---
title: "SPF/DKIM/DMARC"
description: Email security triad to prevent spoofing and ensure deliverability.
tags: ['networking']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: intermediate
category: Networking
status: published
estimated_time: 5 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# SPF/DKIM/DMARC

SPF, DKIM and DMARC form the essential triad of email authentication, protecting against spoofing and improving email deliverability.

## SPF (Sender Policy Framework)

### What is SPF?

SPF is a protocol that lets you verify whether an email server is authorized to send mail on behalf of a domain.

### How It Works

1. **Publication:** The domain publishes its authorized IPs/servers
2. **Verification:** The receiver queries the SPF record of the sending domain
3. **Validation:** It compares the server's IP against the authorized list

### SPF Record Syntax

```
v=spf1 [mechanisms] [modifiers]
```

#### Main Mechanisms

| Mechanism | Description | Example |
|-----------|-------------|---------|
| `+ip4:` | Authorized IPv4 address | `+ip4:192.168.1.1` |
| `+ip6:` | Authorized IPv6 address | `+ip6:2001:db8::1` |
| `+a` | Authorizes A/AAAA records | `+a:mail.example.com` |
| `+mx` | Authorizes MX records | `+mx` |
| `+include:` | Includes another domain's policy | `+include:_spf.google.com` |
| `+all` | Allows everything (not recommended) | `+all` |
| `-all` | Denies everything else | `-all` |
| `~all` | Soft fail (recommended) | `~all` |

#### SPF Record Examples

**Basic, for your own domain:**
```
v=spf1 +mx +a:mail.example.com -all
```

**With external services:**
```
v=spf1 include:_spf.google.com include:spf.protection.outlook.com -all
```

**For mailing lists:**
```
v=spf1 include:_spf.google.com include:servers.mcsv.net ~all
```

### SPF Configuration

#### In BIND/DNS
```bind
@ IN TXT "v=spf1 +mx +a:mail.example.com -all"
```

#### Verification
```bash
# Check the SPF record
dig TXT example.com

# Test SPF
spfquery -ip=192.168.1.1 -sender=user@example.com
```

## DKIM (DomainKeys Identified Mail)

### What is DKIM?

DKIM cryptographically signs outgoing emails, making it possible to verify that the content has not been altered and to confirm the sender's authenticity.

### How DKIM Works

1. **Key generation:** The domain creates a public/private key pair
2. **Signing:** The MTA signs the email with the private key
3. **Publication:** The public key is published in DNS
4. **Verification:** The receiver verifies the signature with the public key

### DKIM Components

#### Selector
Identifies which key to use when there are several:

```
selector._domainkey.example.com
```

#### DKIM Record
```bind
selector._domainkey IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC..."
```

#### DKIM-Signature Header
```
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
 d=example.com; s=selector; h=from:to:subject;
 bh=...; b=...
```

### DKIM Configuration

#### Generate Keys
```bash
# Using opendkim
opendkim-genkey -s selector -d example.com

# Using Python
python3 -c "
import dkim
key = dkim.rsa_key_gen()
print('Private key:')
print(key[0].decode())
print('Public key:')
print(key[1].decode())
"
```

#### In Postfix
```postfix
# main.cf
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
milter_default_action = accept
```

#### DKIM Verification
```bash
# Check the public key
dig TXT selector._domainkey.example.com

# Test DKIM
dkimpy-milter --test
```

## DMARC (Domain-based Message Authentication, Reporting and Conformance)

### What is DMARC?

DMARC combines SPF and DKIM, providing policies for handling emails that fail authentication and reports on domain activity.

### How DMARC Works

1. **Publication:** DMARC policy at `_dmarc.example.com`
2. **Evaluation:** Checks SPF and/or DKIM
3. **Action:** Applies the policy according to the result
4. **Reports:** Sends XML reports to the domain

### DMARC Record

```
v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1
```

#### Main Parameters

| Parameter | Description | Values |
|-----------|-------------|--------|
| `p` | Policy | `none`, `quarantine`, `reject` |
| `sp` | Subdomain policy | `none`, `quarantine`, `reject` |
| `rua` | Aggregate reports | `mailto:usuario@dominio.com` |
| `ruf` | Forensic reports | `mailto:usuario@dominio.com` |
| `fo` | Reporting options | `0`, `1`, `d`, `s` |
| `adkim` | DKIM alignment | `r` (relaxed), `s` (strict) |
| `aspf` | SPF alignment | `r` (relaxed), `s` (strict) |

### DMARC Policies

#### p=none
- **Action:** Do nothing
- **Use:** Monitor mode, reports only
- **Example:** `p=none; rua=mailto:dmarc@example.com`

#### p=quarantine
- **Action:** Send to spam
- **Use:** Moderate protection
- **Example:** `p=quarantine; rua=mailto:dmarc@example.com`

#### p=reject
- **Action:** Reject the email
- **Use:** Maximum protection
- **Example:** `p=reject; rua=mailto:dmarc@example.com`

### DMARC Configuration

#### DNS Record
```bind
_dmarc IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1; adkim=r; aspf=r"
```

#### Verification
```bash
# Check the DMARC record
dig TXT _dmarc.example.com

# Validate syntax
dmarc-validate example.com
```

## Complete Implementation

### Configuration Sequence

1. **Configure SPF**
2. **Implement DKIM**
3. **Publish DMARC in monitor mode (p=none)**
4. **Analyze reports**
5. **Tighten policies gradually**

### Complete Example

#### 1. SPF Record
```
v=spf1 include:_spf.google.com include:spf.protection.outlook.com -all
```

#### 2. DKIM Keys
```bash
# Generate for Google Workspace
# Keys are generated automatically in admin.google.com
```

#### 3. DMARC Record
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1; pct=100
```

### Testing Tools

#### Online Validators
- **MX Toolbox:** SPF, DKIM, DMARC checker
- **Mail Tester:** Sends a test email
- **DMARC Analyzer:** Analyzes reports

#### Commands
```bash
# Check all records
dig TXT example.com _dmarc.example.com selector._domainkey.example.com

# Send a test email
swaks --to test@example.com --from user@example.com --server mail.example.com --tls
```

## DMARC Reports

### Report Types

#### Aggregate Reports (RUA)
- **Format:** Compressed XML
- **Frequency:** Daily
- **Content:** Authentication statistics

#### Forensic Reports (RUF)
- **Format:** Email with details
- **Frequency:** Per failed email
- **Content:** Full headers

### Report Analysis

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feedback>
  <report_metadata>
    <org_name>google.com</org_name>
    <email>noreply-dmarc-support@google.com</email>
    <report_id>123456789</report_id>
  </report_metadata>
  <policy_published>
    <domain>example.com</domain>
    <adkim>r</adkim>
    <aspf>r</aspf>
    <p>quarantine</p>
  </policy_published>
  <record>
    <row>
      <source_ip>192.168.1.1</source_ip>
      <count>100</count>
      <policy_evaluated>
        <disposition>quarantine</disposition>
        <dkim>pass</dkim>
        <spf>fail</spf>
      </policy_evaluated>
    </row>
  </record>
</feedback>
```

### Analysis Tools

- **DMARC Report Analyzer:** Online parser
- **dmarcian:** Commercial service
- **Custom scripts:** Process the XML with Python

```python
import xml.etree.ElementTree as ET
import gzip

def parse_dmarc_report(filename):
    with gzip.open(filename, 'rb') as f:
        tree = ET.parse(f)
    root = tree.getroot()
    
    for record in root.findall('.//record'):
        row = record.find('row')
        source_ip = row.find('source_ip').text
        count = int(row.find('count').text)
        disposition = row.find('.//disposition').text
        
        print(f"IP: {source_ip}, Count: {count}, Disposition: {disposition}")

# Usage
parse_dmarc_report('dmarc_report.xml.gz')
```

## Best Practices

### Initial Setup
1. **Start with p=none** to monitor
2. **Configure reports** for analysis
3. **Gradually tighten** the policy

### Maintenance
- **Monitor reports** regularly
- **Update records** when IPs change
- **Use dedicated subdomains** for email

### Security Considerations
- **Rotate DKIM keys** periodically
- **Protect private keys** from unauthorized access
- **Use DNSSEC** to protect records

## References

- RFC 7208: Sender Policy Framework (SPF)
- RFC 6376: DomainKeys Identified Mail (DKIM)
- RFC 7489: Domain-based Message Authentication, Reporting, and Conformance (DMARC)
- RFC 8461: SMTP MTA Strict Transport Security (MTA-STS)
