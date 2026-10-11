---
title: "Almacenamiento local en Linux: ZFS y LVM"
description: "El disco local de un servidor o nodo Proxmox: LVM (PV, VG, LV, thin provisioning, snapshots) y ZFS (pools, vdevs, datasets, snapshots, send/receive, ARC), cuándo elegir cada uno y qué vigilar."
keywords: "zfs, lvm, lvm-thin, thin provisioning, raidz, mirror, zpool, datasets, snapshots, zfs send, arc, zvol, mdadm, proxmox, smartctl"
tags: ['storage', 'linux', 'proxmox']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 24 min
category: Almacenamiento
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Linux con acceso root y manejo básico de discos (lsblk, particiones)"
  - "[Proxmox base](../proxmox/proxmox_base.md)"
  - "Conceptos de RAID (espejo, paridad)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Almacenamiento local en Linux: ZFS y LVM

## El problema

Instalas Proxmox, aceptas el asistente y de pronto tienes un `local-lvm` que no recuerdas haber creado. O marcas «ZFS (RAID1)» y el instalador te pregunta por un `ashift` que nunca has necesitado. Las guías de [Proxmox](../proxmox/proxmox_base.md), de [Proxmox Backup Server](../backups/pbs.md) y de la [estrategia 3-2-1](../backups/strategy_321.md) dan ZFS y LVM por sabidos: hablan de snapshots, de datasets, de thin pools. Si no los conoces, la primera vez que un pool aparece `DEGRADED` o un thin pool se llena estás improvisando sobre los datos de todas tus máquinas.

Esta página explica los dos sistemas desde el ángulo del **disco local de un servidor o nodo de homelab**: qué es cada pieza, qué comandos usas a diario, cuándo conviene uno u otro y qué mirar para enterarte de los problemas antes de que lo sean.

!!! note "Qué cubre y qué no"
    Almacenamiento **local** en un único host. El almacenamiento distribuido está en [Ceph](ceph/ceph_base.md) y el consumo desde Kubernetes en [CSI en Kubernetes](kubernetes_csi.md). El cifrado se menciona, pero el detalle de LUKS vive en [Criptografía aplicada](../cybersecurity/criptografia_aplicada.md).

## 📋 Tabla de Contenidos

