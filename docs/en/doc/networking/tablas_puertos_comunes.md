---
title: "Common Port Tables"
description: List of standard TCP/UDP ports and associated services (e.g. 22 SSH, 443 HTTPS, 53 DNS).
tags: ['networking']

updated: 2026-10-11
last_reviewed: 2026-10-11
difficulty: intermediate
category: Networking
status: published
estimated_time: 9 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Networking fundamentals"
---

# Common Port Tables

This guide provides a complete reference of the most common TCP/UDP ports used in networking and services. It includes both IANA standard ports and widely used services.

## Well-Known Ports (0-1023)

### Web and HTTP Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 80 | TCP | HTTP | Hypertext Transfer Protocol |
| 443 | TCP | HTTPS | HTTP over TLS/SSL |
| 8080 | TCP | HTTP Alt | Alternative HTTP (proxies, development) |
| 8443 | TCP | HTTPS Alt | Alternative HTTPS |

### Mail Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 25 | TCP | SMTP | Simple Mail Transfer Protocol |
| 110 | TCP | POP3 | Post Office Protocol v3 |
| 143 | TCP | IMAP | Internet Message Access Protocol |
| 465 | TCP | SMTPS | SMTP over SSL |
| 587 | TCP | SMTP MSA | SMTP Mail Submission Agent |
| 993 | TCP | IMAPS | IMAP over SSL |
| 995 | TCP | POP3S | POP3 over SSL |

### DNS and Domain Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 53 | TCP/UDP | DNS | Domain Name System |
| 5353 | UDP | mDNS | Multicast DNS (Bonjour) |
| 5355 | TCP | LLMNR | Link-Local Multicast Name Resolution |

### Authentication and Security Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 22 | TCP | SSH | Secure Shell |
| 389 | TCP | LDAP | Lightweight Directory Access Protocol |
| 636 | TCP | LDAPS | LDAP over SSL |
| 1812 | UDP | RADIUS | Remote Authentication Dial-In User Service |
| 1813 | UDP | RADIUS Acct | RADIUS Accounting |

### Database Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 1433 | TCP | MSSQL | Microsoft SQL Server |
| 1521 | TCP | Oracle | Oracle Database |
| 3306 | TCP | MySQL | MySQL Database |
| 5432 | TCP | PostgreSQL | PostgreSQL Database |
| 6379 | TCP | Redis | Redis Key-Value Store |
| 27017 | TCP | MongoDB | MongoDB Database |

### File Transfer Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 20 | TCP | FTP Data | File Transfer Protocol (data) |
| 21 | TCP | FTP | File Transfer Protocol (control) |
| 69 | UDP | TFTP | Trivial File Transfer Protocol |
| 989 | TCP | FTPS Data | FTP over SSL (data) |
| 990 | TCP | FTPS | FTP over SSL (control) |

### Network and System Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 23 | TCP | Telnet | Telnet (insecure) |
| 67 | UDP | DHCP Server | Dynamic Host Configuration Protocol |
| 68 | UDP | DHCP Client | DHCP Client |
| 123 | UDP | NTP | Network Time Protocol |
| 161 | UDP | SNMP | Simple Network Management Protocol |
| 162 | UDP | SNMP Trap | SNMP Traps |

## Registered Ports (1024-49151)

### Web Application Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 1433 | TCP | MSSQL | Microsoft SQL Server |
| 1521 | TCP | Oracle | Oracle Database |
| 2049 | TCP/UDP | NFS | Network File System |
| 2375 | TCP | Docker | Docker Daemon (without TLS) |
| 2376 | TCP | Docker TLS | Docker Daemon with TLS |
| 3306 | TCP | MySQL | MySQL Database |
| 3389 | TCP | RDP | Remote Desktop Protocol |
| 5432 | TCP | PostgreSQL | PostgreSQL Database |
| 5900 | TCP | VNC | Virtual Network Computing |
| 6379 | TCP | Redis | Redis Key-Value Store |
| 8080 | TCP | HTTP Alt | Alternative HTTP |
| 8443 | TCP | HTTPS Alt | Alternative HTTPS |
| 9000 | TCP | PHP-FPM | PHP FastCGI Process Manager |
| 9090 | TCP | Prometheus | Prometheus monitoring |
| 9200 | TCP | Elasticsearch | Elasticsearch search engine |
| 27017 | TCP | MongoDB | MongoDB Database |

### Communication Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 1194 | UDP | OpenVPN | OpenVPN |
| 1701 | UDP | L2TP | Layer 2 Tunneling Protocol |
| 1723 | TCP | PPTP | Point-to-Point Tunneling Protocol |
| 3478 | UDP | STUN | Session Traversal Utilities for NAT |
| 4500 | UDP | IPSec NAT-T | IPsec NAT Traversal |
| 5004 | UDP | RTP | Real-time Transport Protocol |
| 5005 | UDP | RTCP | Real-time Transport Control Protocol |
| 5060 | TCP/UDP | SIP | Session Initiation Protocol |
| 5061 | TCP | SIPS | SIP over TLS |

