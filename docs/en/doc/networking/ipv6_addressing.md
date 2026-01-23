# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: IPv6 Addressing
description: Estructura de direcciones IPv6, tipos (Link-Local, Global Unicast, Multicast) y reglas de abreviación.
draft: false
---

# IPv6 Addressing

IPv6 es el protocolo de Internet de sexta generación diseñado para reemplazar IPv4. Ofrece un espacio de direcciones masivo (2^128 direcciones) y características avanzadas para el futuro de Internet.

## Estructura de Direcciones

### Formato Básico

Una dirección IPv6 consta de 128 bits, representados como 8 grupos de 4 dígitos hexadecimales separados por dos puntos:

```
2001:0db8:85a3:0000:0000:8a2e:0370:7334
```

### Reglas de Abreviación

#### Regla 1: Omitir Ceros Iniciales
Los ceros iniciales en cada grupo pueden omitirse:

```
2001:db8:85a3:0:0:8a2e:370:7334
```

#### Regla 2: Compresión de Ceros Consecutivos
Un grupo de ceros consecutivos puede reemplazarse por `::` (solo una vez por dirección):

```
2001:db8:85a3::8a2e:370:7334
```

#### Ejemplos de Abreviación

| Dirección Completa | Abreviada | Notas |
|-------------------|-----------|-------|
| 2001:0db8:0000:0000:0000:0000:0000:0001 | 2001:db8::1 | Loopback |
| 0000:0000:0000:0000:0000:0000:0000:0001 | ::1 | Loopback abreviado |
| 0000:0000:0000:0000:0000:0000:0000:0000 | :: | Dirección no especificada |

## Tipos de Direcciones IPv6

### 1. Unicast

Direcciones que identifican una única interfaz:

#### Global Unicast
- **Rango:** 2000::/3
- **Uso:** Internet público
- **Ejemplo:** 2001:db8:85a3::8a2e:370:7334

Estructura de una dirección Global Unicast:
```
| 3 bits | 13 bits | 32 bits | 16 bits | 64 bits |
| Prefix | TLA ID | Reserved | SLA ID | Interface ID |
```

#### Link-Local Unicast
- **Rango:** fe80::/10
- **Uso:** Comunicación dentro del mismo enlace
- **Ejemplo:** fe80::1%eth0
- **Autoconfiguración:** Generadas automáticamente por hosts

#### Unique Local Unicast (ULA)
- **Rango:** fc00::/7
- **Uso:** Redes privadas locales
- **Ejemplo:** fd12:3456:789a::1
- **No enrutable:** Similar a RFC 1918 en IPv4

### 2. Multicast

Direcciones que identifican múltiples interfaces:

- **Rango:** ff00::/8
- **Grupos predefinidos:**
  - ff02::1 - Todos los nodos en el enlace
  - ff02::2 - Todos los routers en el enlace
  - ff05::2 - Todos los routers OSPF
  - ff02::1:ffxx:xxxx - Solicitud de vecino (solicited-node)

### 3. Anycast

Direcciones asignadas a múltiples interfaces, donde el paquete se entrega a la más cercana:

- **Uso:** Servicios distribuidos (DNS, NTP)
- **Identificación:** No distinguible de unicast por sintaxis

## Interface ID y EUI-64

### Generación de Interface ID

En IPv6, los 64 bits menos significativos identifican la interfaz. Se pueden generar de varias formas:

#### EUI-64 (Extended Unique Identifier)
1. Tomar dirección MAC (48 bits)
2. Insertar ffff en el medio: `aa:bb:cc:ff:ff:dd:ee:ff`
3. Invertir el bit U/L del primer octeto

```python
def eui64_from_mac(mac):
    # Ejemplo: 00:1B:44:11:3A:B7
    mac_parts = mac.split(':')
    # Insertar ffff
    eui64 = mac_parts[:3] + ['ff', 'ff'] + mac_parts[3:]
    # Invertir bit 7 del primer byte
    first_byte = int(eui64[0], 16)
    first_byte ^= 0x02  # Invertir bit 1 (U/L bit)
    eui64[0] = f"{first_byte:02x}"
    return ':'.join(eui64)

print(eui64_from_mac("00:1B:44:11:3A:B7"))  # 021b:44ff:fe11:3ab7
```

#### Autoconfiguración Stateless (SLAAC)
- Hosts generan Interface ID automáticamente
- Basado en MAC o aleatorio para privacidad

## Configuración IPv6

### Comandos Linux

#### Ver direcciones IPv6
```bash
ip -6 addr show
ip addr show dev eth0
```

#### Configurar dirección estática
```bash
ip addr add 2001:db8::1/64 dev eth0
```

#### Configurar gateway
```bash
ip -6 route add default via 2001:db8::1 dev eth0
```

### Configuración en /etc/network/interfaces
```
iface eth0 inet6 static
    address 2001:db8:85a3::8a2e:370:7334
    netmask 64
    gateway 2001:db8:85a3::1
```

### Router Advertisement (RA)
Los routers anuncian prefijos automáticamente:
```bash
# Ver RAs recibidos
radvdump
```

## Transición IPv4/IPv6

### Técnicas de Transición

#### Dual Stack
- Hosts con ambas direcciones IPv4 e IPv6
- Aplicaciones eligen protocolo

#### Tunneling
- 6to4: `2002:ipv4_addr::/48`
- Teredo: Para hosts detrás de NAT IPv4
- ISATAP: Tunneling intra-site

#### Translation
- NAT64/DNS64: Traducción de protocolos
- SIIT: Stateless IP/ICMP Translation

### Ejemplos de Configuración

#### Dual Stack en Apache
```
Listen [::]:80
Listen 0.0.0.0:80
```

#### IPv6 en Docker
```yaml
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "80:80"
      - "[::]:80:80"  # IPv6
```

## Seguridad IPv6

### Consideraciones Específicas

- **Autoconfiguración:** Riesgo de spoofing
- **Extension Headers:** Posibles ataques de fragmentación
- **Multicast:** Amplificación de ataques
- **Privacy Extensions:** Direcciones temporales

### Mejores Prácticas

- **Filtrado:** Implementar ACLs IPv6
- **Monitoreo:** Usar herramientas como tcpdump
- **Actualizaciones:** Mantener sistemas actualizados

### Herramientas de Diagnóstico

```bash
# Ping IPv6
ping6 2001:db8::1

# Traceroute IPv6
traceroute6 google.com

# Ver tabla de rutas IPv6
ip -6 route show

# Ver neighbors IPv6
ip -6 neigh show
```

## Referencias

- RFC 4291: IP Version 6 Addressing Architecture
- RFC 4862: IPv6 Stateless Address Autoconfiguration
- RFC 4941: Privacy Extensions for Stateless Address Autoconfiguration
- RFC 7343: An IPv6 Prefix for Overlay Routable Cryptographic Hash Identifiers (ORCHIDv2)