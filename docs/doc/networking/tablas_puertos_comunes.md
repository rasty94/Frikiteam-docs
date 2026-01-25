---
title: Tablas de Puertos Comunes
description: Lista de puertos TCP/UDP estándar y servicios asociados (ej. 22 SSH, 443 HTTPS, 53 DNS).
draft: false
updated: 2026-01-25
---

# Tablas de Puertos Comunes

Esta guía proporciona una referencia completa de los puertos TCP/UDP más comunes utilizados en redes y servicios. Incluye tanto puertos estándar IANA como servicios ampliamente utilizados.

## Puertos Bien Conocidos (0-1023)

### Servicios Web y HTTP

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 80 | TCP | HTTP | Protocolo de Transferencia de Hipertexto |
| 443 | TCP | HTTPS | HTTP sobre TLS/SSL |
| 8080 | TCP | HTTP Alt | HTTP alternativo (proxies, desarrollo) |
| 8443 | TCP | HTTPS Alt | HTTPS alternativo |

### Servicios de Correo

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 25 | TCP | SMTP | Simple Mail Transfer Protocol |
| 110 | TCP | POP3 | Post Office Protocol v3 |
| 143 | TCP | IMAP | Internet Message Access Protocol |
| 465 | TCP | SMTPS | SMTP sobre SSL |
| 587 | TCP | SMTP MSA | SMTP Mail Submission Agent |
| 993 | TCP | IMAPS | IMAP sobre SSL |
| 995 | TCP | POP3S | POP3 sobre SSL |

### Servicios DNS y Dominios

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 53 | TCP/UDP | DNS | Domain Name System |
| 5353 | UDP | mDNS | Multicast DNS (Bonjour) |
| 5355 | TCP | LLMNR | Link-Local Multicast Name Resolution |

### Servicios de Autenticación y Seguridad

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 22 | TCP | SSH | Secure Shell |
| 389 | TCP | LDAP | Lightweight Directory Access Protocol |
| 636 | TCP | LDAPS | LDAP sobre SSL |
| 1812 | UDP | RADIUS | Remote Authentication Dial-In User Service |
| 1813 | UDP | RADIUS Acct | RADIUS Accounting |

### Servicios de Base de Datos

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 1433 | TCP | MSSQL | Microsoft SQL Server |
| 1521 | TCP | Oracle | Oracle Database |
| 3306 | TCP | MySQL | MySQL Database |
| 5432 | TCP | PostgreSQL | PostgreSQL Database |
| 6379 | TCP | Redis | Redis Key-Value Store |
| 27017 | TCP | MongoDB | MongoDB Database |

### Servicios de Transferencia de Archivos

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 20 | TCP | FTP Data | File Transfer Protocol (datos) |
| 21 | TCP | FTP | File Transfer Protocol (control) |
| 69 | UDP | TFTP | Trivial File Transfer Protocol |
| 989 | TCP | FTPS Data | FTP sobre SSL (datos) |
| 990 | TCP | FTPS | FTP sobre SSL (control) |

### Servicios de Red y Sistema

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 23 | TCP | Telnet | Telnet (inseguro) |
| 67 | UDP | DHCP Server | Dynamic Host Configuration Protocol |
| 68 | UDP | DHCP Client | DHCP Client |
| 123 | UDP | NTP | Network Time Protocol |
| 161 | UDP | SNMP | Simple Network Management Protocol |
| 162 | UDP | SNMP Trap | SNMP Traps |

## Puertos Registrados (1024-49151)

### Servicios de Aplicaciones Web

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 1433 | TCP | MSSQL | Microsoft SQL Server |
| 1521 | TCP | Oracle | Oracle Database |
| 2049 | TCP/UDP | NFS | Network File System |
| 2375 | TCP | Docker | Docker Daemon (sin TLS) |
| 2376 | TCP | Docker TLS | Docker Daemon con TLS |
| 3306 | TCP | MySQL | MySQL Database |
| 3389 | TCP | RDP | Remote Desktop Protocol |
| 5432 | TCP | PostgreSQL | PostgreSQL Database |
| 5900 | TCP | VNC | Virtual Network Computing |
| 6379 | TCP | Redis | Redis Key-Value Store |
| 8080 | TCP | HTTP Alt | HTTP alternativo |
| 8443 | TCP | HTTPS Alt | HTTPS alternativo |
| 9000 | TCP | PHP-FPM | PHP FastCGI Process Manager |
| 9090 | TCP | Prometheus | Prometheus monitoring |
| 9200 | TCP | Elasticsearch | Elasticsearch search engine |
| 27017 | TCP | MongoDB | MongoDB Database |

### Servicios de Comunicación

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 1194 | UDP | OpenVPN | OpenVPN |
| 1701 | UDP | L2TP | Layer 2 Tunneling Protocol |
| 1723 | TCP | PPTP | Point-to-Point Tunneling Protocol |
| 3478 | UDP | STUN | Session Traversal Utilities for NAT |
| 4500 | UDP | IPSec NAT-T | IPsec NAT Traversal |
| 5004 | UDP | RTP | Real-time Transport Protocol |
| 5005 | UDP | RTCP | Real-time Transport Control Protocol |
| 5060 | TCP/UDP | SIP | Session Initiation Protocol |
| 5061 | TCP | SIPS | SIP sobre TLS |