### Monitoring and Management Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 161 | UDP | SNMP | Simple Network Management Protocol |
| 162 | UDP | SNMP Trap | SNMP Traps |
| 199 | TCP | SNMP Multiplex | SNMP multiplexing |
| 10050 | TCP | Zabbix Agent | Zabbix monitoring agent |
| 10051 | TCP | Zabbix Server | Zabbix server |
| 24224 | TCP | Zabbix Proxy | Zabbix proxy |
| 5666 | TCP | NRPE | Nagios Remote Plugin Executor |
| 6556 | TCP | Checkmk | Checkmk monitoring |

### Virtualization Services

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 22 | TCP | SSH | Secure Shell (VM access) |
| 135 | TCP | RPC | Microsoft RPC |
| 139 | TCP | NetBIOS | NetBIOS Session Service |
| 445 | TCP | SMB | Server Message Block |
| 902 | TCP | VMware | VMware Server |
| 903 | TCP | VMware | VMware Remote Console |
| 2375 | TCP | Docker | Docker Daemon |
| 2376 | TCP | Docker TLS | Docker Daemon with TLS |
| 6443 | TCP | Kubernetes API | Kubernetes API Server |
| 10250 | TCP | Kubelet | Kubernetes Kubelet |

## Dynamic/Ephemeral Ports (49152-65535)

### Ranges by Operating System

| System | Dynamic Range | Notes |
|---------|----------------|-------|
| Linux | 32768-60999 | Configurable in /proc/sys/net/ipv4/ip_local_port_range |
| Windows | 49152-65535 | Ephemeral ports |
| macOS | 49152-65535 | Ephemeral ports |
| IANA | 49152-65535 | Dynamic/Private ports |

### Common Services on High Ports

| Port | Protocol | Service | Description |
|--------|-----------|----------|-------------|
| 50000-50099 | TCP | SAP | SAP Dispatcher ports |
| 54321 | TCP | PostgreSQL | Alternative PostgreSQL |
| 55000 | TCP | Oracle | Oracle Listener |
| 60000-61000 | TCP | X11 | X Window System |

## Ports by Protocol

### Specific TCP

| Port | Service | Main Use |
|--------|----------|---------------|
| 21 | FTP | File transfer |
| 22 | SSH | Secure remote access |
| 23 | Telnet | Remote access (insecure) |
| 25 | SMTP | Mail sending |
| 53 | DNS | Name resolution |
| 80 | HTTP | Unencrypted web |
| 110 | POP3 | Mail retrieval |
| 143 | IMAP | Mail access |
| 443 | HTTPS | Encrypted web |
| 993 | IMAPS | Secure IMAP |
| 995 | POP3S | Secure POP3 |

### Specific UDP

| Port | Service | Main Use |
|--------|----------|---------------|
| 53 | DNS | DNS queries |
| 67 | DHCP Server | IP assignment |
| 68 | DHCP Client | IP request |
| 69 | TFTP | Simple file transfer |
| 123 | NTP | Time synchronization |
| 161 | SNMP | Network monitoring |
| 500 | IPSec | IPsec VPN |
| 1194 | OpenVPN | OpenVPN VPN |

## Tools to Verify Ports

### Basic Commands

```bash
# View open ports locally
netstat -tlnp
ss -tlnp

# Scan ports on a remote host
nmap -p 1-1000 example.com

# View services by port
lsof -i :80

# View port-to-service mapping
cat /etc/services | grep -E "^[0-9]"
```

### Verification Scripts

```bash
#!/bin/bash
# Check common ports

HOST=$1
PORTS=(22 80 443 3306 5432)

echo "Checking ports on $HOST..."

for port in "${PORTS[@]}"; do
    if nc -z -w5 $HOST $port 2>/dev/null; then
        service=$(grep "^$port/" /etc/services | head -1 | awk '{print $1}')
        echo "✓ Port $port open ($service)"
    else
        echo "✗ Port $port closed"
    fi
done
```

### Nmap for Advanced Scanning

```bash
# Quick scan of common ports
nmap --top-ports 100 example.com

# Service and version detection
nmap -sV -p 1-1000 example.com

# UDP scan
nmap -sU -p 53,67,68,123 example.com

# Firewall detection
nmap -sA example.com
```

## Security Considerations

### High-Risk Ports

- **23 (Telnet):** Cleartext transmission
- **21 (FTP):** Credentials sent in cleartext
- **80 (HTTP):** No encryption
- **3389 (RDP):** Brute-force attacks
- **5900 (VNC):** Unencrypted remote access

### Best Practices

1. **Filtering:** Use firewalls to limit access
2. **Monitoring:** Alerts for unexpected connections
3. **Encryption:** Prefer secure versions of protocols
4. **Updates:** Keep services up to date
5. **Segmentation:** Separate networks by function

### Firewall Configuration

```bash
# UFW (Ubuntu)
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# iptables
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## References

- [IANA Service Name and Transport Protocol Port Number Registry](https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml)
- [RFC 6335: Internet Assigned Numbers Authority (IANA) Procedures for the Management of the Service Name and Transport Protocol Port Number Registry](https://www.rfc-editor.org/rfc/rfc6335)
