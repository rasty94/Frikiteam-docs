---
title: "TLS Certificates"
description: Validation types (DV, OV, EV), chains of trust and configuration best practices.
tags: ['networking']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: intermediate
category: Networking
status: published
estimated_time: 16 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# TLS Certificates

TLS (Transport Layer Security) certificates are fundamental to the security of web communications. This document covers validation types, chain of trust management and configuration best practices.

## TLS Basics

### What Is a TLS Certificate?

A TLS certificate is a digital document that binds a public key to an identity (domain, organization). It makes it possible to establish secure HTTPS connections using asymmetric encryption.

### Certificate Components

- **Subject:** Identity of the holder (CN, O, OU, etc.)
- **Issuer:** Certificate authority (CA)
- **Validity Period:** Validity dates
- **Public Key:** Public key used for encryption
- **Signature:** The CA's digital signature
- **Extensions:** Additional information (SAN, etc.)

## Validation Types

### DV (Domain Validation)

#### Characteristics
- **Validation:** Domain ownership only
- **Process:** Email, HTTP-01, DNS-01 challenge
- **Time:** Minutes to hours
- **Cost:** Low (free with Let's Encrypt)
- **Indicator:** Green padlock in the browser

#### Issuance Process
1. **Request:** Generate a CSR for the domain
2. **Challenge:** The CA sends a token to verify
3. **Validation:** Prove control of the domain
4. **Issuance:** Signed certificate

#### Certbot Example
```bash
# DV with Let's Encrypt
certbot certonly --webroot -w /var/www/html -d example.com

# With DNS challenge
certbot certonly --dns-cloudflare -d example.com
```

### OV (Organization Validation)

#### Characteristics
- **Validation:** Domain ownership + organization identity
- **Process:** Verification of legal documents
- **Time:** Days to weeks
- **Cost:** Medium-high
- **Indicator:** Green padlock + "Verified company"

#### Validation Requirements
- **Domain:** Verified ownership
- **Organization:** Valid business registration
- **Authority:** Person authorized to sign
- **Address:** Physical verification

### EV (Extended Validation)

#### Characteristics
- **Validation:** Exhaustive identity verification
- **Process:** Full audit of the organization
- **Time:** Weeks
- **Cost:** High
- **Indicator:** Green padlock + green address bar

#### EV Benefits
- **Trust:** Maximum user trust
- **Protection:** Against advanced phishing
- **SEO:** Potential ranking boost

## Certificate Chains

### Chain Structure

```
Root CA
├── Intermediate CA 1
│   ├── Intermediate CA 2
│   │   └── Server Certificate
│   └── Server Certificate
└── Server Certificate
```

### Certificate Types in the Chain

#### Root Certificate
- **Issuer:** Self-signed
- **Storage:** In the system trust stores
- **Validity:** Long (10-30 years)
- **Use:** Signing intermediate CAs

#### Intermediate Certificate
- **Issuer:** Root CA
- **Purpose:** Signing server certificates
- **Chain:** Multiple levels possible
- **Rotation:** Periodic

#### Server Certificate (Leaf)
- **Issuer:** Intermediate CA
- **Domain:** The website
- **Validity:** 90 days (Let's Encrypt) to 2 years
- **SAN:** Multiple domains/subdomains

### Full Chain Configuration

#### In Apache
```apache
SSLCertificateFile /etc/ssl/certs/example.com.crt
SSLCertificateKeyFile /etc/ssl/private/example.com.key
SSLCertificateChainFile /etc/ssl/certs/intermediate.crt
```

#### In Nginx
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_trusted_certificate /etc/ssl/certs/chain.pem;
}
```

#### Verify the Chain
```bash
# View the certificate contents
openssl x509 -in example.com.crt -text -noout

# Verify the chain
openssl verify -CAfile chain.pem example.com.crt

# Test the SSL connection
openssl s_client -connect example.com:443 -servername example.com
```

## Certificate Management

### CSR Generation

```bash
# Generate a private key
openssl genrsa -out example.com.key 2048

# Create a CSR
openssl req -new -key example.com.key -out example.com.csr \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=Example Corp/CN=example.com"

# With SAN (Subject Alternative Names)
cat > san.cnf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = ES
ST = Madrid
L = Madrid
O = Example Corp
CN = example.com

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = www.example.com
DNS.3 = api.example.com
EOF

openssl req -new -key example.com.key -out example.com.csr -config san.cnf
```

### Automatic Renewal

#### With Certbot
```bash
# Set up automatic renewal
certbot renew --dry-run

# Post-renewal hook
certbot certonly --webroot -w /var/www/html -d example.com \
  --post-hook "systemctl reload nginx"
```

#### Custom Script
```bash
#!/bin/bash
# Check expiry and renew

DOMAIN="example.com"
DAYS_WARNING=30

# Calculate days until expiry
EXPIRY=$(openssl x509 -enddate -noout -in /etc/ssl/certs/$DOMAIN.crt | cut -d= -f2)
EXPIRY_SECONDS=$(date -d "$EXPIRY" +%s)
NOW_SECONDS=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_SECONDS - $NOW_SECONDS) / 86400 ))

