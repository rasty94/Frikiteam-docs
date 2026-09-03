---
title: "Proxmox — Redes definidas por software (SDN)"
description: "Zonas simple, VLAN, QinQ, VXLAN y EVPN en Proxmox VE: VNets y subredes, el ciclo de aplicar la configuración, IPAM, requisitos de MTU en overlays, cortafuegos y diagnóstico de conectividad entre nodos."
keywords: "proxmox, sdn, vxlan, evpn, vlan, qinq, vnet, ipam, mtu, overlay, frr, bgp, redes definidas por software"
tags: ['proxmox', 'networking', 'virtualization']
updated: 2026-09-03
difficulty: advanced
estimated_time: 25 min
category: Virtualización
status: published
last_reviewed: 2026-09-03
prerequisites:
  - "[Proxmox VE](proxmox_base.md)"
  - "Cluster con quórum y red de gestión funcionando"
  - "VLAN, bridges de Linux y enrutado IP"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Proxmox — Redes definidas por software (SDN)

## El problema

Un bridge de Linux en Proxmox vive en `/etc/network/interfaces`, que es un fichero **local de cada nodo**. Añadir un segmento nuevo a un cluster de cinco máquinas significa editar cinco ficheros a mano y que los cinco queden idénticos. El día que uno se escribe con la VLAN 130 en vez de la 30, la VM funciona perfectamente… hasta que migra a ese nodo y se queda sin red, normalmente un viernes.

El SDN mueve esa definición al sistema de ficheros del cluster: la declaras una vez, Proxmox la replica y genera la configuración de red en todos los nodos. No sustituye al switch físico ni hace la red más rápida; lo que hace es que un segmento sea un objeto del cluster en lugar de un acuerdo tácito entre cinco ficheros de texto.

!!! note "Comprueba tu versión antes de seguir"
    El SDN nació como funcionalidad experimental y maduró a lo largo de varias versiones mayores: cambiaron el paquete que lo provee, los tipos de zona disponibles y la existencia de DHCP integrado. Mira qué tienes con `pveversion -v | grep -E 'pve-manager|libpve-network'` antes de copiar nada de aquí. Si el menú **Datacenter → SDN** no aparece o falta `libpve-network-perl`, tu versión es anterior a la integración y conviene actualizar en lugar de forzarlo a mano. Esta página describe el comportamiento estable y ampliamente documentado; los detalles de tu versión concreta, en la documentación oficial enlazada al final.

## 📋 Tabla de Contenidos

