---

---

# Reserved IP Ranges

Las direcciones IP reservadas son bloques de direcciones que no se enrutan en Internet público. Incluyen rangos privados, de documentación, loopback y otros usos especiales definidos por IANA y RFCs.

## Rangos Privados (RFC 1918)

### Clase A Privada

| Rango | Prefijo CIDR | Hosts Disponibles | Uso |
|-------|--------------|-------------------|-----|
| 10.0.0.0 - 10.255.255.255 | 10.0.0.0/8 | 16,777,214 | Redes corporativas grandes |

**Características:**
- Un solo bloque de /8
- Máximo espacio de direcciones privadas
- Común en grandes organizaciones
- Soporta VLSM para subredes

### Clase B Privada

| Rango | Prefijo CIDR | Hosts Disponibles | Uso |
|-------|--------------|-------------------|-----|
| 172.16.0.0 - 172.31.255.255 | 172.16.0.0/12 | 1,048,574 | Redes medianas |

**Características:**
- 16 bloques de /16 cada uno
- Equilibrio entre tamaño y flexibilidad
- Común en campus universitarios
- Fácil de recordar y gestionar

### Clase C Privada

| Rango | Prefijo CIDR | Hosts Disponibles | Uso |
|-------|--------------|-------------------|-----|
| 192.168.0.0 - 192.168.255.255 | 192.168.0.0/16 | 65,534 | Redes pequeñas |

**Características:**
- 256 bloques de /24 cada uno
- Más fácil de gestionar
- Común en hogares y pequeñas oficinas
- Soporte nativo en routers domésticos

## Rangos Especiales IANA

### Loopback (RFC 5735)

| Rango | Prefijo CIDR | Uso |
|-------|--------------|-----|
| 127.0.0.0 - 127.255.255.255 | 127.0.0.0/8 | Interfaz loopback local |

**Detalles:**
- **127.0.0.1:** Loopback estándar
- **127.0.0.0/8:** Todo el rango reservado
- **No enrutable:** Solo accesible localmente
- **Pruebas:** Usado para testing de servicios locales

### Link-Local (RFC 3927)

| Rango | Prefijo CIDR | Uso |
|-------|--------------|-----|
| 169.254.0.0 - 169.254.255.255 | 169.254.0.0/16 | Autoconfiguración automática |

**Detalles:**
- **APIPA:** Automatic Private IP Addressing
- **Windows:** Asignado cuando DHCP falla
- **Zeroconf:** Usado por Bonjour, Avahi
- **No enrutable:** Solo en enlace local

### TEST-NET (RFC 5735)

| Rango | Prefijo CIDR | Uso |
|-------|--------------|-----|
| 192.0.2.0 - 192.0.2.255 | 192.0.2.0/24 | Documentación y ejemplos |
| 198.51.100.0 - 198.51.100.255 | 198.51.100.0/24 | Documentación y ejemplos |
| 203.0.113.0 - 203.0.113.255 | 203.0.113.0/24 | Documentación y ejemplos |

**Detalles:**
- **RFC 5735:** Rangos para documentación
- **No usar en producción:** Solo ejemplos
- **Libros/Tutoriales:** Común en documentación técnica

## Rangos para CGNAT (Carrier-Grade NAT)

### RFC 6598 (CGNAT)

| Rango | Prefijo CIDR | Uso |
|-------|--------------|-----|
| 100.64.0.0 - 100.127.255.255 | 100.64.0.0/10 | Shared Address Space |

**Detalles:**
- **CGNAT:** Carrier-Grade Network Address Translation
- **ISPs:** Usado por proveedores de Internet
- **RFC 6598:** Estándar para espacio compartido
- **No enrutable:** Solo dentro de redes de operador

### Ejemplos de Uso CGNAT

```
ISP Network:
- Public IPs: 203.0.113.0/24 (rango público)
- CGNAT Pool: 100.64.0.0/16 (para clientes)
- Cliente 1: 100.64.1.1 (NAT a 203.0.113.10)
- Cliente 2: 100.64.1.2 (NAT a 203.0.113.10)
```

## Rangos IANA Reservados

### IPv4 Special-Purpose Address Registry

| Rango | Prefijo CIDR | RFC | Propósito |
|-------|--------------|-----|----------|
| 0.0.0.0/8 | 0.0.0.0/8 | RFC 1122 | "This" network |
| 192.0.0.0/24 | 192.0.0.0/24 | RFC 5736 | IETF Protocol Assignments |
| 192.0.2.0/24 | 192.0.2.0/24 | RFC 5735 | TEST-NET-1 |
| 198.51.100.0/24 | 198.51.100.0/24 | RFC 5735 | TEST-NET-2 |
| 203.0.113.0/24 | 203.0.113.0/24 | RFC 5735 | TEST-NET-3 |
| 240.0.0.0/4 | 240.0.0.0/4 | RFC 1112 | Class E (experimental) |

### Rangos por Continente (RIRs)

