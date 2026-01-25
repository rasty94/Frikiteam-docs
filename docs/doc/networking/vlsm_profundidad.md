---
title: VLSM en Profundidad
description: Guía sobre Variable Length Subnet Masking para optimizar el uso de direcciones IP.
draft: false
updated: 2026-01-25
---

# VLSM (Variable Length Subnet Masking)

VLSM permite crear subredes de diferentes tamaños dentro de una red mayor, optimizando el uso de direcciones IP al asignar exactamente la cantidad necesaria para cada subred.

## Conceptos Fundamentales

### ¿Qué es VLSM?

VLSM es una técnica que permite subdividir una red en subredes de diferentes tamaños, a diferencia del FLSM (Fixed Length Subnet Mask) que usa el mismo tamaño para todas las subredes.

### Ventajas

- **Eficiencia:** Reduce el desperdicio de direcciones IP
- **Escalabilidad:** Permite diseños de red más flexibles
- **Optimización:** Ajusta el tamaño de subredes a las necesidades reales

## Metodología de Diseño

### Paso 1: Requerimientos

Identificar las subredes necesarias y sus tamaños:

| Subred | Hosts Requeridos | Hosts Necesarios* |
|--------|------------------|-------------------|
| Administración | 50 | 62 (/26) |
| Ventas | 25 | 30 (/27) |
| Desarrollo | 12 | 14 (/28) |
| Servidores | 5 | 6 (/29) |
| Enlaces WAN | 2 | 2 (/30) |

*Hosts necesarios = 2^(bits host) - 2

### Paso 2: Ordenar por Tamaño

Ordenar subredes de mayor a menor tamaño para optimizar el espacio:

1. Administración: 62 hosts (/26)
2. Ventas: 30 hosts (/27)
3. Desarrollo: 14 hosts (/28)
4. Servidores: 6 hosts (/29)
5. WAN Links: 2 hosts (/30)

### Paso 3: Asignación de Subredes

Comenzar desde la red principal (ejemplo: 192.168.1.0/24)

#### Subred 1: Administración (62 hosts, /26)
```
Red: 192.168.1.0/26
Rango: 192.168.1.1 - 192.168.1.62
Broadcast: 192.168.1.63
Siguiente disponible: 192.168.1.64
```

#### Subred 2: Ventas (30 hosts, /27)
```
Red: 192.168.1.64/27
Rango: 192.168.1.65 - 192.168.1.94
Broadcast: 192.168.1.95
Siguiente disponible: 192.168.1.96
```

#### Subred 3: Desarrollo (14 hosts, /28)
```
Red: 192.168.1.96/28
Rango: 192.168.1.97 - 192.168.1.110
Broadcast: 192.168.1.111
Siguiente disponible: 192.168.1.112
```

#### Subred 4: Servidores (6 hosts, /29)
```
Red: 192.168.1.112/29
Rango: 192.168.1.113 - 192.168.1.118
Broadcast: 192.168.1.119
Siguiente disponible: 192.168.1.120
```

#### Subred 5: WAN Links (2 hosts, /30)
```
Red: 192.168.1.120/30
Rango: 192.168.1.121 - 192.168.1.122
Broadcast: 192.168.1.123
Siguiente disponible: 192.168.1.124
```

## Cálculo de Subredes

### Fórmula General

Para una red con prefijo base `/N` y subred con `/M`:

- **Bits prestados:** M - N
- **Número de subredes:** 2^(M - N)
- **Hosts por subred:** 2^(32 - M) - 2

### Herramientas de Cálculo

#### Script Python para VLSM
```python
import ipaddress

def calcular_vlsm(red_base, subredes):
    """
    Calcula subredes VLSM
    red_base: string como '192.168.1.0/24'
    subredes: lista de tuplas (nombre, hosts_requeridos)
    """
    red = ipaddress.ip_network(red_base)
    subredes_ordenadas = sorted(subredes, key=lambda x: x[1], reverse=True)
    
    resultado = []
    direccion_actual = red.network_address
    
    for nombre, hosts_req in subredes_ordenadas:
        # Calcular prefijo necesario
        bits_host = 0
        while (2 ** bits_host) - 2 < hosts_req:
            bits_host += 1
        
        prefijo = 32 - bits_host
        nueva_red = ipaddress.ip_network(f"{direccion_actual}/{prefijo}")
        
        resultado.append({
            'nombre': nombre,
            'red': nueva_red,
            'hosts': list(nueva_red.hosts())
        })
        
        # Siguiente dirección disponible
        direccion_actual = nueva_red.broadcast_address + 1
    
    return resultado

# Ejemplo de uso
subredes = [
    ('Administración', 50),
    ('Ventas', 25),
    ('Desarrollo', 12),
    ('Servidores', 5),
    ('WAN', 2)
]

resultado = calcular_vlsm('192.168.1.0/24', subredes)
for subred in resultado:
    print(f"{subred['nombre']}: {subred['red']}")
```

#### Comandos Linux
```bash
# Usar ipcalc para verificar subredes
ipcalc 192.168.1.0/26

# Calcular rangos manualmente
echo "ibase=10; obase=2; 192" | bc  # Convertir a binario
```

## Mejores Prácticas

### Diseño Eficiente

1. **Ordenar correctamente:** Siempre asignar subredes grandes primero
2. **Dejar espacio:** Reservar rangos para crecimiento futuro
3. **Documentar:** Mantener diagramas de red actualizados
4. **Monitorear uso:** Revisar periódicamente la utilización de direcciones

### Consideraciones de Seguridad

- **Segmentación:** Usar VLSM para separar zonas de seguridad
- **Filtrado:** Configurar ACLs basadas en subredes
- **Monitoreo:** Implementar alertas de uso de IP

### Casos de Uso

#### Redes Empresariales
- Departamentos con diferentes tamaños
- Oficinas remotas con requerimientos variables
- Segmentación por función (servidores, usuarios, invitados)

#### Proveedores de Servicios
- Asignación de subredes a clientes
- Optimización de espacio IPv4 limitado
- Migración gradual a IPv6

## Limitaciones y Consideraciones

### Espacio Perdido
- Bits no utilizados en subredes pequeñas
- Broadcast addresses consumen direcciones
- Reserva para crecimiento futuro

### Complejidad
- Cálculos más complejos que FLSM
- Mayor posibilidad de errores humanos
- Necesidad de documentación detallada

### Migración
- Requiere planificación cuidadosa
- Posibles interrupciones de servicio
- Actualización de configuraciones de red

## Referencias

- RFC 950: Internet Standard Subnetting Procedure
- RFC 1812: Requirements for IP Version 4 Routers
- Cisco Networking Academy: VLSM Concepts