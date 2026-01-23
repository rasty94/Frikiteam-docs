# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: Protocolos ICMP/ARP/NDP
description: Diferencias clave entre IPv4 (ARP) e IPv6 (NDP) y tipos de mensajes ICMP para diagnóstico.
draft: false
---

# Protocolos ICMP/ARP/NDP

Los protocolos de red ICMP, ARP y NDP son fundamentales para el funcionamiento de IP. ICMP proporciona diagnóstico y control de errores, mientras que ARP y NDP resuelven direcciones de capa 2 a capa 3.

## ICMP (Internet Control Message Protocol)

### Función Principal

ICMP transporta mensajes de control y error entre dispositivos IP. Es parte integral del protocolo IP y no usa puertos como TCP/UDP.

### Tipos de Mensajes ICMP

#### Mensajes de Error

| Tipo | Código | Descripción | Uso |
|------|--------|-------------|-----|
| 3 | 0 | Network Unreachable | Red no alcanzable |
| 3 | 1 | Host Unreachable | Host no alcanzable |
| 3 | 2 | Protocol Unreachable | Protocolo no soportado |
| 3 | 3 | Port Unreachable | Puerto no disponible |
| 3 | 4 | Fragmentation Needed | Fragmentación requerida |
| 11 | 0 | TTL Exceeded | Tiempo de vida agotado |
| 12 | 0 | Parameter Problem | Problema de parámetros |

#### Mensajes Informativos

| Tipo | Código | Descripción | Uso |
|------|--------|-------------|-----|
| 0 | 0 | Echo Reply | Respuesta a ping |
| 8 | 0 | Echo Request | Solicitud de ping |
| 9 | 0 | Router Advertisement | Anuncio de router (raro) |
| 10 | 0 | Router Solicitation | Solicitud de router |
| 13 | 0 | Timestamp Request | Solicitud de timestamp |
| 14 | 0 | Timestamp Reply | Respuesta de timestamp |

### ICMP en Diagnóstico

#### Ping (Echo Request/Reply)
```bash
# Ping básico
ping 192.168.1.1

# Ping con tamaño específico
ping -s 1472 192.168.1.1  # Para detectar MTU

# Ping continuo
ping -t 192.168.1.1
```

#### Traceroute (TTL Exceeded)
```bash
# Traceroute usando ICMP
traceroute 8.8.8.8

# Windows tracert
tracert 8.8.8.8
```

### ICMPv6

IPv6 tiene ICMPv6 integrado (no separado como en IPv4):

- **Mensajes de error:** Similares a ICMPv4
- **Mensajes informativos:** Incluye NDP
- **Tipos adicionales:** Packet Too Big, Parameter Problem

## ARP (Address Resolution Protocol)

### Función en IPv4

ARP resuelve direcciones IP de capa 3 a direcciones MAC de capa 2. Esencial para comunicación en redes Ethernet.

### Proceso ARP

1. **ARP Request:** Broadcast "Who has IP X?"
2. **ARP Reply:** Unicast "IP X is at MAC Y"
3. **Cache:** Almacena mapeo por tiempo limitado

### Tabla ARP

```bash
# Ver tabla ARP
arp -a

# Ver tabla ARP detallada
ip neigh show

# Limpiar entrada específica
arp -d 192.168.1.1

# Añadir entrada estática
arp -s 192.168.1.1 aa:bb:cc:dd:ee:ff
```

### Tipos de Mensajes ARP

- **ARP Request (1):** Solicitud de resolución
- **ARP Reply (2):** Respuesta de resolución
- **RARP Request (3):** Reverse ARP (obsoleto)
- **RARP Reply (4):** Reverse ARP reply
- **ARP Announcement (8):** Anuncio gratuito (gratuitous ARP)

### ARP Gratuitous

Un host anuncia su propia IP/MAC sin solicitud previa:

- **Uso:** Detección de conflictos IP
- **Failover:** Actualización de switches/caches
- **Clustering:** Notificación de cambios

```bash
# Enviar ARP gratuitous (Linux)
arping -U -I eth0 192.168.1.100
```

