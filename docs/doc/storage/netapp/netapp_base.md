---
title: "NetApp ONTAP — Guía base"
description: "Conceptos de ONTAP (cluster, agregados, SVM, volúmenes, LIFs), CLI básica, exports NFS y shares SMB, snapshots y SnapMirror, eficiencia de espacio e integración con Proxmox y Kubernetes por NFS e iSCSI."
keywords: "netapp, ontap, svm, flexvol, aggregate, lif, snapshot, snapmirror, nfs, smb, iscsi, trident, proxmox"
tags: ['storage', 'netapp']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 18 min
category: Almacenamiento
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Conceptos de NFS, SMB e iSCSI"
  - "[Protocolos de almacenamiento](../protocols/protocols.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# NetApp ONTAP — Guía base

## El problema

Te entregan una cabina NetApp y descubres que no se parece a un servidor NAS: hay un cluster, nodos, agregados, algo llamado SVM y direcciones IP que pertenecen a "interfaces lógicas" en vez de a una tarjeta de red. Creas un volumen, lo exportas y los clientes no lo ven, porque en ONTAP crear el volumen no lo publica: falta el *junction path*, la export policy y una LIF en la SVM correcta. Cada capa tiene su razón de ser, pero hay que conocerlas en orden.

Esta página es el mapa: qué es cada objeto, cómo se relacionan, los comandos básicos para inspeccionar, y cómo se conecta todo con Proxmox y Kubernetes. Es un punto de partida, no un manual de administración de ONTAP.

!!! note "Qué cubre y qué no"
    Aquí se trata el **modelo de objetos** y el acceso por NFS/SMB/iSCSI desde tu infraestructura. Para comparar protocolos y medir rendimiento está [Protocolos de almacenamiento](../protocols/protocols.md); para otra cabina comercial, [Pure Storage](../pure_storage/pure_storage_base.md); para almacenamiento definido por software, [Ceph](../ceph/ceph_base.md).

## 📋 Tabla de Contenidos