- [Qué aporta el SDN frente a un bridge de Linux](#que-aporta-el-sdn-frente-a-un-bridge-de-linux)
- [Tipos de zona](#tipos-de-zona)
- [VNets y subredes](#vnets-y-subredes)
- [El ciclo de aplicar la configuración](#el-ciclo-de-aplicar-la-configuracion)
- [IPAM](#ipam)
- [Ejemplo: zona VLAN](#ejemplo-zona-vlan)
- [Ejemplo: zona VXLAN entre nodos](#ejemplo-zona-vxlan-entre-nodos)
- [MTU en redes overlay](#mtu-en-redes-overlay)
- [Cortafuegos y SDN](#cortafuegos-y-sdn)
- [EVPN y enrutado entre VNets](#evpn-y-enrutado-entre-vnets)
- [Diagnóstico de conectividad entre nodos](#diagnostico-de-conectividad-entre-nodos)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué aporta el SDN frente a un bridge de Linux

| | Bridge clásico | SDN |
|---|---|---|
| Dónde vive la definición | `/etc/network/interfaces`, por nodo | `/etc/pve/sdn/`, replicado en el cluster |
| Alta de un segmento nuevo | Editar cada nodo | Declararlo una vez y aplicar |
| Coherencia entre nodos | Responsabilidad tuya | Garantizada por la configuración generada |
| Segmento que cruza nodos | Depende del switch (VLAN en el trunk) | Posible sin tocar el switch (VXLAN) |
| Direccionamiento | Externo a Proxmox | Subredes e IPAM dentro del cluster |
| Vuelta atrás | Restaurar el fichero y reiniciar la red | Volver a la configuración anterior y aplicar |

Lo que **no** aporta: rendimiento. Un bridge plano sobre una VLAN del switch será siempre el camino más corto. El SDN añade capas —encapsulado en VXLAN, un demonio de enrutado en EVPN— y cada capa es algo más que puede fallar; úsalo cuando el problema sea de gestión o de topología, no para ir más rápido. La jerarquía es corta: una **zona** define el transporte, contiene **VNets** (los bridges a los que enganchas las VMs) y cada VNet puede llevar **subredes**, cuyo direccionamiento gestiona el **IPAM**. Solo EVPN añade una pieza más, el **controlador**.

## Tipos de zona

La zona define **cómo** se transporta el tráfico. Es la decisión importante: cambiarla después implica rehacer las VNets.

| Zona | Qué hace | Cuándo usarla | Lo que te va a costar |
|---|---|---|---|
| **Simple** | Bridge aislado y local a cada nodo, con enrutado y NAT desde el propio host | Laboratorios, redes internas de un único nodo, entornos de prueba | No hay capa 2 entre nodos: dos VMs en nodos distintos no se ven |
| **VLAN** | Etiqueta 802.1Q sobre un bridge VLAN-aware | Ya tienes VLANs en el switch y quieres gestionarlas desde Proxmox | El trunk del switch debe llevar cada VLAN; sin eso no hay magia |
| **QinQ** | Doble etiqueta 802.1ad: una de servicio y la del cliente | Multi-tenant en el que cada inquilino trae su propio plan de VLANs | Soporte real en switch y NIC, y 4 bytes más de cabecera |
| **VXLAN** | Túnel de capa 2 sobre UDP entre los nodos | Un segmento que cruce nodos sin tocar la red física | MTU (ver más abajo) y tráfico de difusión replicado a cada peer |
| **EVPN** | VXLAN con BGP como plano de control, más enrutado L3 entre VNets | Varias subredes que deben enrutarse entre sí y salir al exterior | FRR, un ASN, nodos de salida y depuración con `vtysh` |

Regla de decisión rápida: si el switch ya sabe hacerlo, **VLAN**. Si necesitas un segmento que la red física no conoce, **VXLAN**. Si además necesitas que varias de esas redes se enruten entre sí con una puerta de enlace que sobreviva a las migraciones, **EVPN**. **Simple** para el portátil y el laboratorio. **QinQ** solo si de verdad tienes el problema que resuelve.

## VNets y subredes

Una **VNet** es el bridge al que enganchas la VM. Pertenece a una zona y hereda su transporte; en zonas simple no es más que un bridge:

- En zonas VLAN y QinQ, la VNet lleva la **etiqueta** (`tag`).
- En zonas VXLAN y EVPN, la VNet lleva el **VNI**, el identificador del segmento dentro del túnel.

Una **subred** es un CIDR asociado a una VNet, opcionalmente con puerta de enlace, SNAT y rangos para DHCP. Aquí conviene ser honesto sobre qué hace realmente:

!!! warning "Una subred no crea la puerta de enlace por arte de magia"
    En zonas **simple** y **EVPN**, Proxmox sí levanta la puerta de enlace declarada en la subred (en EVPN, además, como *anycast* en todos los nodos). En zonas **VLAN**, **QinQ** y **VXLAN** el enrutado sigue viviendo fuera: en tu router o cortafuegos. Ahí la subred sirve para IPAM y documentación, no para dar salida. Declarar `10.100.0.1` como gateway en una zona VLAN no hace que nadie responda a esa IP.

Toda la configuración es texto plano bajo `/etc/pve/sdn/` —`zones.cfg`, `vnets.cfg`, `subnets.cfg`, `controllers.cfg`, `ipams.cfg` y `dns.cfg`— replicado por el cluster. Al ser ficheros de `/etc/pve`, entran en el backup de configuración y se pueden versionar con [Ansible](../ansible/ansible_base.md) igual que cualquier otra cosa.

## El ciclo de aplicar la configuración

Este es el punto en el que se pierde más tiempo, así que va primero: **el SDN tiene dos estados**. Lo que editas es la configuración *pendiente*; lo que está funcionando es la configuración *aplicada*. Nada de lo que toques surte efecto hasta que pulsas **Apply**.

```mermaid
flowchart LR
    A["Editas zona / VNet / subred"] --> B["/etc/pve/sdn/*.cfg<br/><i>pendiente</i>"]
    B -->|Apply| C["/etc/pve/sdn/.running-config"]
    C --> D["/etc/network/interfaces.d/sdn<br/>en cada nodo"]
    D --> E[Interfaces recargadas]
```

Aplicar hace tres cosas en cada nodo: escribe `/etc/network/interfaces.d/sdn`, recarga la red y deja constancia en el registro de tareas. Desde la interfaz es **Datacenter → SDN → Apply**; desde la línea de comandos, y comprobando el resultado:

```bash
pvesh get /cluster/sdn          # la configuración tal y como está funcionando
pvesh set /cluster/sdn          # aplicarla en todo el cluster

cat /etc/network/interfaces.d/sdn
ip -br link | grep -E 'vnet|vxlan|vrf'
```

!!! danger "Si el fichero generado está vacío o no existe"
    Significa que la configuración nunca se aplicó en ese nodo, no que la zona esté mal. Causas habituales: el cluster estaba sin quórum en ese momento (`/etc/pve` en solo lectura), el nodo estaba apagado durante el *apply*, o falta `ifupdown2`, que es lo que permite recargar la red sin reiniciar. Recupera el quórum, comprueba `pvecm status` y vuelve a aplicar.

## IPAM

El IPAM lleva la cuenta de qué IP está asignada a qué. Proxmox trae uno interno y sabe hablar con dos externos:

| Backend | Dónde vive | Cuándo elegirlo |
|---|---|---|
| **PVE** | Dentro del cluster, sin dependencias | Por defecto, y suficiente si Proxmox es el único que reparte direcciones |
| **phpIPAM** | Servidor externo, vía API | Ya lo usas como fuente de verdad para toda la red, no solo la virtual |
| **NetBox** | Servidor externo, vía API | Igual, con inventario y documentación de red integrados |

Con un backend externo, Proxmox **consulta y reserva** en él en lugar de decidir por su cuenta: el objetivo es que no haya dos sitios repartiendo las mismas IPs. Requiere un token de API con permisos de escritura y conectividad desde los nodos; si la API no responde, las operaciones que necesiten una dirección fallan.

En zonas **simple** puede además ofrecer DHCP a las VMs a partir de los rangos de la subred, apoyándose en `dnsmasq`. Es la forma cómoda de tener un laboratorio autocontenido. Comprueba en la documentación de tu versión qué tipos de zona lo soportan, porque es de las partes que más han cambiado.

## Ejemplo: zona VLAN

El escenario más común y el más aburrido, que es un elogio. Requisito previo: el bridge físico debe ser **VLAN-aware**.

```bash
# /etc/network/interfaces — en cada nodo
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

Después, la zona y la VNet. Se pueden crear desde **Datacenter → SDN**; así queda la configuración resultante:

```ini
# /etc/pve/sdn/zones.cfg
vlan: lan
	bridge vmbr0
	ipam pve

# /etc/pve/sdn/vnets.cfg
vnet: srv30
	zone lan
	tag 30
	alias Servidores internos
```

Aplicar y enganchar una VM a la VNet, que a partir de ahí se usa como cualquier bridge:

```bash
pvesh set /cluster/sdn
qm set 100 --net0 virtio,bridge=srv30
```

La VM no ve ninguna etiqueta: envía tramas sin marcar y el bridge le pone la 30 al salir. Si no hay conectividad, el sospechoso número uno es el **trunk del switch físico**, que tiene que llevar la VLAN 30 hasta el puerto de ese nodo. El SDN no configura tu switch.

## Ejemplo: zona VXLAN entre nodos

Aquí el segmento existe aunque la red física no sepa nada de él. Tres nodos con IPs `10.10.10.1`, `.2` y `.3` en una red dedicada al tráfico de VMs:

```ini
# /etc/pve/sdn/zones.cfg
vxlan: overlay
	peers 10.10.10.1,10.10.10.2,10.10.10.3
	ipam pve
	mtu 1450

# /etc/pve/sdn/vnets.cfg
vnet: app100
	zone overlay
	tag 100
	alias Red interna de aplicaciones
```

Tres detalles que deciden si esto funciona:

1. **Todos los nodos van en `peers`, incluido el propio.** La lista es idéntica en todo el cluster; Proxmox descarta su propia dirección al generar la configuración.
2. **Las IPs de `peers` eligen por dónde va el tráfico.** Si pones las de gestión, el tráfico de las VMs compartirá enlace con corosync, que es exactamente lo que no quieres. Usa las de la red dedicada.
3. **El `tag` es el VNI**, no una VLAN. Es el identificador del segmento dentro del túnel y debe ser único en la zona.

Entre nodos hace falta conectividad IP y el puerto **UDP 4789** abierto en ambos sentidos. Sin plano de control, la difusión y el tráfico a destinos desconocidos se replican por unicast a cada peer: con muchos nodos, el coste crece rápido y ahí es donde EVPN empieza a compensar.

## MTU en redes overlay

Si algo va a fallar en un overlay, es esto. Encapsular en VXLAN añade **50 bytes** a cada trama sobre un underlay IPv4 —cabecera Ethernet exterior (14), IP (20), UDP (8) y VXLAN (8)—, y **70 bytes** si el underlay es IPv6. Una trama de invitado de 1500 bytes sale al cable como un paquete de 1550.

Si el switch físico está en 1500, ese paquete no cabe. Y no se fragmenta: el paquete exterior lleva el bit *don't fragment*, así que **se descarta en silencio**. El síntoma no es "no hay red", que sería fácil:

- El `ping` y el *handshake* de TCP funcionan: son paquetes pequeños.
- `ssh` conecta, y se cuelga en cuanto se transfiere algo de volumen.
- Una página web carga a medias; una copia de ficheros se queda a cero.
- El descubrimiento de MTU de camino (PMTUD) no te rescata, porque el ICMP que avisa se genera en el underlay y muchos cortafuegos lo filtran.

Ese cuadro —"va lento y a veces falla"— es casi siempre MTU. Las dos salidas:

| Underlay | MTU máximo de la VNet | Qué hacer |
|---|---|---|
| 1500 (estándar) | 1450 | Fijar 1450 en la zona **y** en los invitados |
| 9000 (jumbo) | 8950 | Jumbo de extremo a extremo y dejar la MTU por defecto |

La opción buena es **jumbo frames en el underlay**: NICs, bonds, bridges y puertos del switch a 9000, y la VNet queda en 1500 sin que nadie note nada. La opción de emergencia es bajar la MTU del invitado a 1450, que funciona sobre un underlay de 1500 pero exige que los invitados hagan caso: por DHCP (opción 26) o a mano en cada VM. Un solo invitado con 1500 reproduce el problema entero.

Comprueba el camino real con un paquete que no se pueda fragmentar, antes de dar la configuración por buena:

```bash
ping -M do -s 8972 10.10.10.2   # 9000 - 20 (IP) - 8 (ICMP): si responde, hay jumbo de verdad
ping -M do -s 1472 10.10.10.2   # 1500 - 28: debe responder siempre
```

!!! warning "La MTU es del camino entero, no de la interfaz"
    Un solo eslabón a 1500 —un puerto de switch olvidado, un enlace entre armarios, un router intermedio, una interfaz del bond— convierte todo el trayecto en 1500. La prueba con `ping -M do` es la única forma fiable de saberlo: `ip link` te dice lo que has configurado, no lo que el cable transporta.

## Cortafuegos y SDN

El cortafuegos de Proxmox actúa sobre la interfaz de la VM, y le da igual si el bridge lo creó el SDN o `/etc/network/interfaces`. Lo que cambia es lo que hay que dejar pasar **entre los nodos**:

- **UDP 4789** para el tráfico VXLAN encapsulado.
- **TCP 179** entre los nodos si usas EVPN, para las sesiones BGP.
- Los puertos habituales del cluster, que ya deberían estar contemplados.

El cortafuegos ve el flujo UDP exterior, no las tramas que van dentro. Filtrar tráfico entre dos VMs del mismo segmento se hace en la interfaz de la VM, nunca a nivel de nodo.

!!! danger "Los tres interruptores"
    El cortafuegos se habilita en **Datacenter**, en el **nodo** y en la **VM**, y los tres tienen que estar activos. Con el de Datacenter apagado no se aplica nada, por muchas reglas que tengas escritas en la VM. Es el motivo más frecuente de "las reglas no hacen nada", y también de dejarse un segmento abierto creyendo que está cerrado.

El aislamiento entre VNets de una misma zona es de capa 2: lo dan la etiqueta o el VNI, no las reglas. Pero en cuanto enrutas entre ellas —con EVPN o con un router externo— ese aislamiento desaparece y hace falta política explícita. Los *IPSets* y los grupos de seguridad a nivel de Datacenter evitan repetir la misma regla en veinte máquinas; ver [seguridad en Proxmox](proxmox_base.md#seguridad).

## EVPN y enrutado entre VNets

EVPN añade a VXLAN un plano de control basado en BGP: los nodos se anuncian entre sí qué MAC e IP tienen detrás, en lugar de inundar la red para averiguarlo. Necesita un **controlador** además de la zona.

```ini
# /etc/pve/sdn/controllers.cfg
evpn: ctrl1
	asn 65000
	peers 10.10.10.1,10.10.10.2,10.10.10.3

# /etc/pve/sdn/zones.cfg
evpn: tenants
	controller ctrl1
	vrf-vxlan 10000
	exit-nodes pve1,pve2
	ipam pve
	mtu 1450
```

Cada VNet de la zona lleva su subred con puerta de enlace, y esa puerta de enlace se levanta como **anycast**: la misma IP y la misma MAC en todos los nodos, de modo que una VM que migra sigue hablando con su gateway sin enterarse de nada. Ese es el motivo real para usar EVPN, más que el ahorro de inundación. Los **exit nodes** son los nodos por los que el tráfico sale al exterior: declara al menos dos si la salida importa, porque con uno solo apagarlo para mantenimiento deja sin Internet a toda la zona.

Por debajo hay FRR (`frr.service`), y la depuración no pasa por la interfaz web:

```bash
systemctl status frr
vtysh -c 'show bgp l2vpn evpn summary'   # sesiones BGP entre nodos
vtysh -c 'show evpn vni'                 # VNIs conocidos y su VRF
vtysh -c 'show evpn mac vni all'         # MACs aprendidas por el plano de control
```

!!! note "EVPN es la parte cara"
    Da por hecho un underlay IP estable entre nodos, sesiones BGP funcionando y alguien que sepa leer una tabla de rutas cuando algo falle. Si lo único que necesitas es un segmento que cruce nodos, una zona **VXLAN** hace ese trabajo con una fracción de las piezas móviles. EVPN empieza a compensar cuando hay varias subredes que enrutar entre sí, muchos nodos, o la puerta de enlace anycast es un requisito.

## Diagnóstico de conectividad entre nodos

En orden, de abajo hacia arriba. La mayoría de los problemas se cierran en los dos primeros pasos:

```bash
# 1. ¿Se ven los nodos, y aguanta la MTU del camino?
ping -c3 10.10.10.2
ping -M do -s 8972 10.10.10.2

# 2. ¿Está aplicada la configuración en ESTE nodo?
cat /etc/pve/sdn/.running-config
cat /etc/network/interfaces.d/sdn

# 3. ¿Existen las interfaces y con qué parámetros?
ip -br link | grep -E 'vnet|vxlan'
ip -d link show vxlan_app100     # VNI, puerto UDP, MTU y peers reales

# 4. ¿Qué sabe el túnel, qué sale por el cable y qué dijo el último apply?
bridge fdb show dev vxlan_app100
bridge vlan show                 # en zonas VLAN, etiquetas por puerto
tcpdump -ni eno1 udp port 4789
journalctl -u pvedaemon -u pveproxy --since '30 min ago'
```

Si `tcpdump` muestra paquetes saliendo pero el destino no ve nada, el problema está en la red física o en un cortafuegos intermedio, no en Proxmox. Si no sale nada, la interfaz no está encapsulando: vuelve al paso 2.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| Los cambios no tienen ningún efecto | Configuración pendiente sin aplicar | **Apply**, o `pvesh set /cluster/sdn` |
| Un nodo se queda sin las interfaces | Estaba apagado o sin quórum al aplicar | `pvecm status` y volver a aplicar |
| Ping bien, transferencias colgadas | MTU del underlay insuficiente | Jumbo frames, o MTU 1450 en zona e invitados |
| Dos VMs no se ven en nodos distintos | Zona **simple**: no cruza nodos | Cambiar a VLAN o VXLAN |
| VLAN sin conectividad fuera del nodo | Bridge sin `bridge-vlan-aware`, o VLAN ausente del trunk | Corregir el bridge y el puerto del switch |
| VXLAN sin tráfico entre nodos | UDP 4789 bloqueado o `peers` mal | Abrir el puerto y revisar las IPs de `peers` |
| Nadie responde en la IP de la puerta de enlace | Zona VLAN/VXLAN: el gateway vive fuera | Configurarlo en el router, o usar EVPN |
| EVPN sin rutas entre VNets | Sesiones BGP caídas | `vtysh -c 'show bgp l2vpn evpn summary'` |
| Las VNets pierden la salida exterior | Único exit node apagado | Declarar al menos dos nodos de salida |
| Las reglas de cortafuegos no se aplican | Falta el interruptor de Datacenter o de nodo | Habilitarlo en los tres niveles |

## Buenas prácticas

- **Empieza por la zona más simple que resuelva el problema.** Si la VLAN llega, VLAN. Cada capa de encapsulado es una fuente de fallos más y una capa menos de visibilidad para `tcpdump`.
- **Red dedicada para el tráfico del overlay.** Compartir enlace con corosync convierte una copia de 64 GB en una pérdida de quórum; ver [migración](migration_guide.md).
- **Decide la MTU antes de crear nada** y verifícala con `ping -M do` de extremo a extremo. Cambiarla después obliga a tocar todos los invitados.
- **Aplica con todos los nodos encendidos.** Un nodo ausente durante el *apply* queda con una configuración distinta al resto, y el fallo aparece semanas después al migrar una VM.
- **Nombres de VNet que digan algo.** `srv30` o `dmz` sobreviven a un incidente a las tres de la mañana; `vnet0` y `vnet1`, no.
- **Un solo IPAM como fuente de verdad.** Proxmox repartiendo direcciones a la vez que el DHCP corporativo termina siempre igual.
- **Prueba la migración de una VM antes de dar el segmento por bueno.** Es el escenario que descubre las diferencias entre nodos, y el único que importa de verdad en un cluster.

## Referencias

- [SDN — documentación oficial de Proxmox VE](https://pve.proxmox.com/wiki/Software_Defined_Network)
- [Manual de referencia de PVE, capítulo SDN](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html)
- [RFC 7348 — VXLAN](https://datatracker.ietf.org/doc/html/rfc7348) · [RFC 8365 — EVPN como plano de control](https://datatracker.ietf.org/doc/html/rfc8365)
- [FRRouting — documentación de EVPN](https://docs.frrouting.org/en/latest/evpn.html)
- [Proxmox VE](proxmox_base.md) · [Migración de VMs y contenedores](migration_guide.md)
