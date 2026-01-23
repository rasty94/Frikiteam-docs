# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: ASN & BGP
description: Conceptos sobre Sistemas Autónomos y enrutamiento global mediante BGP.
draft: false
---

# ASN & BGP

Los Sistemas Autónomos (AS) y el Protocolo de Gateway Fronterizo (BGP) son fundamentales para el enrutamiento interdominio en Internet. Este documento explica cómo funciona el enrutamiento global de Internet.

## Conceptos Básicos

### ¿Qué es un Sistema Autónomo (AS)?

Un Sistema Autónomo es un conjunto de routers bajo una administración técnica común que presenta una política de enrutamiento coherente al resto de Internet.

**Características:**
- **Número único:** ASN (Autonomous System Number)
- **Políticas propias:** Controla sus propias rutas
- **Conectividad:** Interconecta con otros AS
- **Escalabilidad:** Divide Internet en dominios manejables

### Tipos de AS

#### AS Stub
- **Conexiones:** Solo un upstream provider
- **Rutas:** Recibe rutas completas, anuncia solo sus prefijos
- **Ejemplo:** Pequeña empresa o ISP local

#### AS Multihomed
- **Conexiones:** Múltiples upstream providers
- **Rutas:** Recibe rutas de todos, anuncia sus prefijos
- **Beneficio:** Redundancia y mejor rendimiento

#### AS Transit
- **Función:** Proporciona tránsito a otros AS
- **Rutas:** Anuncia rutas aprendidas
- **Ejemplo:** Grandes proveedores de Internet

## Autonomous System Numbers (ASN)

### Rango de ASN

| Rango | Tipo | Estado |
|-------|------|--------|
| 1-64511 | ASN públicos | Asignados por RIRs |
| 64512-65534 | ASN privados | Uso interno |
| 65535 | Reservado | No usar |
| 4200000000-4294967294 | ASN de 32 bits | Nuevos |

### Asignación de ASN

#### Por RIR (Regional Internet Registry)

| RIR | Región | ASN Range |
|-----|--------|-----------|
| ARIN | Norteamérica | 1-64511, 4-byte |
| RIPE | Europa/Oriente Medio | 1-64511, 4-byte |
| APNIC | Asia/Pacífico | 1-64511, 4-byte |
| LACNIC | Latinoamérica | 1-64511, 4-byte |
| AFRINIC | África | 1-64511, 4-byte |

#### Requisitos para ASN

- **Justificación:** Necesidad técnica
- **Infraestructura:** Múltiples conexiones
- **Documentación:** Políticas de enrutamiento
- **Contacto:** Información actualizada

### ASN Privados

Los ASN privados (64512-65534) se usan para:

- **iBGP interno:** Conexiones dentro de un AS
- **VPN MPLS:** Customer VPNs
- **Testing:** Laboratorios y pruebas

**Importante:** No se anuncian en Internet global.

## BGP (Border Gateway Protocol)

### ¿Qué es BGP?

BGP es el protocolo estándar para enrutamiento entre AS. Es un protocolo de vector de distancia que usa TCP como transporte.

**Características principales:**
- **Versión actual:** BGP-4 (RFC 4271)
- **Puerto:** TCP 179
- **Confiabilidad:** Usa TCP para entrega
- **Escalabilidad:** Maneja cientos de miles de rutas

### Tipos de BGP

#### eBGP (External BGP)
- **Uso:** Entre AS diferentes
- **Next-hop:** Cambia al router eBGP
- **AS Path:** Añade ASN propio
- **Políticas:** Más restrictivas

#### iBGP (Internal BGP)
- **Uso:** Dentro del mismo AS
- **Next-hop:** Mantiene next-hop original
- **AS Path:** No modifica
- **Políticas:** Más flexibles

### Mensajes BGP

| Tipo | Descripción | Frecuencia |
|------|-------------|------------|
| OPEN | Establece sesión BGP | Una vez |
| UPDATE | Anuncia/revoca rutas | Periódico |
| KEEPALIVE | Mantiene sesión | Cada 60s |
| NOTIFICATION | Error/cierre | Cuando ocurre |

## Configuración BGP

### Configuración Básica Cisco IOS