### Servicios de Monitoreo y Gestión

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 161 | UDP | SNMP | Simple Network Management Protocol |
| 162 | UDP | SNMP Trap | SNMP Traps |
| 199 | TCP | SNMP Multiplex | SNMP multiplexing |
| 10050 | TCP | Zabbix Agent | Zabbix monitoring agent |
| 10051 | TCP | Zabbix Server | Zabbix server |
| 24224 | TCP | Zabbix Proxy | Zabbix proxy |
| 5666 | TCP | NRPE | Nagios Remote Plugin Executor |
| 6556 | TCP | Checkmk | Checkmk monitoring |

### Servicios de Virtualización

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 22 | TCP | SSH | Secure Shell (VM access) |
| 135 | TCP | RPC | Microsoft RPC |
| 139 | TCP | NetBIOS | NetBIOS Session Service |
| 445 | TCP | SMB | Server Message Block |
| 902 | TCP | VMware | VMware Server |
| 903 | TCP | VMware | VMware Remote Console |
| 2375 | TCP | Docker | Docker Daemon |
| 2376 | TCP | Docker TLS | Docker Daemon con TLS |
| 6443 | TCP | Kubernetes API | Kubernetes API Server |
| 10250 | TCP | Kubelet | Kubernetes Kubelet |

## Puertos Dinámicos/Efemeros (49152-65535)

### Rangos por Sistema Operativo

| Sistema | Rango Dinámico | Notas |
|---------|----------------|-------|
| Linux | 32768-60999 | Configurable en /proc/sys/net/ipv4/ip_local_port_range |
| Windows | 49152-65535 | Ephemeral ports |
| macOS | 49152-65535 | Ephemeral ports |
| IANA | 49152-65535 | Dynamic/Private ports |

### Servicios Comunes en Puertos Altos

| Puerto | Protocolo | Servicio | Descripción |
|--------|-----------|----------|-------------|
| 50000-50099 | TCP | SAP | SAP Dispatcher ports |
| 54321 | TCP | PostgreSQL | PostgreSQL alternativo |
| 55000 | TCP | Oracle | Oracle Listener |
| 60000-61000 | TCP | X11 | X Window System |

## Puertos por Protocolo

### TCP Específicos

| Puerto | Servicio | Uso Principal |
|--------|----------|---------------|
| 21 | FTP | Transferencia de archivos |
| 22 | SSH | Acceso remoto seguro |
| 23 | Telnet | Acceso remoto (inseguro) |
| 25 | SMTP | Envío de correo |
| 53 | DNS | Resolución de nombres |
| 80 | HTTP | Web sin cifrado |
| 110 | POP3 | Recuperación de correo |
| 143 | IMAP | Acceso a correo |
| 443 | HTTPS | Web con cifrado |
| 993 | IMAPS | IMAP seguro |
| 995 | POP3S | POP3 seguro |

### UDP Específicos

| Puerto | Servicio | Uso Principal |
|--------|----------|---------------|
| 53 | DNS | Consultas DNS |
| 67 | DHCP Server | Asignación de IP |
| 68 | DHCP Client | Solicitud de IP |
| 69 | TFTP | Transferencia simple de archivos |
| 123 | NTP | Sincronización de tiempo |
| 161 | SNMP | Monitoreo de red |
| 500 | IPSec | VPN IPsec |
| 1194 | OpenVPN | VPN OpenVPN |

## Herramientas para Verificar Puertos

### Comandos Básicos

```bash
# Ver puertos abiertos localmente
netstat -tlnp
ss -tlnp

# Escanear puertos en host remoto
nmap -p 1-1000 example.com

# Ver servicios por puerto
lsof -i :80

# Ver tabla de rutas de puertos
cat /etc/services | grep -E "^[0-9]"
```

### Scripts de Verificación

```bash
#!/bin/bash
# Verificar puertos comunes

HOST=$1
PORTS=(22 80 443 3306 5432)

echo "Verificando puertos en $HOST..."

for port in "${PORTS[@]}"; do
    if nc -z -w5 $HOST $port 2>/dev/null; then
        service=$(grep "^$port/" /etc/services | head -1 | awk '{print $1}')
        echo "✓ Puerto $port abierto ($service)"
    else
        echo "✗ Puerto $port cerrado"
    fi
done
```

### Nmap para Escaneo Avanzado

```bash
# Escaneo rápido de puertos comunes
nmap --top-ports 100 example.com

# Detección de servicios y versiones
nmap -sV -p 1-1000 example.com

# Escaneo UDP
nmap -sU -p 53,67,68,123 example.com

# Detección de firewall
nmap -sA example.com
```

## Consideraciones de Seguridad

### Puertos de Riesgo Alto

- **23 (Telnet):** Transmisión en claro
- **21 (FTP):** Credenciales en claro
- **80 (HTTP):** Sin cifrado
- **3389 (RDP):** Ataques de fuerza bruta
- **5900 (VNC):** Acceso remoto sin cifrado

### Mejores Prácticas

1. **Filtrado:** Usar firewalls para limitar acceso
2. **Monitoreo:** Alertas de conexiones inesperadas
3. **Cifrado:** Preferir versiones seguras de protocolos
4. **Actualización:** Mantener servicios actualizados
5. **Segmentación:** Separar redes por función

### Configuración de Firewall

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

## Referencias

- IANA Service Name and Transport Protocol Port Number Registry
- RFC 6335: Internet Assigned Numbers Authority (IANA) Procedures for the Management of the Service Name and Transport Protocol Port Number Registry
- Common Ports and Protocols Cheat Sheet (SANS Institute)