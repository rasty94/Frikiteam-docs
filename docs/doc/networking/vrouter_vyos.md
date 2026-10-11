---
title: "VyOS (vRouter orientado a automatización)"
description: "VyOS como router virtual en un homelab o laboratorio: despliegue, configuración base con NAT y firewall, BGP/OSPF, commit/rollback y gestión de la configuración como código."
keywords: "vyos, vrouter, bgp, ospf, nat, firewall, commit, rollback, ansible, gitops, homelab"
tags: ['networking', 'vrouter', 'automation']
updated: 2026-10-11
difficulty: advanced
estimated_time: 16 min
category: Redes
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
  - "Conceptos de enrutamiento dinámico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# VyOS (vRouter orientado a automatización)

## El problema

Tu red crece: un par de VLAN, un túnel a otra sede, quizá un vecino BGP. El router actual se configura con clics en una interfaz web y nadie sabe qué cambió el martes pasado. Si se corrompe la máquina virtual, reconstruirla significa recordar decenas de pantallas.

VyOS ataca justo eso. Es un sistema de red basado en Linux (con FRR para el enrutamiento dinámico) cuya configuración es un árbol de texto: se edita en una sesión, se valida, se confirma con `commit` y se puede exportar como una lista de comandos `set`. Eso lo convierte en un fichero que cabe en Git, se revisa en un pull request y se vuelve a aplicar sobre una máquina limpia. El precio es una curva de aprendizaje: no hay interfaz gráfica que te guíe.

Esta página es la ficha de VyOS dentro de la serie de vRouters; el criterio de elección frente a OPNsense, pfSense y MikroTik CHR está en [vRouters: comparativa](vrouters.md).

## 📋 Tabla de Contenidos