- [LVM: PV, VG y LV](#lvm-pv-vg-y-lv)
- [Ampliar en caliente](#ampliar-en-caliente)
- [Thin provisioning](#thin-provisioning)
- [Snapshots LVM y sus límites](#snapshots-lvm-y-sus-limites)
- [ZFS: pools y vdevs](#zfs-pools-y-vdevs)
- [Datasets y propiedades](#datasets-y-propiedades)
- [Snapshots y replicación con send/receive](#snapshots-y-replicacion-con-sendreceive)
- [Scrub, ARC y zvols](#scrub-arc-y-zvols)
- [Cuándo elegir cada uno](#cuando-elegir-cada-uno)
- [Cifrado](#cifrado)
- [Monitorización mínima](#monitorizacion-minima)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## LVM: PV, VG y LV

LVM (Logical Volume Manager) añade una capa entre los discos y el sistema de ficheros. Tiene tres niveles y conviene no confundirlos:

| Nivel | Qué es | Comando de listado |
|---|---|---|
| **PV** (*Physical Volume*) | Un disco o partición entregado a LVM | `pvs` |
| **VG** (*Volume Group*) | Bolsa de espacio formada por uno o varios PV | `vgs` |
| **LV** (*Logical Volume*) | «Partición» recortada del VG, donde pones el sistema de ficheros | `lvs` |

La idea clave: el LV no está atado a un disco concreto. Puedes crecerlo con espacio de otro disco, moverlo y hacer snapshots sin tocar el sistema de ficheros.

```bash
# Entregar dos discos a LVM y crear un grupo
pvcreate /dev/sdb /dev/sdc
vgcreate vg_datos /dev/sdb /dev/sdc

# Crear un volumen de 100 GiB con un sistema de ficheros
lvcreate -L 100G -n lv_backups vg_datos
mkfs.ext4 /dev/vg_datos/lv_backups
mount /dev/vg_datos/lv_backups /srv/backups
```

!!! warning "LVM no es redundancia"
    Un VG con dos discos y LVs lineales **suma capacidad, no protege**: si falla un disco, pierdes los LV con extensiones en él. La redundancia va debajo (mdadm, RAID hardware) o en las opciones RAID de LVM. Y LVM no calcula checksums: no detecta corrupción silenciosa.

## Ampliar en caliente

Es el motivo por el que casi todo el mundo usa LVM. Con el LV montado y en uso:

```bash
# Si el VG se queda sin espacio libre, añadir un disco
pvcreate /dev/sdd
vgextend vg_datos /dev/sdd

# Crecer el LV y su sistema de ficheros en un solo paso
lvextend -r -L +50G /dev/vg_datos/lv_backups
# O ocupar todo el espacio libre: lvextend -r -l +100%FREE ...
```

La opción `-r` (`--resizefs`) llama a la herramienta adecuada del sistema de ficheros (ext4, XFS…). Sin ella, el LV crece pero el sistema de ficheros sigue con el tamaño antiguo y `df` no cambia.

Reducir es otra historia: ext4 solo se encoge **desmontado**, XFS no se puede encoger y un `lvreduce` sin reducir antes el sistema de ficheros destruye datos.

## Thin provisioning

Un LV normal reserva todo su espacio al crearlo. Con *thin provisioning* creas un **thin pool** y los LV finos consumen del pool solo lo que escriben, así que puedes prometer más espacio del que existe (sobreasignación).

```bash
# Un pool de 500 GiB y dos volúmenes finos de 300 GiB cada uno
lvcreate -L 500G --thinpool tpool vg_datos
lvcreate -V 300G --thin -n vm1 vg_datos/tpool
lvcreate -V 300G --thin -n vm2 vg_datos/tpool
```

Hay 600 GiB prometidos sobre 500 reales. Mientras lo escrito quepa, todo va bien; cuando no, las escrituras fallan.

!!! danger "Un thin pool lleno es una avería, no un aviso"
    Al llenarse, las máquinas y sistemas de ficheros sobre el pool empiezan a dar errores de E/S y, en el peor caso, se corrompen. Un thin pool tiene además un **LV de metadatos** que también se puede llenar. Hay que vigilar los dos porcentajes.

```bash
# Uso de datos y de metadatos del pool
lvs -o lv_name,lv_size,data_percent,metadata_percent vg_datos
```

Dos medidas que lo hacen manejable:

- **Auto-extensión**: en `/etc/lvm/lvm.conf`, sección `activation`, los parámetros `thin_pool_autoextend_threshold` y `thin_pool_autoextend_percent` hacen que el pool crezca solo cuando se acerca al umbral, siempre que el VG tenga espacio libre y el monitor de eventos (`dmeventd`) esté activo.
- **Devolver espacio**: borrar ficheros dentro del LV fino no libera bloques del pool a menos que se emitan descartes. Ejecuta `fstrim -a` periódicamente o monta con `discard`.

### LVM-thin como backend de Proxmox

El instalador de Proxmox con ext4 crea un VG `pve` con un LV raíz y un thin pool `data`, expuesto como el almacenamiento `local-lvm`. Cada disco de VM es un LV fino y los snapshots de Proxmox son snapshots finos. Una entrada típica en `/etc/pve/storage.cfg` (hereda todos los riesgos anteriores; el panel muestra el uso del pool, pero conviene una alerta propia sobre `data_percent`):

```ini
lvmthin: local-lvm
        thinpool data
        vgname pve
        content rootdir,images
```

## Snapshots LVM y sus límites

Un snapshot congela el estado de un LV en un instante. Hay dos tipos y se comportan muy distinto:

| | Snapshot clásico (*thick*) | Snapshot de LV fino (*thin*) |
|---|---|---|
| Tamaño | Fijo, lo eliges al crearlo | Sin tamaño propio, consume del pool |
| Si se llena | Se **invalida** y se pierde | Compite con el resto por el pool |
| Rendimiento del origen | Cae: cada escritura copia el bloque antiguo | Casi sin penalización |

```bash
# Snapshot clásico: hay que reservar espacio para los cambios
lvcreate -s -n snap_pre_upgrade -L 10G /dev/vg_datos/lv_backups
# Snapshot de LV fino: sin tamaño
lvcreate -s -n snap_vm1 vg_datos/vm1
# Volver atrás: fusionar el snapshot en el origen
lvconvert --merge vg_datos/snap_pre_upgrade
```

Límites que conviene tener presentes:

- Un snapshot **no es una copia de seguridad**: vive en el mismo VG y en los mismos discos. Si el disco muere, se va con el original.
- Los snapshots clásicos largos degradan el rendimiento; úsalos para una operación concreta y bórralos.
- Los snapshots de LV fino se crean con la marca de «saltar en la activación»: para activarlos a mano, `lvchange -ay -K`.

## ZFS: pools y vdevs

ZFS combina gestor de volúmenes y sistema de ficheros en uno. Su rasgo definitorio es que **verifica con checksums todo lo que lee**, y si tiene redundancia, corrige lo corrupto con la copia buena. LVM más ext4 o XFS no hacen eso.

La jerarquía es distinta: un **pool** (`zpool`) se compone de uno o más **vdevs**, y cada vdev se compone de discos.

| Tipo de vdev | Discos mínimos | Tolera | Cuándo |
|---|---|---|---|
| **mirror** | 2 | Todos menos uno | VMs, bases de datos, nodos pequeños |
| **raidz1** | 3 | 1 disco | Datos fríos con discos pequeños |
| **raidz2** | 4 | 2 discos | Almacén grande de ficheros |
| **raidz3** | 5 | 3 discos | Vdevs muy anchos |

La redundancia es **por vdev**, y el pool reparte entre sus vdevs. Perder un vdev entero pierde el pool entero, así que mezclar un vdev sin redundancia con uno en espejo anula la protección del segundo.

```bash
# Dos discos en espejo; usa siempre rutas estables by-id
zpool create -o ashift=12 tank mirror \
  /dev/disk/by-id/ata-DISK_A /dev/disk/by-id/ata-DISK_B

# Seis discos en raidz2: mismo comando con "raidz2" y seis rutas
```

`ashift` es el tamaño de sector que ZFS asume, como potencia de 2 (`12` = 4 KiB). **No se puede cambiar después de crear el vdev.** Muchos discos modernos se anuncian con sectores de 512 B aunque usen 4 KiB; un `ashift` demasiado bajo causa escrituras desalineadas y pérdida permanente de rendimiento. Con `12` aciertas en casi todos los discos actuales.

### Ampliar un pool

A diferencia de un RAID clásico, **un vdev raidz no se amplía añadiéndole un disco**. Las formas habituales de crecer son:

- **Añadir otro vdev** con `zpool add` (por ejemplo, otro espejo), mejor del mismo tipo que los existentes.
- **Sustituir los discos por otros mayores** uno a uno con `zpool replace`; el espacio extra aparece cuando se han cambiado todos los del vdev (con `autoexpand=on` en el pool, o `zpool online -e`).
- **Espejos**: `zpool attach` añade un disco a un espejo y `zpool detach` lo quita.

!!! warning "La expansión de raidz depende de la versión"
    Las versiones recientes de OpenZFS (la serie 2.3 en adelante, según el proyecto) incorporan expansión de raidz, que permite añadir un disco a un vdev raidz existente con `zpool attach`. Comprueba con `zfs version` qué tienes antes de contar con ello: Proxmox y las distribuciones suelen ir por detrás del proyecto. Además, los datos escritos antes de expandir conservan la proporción antigua de paridad hasta que se reescriben.

## Datasets y propiedades

Dentro de un pool creas **datasets**: parecen directorios, pero cada uno tiene sus propias propiedades, cuotas y snapshots. A diferencia de LVM, no reservas tamaño por adelantado: comparten el espacio libre del pool.

```bash
zfs create tank/vms
zfs create tank/backups
zfs set quota=500G tank/backups
zfs get compression,recordsize,atime tank/backups

zfs set compression=lz4 tank
zfs set atime=off tank
zfs set recordsize=16K tank/postgres
```

Las propiedades que más importan en un servidor:

| Propiedad | Valor habitual | Para qué |
|---|---|---|
| `compression` | `lz4` (o `zstd`) | Comprime en línea. Con `lz4` casi siempre **mejora** el rendimiento al escribir menos |
| `recordsize` | `128K` por defecto; `1M` para ficheros grandes; `16K` para bases de datos | Tamaño de bloque máximo de un fichero |
| `atime` | `off` | Evita una escritura por cada lectura |
| `quota` / `reservation` | según caso | Tope o espacio garantizado para un dataset |

Las propiedades se heredan del padre. `recordsize` solo afecta a los datos escritos a partir del cambio. `zstd` como valor de `compression` exige una versión de OpenZFS que lo incluya (la serie 2.x).

## Snapshots y replicación con send/receive

Los snapshots de ZFS son instantáneos y, mientras no cambien los datos, no ocupan nada. Están en el mismo pool, así que valen lo mismo que un snapshot LVM: no son copia de seguridad hasta que salen de ese disco.

```bash
zfs snapshot tank/vms@2026-10-11
zfs list -t snapshot tank/vms
zfs rollback tank/vms@2026-10-11    # vuelve a ese momento
zfs destroy tank/vms@2026-10-11
```

Lo que los convierte en réplica es `zfs send`/`zfs receive`: serializa un snapshot y lo reconstruye en otro pool, local o remoto.

```bash
# Primera réplica completa
zfs send tank/vms@snap1 | ssh nas zfs receive reserva/vms

# Réplicas siguientes: solo lo que cambió entre dos snapshots
zfs send -i tank/vms@snap1 tank/vms@snap2 | ssh nas zfs receive reserva/vms
```

El envío incremental solo funciona si el destino conserva el snapshot base. Es la pieza que usa el [3-2-1](../backups/strategy_321.md) para tener una copia fuera del equipo. Para medir cómo se comporta el pool bajo carga, usa [fio](protocols/examples/fio_example.md).

## Scrub, ARC y zvols

**Scrub.** Recorre todos los datos del pool, verifica los checksums y repara lo que pueda con la redundancia. Es la forma de detectar la degradación antes de necesitar el dato.

```bash
zpool scrub tank
zpool status tank     # progreso y resultado
```

Programa un scrub periódico y revisa el resultado. Carga los discos: no lo lances en horas punta.

**ARC.** Es la caché de lectura de ZFS en RAM y la razón por la que «ZFS se come la memoria». Su tamaño máximo por defecto ha cambiado entre versiones de OpenZFS, y algunos instaladores, como el de Proxmox, ya fijan un límite propio: comprueba el valor efectivo con `arc_summary` en vez de suponerlo. Libera memoria cuando el sistema la necesita, pero verás poca memoria «libre» en `free`. Si el nodo ejecuta VMs, limítala para dejarles sitio:

```bash
# Límite de 4 GiB (valor en bytes) de forma persistente
echo "options zfs zfs_arc_max=4294967296" > /etc/modprobe.d/zfs.conf
update-initramfs -u -k all      # solo si la raíz está en ZFS; reiniciar después
# En caliente: echo 4294967296 > /sys/module/zfs/parameters/zfs_arc_max
```

No hay una cifra universal: ajústala mirando los aciertos de caché (`arc_summary`) y la memoria que necesitan tus VM. Con la deduplicación activada el consumo de RAM se dispara: déjala apagada salvo motivo claro.

**Zvols.** Un zvol es un dataset que se comporta como un dispositivo de bloque (`/dev/zvol/...`). Es lo que Proxmox usa para los discos de las VM sobre ZFS: cada disco es un zvol, con snapshots y clones propios.

```bash
zfs create -V 32G tank/vm-100-disk-0    # aparece en /dev/zvol/tank/
```

El tamaño de bloque (`volblocksize`) se fija al crear el zvol y su valor por defecto cambia entre versiones. Sobre raidz, los zvols pueden ocupar más de lo esperado por el relleno de paridad; para VMs se recomiendan espejos.

## Cuándo elegir cada uno

| Criterio | LVM (+ ext4/XFS) | LVM-thin | ZFS | mdadm + LVM |
|---|---|---|---|---|
| **Integridad de datos** | Sin checksums | Sin checksums | Checksums y autocuración | Sin checksums |
| **RAM** | Mínima | Mínima | Alta (ARC, ajustable) | Mínima |
| **Snapshots** | Clásicos, con coste | Rápidos, baratos | Instantáneos, sin límite práctico | Los de LVM |
| **Ampliación** | Muy flexible, en caliente | Muy flexible | Añadir vdevs; raidz limitado | Flexible; crecer el array es más lento |
| **Rendimiento** | Alto, predecible | Alto; riesgo de fragmentación | Muy bueno con RAM y ajuste | Alto, predecible |
| **Complejidad** | Baja | Media (vigilar el pool) | Media-alta (modelo propio) | Media (dos capas) |

Un criterio práctico:

- **ZFS** cuando el dato importa más que el último MiB/s: almacén de ficheros, copias, nodo Proxmox con dos discos en espejo. La integridad y `send/receive` justifican la RAM.
- **LVM-thin** en un nodo con poca RAM, un solo disco o una controladora RAID hardware, donde quieres snapshots de VM baratos. Acepta el riesgo y alerta sobre el pool.
- **mdadm + LVM** es la tercera vía: mdadm da el RAID por software y LVM la flexibilidad encima. Es la combinación clásica y sobria, sin checksums. Creas el array con `mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc`, lo entregas con `pvcreate /dev/md0` y sigues como en la sección de LVM.
- **Evita ZFS sobre un RAID hardware** que oculte los discos: necesita verlos (HBA en modo paso directo) para detectar y reparar errores.

## Cifrado

Ambos admiten cifrado, por caminos distintos:

- **LUKS bajo LVM**: cifras el disco o la partición con `cryptsetup`, y sobre el dispositivo descifrado montas el PV. Todo lo que hay encima (VG, LV, snapshots) queda cifrado de una vez.
- **Cifrado nativo de ZFS**: se activa por dataset al crearlo (`zfs create -o encryption=on -o keyformat=passphrase tank/privado`). Permite cifrar unos datasets y otros no, y replicar snapshots sin que salgan descifrados, siempre que se envíen en crudo con `zfs send -w`: un `zfs send` normal transmite los datos ya descifrados.

La gestión de claves, las cabeceras de LUKS y la recuperación están en [Criptografía aplicada](../cybersecurity/criptografia_aplicada.md); no se repiten aquí.

## Monitorización mínima

No hace falta Prometheus para empezar; estos comandos, a mano o en un cron, cubren casi todos los sustos:

```bash
# ZFS
zpool status -x      # "all pools are healthy" o el detalle del problema
zpool list           # capacidad, ocupación y salud de cada pool
zfs list             # espacio por dataset

# LVM
pvs ; vgs ; lvs      # discos, grupos y volúmenes
lvs -a -o+data_percent,metadata_percent    # incluye pools y metadatos

smartctl -H /dev/sda        # SMART: veredicto global
smartctl -a /dev/sda        # SMART: atributos completos
```

Qué vigilar: un pool distinto de `ONLINE`, errores de lectura/escritura/checksum en `zpool status`, un pool por encima de un 80 % de ocupación (el rendimiento de ZFS cae al llenarse), `data_percent` o `metadata_percent` de un thin pool cerca del 100 %, y sectores reasignados o pendientes en aumento en SMART. Para NVMe, `smartctl -a /dev/nvme0` da desgaste y temperatura. El demonio `smartd` de `smartmontools` puede avisar por correo.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `zpool status` marca `DEGRADED` | Un disco ha fallado o se ha desconectado | Identificar el disco en `zpool status`, cambiarlo y `zpool replace tank viejo nuevo` |
| Las VM dan errores de E/S de golpe | Thin pool lleno (datos o metadatos) | Ampliar el pool (`lvextend` sobre el thin pool), liberar con `fstrim`, borrar snapshots |
| `lvextend` dice que no hay extensiones libres | El VG está lleno | `vgextend` con otro PV, o reducir lo que sobre |
| El LV crece pero `df` no cambia | Se omitió `-r` | `lvextend -r` o, a mano, `resize2fs` (ext4) / `xfs_growfs` (XFS) |
| Un snapshot LVM clásico desaparece o queda inválido | Se llenó su espacio reservado | Reservar más, o usar snapshots de LV fino; borrarlo tras la operación |
| «Se come la RAM» tras instalar ZFS | El ARC crece mientras haya memoria | Fijar `zfs_arc_max` y comprobar con `free` y los contadores de ARC |
| El pool va lento al acercarse al 90 % | Fragmentación y poco espacio libre | Liberar espacio, ampliar con otro vdev, mantener margen |
| `zpool import` rechaza un pool de otra instalación | El pool no se exportó y consta como en uso | Verificar que no está en uso y `zpool import -f nombre`; antes, `zpool export` |

## Buenas prácticas

- **Usa `/dev/disk/by-id/`** al crear pools y VG. Los nombres `/dev/sdX` cambian entre arranques.
- **Redundancia debajo de todo.** LVM sin RAID suma capacidad pero no protege; y en ninguno de los dos casos hay copia de seguridad hasta tener otra copia fuera del host ([3-2-1](../backups/strategy_321.md), [PBS](../backups/pbs.md)).
- **Alerta sobre ocupación de pools y thin pools** antes del 80 %, no después del 100 %.
- **`ashift=12` y `compression=lz4`** desde el primer día: `ashift` no se corrige después y la compresión solo afecta a lo escrito a partir de ahí.
- **Scrub mensual y SMART periódico** con aviso por correo. **Limita el ARC** en nodos con VM. **Prueba la restauración**, no solo la copia.

## Referencias

- [OpenZFS — documentación](https://openzfs.github.io/openzfs-docs/) · [zpool(8)](https://openzfs.github.io/openzfs-docs/man/master/8/zpool.8.html) · [zfs(8)](https://openzfs.github.io/openzfs-docs/man/master/8/zfs.8.html)
- [lvmthin(7)](https://manpages.debian.org/stable/lvm2/lvmthin.7.en.html) · [Proxmox VE — Storage](https://pve.proxmox.com/wiki/Storage)
- [Proxmox base](../proxmox/proxmox_base.md) · [Proxmox Backup Server](../backups/pbs.md) · [Estrategia 3-2-1](../backups/strategy_321.md)
- [Ceph](ceph/ceph_base.md) · [CSI en Kubernetes](kubernetes_csi.md) · [Benchmarks con fio](protocols/examples/fio_example.md) · [Criptografía aplicada](../cybersecurity/criptografia_aplicada.md)
- [lvchange(8)](https://manpages.debian.org/stable/lvm2/lvchange.8.en.html)
- [zpool-online(8)](https://openzfs.github.io/openzfs-docs/man/master/8/zpool-online.8.html)
