# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: MTU/MSS Values
description: Valores típicos de Maximum Transmission Unit para diferentes medios (Ethernet, PPPoE, Jumbo Frames).
draft: false
---

# MTU/MSS Values

MTU (Maximum Transmission Unit) y MSS (Maximum Segment Size) son parámetros críticos en redes TCP/IP que afectan el rendimiento y la eficiencia de la transmisión de datos.

## Conceptos Básicos

### MTU (Maximum Transmission Unit)

La MTU es el tamaño máximo de paquete que puede transmitirse en una interfaz de red sin fragmentación.

**Fórmula básica:**
```
MTU = Payload + Headers
```

### MSS (Maximum Segment Size)

El MSS es el tamaño máximo de datos en un segmento TCP, excluyendo los headers TCP/IP.

**Relación con MTU:**
```
MSS = MTU - (IP Header + TCP Header)
MSS = MTU - 40 bytes (IPv4) o 60 bytes (IPv6 con opciones)
```

## Valores MTU por Tecnología

### Ethernet

| Estándar | MTU | Notas |
|----------|-----|-------|
| Ethernet II | 1500 | Estándar más común |
| IEEE 802.3 | 1492 | Con LLC/SNAP |
| Jumbo Frames | 9000 | Frames grandes |
| Super Jumbo | 16000+ | Para storage networks |

### Tecnologías WAN

| Tecnología | MTU Típico | Overhead | Notas |
|------------|------------|----------|-------|
| PPPoE | 1492 | 8 bytes | DSL común |
| PPTP | 1460 | 40 bytes | VPN Microsoft |
| L2TP | 1460 | 40 bytes | VPN estándar |
| GRE | 1476 | 24 bytes | Tunneling |
| IPsec | 1380-1420 | 50-90 bytes | VPN cifrado |
| MPLS | 1500 | Variable | Provider dependent |

### Tecnologías Inalámbricas

| Tecnología | MTU | Notas |
|------------|-----|-------|
| Wi-Fi (802.11) | 1500 | Igual que Ethernet |
| Wi-Fi (802.11n/ac) | 2304 | Con agregación |
| LTE/4G | 1428 | Dependiente del operador |
| 5G | 1428+ | Mayor en algunas implementaciones |

### Tecnologías de Storage

| Tecnología | MTU | Uso |
|------------|-----|-----|
| iSCSI | 9000 | Jumbo frames recomendado |
| NFS | 9000 | Mejor rendimiento |
| Fibre Channel over IP | 2400+ | Dependiente de FC |

## Cálculo de MSS

### IPv4

**Headers mínimos:**
- IP Header: 20 bytes
- TCP Header: 20 bytes
- **Total overhead:** 40 bytes

```
MSS = MTU - 40
```

**Ejemplos:**
- MTU 1500: MSS = 1460
- MTU 1492 (PPPoE): MSS = 1452
- MTU 9000 (Jumbo): MSS = 8960

### IPv6

**Headers mínimos:**
- IPv6 Header: 40 bytes
- TCP Header: 20 bytes
- **Total overhead:** 60 bytes

```
MSS = MTU - 60
```

**Con extensiones:**
- Fragment Header: +8 bytes
- Routing Header: +8-24 bytes
- Total puede llegar a 100+ bytes

### TCP con Opciones

**Opciones comunes:**
- Timestamp: +12 bytes
- SACK: +variable
- Window Scaling: +4 bytes

**MSS efectivo:**
```
MSS_Efectivo = MSS - Opciones_TCP
```

## Configuración en Sistemas

### Linux

#### Ver MTU actual
```bash
ip link show dev eth0
ip addr show dev eth0
```

#### Configurar MTU
```bash
# Temporal
ip link set dev eth0 mtu 9000

# Permanente (Ubuntu/Debian)
# /etc/network/interfaces
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    mtu 9000

# Permanente (systemd-networkd)
# /etc/systemd/network/10-eth0.network
[Match]
Name=eth0

[Network]
Address=192.168.1.100/24
MTUBytes=9000
```

#### TCP MSS clamping
```bash
# Ver MSS actual
ip route show

# Configurar MSS clamping
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1452
```

### Windows

#### Ver MTU
```cmd
netsh interface ipv4 show interfaces
netsh interface ipv4 show subinterfaces
```

#### Configurar MTU
```cmd
netsh interface ipv4 set subinterface "Ethernet" mtu=9000 store=persistent
```

#### PowerShell
```powershell
Get-NetAdapter | Select Name, MtuSize
Set-NetAdapterAdvancedProperty -Name "Ethernet" -RegistryKeyword "*MTU" -RegistryValue 9000
```

### Cisco IOS