```cisco
! Configurar ASN y router ID
router bgp 65001
 bgp router-id 192.168.1.1

! Configurar vecino eBGP
 neighbor 203.0.113.1 remote-as 65002
 neighbor 203.0.113.1 description Upstream Provider

! Configurar vecino iBGP
 neighbor 192.168.2.1 remote-as 65001
 neighbor 192.168.2.1 update-source Loopback0

! Anunciar redes
 network 192.168.1.0 mask 255.255.255.0
 network 203.0.113.0 mask 255.255.255.0
```

### Configuración Juniper JunOS

```junos
# Configurar BGP
set routing-options autonomous-system 65001
set routing-options router-id 192.168.1.1

# Grupo eBGP
set protocols bgp group upstream type external
set protocols bgp group upstream peer-as 65002
set protocols bgp group upstream neighbor 203.0.113.1

# Grupo iBGP
set protocols bgp group internal type internal
set protocols bgp group internal local-address 192.168.1.1
set protocols bgp group internal neighbor 192.168.2.1

# Políticas
set policy-options policy-statement export-routes term 1 from protocol direct
set policy-options policy-statement export-routes term 1 then accept
```

### Configuración en Linux (BIRD)

```bird
# Configuración BIRD BGP

router id 192.168.1.1;

protocol bgp upstream {
    local as 65001;
    neighbor 203.0.113.1 as 65002;
    export filter { accept; };
    import filter { accept; };
}

protocol bgp internal {
    local as 65001;
    neighbor 192.168.2.1;
    export filter { accept; };
    import filter { accept; };
}
```

## Atributos BGP

### Atributos Well-Known Mandatory

| Atributo | Descripción | Uso |
|----------|-------------|-----|
| AS_PATH | Lista de AS transitados | Previene loops |
| NEXT_HOP | IP del próximo salto | Enrutamiento |
| ORIGIN | Cómo se aprendió la ruta | Preferencia |

### Atributos Well-Known Discretionary

| Atributo | Descripción | Uso |
|----------|-------------|-----|
| LOCAL_PREF | Preferencia local | iBGP |
| ATOMIC_AGGREGATE | Agregación realizada | Información |
| AGGREGATOR | Router que agregó | Trazabilidad |

### Atributos Optional

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| MULTI_EXIT_DISC (MED) | Optional Non-transitive | Preferencia de entrada |
| COMMUNITY | Optional Transitive | Etiquetado de rutas |
| ORIGINATOR_ID | Optional Non-transitive | iBGP loop prevention |
| CLUSTER_LIST | Optional Non-transitive | Route reflection |

## Políticas BGP

### Route Maps

```cisco
! Route map para filtrado
route-map FILTER-OUT permit 10
 match ip address prefix-list MY-PREFIXES
 set community 65001:100

route-map FILTER-IN deny 10
 match as-path 666
route-map FILTER-IN permit 20

! Aplicar a vecino
neighbor 203.0.113.1 route-map FILTER-IN in
neighbor 203.0.113.1 route-map FILTER-OUT out
```

### Prefix Lists

```cisco
! Lista de prefijos
ip prefix-list MY-NETWORKS permit 192.168.0.0/16
ip prefix-list MY-NETWORKS permit 203.0.113.0/24

! Aplicar
neighbor 203.0.113.1 prefix-list MY-NETWORKS out
```

### AS Path Filtering

```cisco
! Filtrar AS específicos
ip as-path access-list 10 deny _666_
ip as-path access-list 10 permit .*

! Aplicar
neighbor 203.0.113.1 filter-list 10 in
```

## Comunidad BGP

### Uso de Communities

Las comunidades BGP permiten etiquetar rutas para aplicar políticas específicas.

**Sintaxis:** `ASN:valor`

#### Communities Comunes

| Comunidad | Descripción | Uso |
|-----------|-------------|-----|
| 65001:100 | Customer routes | Rutas de cliente |
| 65001:200 | Peer routes | Rutas de peer |
| 65001:666 | Blackhole | Rutas a blackhole |
| 65535:65281 | No export | No exportar |
| 65535:65282 | No advertise | No anunciar |

### Configuración