1. [Cuándo elegir VyOS](#cuando-elegir-vyos)
2. [Despliegue recomendado](#despliegue-recomendado)
3. [Cómo se trabaja: configure, commit, save](#como-se-trabaja-configure-commit-save)
4. [Configuración base](#configuracion-base)
5. [NAT y firewall](#nat-y-firewall)
6. [Enrutamiento dinámico](#enrutamiento-dinamico)
7. [Configuración como código](#configuracion-como-codigo)
8. [Riesgos comunes](#riesgos-comunes)
9. [Troubleshooting](#troubleshooting)
10. [Buenas prácticas](#buenas-practicas)
11. [Lista de comprobación operativa](#lista-de-comprobacion-operativa)
12. [Referencias](#referencias)

## Cuándo elegir VyOS

- Necesitas BGP/OSPF con automatización declarativa
- Quieres versionar configuración de red como código
- Tu operación se apoya en canalizaciones de desarrollo y operaciones de red
- Prefieres una CLI coherente a una interfaz gráfica, y te vale un router sin paneles ni complementos de terceros

Si lo que buscas es un cortafuegos con interfaz web y listas de reglas navegables, [OPNsense](vrouter_opnsense.md) o [pfSense](vrouter_pfsense.md) te dan menos fricción. Para entornos con herramientas de MikroTik ya en marcha, mira [MikroTik CHR](vrouter_mikrotik_chr.md).

## Despliegue recomendado

- 2+ vNIC según diseño
- CPU: 2+ vCPU, RAM: 4 GB
- Disco: 10 GB+

Una guía práctica de reparto de interfaces para un laboratorio doméstico:

| Interfaz | Uso | Notas |
|---|---|---|
| `eth0` | WAN / enlace ascendente | DHCP o IP estática del proveedor |
| `eth1` | LAN o troncal de VLAN | Direccionamiento interno; subinterfaces `vif` para VLAN |
| `eth2` (opcional) | Gestión | Red de administración separada del tráfico de datos |

En Proxmox, cada vNIC se conecta a un bridge distinto (`vmbr0` hacia la WAN, `vmbr1` hacia la LAN). Usa un controlador de red paravirtualizado (VirtIO) y comprueba que el bridge de la LAN no tenga una pasarela propia compitiendo con el router. La imagen de instalación en vivo sirve para instalar en disco con el comando `install image`; las versiones rolling se descargan libremente y las estables (LTS) requieren suscripción o compilación propia (los requisitos mínimos de la documentación son 4 GB de RAM y 10 GB de disco), así que comprueba qué canal usas antes de depender de él en producción.

## Cómo se trabaja: configure, commit, save

VyOS tiene dos modos. El **operativo** (`show`, `ping`, `reboot`) no cambia nada; el de **configuración** se abre con `configure` y trabaja sobre una copia candidata:

```bash
configure
set system host-name vyos-lab
commit
save
exit
```

- `set` y `delete` modifican el candidato.
- `commit` valida y aplica los cambios al sistema en marcha.
- `save` los escribe en el fichero de arranque; sin `save`, un reinicio vuelve a la configuración anterior.
- `compare` muestra la diferencia entre lo que tienes y lo aplicado. Revísala antes de cada `commit`.
- `rollback` vuelve a una revisión anterior de la configuración confirmada.

Para cambios arriesgados, `commit-confirm` aplica la configuración y la revierte sola si no la confirmas a tiempo con `confirm`:

```bash
commit-confirm 5
confirm
```

Es el equivalente a «prueba esto, y si me quedo sin acceso, vuelve atrás»: la red de gestión te lo agradecerá la primera vez que cambies el firewall por SSH.

## Configuración base

1. Define interfaces y direccionamiento.
2. Endurece acceso SSH y cuentas administrativas.
3. Configura políticas firewall por zonas.
4. Implementa enrutamiento estático o dinámico (FRR).
5. Automatiza copias de seguridad y validaciones de configuración.

Interfaces, pasarela por defecto y DNS:

```bash
configure
set interfaces ethernet eth0 address 'dhcp'
set interfaces ethernet eth1 address '192.168.10.1/24'
set interfaces ethernet eth1 description 'LAN'
set protocols static route 0.0.0.0/0 next-hop 203.0.113.1
set system name-server '1.1.1.1'
commit
save
```

Si la WAN toma dirección por DHCP, no necesitas la ruta estática por defecto (la aprende del servidor), y `203.0.113.1` aquí es solo un ejemplo del rango de documentación. Si tienes una WAN con IP fija, sustitúyelo por la pasarela de tu proveedor.

El servicio SSH viene activado en la instalación estándar, pero conviene fijar el puerto y revisar la cuenta inicial:

```bash
set service ssh port '22'
```

Cambia la contraseña del usuario `vyos` que se crea en la instalación y, cuando puedas, sustitúyela por una clave pública (`set system login user ... authentication`; consulta la documentación de tu versión para la sintaxis exacta). Un DHCP para la LAN y un reenviador de DNS se configuran con `set service dhcp-server` y `set service dns forwarding`, en el árbol `service`; la sintaxis se modificó entre versiones, así que consulta la guía de tu versión antes de copiar.

## NAT y firewall

Una LAN privada necesita NAT de salida para llegar a Internet. Una regla de enmascaramiento sobre la interfaz WAN:

```bash
set nat source rule 100 outbound-interface name 'eth0'
set nat source rule 100 source address '192.168.10.0/24'
set nat source rule 100 translation address 'masquerade'
commit
save
```

!!! warning "La sintaxis de firewall cambió entre 1.3 y 1.4"
    VyOS 1.4 reorganizó el firewall: el árbol antiguo `firewall name <NOMBRE>` aplicado a interfaces dio paso a cadenas `firewall ipv4 input|forward|output` (y `ipv6`) con `filter` dentro, y los cambios llegaron también a NAT y a algunas opciones (por ejemplo, `outbound-interface` pasó a llevar `name` o `group`). Un ejemplo de 1.3 pegado en 1.4 no valida, y viceversa. Antes de copiar nada, ejecuta `show version` y usa la documentación de **esa** versión.

Un cortafuegos mínimo para el propio router en 1.4 (tráfico dirigido al router, cadena `input`):

```bash
set firewall ipv4 input filter default-action 'drop'
set firewall ipv4 input filter rule 10 action 'accept'
set firewall ipv4 input filter rule 10 inbound-interface name 'eth1'
set firewall ipv4 input filter rule 10 protocol 'tcp'
set firewall ipv4 input filter rule 10 destination port '22'
commit
```

Esto permite SSH solo desde la LAN y descarta el resto. **No lo apliques por SSH sin `commit-confirm`**, y recuerda añadir antes una regla para las conexiones ya establecidas, o las respuestas del propio router a lo que él inicia (DNS, actualizaciones) se perderán. La opción de estado de conexión se escribe distinto según la versión; consulta la referencia de `state` de la tuya.

Para el tráfico que cruza el router (LAN a Internet, LAN a LAN) se usa la cadena `forward`. En 1.3 la misma idea se expresaba con conjuntos de reglas con nombre aplicados a la interfaz, y también existe el modelo por zonas (`set firewall zone`) que la lista de configuración base recomienda: asignas interfaces a zonas y escribes qué pasa entre cada par. Para un homelab, dos zonas (interna y externa) bastan.

## Enrutamiento dinámico

El enrutamiento dinámico lo gestiona FRR, integrado en la CLI de VyOS. OSPF para una red interna:

```bash
set protocols ospf parameters router-id '10.255.0.1'
set protocols ospf area 0 network '192.168.10.0/24'
set protocols ospf interface eth1 passive
commit
```

`passive` evita enviar anuncios OSPF hacia interfaces donde no hay otro router. Y BGP, por ejemplo para un par con tu proveedor o con otro laboratorio:

```bash
set protocols bgp system-as '65001'
set protocols bgp neighbor 192.0.2.2 remote-as '65002'
set protocols bgp neighbor 192.0.2.2 address-family ipv4-unicast
set protocols bgp address-family ipv4-unicast network '192.168.10.0/24'
commit
```

El AS local se declara con `system-as` (no `system-as-number`); la documentación de VyOS no compara versiones para este nodo, así que verifica con la tuya. Para entender el esquema de números AS, rangos privados y conceptos básicos, lee [ASN y BGP](asn_bgp.md). En un homelab, usa números AS del rango privado y filtra siempre lo que anuncias y lo que aceptas mediante prefijos permitidos, incluso con vecinos de confianza.

Comandos operativos para comprobar el estado:

```bash
show ip route
show ip ospf neighbor
show bgp ipv4 summary
```

Los dos últimos muestran el estado de los vecinos; una sesión en `Established` (BGP) o `Full` (OSPF) es la señal sana. La salida exacta depende de la versión.

## Configuración como código

VyOS puede exportar su configuración como lista de comandos `set`, lo que facilita el versionado:

```bash
show configuration commands
```

El fichero persistente vive en `/config/config.boot`. Con esto, el flujo GitOps es:

1. Guarda en un repositorio el volcado de `show configuration commands` (o los comandos `set` que mantienes tú como fuente de verdad).
2. Cambios mediante pull request y revisión técnica; el diff es legible por humanos.
3. Un job aplica los cambios al router: la colección de Ansible `vyos.vyos` incluye módulos para ello, o puedes ejecutar los comandos con `configure` y `commit` desde un script por SSH. Ansible se introduce en [Ansible base](../ansible/ansible_base.md).
4. Tras aplicar, la canalización ejecuta comprobaciones: vecinos en `Established`, rutas esperadas, un `ping` a través de la pasarela.

Para copias de seguridad, además del repositorio, VyOS puede archivar cada `commit` en un servidor remoto (la opción `commit-archive` de `system config-management`; revisa la sintaxis exacta en tu versión). Guarda también una instantánea de la VM antes de cada actualización de versión mayor.

!!! tip "La fuente de verdad es el repositorio"
    Si alguien cambia algo a mano en el router, el siguiente despliegue lo pisa o lo contradice. Decide una regla y cúmplela: o el Git manda y los cambios manuales se descartan, o se documentan y se traen al repositorio.

## Riesgos comunes

- Cambios manuales fuera de flujo GitOps.
- Falta de validaciones previas al despliegue.
- No medir tiempos de convergencia ante fallos.
- Aplicar firewall sin `commit-confirm` por una sesión SSH y quedarse fuera.
- Olvidar `save`: la configuración funciona hasta el siguiente reinicio.
- Mezclar sintaxis de versiones distintas al copiar ejemplos de Internet.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `commit` falla con un error de validación | Sintaxis de otra versión o nodo inexistente | Comprueba `show version` y la documentación de esa versión; usa `?` o tabulador para ver las opciones válidas |
| Tras reiniciar, la configuración vuelve a la anterior | Se hizo `commit` pero no `save` | Ejecuta `save` tras confirmar; valora automatizarlo en el flujo |
| La LAN no sale a Internet | Falta NAT de origen o la ruta por defecto | Revisa la regla `nat source` y `show ip route` |
| Pierdes el acceso SSH tras un cambio de firewall | La regla bloquea tu propia sesión | Usa `commit-confirm`; recupera por consola de la VM |
| Vecino BGP atascado en `Active` o `Idle` | No hay conectividad TCP/179, AS incorrecto o filtro | Comprueba `ping`, la regla de firewall hacia el router, `remote-as` y la configuración del otro extremo |
| Vecino OSPF no llega a `Full` | Áreas o tipos de red incoherentes, o MTU distinta | Verifica área, tipo de red y MTU en ambos lados |
| Rendimiento bajo en la VM | Controlador de red emulado o vCPU insuficiente | Usa VirtIO, asigna más vCPU y comprueba la carga con `show system cpu` |
| La regla de firewall no tiene efecto | Está definida pero no aplicada a una cadena o interfaz | En 1.4 comprueba la cadena (`input`, `forward`, `output`); en 1.3, que el conjunto de reglas esté asignado a la interfaz |

## Buenas prácticas

- Usa plantillas y repositorio Git para la configuración.
- Introduce cambios mediante solicitudes de cambio (pull request) y revisión técnica.
- Separa entornos de laboratorio/preproducción/producción cuando sea posible.
- Ejecuta pruebas periódicas de convergencia y conmutación por error.
- Ejecuta `compare` antes de cada `commit` y `commit-confirm` en cambios remotos de riesgo.
- Fija la versión de VyOS en la documentación y actualiza primero en el laboratorio; la sintaxis cambia entre versiones.
- Reserva una interfaz de gestión separada y alcanzable por consola aunque falle el firewall.
- Si el router termina túneles, mira [WireGuard](../linux/wireguard.md) como opción ligera de VPN entre sedes.

## Lista de comprobación operativa

- ¿Toda la configuración crítica está versionada?
- ¿Existe canalización de validación sintáctica y funcional?
- ¿Se han probado escenarios de caída de enlace/vecino?
- ¿Hay instantáneas o copias de seguridad listas para reversión?
- ¿El último cambio se guardó con `save` y coincide con el repositorio?
- ¿Sabes qué versión de VyOS corre y si la sintaxis de la documentación es la suya?

## Referencias

- [VyOS: documentación oficial](https://docs.vyos.io/)
- [vRouters: comparativa](vrouters.md)
- [OPNsense](vrouter_opnsense.md)
- [pfSense](vrouter_pfsense.md)
- [MikroTik CHR](vrouter_mikrotik_chr.md)
- [ASN y BGP](asn_bgp.md)
- [WireGuard](../linux/wireguard.md)
- [Ansible base](../ansible/ansible_base.md)
- [VyOS: BGP](https://docs.vyos.io/en/latest/configuration/protocols/bgp.html)
- [VyOS: OSPF](https://docs.vyos.io/en/latest/configuration/protocols/ospf.html)
