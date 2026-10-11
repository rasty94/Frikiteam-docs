---
title: "Pure Storage — Guía base"
description: "Pure Storage FlashArray en infraestructura propia: tiers, volúmenes, hosts, snapshots, protection groups, ActiveCluster y CSI para Kubernetes y virtualización."
keywords: "pure storage, flasharray, purity, ansible, purestorage.flasharray, protection group, activecluster, csi, iscsi, multipath, snapshots"
tags: ['storage', 'pure-storage']
updated: 2026-10-11
difficulty: beginner
estimated_time: 17 min
category: Almacenamiento
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Conceptos básicos de SAN (LUN, iSCSI, multipath)"
  - "Acceso administrativo a un FlashArray (CLI por SSH o GUI)"
  - "Kubernetes o un hipervisor como consumidor del almacenamiento"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Pure Storage — Guía base

## El problema

Tienes un array todo-flash caro y un conjunto de consumidores muy distintos: una base de datos que exige latencia baja y estable, un clúster de virtualización con cientos de VMs casi idénticas y un Kubernetes que pide volúmenes por API. Si presentas LUNs a mano, acabas con volúmenes sin etiquetar, hosts mal definidos y snapshots que nadie sabe si se pueden borrar.

Un FlashArray rinde bien cuando lo tratas como **un pequeño conjunto de objetos declarativos**: volúmenes finos, hosts, grupos de protección y políticas. Esta página recoge ese modelo y cómo conectarlo con la infraestructura del sitio, sin repetir el manual del fabricante.

!!! note "Qué cubre y qué no"
    Se trata el modelo de objetos, la integración con hipervisores y Kubernetes y la protección de datos. La configuración de red, los números de rendimiento y los límites exactos dependen del modelo y de la versión de Purity: consulta la documentación del fabricante para tu array.

## 📋 Tabla de Contenidos