if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
    echo "Certificate expires in $DAYS_LEFT days. Renewing..."
    certbot renew --cert-name $DOMAIN
    systemctl reload nginx
fi
```

## Secure Configurations

### Recommended Cipher Suites

#### Modern (Recommended)
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
```

#### Intermediate
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256;
```

#### Legacy Compatibility (Not Recommended)
```nginx
ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
ssl_ciphers HIGH:!aNULL:!MD5;
```

### OCSP Stapling

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/certs/chain.pem;

resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### HSTS (HTTP Strict Transport Security)

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

### HPKP (Public Key Pinning) - DEPRECATED

**Note:** HPKP is obsolete. Use Certificate Transparency instead.

## Monitoring and Alerts

### Certificate Verification

```bash
# Check expiry
openssl x509 -enddate -noout -in cert.pem

# Check against a remote server
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# SSL Labs test
curl -s "https://api.ssllabs.com/api/v3/analyze?host=example.com" | jq '.endpoints[0].grade'
```

### Monitoring Scripts

```python
import ssl
import socket
from datetime import datetime

def check_ssl_cert(hostname, port=443):
    context = ssl.create_default_context()
    conn = context.wrap_socket(socket.socket(), server_hostname=hostname)
    conn.connect((hostname, port))
    
    cert = conn.getpeercert()
    conn.close()
    
    # Extract dates
    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    
    days_left = (not_after - datetime.now()).days
    
    return {
        'subject': cert['subject'],
        'issuer': cert['issuer'],
        'not_before': not_before,
        'not_after': not_after,
        'days_left': days_left,
        'valid': days_left > 0
    }

# Usage
cert_info = check_ssl_cert('example.com')
print(f"Certificate valid for {cert_info['days_left']} days")
```

### Alerts with Nagios/Icinga

```bash
# check_ssl_cert command
/usr/lib/nagios/plugins/check_ssl_cert -H example.com -w 30 -c 7
```

## Common Problems and Solutions

### 1. Certificate Chain Issues

**Error:** `unable to get local issuer certificate`

**Solution:** Include the intermediate certificates in the configuration

### 2. Mismatched Domain

**Error:** `Certificate verification error`

**Solution:** Check that the CN or SAN matches the domain

### 3. Expired Certificate

**Error:** `certificate verify failed`

**Solution:** Renew the certificate before it expires

### 4. Weak Cipher Suites

**Error:** SSL/TLS vulnerabilities

**Solution:** Configure modern cipher suites

## Certificate Transparency

### What Is CT?

Certificate Transparency is a framework for monitoring and auditing SSL/TLS certificates issued by CAs.

### SCT (Signed Certificate Timestamp)

Certificates include SCTs to prove they were recorded in public CT logs.

### CT Verification

```bash
# View SCTs in a certificate
openssl x509 -in cert.pem -text | grep -A 5 "CT Precertificate SCTs"

# Check with crt.sh
curl "https://crt.sh/?q=example.com&output=json"
```

## Best Practices

### Management
1. **Automation:** Use ACME (Let's Encrypt) for DV
2. **Monitoring:** Expiry alerts
3. **Backup:** Secure copies of private keys
4. **Rotation:** Renew before expiry

### Security
1. **Strong keys:** At least 2048-bit RSA, prefer ECDSA
2. **SAN:** Use Subject Alternative Names
3. **HSTS:** Implement HTTP Strict Transport Security
4. **OCSP:** Configure OCSP Stapling

### Performance
1. **Session resumption:** TLS session tickets
2. **OCSP stapling:** Avoid OCSP queries
3. **CDN:** Use a CDN with managed certificates

## References

- RFC 5246: The Transport Layer Security (TLS) Protocol Version 1.2
- RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 5280: Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile
- RFC 6962: Certificate Transparency
- CA/Browser Forum Baseline Requirements