- [Conceptos de ONTAP](#conceptos-de-ontap)
- [CLI básica](#cli-basica)
- [Crear y publicar un volumen](#crear-y-publicar-un-volumen)
- [Eficiencia de espacio](#eficiencia-de-espacio)
- [Snapshots y SnapMirror](#snapshots-y-snapmirror)
- [Integración con Proxmox](#integracion-con-proxmox)
- [Integración con Kubernetes](#integracion-con-kubernetes)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Conceptos de ONTAP

ONTAP es el sistema operativo de las cabinas NetApp (FAS, AFF, ASA). Los objetos, de abajo arriba:

| Objeto | Qué es |
|---|---|
| **Nodo** | Un controlador físico. Los nodos se agrupan en parejas de alta disponibilidad (HA pair) que se cubren entre sí |
| **Cluster** | El conjunto de nodos administrado como una unidad, con una sola gestión |
| **Agregado** | Pool de discos de un nodo. Aporta la capacidad física sobre la que viven los volúmenes |
| **SVM** (vserver) | *Storage Virtual Machine*: un servidor de ficheros/bloques virtual con su propio espacio de nombres, usuarios, protocolos y LIFs. Es la frontera de multi-tenencia |
| **Volumen (FlexVol)** | La unidad que ven los clientes: contiene ficheros (NAS) o LUNs (SAN). Pertenece a una SVM y vive en un agregado |
| **Qtree** | Subdirectorio dentro de un volumen al que se pueden aplicar cuotas |
| **LUN** | Disco de bloque presentado por iSCSI o FC, almacenado dentro de un volumen |
| **LIF** | *Logical Interface*: IP (o WWPN) de servicio de una SVM. Se asocia a un puerto físico y puede migrar entre nodos |

Las ideas que más tropiezos evitan:

- **Los clientes hablan con la SVM, no con el cluster.** Montas `svm1:/vol_datos`, no un nodo. La IP a la que apuntas es una LIF de datos de esa SVM.
- **Los LIFs son móviles.** Si un nodo cae o se hace un takeover, la LIF migra y la IP sigue respondiendo. Por eso el cliente nunca debe apuntar a la IP de gestión de un nodo.
- **Un volumen NAS necesita *junction path***: su posición en el árbol de nombres de la SVM (`/vol_datos`). Sin él existe pero no se puede exportar.
- **Acceso = protocolo habilitado + LIF + política.** En NFS la política es la *export policy*; en SMB, el share y sus ACL; en iSCSI, el *igroup* que mapea la LUN a los iniciadores.

## CLI básica

La CLI de ONTAP es jerárquica (`volume show`, `network interface show`) y se conecta por SSH a la LIF de gestión del cluster con un usuario administrador. Los comandos de inspección son seguros y no modifican nada:

```text
cluster show                  # nodos del cluster y su estado
storage aggregate show        # agregados, capacidad usada y libre
vserver show                  # SVMs y protocolos permitidos
volume show                   # volúmenes, su SVM, agregado y tamaño
network interface show        # LIFs: IP, nodo y puerto actuales, estado
volume snapshot show          # snapshots por volumen
```

Cada comando admite filtrar por SVM o volumen con parámetros como `-vserver` y `-volume`, y completa con el tabulador. Léelos en prosa: `network interface show` te dice si cada LIF está arriba y si está en su nodo de origen o ha migrado; `volume show` te dice el espacio disponible y a qué agregado pertenece cada volumen.

!!! warning "Dependen de la versión"
    La sintaxis y los campos mostrados cambian entre versiones de ONTAP (la 9.x añade parámetros y reorganiza algunas salidas). Comprueba la ayuda de tu versión con `?` en la propia CLI antes de copiar comandos de otra instalación.

## Crear y publicar un volumen

Orden lógico: volumen, política de acceso, publicación. Ejemplo para un datastore NFS:

```text
volume create -vserver svm1 -volume vol_datos -aggregate aggr1_nodo1 -size 500GB -junction-path /vol_datos
vserver export-policy create -vserver svm1 -policyname pol_proxmox
vserver export-policy rule create -vserver svm1 -policyname pol_proxmox -clientmatch 10.0.10.0/24 -protocol nfs -rorule sys -rwrule sys -superuser sys
volume modify -vserver svm1 -volume vol_datos -policy pol_proxmox
```

La *export policy* es el equivalente al fichero `/etc/exports`: define qué clientes entran y con qué privilegios. `-superuser sys` equivale a `no_root_squash` y solo debe darse a hosts de confianza, como los hipervisores. Una política vacía no deja pasar a nadie, y la regla por defecto de la política `default` rara vez es lo que quieres.

Para exponer el mismo volumen por SMB se crea un share sobre su junction path, siempre que la SVM tenga CIFS configurado y unido al dominio:

```text
vserver cifs share create -vserver svm1 -share-name datos -path /vol_datos
vserver cifs share show -vserver svm1
```

El share controla el acceso por usuario y grupo mediante ACL; la export policy no interviene en SMB. Si el volumen se comparte por NFS y SMB a la vez, el estilo de seguridad del volumen (unix, ntfs o mixed) decide cómo se resuelven los permisos entre los dos mundos: elígelo al crear el volumen y no lo cambies con datos dentro.

### Comprobar desde un cliente Linux

Antes de dar el volumen por bueno, móntalo a mano desde un host autorizado y escribe un fichero de prueba:

```bash
sudo mkdir -p /mnt/netapp
sudo mount -t nfs -o vers=4.1 10.0.10.50:/vol_datos /mnt/netapp
touch /mnt/netapp/prueba && ls -l /mnt/netapp
sudo umount /mnt/netapp
```

La IP es la de una LIF de datos de la SVM y la ruta es el junction path. Si el montaje falla, el mensaje del cliente distingue casi siempre entre "no hay ruta hasta la LIF" y "la LIF responde pero la export policy te rechaza". Si el servidor solo ofrece NFSv3, cambia `vers=4.1` por `vers=3`.

!!! warning "Versión de NFS"
    Qué versiones de NFS están habilitadas es un ajuste de la SVM y varía según su configuración y la versión de ONTAP. Confírmalo con tu administrador antes de fijar `vers=` en `/etc/fstab`.

## Eficiencia de espacio

ONTAP aplica deduplicación, compresión y compactación a nivel de volumen. En los sistemas todo-flash (AFF, ASA) suelen venir activadas por defecto; en FAS con discos rotacionales conviene comprobarlo.

- **Thin provisioning**: el volumen declara un tamaño pero solo consume lo que se escribe. Vigila el espacio libre del **agregado**, no solo el del volumen: puedes prometer más de lo que existe.
- **`volume autosize`**: permite que el volumen crezca solo hasta un máximo definido. Úsalo siempre con límite, para que un cliente descontrolado no se coma el agregado.
- **Cuotas en qtrees**: si varios equipos comparten un volumen, un qtree por equipo con su cuota acota el consumo.
- **FabricPool**: mueve bloques fríos a un almacén de objetos S3 (on-prem o cloud). La política del volumen (`auto`, `snapshot-only`...) decide qué se considera frío; evalúa la latencia de recuperación antes de aplicarlo a datos que se leen a menudo.

!!! warning "Eficiencia no es capacidad garantizada"
    Los ratios de dedupe y compresión dependen de los datos: bases de datos comprimidas, vídeo o datos ya cifrados apenas mejoran. Dimensiona con los datos reales, no con el ratio del folleto.

## Snapshots y SnapMirror

Un **snapshot** de ONTAP es una imagen puntual del volumen basada en punteros, no en una copia de datos: se crea en segundos y solo consume espacio cuando los bloques originales cambian. Por eso se pueden tener muchos.

```text
volume snapshot create -vserver svm1 -volume vol_datos -snapshot antes_de_migrar
volume snapshot show -vserver svm1 -volume vol_datos
```

- **Políticas de snapshot**: se asignan al volumen y generan copias periódicas (por ejemplo, cada hora, diaria y semanal) con una retención por cada una. Es el sitio donde defines cuánto histórico tienes "gratis".
- **Restaurar**: se puede recuperar un fichero concreto desde el directorio oculto `.snapshot` del volumen o revertir el volumen entero a un snapshot. Revertir el volumen descarta todo lo posterior: es la opción nuclear.
- **SnapMirror**: replica un volumen a otro (en el mismo cluster o en otro) transfiriendo solo los bloques cambiados entre snapshots. Es la base de la recuperación ante desastres. Hay modos asíncronos, con un RPO igual al intervalo de la programación, y modos síncronos para RPO casi nulo.
- **Etiquetas de snapshot (`snapmirror-label`)**: permiten que la relación replique o retenga solo ciertos snapshots, útil para tener retenciones distintas en origen y destino.
- **SnapVault / destino de larga retención**: el destino conserva más histórico que el origen. Programa una actualización tras eventos críticos, como el volcado de una base de datos.

```text
snapmirror show               # relaciones de replicación, su estado y el retraso
```

Una relación se crea y se inicializa entre dos volúmenes, con el destino marcado como tipo DP o su equivalente en tu versión. Los pasos exactos cambian entre versiones y entre cluster peering y SVM peering, así que sigue la guía de tu versión.

!!! danger "Un snapshot no es un backup"
    Los snapshots viven en el mismo volumen y el mismo agregado que los datos: si se pierde la cabina, o un administrador borra el volumen, se van con él. SnapMirror a otro cluster mejora mucho el caso, pero sigue siendo una copia gestionada por el mismo sistema. Aplica la regla de [Estrategia 3-2-1](../../backups/strategy_321.md) y complementa con una copia independiente, por ejemplo con [Restic y Borg](../../backups/restic_borg.md).

## Integración con Proxmox

Dos caminos, según lo que sea más importante:

**NFS** es el más sencillo: el volumen se monta como almacenamiento compartido, ideal para imágenes de disco, ISOs y backups, y para migración en vivo entre nodos sin configurar nada más. En Proxmox se añade desde la interfaz o con `pvesm`:

```bash
pvesm add nfs netapp-nfs --server 10.0.10.50 --export /vol_datos --content images,iso,backup
```

La IP es una LIF de datos NFS de la SVM, no la de gestión. Habilita en la export policy a **todos los nodos** de Proxmox. Prefiere NFSv4.1 cuando el entorno lo admita y ajusta `rsize`/`wsize` solo tras medir con `fio`, como se explica en [Protocolos de almacenamiento](../protocols/protocols.md). Para una LIF de datos con varios caminos de red, comprueba la compatibilidad de tu versión de Proxmox con las opciones de multipath y sesiones de NFS antes de basar el diseño en ellas.

**iSCSI** ofrece bloque y mejor latencia para bases de datos o VMs sensibles. Se publica la LUN a los iniciadores de cada nodo (igroup), se configura `multipath` en los hosts y sobre el dispositivo se monta LVM compartido o similar. Es más trabajo y hay que cuidar el multipath: dos LIFs iSCSI en redes distintas y rutas activas en los dos nodos.

Regla práctica: NFS para datastores generales, iSCSI para las cargas donde mides la latencia y lo justificas. El detalle de la plataforma está en [Proxmox base](../../proxmox/proxmox_base.md).

## Integración con Kubernetes

El proveedor CSI de NetApp se llama **Trident**. Se instala en el cluster, se le da un *backend* (la SVM y sus credenciales) y se exponen *StorageClasses* que apuntan a ese backend. El tipo de backend define el protocolo: los drivers `ontap-nas` para NFS y `ontap-san` para iSCSI.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ontap-nas
provisioner: csi.trident.netapp.io
parameters:
  backendType: "ontap-nas"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

- `WaitForFirstConsumer` retrasa la creación del volumen hasta que hay un pod, para que se cree donde se va a usar.
- `allowVolumeExpansion: true` permite crecer el PVC en caliente.
- Una StorageClass por nivel de servicio (por ejemplo `ontap-nas` para ficheros compartidos y una de bloque para bases de datos) deja decidir al equipo de la aplicación sin tocar la cabina.
- Los nodos de Kubernetes necesitan acceso en la export policy (NFS) o en el igroup (iSCSI), y los clientes NFS/iSCSI instalados.

!!! warning "Nombres y parámetros dependen de la versión de Trident"
    Los parámetros de la StorageClass, el formato del backend y los drivers disponibles cambian entre versiones de Trident y de ONTAP. Contrasta con la documentación de la versión instalada. El modelo general de CSI y los modos de acceso están en [Kubernetes y CSI](../kubernetes_csi.md).

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| El cliente NFS recibe `access denied` al montar | La IP del cliente no coincide con ninguna regla de la export policy, o la política no está asignada al volumen | Revisar `vserver export-policy rule show` y que el volumen use esa política |
| El volumen existe pero no se puede montar | No tiene junction path, o la SVM no tiene NFS habilitado | Comprobar `volume show` y `vserver show` |
| Se monta pero los ficheros son de `nobody` | Desajuste de dominio de ID en NFSv4 o de mapeo de usuarios | Alinear el dominio de ID entre cliente y SVM, o usar NFSv3 si no hay identidad centralizada |
| El cliente no llega a la IP | La LIF migró, está caída o está en una VLAN distinta | `network interface show`: estado y nodo actual de la LIF |
| El volumen se llena aunque hay espacio en el agregado | `autosize` desactivado o con un máximo bajo | Ajustar `volume autosize` o ampliar el volumen |
| El agregado se llena de golpe | Thin provisioning sobreasignado, o snapshots retenidos que consumen | Revisar `storage aggregate show` y la política de snapshots |
| El share SMB no autentica | La SVM no está unida al dominio o hay desfase horario con el controlador de dominio | Revisar la configuración CIFS de la SVM y sincronizar la hora |
| Rendimiento irregular por iSCSI | Multipath mal configurado o una sola ruta activa | Verificar que hay rutas activas por cada LIF y el balanceo en el host |
| SnapMirror aparece con retraso creciente | Enlace saturado o transferencia anterior sin terminar | `snapmirror show` y revisar ancho de banda y programación |

## Buenas prácticas

- **Una SVM por dominio de confianza** (entornos, clientes, equipos): es la frontera de acceso y de protocolos.
- **LIFs de datos separadas de la gestión**, y al menos una por nodo y protocolo para que el failover mantenga el servicio.
- **Export policies mínimas**: subredes concretas, `superuser` solo para los hipervisores, nunca `0.0.0.0/0`.
- **Un volumen por datastore o aplicación**, no un volumen gigante: snapshots, cuotas y restauraciones por unidad.
- **`autosize` con límite y alertas** sobre el espacio libre del agregado.
- **Políticas de snapshot explícitas**, con etiquetas para decidir qué replica SnapMirror.
- **Prueba la restauración**, desde `.snapshot` y desde el destino de SnapMirror, antes de necesitarla.
- **Copia independiente fuera de la cabina**: un snapshot y una réplica no sustituyen a un backup real.
- **Documenta la versión de ONTAP y de Trident** en uso; los comandos y parámetros de esta página pueden diferir en otras.

## Referencias

- [Documentación de NetApp ONTAP](https://docs.netapp.com/us-en/ontap/)
- [Documentación de Trident](https://docs.netapp.com/us-en/trident/)
- [Protocolos de almacenamiento](../protocols/protocols.md) · [Kubernetes y CSI](../kubernetes_csi.md)
- [Pure Storage](../pure_storage/pure_storage_base.md) · [Ceph](../ceph/ceph_base.md)
- [Estrategia 3-2-1](../../backups/strategy_321.md) · [Restic y Borg](../../backups/restic_borg.md)
- [Proxmox base](../../proxmox/proxmox_base.md)
