---
title: "Firewall y Seguridad de Red"
date: 2026-01-09
tags: [cybersecurity, firewall, networking, iptables, suricata]
draft: false
updated: 2026-01-25
difficulty: intermediate
estimated_time: 3 min
category: Ciberseguridad
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Linux intermedio"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

## Resumen

Esta guía cubre configuración de firewalls en Linux (iptables/nftables, UFW) y herramientas de detección de intrusiones como Suricata/Zeek. Incluye ejemplos prácticos para hardening de red en servidores y contenedores.

## Prerrequisitos

- Conocimientos básicos de redes (TCP/IP, puertos, protocolos).
- Acceso a un servidor Linux (Ubuntu/Debian/CentOS).
- Familiaridad con comandos de terminal.

## Firewalls en Linux

### UFW (Uncomplicated Firewall)

Interfaz simplificada para iptables, recomendado para principiantes.

#### Instalación y Configuración Básica

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ufw

# Habilitar
sudo ufw enable

# Reglas básicas
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Denegar todo por defecto
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

#### Reglas Avanzadas

```bash
# Permitir rango de puertos
sudo ufw allow 3000:4000/tcp

# Permitir desde IP específica
sudo ufw allow from 192.168.1.100 to any port 22

# Limitar conexiones SSH
sudo ufw limit ssh

# Ver estado
sudo ufw status verbose
```

### iptables

Herramienta clásica para configuración de firewall en kernel Linux.

#### Sintaxis Básica

```bash
# Ver reglas actuales
sudo iptables -L -n

# Permitir loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Permitir conexiones establecidas
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Permitir SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Política por defecto
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Guardar reglas
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

### nftables

Reemplazo moderno de iptables, más eficiente y legible.

#### Ejemplo Básico

```bash
# Crear tabla
sudo nft add table inet filter

# Crear cadenas
sudo nft add chain inet filter input { type filter hook input priority 0 \; }
sudo nft add chain inet filter output { type filter hook output priority 0 \; }

# Reglas
sudo nft add rule inet filter input iif lo accept
sudo nft add rule inet filter input ct state established,related accept
sudo nft add rule inet filter input tcp dport 22 accept
sudo nft add rule inet filter input drop

# Ver reglas
sudo nft list ruleset
```

## Herramientas de Detección de Intrusiones (IDS)

### Suricata

IDS/IPS open-source, similar a Snort pero más moderno.

#### Instalación

```bash
# Ubuntu
sudo apt install suricata

# Configurar interfaz
sudo suricata -c /etc/suricata/suricata.yaml -i eth0
```

#### Configuración Básica

```yaml
# /etc/suricata/suricata.yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"

rule-files:
  - suricata.rules
  - custom.rules
```

#### Reglas Personalizadas

```bash
# Archivo custom.rules
alert tcp any any -> $HOME_NET 22 (msg:"SSH connection attempt"; sid:1000001; rev:1;)
```

#### Modos de Operación

```bash
# Modo IDS (solo detección)
suricata -c suricata.yaml -i eth0

# Modo IPS (prevención)
suricata -c suricata.yaml -i eth0 --af-packet
```

### Zeek (anteriormente Bro)

Framework de análisis de red, enfocado en seguridad.

#### Instalación y Uso

```bash
# Instalar
sudo apt install zeek

# Ejecutar
zeek -i eth0 local

# Ver logs
tail -f /var/log/zeek/current/conn.log
```

## Aplicación en Contenedores

### Docker

```bash
# Ejecutar contenedor con red host (menos seguro)
docker run --network host nginx

# Mejor: usar redes bridge y publicar puertos específicos
docker run -p 8080:80 nginx

# Firewall en host para contenedores
sudo ufw allow 8080/tcp
```

### Kubernetes

```yaml
# Network Policy para restringir tráfico
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

## Mejores Prácticas

- **Principio de Least Privilege:** Permitir solo lo necesario.
- **Monitoreo:** Logs de firewall y alertas.
- **Actualizaciones:** Mantener reglas y firmas IDS actualizadas.
- **Testing:** Probar reglas antes de aplicar en producción.

## Troubleshooting

```bash
# Ver logs de UFW
sudo tail -f /var/log/ufw.log

# Ver logs de Suricata
sudo tail -f /var/log/suricata/fast.log

# Ver conexiones activas
sudo ss -tuln
sudo netstat -tuln
```

## Referencias

- [UFW Documentation](https://help.ubuntu.com/community/UFW)
- [iptables Tutorial](https://netfilter.org/documentation/)
- [nftables Wiki](https://wiki.nftables.org/)
- [Suricata User Guide](https://suricata.readthedocs.io/)
- [Zeek Documentation](https://docs.zeek.org/)