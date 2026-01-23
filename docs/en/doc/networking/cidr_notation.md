# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: CIDR Notation
description: Explicación detallada de la notación Classless Inter-Domain Routing y cómo calcular rangos.
draft: false
---

# CIDR Notation

La notación CIDR (Classless Inter-Domain Routing) es un método para asignar direcciones IP y definir rutas en redes IP. Reemplaza el sistema de clases fijas (A, B, C) con un enfoque más flexible basado en prefijos.

## Conceptos Básicos

### Sintaxis
Una dirección CIDR se escribe como: `dirección_IP/prefijo`

- **Dirección IP:** La dirección base de la red
- **Prefijo:** Número de bits consecutivos que representan la parte de red (de 0 a 32 para IPv4)

### Ejemplo
`192.168.1.0/24`

- Red: 192.168.1.0
- Máscara: 255.255.255.0
- Hosts disponibles: 256 - 2 = 254 (excluyendo red y broadcast)

## Cálculo de Rangos

### Conversión de Prefijo a Máscara
El prefijo indica cuántos bits son de red. Los bits restantes son de host.

**Fórmula:** Máscara = 2^(32-prefijo) - 1 en los octetos correspondientes

### Tabla de Prefijos Comunes

| Prefijo | Máscara | Hosts | Uso Típico |
|---------|---------|-------|------------|
| /8 | 255.0.0.0 | 16M | Grandes organizaciones |
| /16 | 255.255.0.0 | 65K | Redes empresariales |
| /24 | 255.255.255.0 | 254 | Subredes LAN |
| /25 | 255.255.255.128 | 126 | Subredes pequeñas |
| /26 | 255.255.255.192 | 62 | Subredes muy pequeñas |
| /27 | 255.255.255.224 | 30 | Subredes punto a punto |
| /28 | 255.255.255.240 | 14 | Subredes mínimas |
| /29 | 255.255.255.248 | 6 | Subredes para routers |
| /30 | 255.255.255.252 | 2 | Enlaces punto a punto |
| /31 | 255.255.255.254 | 2* | Enlaces punto a punto (RFC 3021) |
| /32 | 255.255.255.255 | 1 | Host específico |

*Nota: /31 permite 2 hosts sin broadcast, útil para enlaces punto a punto.

### Cálculo Manual

Para calcular el rango de una red CIDR:

1. **Convertir IP a binario**
2. **Identificar bits de red y host**
3. **Calcular dirección de red:** AND bit a bit con la máscara
4. **Calcular broadcast:** OR bit a bit con el complemento de la máscara
5. **Rango de hosts:** De red+1 a broadcast-1

#### Ejemplo: 192.168.1.100/25

```
IP: 192.168.1.100 = 11000000.10101000.00000001.01100100
Máscara /25: 11111111.11111111.11111111.10000000

Red: 192.168.1.0 (AND)
Broadcast: 192.168.1.127 (OR con ~máscara)
Hosts: 192.168.1.1 - 192.168.1.126
```

## Ventajas de CIDR

- **Eficiencia:** Mejor uso del espacio de direcciones IP
- **Flexibilidad:** Subredes de cualquier tamaño
- **Agregación:** Facilita el enrutamiento jerárquico
- **Escalabilidad:** Reduce el tamaño de las tablas de rutas

## Herramientas Prácticas

### Calculadoras Online
- IP Calculator (ipleak.net)
- Subnet Calculator (subnet-calculator.com)

### Comandos Linux
```bash
# Calcular subredes
ipcalc 192.168.1.0/24

# Mostrar información de red
ip route show
```

### Scripts Python
```python
import ipaddress

# Crear objeto de red
red = ipaddress.ip_network('192.168.1.0/24')

print(f"Red: {red.network_address}")
print(f"Broadcast: {red.broadcast_address}")
print(f"Hosts: {list(red.hosts())[:5]}...")  # Primeros 5 hosts
```

## Casos de Uso Comunes

### Subredes Empresariales
- `/24` para oficinas pequeñas
- `/23` o `/22` para campus
- `/16` para redes corporativas grandes

### Cloud Computing
- AWS VPC: Típicamente `/16` o `/24`
- Subnets: `/24` a `/28` según necesidades

### VPN y Remote Access
- `/30` para enlaces punto a punto
- `/24` para redes de usuarios remotos

## Consideraciones de Seguridad

- **Filtrado:** Asegurar que las ACLs usen notación CIDR
- **Monitoreo:** Detectar cambios en subredes
- **Documentación:** Mantener actualizado el mapa de red

## Referencias

- RFC 4632: Classless Inter-domain Routing (CIDR)
- RFC 1918: Address Allocation for Private Internets
- IANA IPv4 Address Space Registry