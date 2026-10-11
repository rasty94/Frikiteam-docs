---
title: "Firewall and Network Security"
tags: ['cybersecurity', 'firewall', 'networking', 'siem']

updated: 2026-01-23
last_reviewed: 2026-01-25
difficulty: intermediate
category: Cybersecurity
status: published
estimated_time: 15 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Intermediate Linux"
---

## Summary

This guide covers firewall configuration on Linux (iptables/nftables, UFW) and intrusion detection tools such as Suricata/Zeek. It includes practical examples for network hardening on servers and containers.

## Prerequisites

- Basic networking knowledge (TCP/IP, ports, protocols).
- Access to a Linux server (Ubuntu/Debian/CentOS).
- Familiarity with terminal commands.

## Firewalls on Linux

### UFW (Uncomplicated Firewall)

Simplified interface for iptables, recommended for beginners.

#### Installation and Basic Configuration

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ufw

# Enable
sudo ufw enable

# Basic rules
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Deny everything by default
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

#### Advanced Rules

```bash
# Allow port range
sudo ufw allow 3000:4000/tcp

# Allow from a specific IP
sudo ufw allow from 192.168.1.100 to any port 22

# Rate-limit SSH connections
sudo ufw limit ssh

# Show status
sudo ufw status verbose
```

### iptables

Classic tool for configuring the firewall in the Linux kernel.

#### Basic Syntax

```bash
# Show current rules
sudo iptables -L -n

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Default policy
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Save rules
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

### nftables

Modern replacement for iptables, more efficient and readable.

#### Basic Example

```bash
# Create table
sudo nft add table inet filter

# Create chains
sudo nft add chain inet filter input { type filter hook input priority 0 \; }
sudo nft add chain inet filter output { type filter hook output priority 0 \; }

# Rules
sudo nft add rule inet filter input iif lo accept
sudo nft add rule inet filter input ct state established,related accept
sudo nft add rule inet filter input tcp dport 22 accept
sudo nft add rule inet filter input drop

# Show rules
sudo nft list ruleset
```

## Intrusion Detection Tools (IDS)

### Suricata

Open-source IDS/IPS, similar to Snort but more modern.

#### Installation

```bash
# Ubuntu
sudo apt install suricata

# Configure interface
sudo suricata -c /etc/suricata/suricata.yaml -i eth0
```

#### Basic Configuration

```yaml
# /etc/suricata/suricata.yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"

rule-files:
  - suricata.rules
  - custom.rules
```

#### Custom Rules

```bash
# custom.rules file
alert tcp any any -> $HOME_NET 22 (msg:"SSH connection attempt"; sid:1000001; rev:1;)
```

#### Operating Modes

```bash
# IDS mode (detection only)
suricata -c suricata.yaml -i eth0

# IPS mode (prevention)
suricata -c suricata.yaml -i eth0 --af-packet
```

### Zeek (formerly Bro)

Network analysis framework focused on security.

#### Installation and Usage

```bash
# Install
sudo apt install zeek

# Run
zeek -i eth0 local

# View logs
tail -f /var/log/zeek/current/conn.log
```

## Use in Containers

### Docker

```bash
# Run container with host network (less secure)
docker run --network host nginx

# Better: use bridge networks and publish specific ports
docker run -p 8080:80 nginx

# Host firewall for containers
sudo ufw allow 8080/tcp
```

### Kubernetes

```yaml
# Network Policy to restrict traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 80
```

## Best Practices

- **Least Privilege principle:** Allow only what is necessary.
- **Monitoring:** Firewall logs and alerts.
- **Updates:** Keep rules and IDS signatures up to date.
- **Testing:** Test rules before applying them in production.

## Troubleshooting

```bash
# View UFW logs
sudo tail -f /var/log/ufw.log

# View Suricata logs
sudo tail -f /var/log/suricata/fast.log

# View active connections
sudo ss -tuln
sudo netstat -tuln
```

## References

- [UFW Documentation](https://help.ubuntu.com/community/UFW)
- [iptables Tutorial](https://netfilter.org/documentation/)
- [nftables Wiki](https://wiki.nftables.org/)
- [Suricata User Guide](https://suricata.readthedocs.io/)
- [Zeek Documentation](https://docs.zeek.org/)
