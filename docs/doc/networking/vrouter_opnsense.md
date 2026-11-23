---
title: "OPNsense (vRouter/cortafuegos virtual)"
description: "Despliegue virtualizado, ajustes de VirtIO, segmentación VLAN, alta disponibilidad CARP y operación de OPNsense."
tags: ['networking', 'cybersecurity', 'vrouter']
updated: 2026-11-23
difficulty: intermediate
estimated_time: 4 min
category: Redes
status: published
last_reviewed: 2026-11-23
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# OPNsense (vRouter/cortafuegos virtual)

## El problema

Montar un cortafuegos perimetral con `nftables` a mano funciona bien hasta que necesitas segmentar diez VLANs, gestionar VPNs WireGuard/IPsec, auditar reglas en equipo y aplicar actualizaciones sin cortar la red. **OPNsense** (basado en FreeBSD) resuelve esa capa con una interfaz web clara, actualizaciones frecuentes bien empaquetadas y soporte nativo de alta disponibilidad mediante CARP.

## Cuándo elegir OPNsense

- Necesitas una interfaz gráfica clara y auditable para la operación diaria del cortafuegos.
- Quieres segmentación por VLAN, VPN (WireGuard/OpenVPN/IPsec), DNS local (Unbound) y proxy/IDS opcional en un mismo appliance.
- Buscas un ciclo de actualizaciones predecible (dos ramas mayores al año) sin atarte a hardware propietario.

Si necesitas enrutamiento puro de operador (BGP complejo, MPLS, consumo mínimo), revisa [MikroTik CHR](vrouter_mikrotik_chr.md).

## Despliegue recomendado en hipervisor (Proxmox / KVM)

- **vNIC**: mínimo 2 interfaces `virtio` (`vtnet0` para WAN y `vtnet1` para LAN; una tercera interfaz dedicada `SYNC` si montas alta disponibilidad).
- **CPU y RAM**: 2 vCPU mínimo, 4 GB de RAM (mínimo oficial 3 GB; 8 GB+ si activas Suricata IDS/IPS o Zenarmor).
- **Disco**: 40 GB+ SSD (recomendación oficial «razonable»), idealmente sobre **ZFS** para disponer de *Boot Environments* al actualizar.

### Ajuste crítico con VirtIO en FreeBSD

Al virtualizar OPNsense sobre KVM/Proxmox con tarjetas `virtio`, los paquetes con checksum descargado en hardware suelen fallar al salir hacia otras VMs o al puente físico. En **Interfaces → Settings**, marca las tres casillas de desactivación de offload:

- **Disable hardware checksum offload**
- **Disable hardware TCP segmentation offload (TSO)**
- **Disable hardware large receive offload (LRO)**

Aplica los cambios y reinicia la VM para que tomen efecto limpio en todas las interfaces `vtnet`.

## Configuración base paso a paso

1. **Asigna interfaces** desde consola (`vtnet0` = WAN, `vtnet1` = LAN) y fija la IP de gestión LAN.
2. **Endurece el acceso**: cambia la contraseña de `root`, crea un usuario nominal, desactiva el acceso web en WAN y activa autenticación de dos factores (TOTP) en **System → Access → Servers**.
3. **Configura WAN y LAN**: bloquea redes privadas (RFC1918) y bogons en WAN (si la WAN es pública) y define el rango DHCP/DNS (Unbound) en LAN.
4. **Segmenta por VLAN**: crea interfaces en **Interfaces → Other Types → VLAN** sobre el trunk LAN y aplica reglas explícitas por VLAN (denegación por defecto entre segmentos).
5. **Revisa las reglas de firewall**: la regla *anti-lockout* evita perder acceso a la GUI en LAN; sustituye cualquier regla genérica `any any` en VLANs de servidores o IoT por reglas por puerto y destino.

## Alta disponibilidad, copias de seguridad y actualizaciones

- **Alta disponibilidad (HA)**: dos nodos OPNsense con IP virtuales **CARP** en WAN/LAN, sincronización de estados (`pfsync`) por una interfaz dedicada y replicación de configuración XMLRPC desde el primario al secundario.
- **Copia de seguridad (`config.xml`)**: exportable desde **System → Configuration → Backups** (o automatizada hacia Nextcloud/Git). Toda la configuración vive en ese único XML.
- **Actualizaciones seguras**: antes de subir de versión mayor, descarga `config.xml`, toma un snapshot de la VM en el hipervisor y verifica la consola serie por si cambia algún nombre de interfaz o plugin.

## Buenas prácticas

- Separa redes por VLAN (gestión, servidores, usuarios, invitados/IoT) y usa **Aliases** para agrupar IPs y puertos en las reglas.
- Exporta `config.xml` antes de cualquier cambio crítico y conserva copias fuera del propio cortafuegos.
- Mantén firmware y complementos al día en ventana de mantenimiento y evita instalar plugins que no operes.
- Activa el registro (*logging*) en las reglas de denegación y envía los logs por syslog a tu stack de observabilidad.

## Riesgos comunes

- Dejar reglas permisivas `any any` en VLANs internas, anulando el beneficio de segmentar.
- Olvidar desactivar *hardware checksum/TSO/LRO* en interfaces `virtio`, causando pérdidas intermitentes o conexiones TCP colgadas.
- No ajustar MTU/MSS en túneles PPPoE, WireGuard o IPsec (provoca páginas que cargan a medias).
- No documentar redirecciones NAT ni comprobar si un plugin de terceros bloquea una actualización mayor.

## Lista de comprobación operativa

- ¿WAN y LAN están en interfaces distintas sin solapamiento y sin acceso de gestión desde WAN?
- ¿Están desactivados checksum offload, TSO y LRO en entornos VirtIO?
- ¿Existe copia reciente y probada de `config.xml` fuera del firewall?
- ¿Se monitorizan latencia de gateway, pérdida de paquetes, estado de CARP y tabla de estados?
- ¿Hay procedimiento de reversión (snapshot o *Boot Environment* ZFS)?

## Referencias

- [OPNsense: requisitos de hardware](https://docs.opnsense.org/manual/hardware.html)
- [OPNsense: autenticación de dos factores](https://docs.opnsense.org/manual/how-tos/two_factor.html)
- [OPNsense: alta disponibilidad (CARP)](https://docs.opnsense.org/manual/hacarp.html)