```cisco
! Ver MTU
show interfaces GigabitEthernet 0/0

! Configurar MTU
interface GigabitEthernet 0/0
 mtu 9000
 ip mtu 9000  ! Para IPv4
 ipv6 mtu 9000  ! Para IPv6

! MSS clamping
ip tcp mss 1452
```

### Juniper JunOS

```junos
# Ver MTU
show interfaces ge-0/0/0

# Configurar MTU
set interfaces ge-0/0/0 mtu 9000

# MSS clamping
set security flow tcp-mss all-tcp mss 1452
```

## Problemas de MTU y Solución

### Síntomas de MTU Baja

1. **Pérdida de paquetes grandes**
2. **Rendimiento lento en descargas**
3. **Problemas con VPN**
4. **Errores de fragmentación**

### Diagnóstico

#### Herramientas de prueba

```bash
# Ping con tamaño específico
ping -M do -s 1472 192.168.1.1  # 1500 - 28 = 1472

# Descubrir MTU path
tracepath example.com

# MTR con MTU
mtr --mtu example.com
```

#### Script de discovery MTU

```bash
#!/bin/bash
# Descubrir MTU path

TARGET=$1
MTU=1500

echo "Descubriendo MTU path a $TARGET..."

while [ $MTU -gt 0 ]; do
    if ping -M do -s $((MTU-28)) -c 1 $TARGET >/dev/null 2>&1; then
        echo "MTU path: $MTU"
        break
    fi
    MTU=$((MTU-10))
done
```

### Problemas Comunes y Soluciones

#### 1. PPPoE Overhead

**Problema:** MTU 1500 en enlace PPPoE (MTU real 1492)

**Solución:**
```bash
# Linux
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1452

# Router
ip tcp mss 1452
```

#### 2. VPN Overhead

**Problema:** IPSec/GRE añade overhead

**Solución:**
```bash
# Calcular MSS correcto
# Para IPSec: MTU - 50-90 bytes
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1380
```

#### 3. Jumbo Frames

**Problema:** No todos los dispositivos soportan jumbo frames

**Solución:**
- Verificar compatibilidad de todos los dispositivos
- Usar VLANs separadas para jumbo frames
- Configurar MTU por interfaz

## Rendimiento y Optimización

### Beneficios de MTU Alta

1. **Menos overhead:** Menos headers por byte de datos
2. **Mejor throughput:** Menos interrupciones de CPU
3. **Eficiencia:** Mejor para transferencias grandes

### Jumbo Frames en Práctica

#### Configuración recomendada

```bash
# Servidor de archivos
ip link set dev eth0 mtu 9000

# Verificar soporte
ethtool -i eth0  # Ver driver
ethtool eth0     # Ver capacidades
```

#### Casos de uso

- **Storage:** iSCSI, NFS sobre Ethernet
- **Backup:** Transferencias grandes
- **Virtualización:** Tráfico entre VMs
- **Data centers:** Redes de alta velocidad

### Consideraciones de Seguridad

#### Fragmentación y Seguridad

- **PMTU Discovery:** Ataques de fragmentación
- **ICMP blocking:** Puede causar problemas de MTU
- **VPN:** MTU afecta rendimiento de túneles

#### Mejores Prácticas

1. **Monitoreo:** Alertas de cambios de MTU
2. **Documentación:** Registrar MTU por segmento
3. **Testing:** Verificar compatibilidad antes de cambiar
4. **Backup:** Plan de rollback

## Valores de Referencia

### MTU por Tipo de Red

| Tipo de Red | MTU Recomendado | Notas |
|-------------|------------------|-------|
| LAN Ethernet | 1500 | Estándar |
| LAN Gigabit | 1500-9000 | Jumbo si soportado |
| WAN PPPoE | 1492 | Overhead PPPoE |
| WAN MPLS | 1500 | Provider dependent |
| VPN IPSec | 1380-1420 | Overhead cifrado |
| Wireless | 1500 | Igual que Ethernet |
| Storage | 9000 | Jumbo frames |

### MSS por Escenario

| Escenario | MTU | MSS IPv4 | MSS IPv6 |
|-----------|-----|----------|----------|
| Ethernet estándar | 1500 | 1460 | 1440 |
| PPPoE | 1492 | 1452 | 1432 |
| IPSec tunnel | 1420 | 1380 | 1360 |
| PPTP | 1460 | 1420 | 1400 |
| Jumbo frames | 9000 | 8960 | 8940 |

## Referencias

- RFC 1191: Path MTU Discovery
- RFC 1981: Path MTU Discovery for IPv6
- RFC 2923: TCP Problems with Path MTU Discovery
- RFC 879: The TCP Maximum Segment Size and Related Topics
- IEEE 802.3: Ethernet Standards