## NDP (Neighbor Discovery Protocol)

### Función en IPv6

NDP reemplaza ARP, ICMP Router Discovery y Redirect en IPv6. Usa ICMPv6 para todas las funciones.

### Componentes de NDP

#### Neighbor Solicitation (NS) / Neighbor Advertisement (NA)

Equivalente a ARP Request/Reply:

- **NS:** Solicita MAC de un vecino
- **NA:** Responde con MAC propio
- **Tipo ICMP:** 135 (NS), 136 (NA)

```bash
# Ver tabla de vecinos IPv6
ip -6 neigh show

# Solicitar vecino manualmente
ndisc6 -n 2001:db8::1 eth0
```

#### Router Solicitation (RS) / Router Advertisement (RA)

Descubrimiento de routers:

- **RS:** Solicita información de routers (tipo 133)
- **RA:** Anuncia presencia y configuración (tipo 134)

```bash
# Ver RAs
radvdump

# Configurar RA en router
radvd -d  # Modo debug
```

#### Redirect

Similar a ICMP Redirect en IPv4 (tipo 137).

### DAD (Duplicate Address Detection)

Prevención de conflictos de direcciones:

1. Host envía NS con dirección tentative
2. Si recibe NA, dirección está duplicada
3. Si no recibe respuesta, dirección es válida

## Comparación ARP vs NDP

| Aspecto | ARP (IPv4) | NDP (IPv6) |
|---------|------------|------------|
| Protocolo | Protocolo separado | Parte de ICMPv6 |
| Mensajes | ARP Request/Reply | NS/NA (ICMP 135/136) |
| Broadcast | Sí (ARP Request) | No (usa multicast) |
| Gratuitous | Sí | NA unsolicited |
| Router Discovery | No (usa ICMP) | Sí (RS/RA) |
| DAD | No | Sí |
| Redirect | No (usa ICMP) | Sí |

## Seguridad y Consideraciones

### Ataques Comunes

#### ARP Spoofing/Poisoning
- Atacante envía ARP replies falsas
- Redirige tráfico a través de su máquina
- **Mitigación:** ARP inspection, certificados

#### ICMP Attacks
- **Smurf:** Amplificación usando broadcast
- **Ping of Death:** Paquetes ICMP oversized
- **Mitigación:** Filtrado ICMP, rate limiting

#### NDP Attacks
- **NDP Spoofing:** Similar a ARP poisoning
- **RA Spoofing:** Falso router advertisement
- **Mitigación:** RA Guard, DHCPv6 con auth

### Mejores Prácticas

#### Configuración Segura
```bash
# Deshabilitar ICMP redirects (si no necesario)
sysctl -w net.ipv4.conf.all.accept_redirects=0

# Rate limiting ICMP
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT
```

#### Monitoreo
```bash
# Monitorear ARP changes
arpwatch

# Detectar ARP spoofing
arpspoof -i eth0 192.168.1.1 192.168.1.2
```

## Herramientas de Diagnóstico

### Wireshark Filtros

```
# ARP
arp

# ICMP
icmp

# NDP
icmpv6.type == 135 || icmpv6.type == 136

# Router Advertisements
icmpv6.type == 134
```

### Scripts de Monitoreo

```python
import subprocess
import re

def get_arp_table():
    result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
    arp_entries = []
    
    for line in result.stdout.split('\n'):
        match = re.search(r'(\S+)\s+\(([\d.]+)\)\s+at\s+([\w:]+)', line)
        if match:
            arp_entries.append({
                'hostname': match.group(1),
                'ip': match.group(2),
                'mac': match.group(3)
            })
    
    return arp_entries

# Uso
arp_table = get_arp_table()
for entry in arp_table:
    print(f"{entry['ip']} -> {entry['mac']}")
```

## Referencias

- RFC 792: Internet Control Message Protocol
- RFC 826: Ethernet Address Resolution Protocol
- RFC 4861: Neighbor Discovery for IP version 6 (IPv6)
- RFC 4862: IPv6 Stateless Address Autoconfiguration