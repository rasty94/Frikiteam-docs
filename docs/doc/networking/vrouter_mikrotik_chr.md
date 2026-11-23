---
title: "MikroTik CHR (enrutador en la nube)"
description: "Despliegue, licencias, configuración base en RouterOS v7 y endurecimiento de MikroTik CHR para enrutamiento L3 y laboratorios."
tags: ['networking', 'vrouter']
updated: 2026-11-23
difficulty: advanced
estimated_time: 4 min
category: Redes
status: published
last_reviewed: 2026-11-23
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
  - "Conceptos de enrutamiento dinámico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# MikroTik CHR (enrutador en la nube)

## El problema

Cuando necesitas un router virtual con enrutamiento L3 avanzado (BGP, OSPF, VRF, WireGuard o MPLS) en Proxmox, KVM o un proveedor cloud, muchas opciones se disparan en licencia o exigen máquinas sobredimensionadas. **MikroTik Cloud Hosted Router (CHR)** ejecuta RouterOS 64-bit pensado específicamente para hipervisores: arranca en segundos, consume poca RAM y ofrece el mismo conjunto de funciones de red que un router físico de MikroTik.

## Cuándo elegir MikroTik CHR

- Escenarios ISP/WISP, laboratorios de operador o interconexión multi-sede con BGP/OSPF.
- Necesidad de políticas de enrutamiento avanzadas (VRF, Policy-Based Routing, túneles GRE/WireGuard/IPsec).
- Equipos que ya operan RouterOS y quieren reproducir topologías en virtualizado con bajo consumo.

Si priorizas una interfaz web guiada orientada a cortafuegos perimetral y segmentación de oficina, suele encajar mejor [OPNsense](vrouter_opnsense.md) o [pfSense](vrouter_pfsense.md).

## Despliegue recomendado y licencias

- **vNIC**: 2-4 interfaces `virtio` (o `vmxnet3` en ESXi) según topología, separando gestión si es posible.
- **CPU y RAM**: 2+ vCPU, 512 MB–2 GB de RAM (hasta 4 GB si manejas tablas BGP completas).
- **Disco**: 2-8 GB (imagen raw/qcow2 oficial de CHR; ampliar si guardas logs locales).

El modelo de licencia de CHR limita la **velocidad de subida por interfaz**, no las funcionalidades de RouterOS:

| Licencia CHR | Límite de subida por interfaz | Uso habitual |
| --- | --- | --- |
| **Free** | 1 Mbps | Laboratorios funcionales, pruebas de BGP/OSPF |
| **P1** | 1 Gbps | Perímetro de oficina, VPN concentrator, laboratorios con tráfico real |
| **P10** | 10 Gbps | Core virtualizado, enlaces troncales de alta capacidad |
| **P-Unlimited** | Sin límite de licencia | Operadores y nodos con interfaces 25G/40G+ |

## Configuración base en RouterOS v7

Tras importar el disco CHR en tu hipervisor, el usuario inicial es `admin` sin contraseña (conviene cambiarla en el primer acceso por consola). Un arranque mínimo seguro con una WAN (`ether1`) y una LAN (`ether2`):

```text
# 1. Identidad y contraseña de administración
/system/identity/set name=chr-edge-01
/user/set admin password="CAMBIA-ESTA-CLAVE-LARGA"

# 2. Direccionamiento y ruta por defecto
/ip/address/add address=203.0.113.10/24 interface=ether1 comment="WAN"
/ip/address/add address=10.10.20.1/24 interface=ether2 comment="LAN"
/ip/route/add dst-address=0.0.0.0/0 gateway=203.0.113.1

# 3. Desactivar servicios de gestión innecesarios y restringir SSH/WinBox a la LAN
/ip/service/disable telnet,ftp,www,api,api-ssl
/ip/service/set ssh address=10.10.20.0/24
/ip/service/set winbox address=10.10.20.0/24

# 4. Firewall stateful mínimo (input + forward)
/ip/firewall/filter/add chain=input connection-state=established,related action=accept
/ip/firewall/filter/add chain=input in-interface=ether2 action=accept comment="Permitir gestion LAN"
/ip/firewall/filter/add chain=input action=drop comment="Denegar resto hacia el router"

/ip/firewall/filter/add chain=forward connection-state=established,related action=accept
/ip/firewall/filter/add chain=forward connection-state=invalid action=drop
/ip/firewall/filter/add chain=forward in-interface=ether2 out-interface=ether1 action=accept
/ip/firewall/filter/add chain=forward action=drop comment="Denegar resto en forward"

# 5. NAT de salida para la LAN
/ip/firewall/nat/add chain=srcnat out-interface=ether1 action=masquerade
```

## Copias de seguridad y reversión

Conviene combinar dos tipos de copia antes de cualquier cambio o actualización de RouterOS:

```text
# Export legible en texto plano (ideal para versionar en Git y auditar diffs)
/export file=chr-edge-01-base

# Backup binario completo (solo restaurable en la misma versión/arquitectura)
/system/backup/save name=chr-edge-01-bin
```

Además, en el hipervisor toma un snapshot de la VM antes de saltar de rama de RouterOS.

## Buenas prácticas

- Separa el plano de gestión del plano de datos (VLAN o VRF dedicada) y limita WinBox/SSH por dirección origen.
- Documenta filtros de rutas BGP/OSPF y evita anunciar prefijos sin lista explícita.
- Evalúa **FastTrack** con cautela: acelera mucho el reenvío, pero salta colas simples, IPsec y parte del marcado de paquetes.
- Fija una versión estable de RouterOS en tu parque y valida las actualizaciones en un CHR clónico antes de tocar producción.

## Riesgos comunes

- Dejar servicios de gestión (`www`, `api`, `winbox`, `ssh`) expuestos en la interfaz WAN.
- Olvidar que la licencia **Free** recorta cada interfaz a 1 Mbps de subida y diagnosticarlo como un fallo de red del hipervisor.
- Hacer cambios de firewall sin activar **Safe Mode** (`Ctrl+X` en consola), perdiendo el acceso remoto en remoto.

## Lista de comprobación operativa

- ¿La licencia CHR cubre el ancho de banda real de subida por interfaz?
- ¿Están desactivados `telnet`, `ftp`, `www` y restringidos `ssh`/`winbox` a la red de gestión?
- ¿Existen reglas de firewall `input`/`forward` con denegación por defecto y filtros anti-spoofing/bogons?
- ¿Se monitoriza CPU, paquetes/s, colas y tráfico por interfaz (SNMP o syslog remoto)?
- ¿Hay export en texto plano y procedimiento de reversión probado?

## Referencias

- [MikroTik: Cloud Hosted Router (CHR)](https://help.mikrotik.com/docs/spaces/ROS/pages/18350234/Cloud+Hosted+Router+CHR)
- [MikroTik: Securing your router (RouterOS)](https://help.mikrotik.com/docs/spaces/ROS/pages/328353/Securing+your+router)