- [Línea de producto y tiers](#linea-de-producto-y-tiers)
- [Modelo de objetos](#modelo-de-objetos)
- [Provisioning por CLI](#provisioning-por-cli)
- [Conectar hosts: iSCSI, multipath y NFS](#conectar-hosts-iscsi-multipath-y-nfs)
- [Reducción de datos y thin provisioning](#reduccion-de-datos-y-thin-provisioning)
- [Snapshots, clones y protection groups](#snapshots-clones-y-protection-groups)
- [Replicación y ActiveCluster](#replicacion-y-activecluster)
- [Kubernetes con el CSI](#kubernetes-con-el-csi)
- [Monitorización](#monitorizacion)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Línea de producto y tiers

- **FlashArray//X y //XL**: bloque NVMe de alto rendimiento para bases de datos, VMs y cargas sensibles a latencia.
- **FlashArray//C**: capacidad sobre flash QLC. Encaja con datos tibios, réplicas y entornos de pruebas, cuando lo que importa es el coste por TB.
- **FlashBlade**: archivo y objetos (NFS/SMB/S3) para backups, logs y analítica.

La idea de tier en un entorno propio es sencilla: lo que duele si va lento va a //X; lo que solo debe existir va a //C o a un repositorio NFS/S3 barato. Para el repositorio barato, mira también [Restic y Borg](../../backups/restic_borg.md) y la [estrategia 3-2-1](../../backups/strategy_321.md): un array, por bueno que sea, no es un backup.

## Modelo de objetos

| Objeto | Qué es | Módulo de Ansible |
|--------|--------|-----------------------|
| Volumen | Bloque fino, con nombre y tamaño | `purefa_volume` |
| Host | Iniciadores (IQN, WWN o NQN) de un consumidor | `purefa_host` |
| Host group | Conjunto de hosts que comparten volúmenes (clústeres) | `purefa_hg` |
| Protection group | Volúmenes + calendario de snapshots + destino de replicación | `purefa_pg` |
| Array | Estado global, versión de Purity, capacidad | `purefa_info` |

La regla práctica: **los volúmenes compartidos entre nodos se conectan al host group, no a cada host**. Así, añadir un nodo al clúster es añadirlo al grupo, y todos los LUN aparecen con el mismo número.

## Provisioning con Ansible

La referencia de la CLI de Purity solo está disponible con acceso al soporte de Pure. Para automatizar con una fuente pública, la colección oficial `purestorage.flasharray` de Ansible cubre lo mismo: inventario del array, volúmenes, hosts, snapshots y protection groups. Este playbook crea un volumen y lo presenta a un host:

```yaml
# provision.yml: ejecutar con ansible-playbook provision.yml
- hosts: localhost
  gather_facts: false
  vars:
    fa: &fa
      fa_url: flasharray.lab.example
      api_token: REEMPLAZA_POR_TU_TOKEN
  tasks:
    - name: Estado general del array
      purestorage.flasharray.purefa_info:
        <<: *fa
      register: array_info

    - name: Volumen fino de 2 TiB para la base de datos
      purestorage.flasharray.purefa_volume:
        <<: *fa
        name: db-prod
        size: 2T
        state: present

    - name: Host con su iniciador iSCSI y el volumen presentado
      purestorage.flasharray.purefa_host:
        <<: *fa
        name: esx01
        iqn:
          - iqn.2026-01.lab.example:esx01
        volume: db-prod
        state: present
```

!!! tip "Límites de QoS por volumen"
    `purefa_volume` acepta `bw_qos` e `iops_qos` para limitar ancho de banda e IOPS de un volumen. Sin límites, un volumen ruidoso puede perjudicar a los demás.

## Conectar hosts: iSCSI, multipath y NFS

- **iSCSI con multipath**: dos redes o VLAN de almacenamiento separadas, una IP de portal por controlador y por red. Con `multipath-tools` en Linux, la política que recomienda el fabricante para sus LUN es la que debes aplicar; comprueba su guía de ajustes para tu distribución.
- **Fibre Channel o NVMe/TCP**: si tu array y tus hosts lo soportan, evita capas de traducción. El proceso de definir hosts y conectar volúmenes es el mismo; solo cambian los identificadores.
- **NFS**: lo ofrece FlashBlade como servicio de ficheros. Para virtualización sobre NFS, valida la versión de protocolo que soporta tu hipervisor y el modo de montaje. Compara protocolos en [Protocolos de almacenamiento](../protocols/protocols.md).

En Proxmox y en VMware el patrón es el mismo: un LUN grande compartido por todo el clúster, presentado al host group. En VMware, el plugin de vSphere y los offloads VAAI aceleran clones y borrados; en Proxmox, LVM compartido sobre iSCSI con multipath es el esquema habitual.

!!! tip "Una red de almacenamiento propia"
    Separa el tráfico de almacenamiento del de gestión y de VMs, con MTU 9000 solo si **toda** la ruta lo soporta. Un salto a 1500 en medio provoca fragmentación y latencias erráticas que se confunden con problemas del array.

## Reducción de datos y thin provisioning

Los volúmenes son finos por diseño y el array aplica deduplicación y compresión en línea. Consecuencias que importan al operar:

- La capacidad que ves en el host (2 TiB) no es la que consume el array. Vigila el espacio **físico** disponible, no la suma de lo aprovisionado.
- La reducción de datos depende del contenido: bases de datos y VMs idénticas reducen mucho; datos ya comprimidos o cifrados, casi nada. No dimensiones con la mejor cifra que encuentres.
- Si cifras en el guest (LUKS, cifrado de disco), anulas buena parte de la reducción. Decide dónde cifrar antes de dimensionar.
- `discard`/`UNMAP` desde el guest o el hipervisor devuelve espacio al array; sin él, el espacio libre del sistema de ficheros sigue contando.

## Snapshots, clones y protection groups

Un snapshot de FlashArray es de coste casi nulo al crearlo y consistente a nivel de crash. Para consistencia de aplicación, congela o notifica a la aplicación antes (por ejemplo, un `CHECKPOINT` en PostgreSQL o el modo backup de la herramienta que uses).

```yaml
# Dentro de la misma lista de tareas del playbook anterior
- name: Snapshot manual con un sufijo legible (db-prod.pre-upgrade)
  purestorage.flasharray.purefa_snap:
    <<: *fa
    name: db-prod
    suffix: pre-upgrade
    state: present

- name: Clon de lectura/escritura del snapshot para pruebas
  purestorage.flasharray.purefa_snap:
    <<: *fa
    name: db-prod
    suffix: pre-upgrade
    target: db-test
    state: copy
```

Para lo recurrente, no programes crones: usa un **protection group**. Reúne volúmenes, un calendario de snapshots (por ejemplo, horario con retención corta y diario con retención larga) y, opcionalmente, un destino de replicación. Cambiar la política en un sitio cambia el comportamiento de todos los volúmenes del grupo.

Recomendaciones:

- Un protection group por **carga de trabajo**, no uno global: la retención de una base de datos no es la de un volumen de ISOs.
- Nombra por servicio y entorno (`pg-prod`, `k8s-dev`) para que la lista de snapshots se entienda sin abrir cada uno.
- Un snapshot en el mismo array **no protege contra la pérdida del array**. Combínalo con replicación o con una copia fuera.

## Replicación y ActiveCluster

- **Replicación asíncrona**: un protection group con destino en otro array. Pensada para recuperación ante desastres con un RPO de minutos u horas.
- **ActiveCluster**: replicación síncrona entre dos arrays, con volúmenes accesibles desde ambos sitios y un mediador que decide quién sigue sirviendo ante un fallo de enlace. Requiere baja latencia entre sitios y red dedicada.
- **ActiveDR**: replicación casi síncrona, orientada a RPO muy bajo sin la restricción de latencia de la síncrona.

!!! warning "Disponibilidad según modelo y licencia"
    Qué opciones de replicación están disponibles, sus requisitos de latencia y la versión mínima de Purity dependen de tu modelo y licencia. Confírmalos con la documentación del fabricante antes de diseñar el DR sobre ellas.

En un homelab o una pyme pequeña, lo habitual es un único array más replicación asíncrona o copia a un repositorio externo. ActiveCluster compensa cuando tienes dos sitios y una ventana de caída casi nula como requisito de negocio.

## Kubernetes con el CSI

Pure ofrece el driver Portworx CSI (PX-CSI) —el antiguo Pure Service Orchestrator se anunció como discontinuado en 2022— que crea y expande volúmenes bajo demanda. Detalles generales del modelo CSI en [Kubernetes CSI](../kubernetes_csi.md). Con una StorageClass bien definida, el desarrollador pide un PVC y el array crea el volumen.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pure-gold
provisioner: pure-csi
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

!!! warning "El nombre del provisioner depende del driver"
    El valor de `provisioner` y los parámetros admitidos (`backend`, tipo de volumen, etc.) dependen del driver y de su versión. Toma el manifiesto de la documentación del driver que instales, no de esta página.

- `WaitForFirstConsumer` evita crear volúmenes antes de saber en qué nodo se planifica el pod, y por tanto en uno sin conectividad al array.
- `allowVolumeExpansion: true` permite crecer online editando el PVC.
- `reclaimPolicy: Retain` en producción: borrar un PVC por error no debe borrar los datos. En desarrollo, `Delete` limpia solo.
- Una StorageClass por nivel (`gold`, `silver`, `bronze`), cada una mapeada a límites distintos en el array.

## Monitorización

Qué vigilar, por orden de utilidad:

1. **Capacidad física y ratio de reducción**: la alerta importante. Un array lleno degrada y acaba rechazando escrituras.
2. **Latencia de lectura y escritura por volumen**: lo que ve la aplicación. Un pico sostenido apunta a un vecino ruidoso o a la red.
3. **IOPS y ancho de banda por volumen**: para identificar quién consume y decidir límites.
4. **Estado de controladoras, discos y rutas**: una ruta caída pasa desapercibida si multipath funciona, hasta que cae la segunda.

Para el almacenamiento de métricas y alertas puedes usar el exportador de Prometheus del fabricante y paneles de Grafana, igual que en el resto de la infraestructura del sitio.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---------|----------------|---------|
| El host no ve el LUN | Iniciador mal declarado en el host o volumen sin presentar | Comparar en la GUI del array el IQN/WWN declarado con el del host y volver a presentar el volumen con `purefa_host` (`volume`) |
| Cada LUN aparece varias veces en el host | Multipath sin configurar | Instalar y habilitar multipath y aplicar la política recomendada por el fabricante |
| Latencia errática en iSCSI | MTU inconsistente o red compartida con gestión | Verificar MTU en toda la ruta, aislar VLAN o red de almacenamiento |
| El espacio libre no sube tras borrar datos | El guest o hipervisor no envía `discard`/`UNMAP` | Activar `discard` en el guest o ejecutar `fstrim` periódicamente |
| El PVC queda en `Pending` | StorageClass inexistente, driver caído o sin conectividad al array | `kubectl describe pvc`, revisar logs del driver CSI y la ruta de red |
| Un volumen degrada a los demás | Sin límites de rendimiento | Aplicar límites de IOPS/ancho de banda (según versión) o mover la carga a otro tier |
| Snapshots que ocupan demasiado | Retención larga en cargas con mucho cambio | Revisar el calendario del protection group y la tasa de cambio del volumen |

## Buenas prácticas

- Trabaja con **host groups** para clústeres: añadir un nodo no debe significar repasar cada volumen.
- Define **protection groups por carga**, con nombres que se entiendan solos, y revisa la retención cada trimestre.
- Vigila el **espacio físico**, no el aprovisionado: el thin provisioning transfiere el riesgo del volumen al array.
- Un snapshot no es un backup. Mantén una copia fuera del array siguiendo [la regla 3-2-1](../../backups/strategy_321.md).
- Documenta qué volumen es de qué servicio. Un volumen sin dueño es un volumen que nadie se atreve a borrar.
- Prueba la **restauración** (clonar un snapshot y montarlo) antes de necesitarla, no durante el incidente.
- Si ya tienes otro array, compara enfoques en [NetApp ONTAP](../netapp/netapp_base.md) antes de duplicar procesos.

## Referencias

- [Documentación oficial de Pure Storage](https://support.purestorage.com/)
- [Portworx CSI (docs.portworx.com)](https://docs.portworx.com/portworx-csi/)
- [Protocolos de almacenamiento](../protocols/protocols.md)
- [Kubernetes CSI](../kubernetes_csi.md)
- [NetApp ONTAP](../netapp/netapp_base.md)
- [Estrategia de backup 3-2-1](../../backups/strategy_321.md)
- [Colección purestorage.flasharray de Ansible](https://docs.ansible.com/projects/ansible/latest/collections/purestorage/flasharray/index.html)
- [purefa_volume](https://docs.ansible.com/projects/ansible/latest/collections/purestorage/flasharray/purefa_volume_module.html)
- [purefa_host](https://docs.ansible.com/projects/ansible/latest/collections/purestorage/flasharray/purefa_host_module.html)
- [purefa_snap](https://docs.ansible.com/projects/ansible/latest/collections/purestorage/flasharray/purefa_snap_module.html)
- [purefa_pg](https://docs.ansible.com/projects/ansible/latest/collections/purestorage/flasharray/purefa_pg_module.html)