```cisco
! Set community
route-map SET-COMMUNITY permit 10
 set community 65001:100

! Filtrar por community
ip community-list 1 permit 65001:100

route-map FILTER-COMMUNITY permit 10
 match community 1
```

## Troubleshooting BGP

### Comandos de Diagnóstico

#### Ver estado BGP
```cisco
show ip bgp summary
show ip bgp neighbors
show ip bgp
```

#### Ver rutas específicas
```cisco
show ip bgp 192.168.1.0
show ip bgp regexp _65001_
```

#### Ver atributos
```cisco
show ip bgp 192.168.1.0 | include Origin|AS Path|Next Hop
```

### Problemas Comunes

#### 1. Sesión no estable
```
* BGP neighbor state = Idle
```
**Posibles causas:**
- Conectividad IP rota
- ACL bloqueando puerto 179
- Router ID duplicado

#### 2. Rutas no anunciadas
```
* No routes received
```
**Posibles causas:**
- Filtro de entrada muy restrictivo
- Network statement faltante
- Next-hop unreachable

#### 3. Rutas no instaladas
```
* Best path not selected
```
**Posibles causas:**
- LOCAL_PREF más bajo
- AS_PATH más largo
- MED más alto

### Herramientas de Troubleshooting

#### BGP Looking Glass
- **Route Views:** bgp.he.net
- **Traceroute con AS:** traceroute -A

#### Scripts de Monitoreo

```bash
#!/bin/bash
# Verificar estado BGP

BGP_NEIGHBOR="203.0.113.1"

# Ver estado
STATE=$(vtysh -c "show ip bgp summary" | grep $BGP_NEIGHBOR | awk '{print $10}')

if [ "$STATE" != "Established" ]; then
    echo "ALERTA: BGP con $BGP_NEIGHBOR en estado $STATE"
    # Enviar email o alerta
else
    echo "OK: BGP establecido con $BGP_NEIGHBOR"
fi
```

## BGP en la Práctica

### Peering

#### Internet Exchange Points (IXP)
Los IXP permiten peering directo entre AS:

- **AMS-IX:** Amsterdam
- **DE-CIX:** Frankfurt
- **LINX:** London
- **Equinix:** Global

#### Configuración de Peering

```cisco
! Peering en IXP
router bgp 65001
 neighbor 198.32.1.1 remote-as 65002
 neighbor 198.32.1.1 description Peer at IXP
 neighbor 198.32.1.1 route-map PEER-IN in
 neighbor 198.32.1.1 route-map PEER-OUT out
```

### Route Aggregation

La agregación reduce el tamaño de la tabla de rutas global:

```cisco
! Agregar rutas
router bgp 65001
 aggregate-address 192.168.0.0 255.255.0.0 summary-only
```

### BGP FlowSpec

BGP FlowSpec permite mitigar ataques DDoS vía BGP:

```cisco
! FlowSpec route
router bgp 65001
 address-family ipv4 flowspec
  neighbor 203.0.113.1 activate
```

## Seguridad BGP

### Amenazas BGP

1. **Route hijacking:** Anunciar rutas no propias
2. **Blackholing:** Enviar tráfico a null
3. **Prefix deaggregation:** Anunciar subprefijos
4. **AS path poisoning:** Manipular AS_PATH

### Medidas de Protección

#### RPKI (Resource Public Key Infrastructure)

RPKI permite verificar la validez de anuncios de rutas:

```cisco
! Configurar RPKI
router bgp 65001
 rpki server tcp 192.0.2.1 port 323 refresh 600
 rpki cache 192.0.2.1
```

#### BGPsec

BGPsec añade firmas criptográficas a anuncios BGP para prevenir manipulación.

### Mejores Prácticas de Seguridad

1. **Filtrado estricto:** Solo aceptar rutas válidas
2. **IRR validation:** Verificar en bases de datos de rutas
3. **Monitoring:** Alertas de cambios de rutas
4. **Diversidad:** Múltiples upstream providers

## Referencias

- RFC 4271: A Border Gateway Protocol 4 (BGP-4)
- RFC 1997: BGP Communities Attribute
- RFC 6793: BGP Support for Four-Octet Autonomous System (AS) Number Space
- RFC 6811: BGP Prefix Origin Validation
- RFC 8205: BGPsec Protocol Specification