| RIR | Región | Rango Asignado |
|-----|--------|----------------|
| ARIN | Norteamérica | 192.168.0.0/16, 172.16.0.0/12, 10.0.0.0/8 |
| RIPE | Europa/Oriente Medio | 192.168.0.0/16, 172.16.0.0/12, 10.0.0.0/8 |
| APNIC | Asia/Pacífico | 192.168.0.0/16, 172.16.0.0/12, 10.0.0.0/8 |
| LACNIC | Latinoamérica | 192.168.0.0/16, 172.16.0.0/12, 10.0.0.0/8 |
| AFRINIC | África | 192.168.0.0/16, 172.16.0.0/12, 10.0.0/8 |

## IPv6 Reserved Ranges

### Unique Local Addresses (ULA)

| Rango | Prefijo | RFC | Uso |
|-------|---------|-----|-----|
| fc00::/7 | fc00::/7 | RFC 4193 | Direcciones locales únicas |

**Detalles:**
- **fc00::/8:** Asignadas por LIRs
- **fd00::/8:** Generadas localmente
- **No enrutables:** Solo dentro de sitio

### Link-Local Unicast

| Rango | Prefijo | RFC | Uso |
|-------|---------|-----|-----|
| fe80::/10 | fe80::/10 | RFC 4291 | Enlace local |

**Detalles:**
- **fe80::/64:** Por interfaz
- **Autoconfiguración:** SLAAC
- **No enrutable:** Solo enlace local

### Multicast

| Rango | Prefijo | RFC | Uso |
|-------|---------|-----|-----|
| ff00::/8 | ff00::/8 | RFC 4291 | Direcciones multicast |

**Grupos importantes:**
- **ff02::1:** All nodes
- **ff02::2:** All routers
- **ff05::2:** All OSPF routers

## Configuración en Dispositivos

### Router Cisco (IOS)

```cisco
! Configurar interfaz con IP privada
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
 no shutdown

! Configurar NAT para acceso a Internet
ip nat inside source list 1 interface GigabitEthernet0/1 overload
access-list 1 permit 192.168.1.0 0.0.0.255

! Configurar DHCP para clientes
ip dhcp pool LAN
 network 192.168.1.0 255.255.255.0
 default-router 192.168.1.1
 dns-server 8.8.8.8
```

### Linux (netplan)

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
```

### Windows (PowerShell)

```powershell
# Configurar IP privada
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.1.100 -PrefixLength 24 -DefaultGateway 192.168.1.1

# Configurar DNS
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses ("8.8.8.8","1.1.1.1")
```

## Consideraciones de Seguridad

### Riesgos de Rangos Privados

1. **Conflictos IP:** Múltiples redes usando mismo rango
2. **Ruteo accidental:** Filtrado insuficiente
3. **Ataques internos:** Sin segmentación adecuada

### Mejores Prácticas

#### Segmentación de Red

```bash
# Linux - Crear VLANs
ip link add link eth0 name eth0.10 type vlan id 10
ip addr add 192.168.10.1/24 dev eth0.10

# Firewall rules
iptables -A FORWARD -s 192.168.1.0/24 -d 192.168.2.0/24 -j DROP
```

#### Monitoreo de Rangos

```bash
#!/bin/bash
# Escanear red privada por dispositivos

NETWORK="192.168.1.0/24"

echo "Escaneando $NETWORK..."
nmap -sn $NETWORK | grep "Nmap scan report" | awk '{print $5}' > hosts.txt

echo "Hosts encontrados:"
cat hosts.txt
```

### VPN y Rangos Privados

#### OpenVPN con rangos privados

```openvpn
server 10.8.0.0 255.255.255.0
push "route 192.168.1.0 255.255.255.0"
```

#### WireGuard

```wg
[Interface]
Address = 10.0.0.1/24
PrivateKey = ...

[Peer]
AllowedIPs = 10.0.0.2/32, 192.168.1.0/24
```

## Troubleshooting

### Problemas Comunes

#### 1. Conflicto de IP
```
# Verificar IPs en uso
arp -a
nmap -sn 192.168.1.0/24
```

#### 2. No hay conectividad
```
# Verificar configuración IP
ip addr show
ip route show

# Probar conectividad
ping 192.168.1.1
traceroute 8.8.8.8
```

#### 3. DNS no funciona
```
# Verificar servidores DNS
cat /etc/resolv.conf
nslookup google.com
```

### Herramientas de Diagnóstico

```bash
# Ver tabla ARP
arp -n

# Ver rutas
ip route

# Ver interfaces
ip link show

# Test de conectividad
mtr 8.8.8.8

# Ver procesos de red
netstat -tlnp
ss -tlnp
```

## Referencias

- RFC 1918: Address Allocation for Private Internets
- RFC 3927: Dynamic Configuration of IPv4 Link-Local Addresses
- RFC 4193: Unique Local IPv6 Unicast Addresses
- RFC 5735: Special Use IPv4 Addresses
- RFC 6598: IANA-Reserved IPv4 Prefix for Shared Address Space
- IANA IPv4 Special-Purpose Address Registry
- IANA IPv6 Special-Purpose Address Registry
