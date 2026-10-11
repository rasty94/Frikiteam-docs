---
title: "Ceph — Optimización y Planificación de Capacidad"
description: "Tuning de Ceph para bloques RBD y bases de datos: pools, BlueStore, memoria de OSD, red, cliente, capacidad y mantenimiento en clústeres propios."
keywords: "ceph, rbd, bluestore, osd_memory_target, pg autoscaler, crush, nearfull, fio, wal, db, rendimiento, capacidad"
tags: ['storage']
updated: 2026-10-10
difficulty: expert
estimated_time: 15 min
category: Almacenamiento
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Un clúster Ceph funcionando"
  - "[Ceph — Guía base](ceph_base.md)"
  - "Conocimientos de redes y de almacenamiento en bloque"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ceph — Optimización y Planificación de Capacidad

## El problema

Ceph arranca con valores razonables y un clúster pequeño funciona bien durante meses. Después llega la base de datos sobre RBD y aparecen las latencias de cola, o crece el uso y un día un OSD llega al 95 % y el clúster deja de aceptar escrituras. Ninguna de las dos cosas es un fallo de Ceph: son decisiones de diseño (réplicas, DB en NVMe, red, reservas de capacidad) que se tomaron por defecto.

Esta página reúne los ajustes que más pesan en un clúster propio con cargas de bloque y bases de datos, y cómo comprobar con comandos si lo que cambiaste sirvió. Primero se mide, luego se toca.

!!! note "Qué cubre y qué no"
    Aquí va el tuning y la planificación de capacidad. La instalación y la arquitectura están en [Ceph — Guía base](ceph_base.md); el diagnóstico de incidencias, en [Troubleshooting Ceph](troubleshooting_ceph.md); y el uso con PostgreSQL, en [PostgreSQL sobre Ceph](../postgresql_ceph.md).

!!! warning "Las opciones cambian entre versiones"
    Los nombres, valores por defecto y comportamiento de muchas opciones (caché de BlueStore, autoscaler, `bluestore_compression_mode`) varían entre versiones de Ceph. Antes de aplicar un ajuste, consulta con `ceph config help <opción>` qué significa en tu versión y no copies valores de otro clúster sin medir.

## 📋 Tabla de Contenidos

- [Medir antes de tocar](#medir-antes-de-tocar)
- [Pools y placement groups](#pools-y-placement-groups)
- [BlueStore: WAL/DB y memoria](#bluestore-waldb-y-memoria)
- [Red](#red)
- [RBD y cliente](#rbd-y-cliente)
- [Prueba con fio](#prueba-con-fio)
- [Planificación de capacidad](#planificacion-de-capacidad)
- [Recuperación y rebalanceo](#recuperacion-y-rebalanceo)
- [Monitorización y alertas](#monitorizacion-y-alertas)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Medir antes de tocar

Tres comandos dan la foto base. Guarda su salida antes y después de cada cambio para comparar.

```bash
# Estado global: salud, OSDs, PGs, I/O de clientes
ceph -s

# Uso por OSD y por clase; busca desequilibrios
ceph osd df

# Qué hace el autoscaler de PGs con cada pool
ceph osd pool autoscale-status
```

En `ceph osd df` fíjate en la columna de uso (`%USE`) y en la dispersión entre OSDs: si un OSD está bastante más lleno que la media, la capacidad útil del clúster la marca él, no la media. En `ceph -s`, cualquier `slow ops` o PG que no esté `active+clean` debe resolverse antes de afinar nada.

## Pools y placement groups

- **Réplicas**: `size=3` y `min_size=2` para datos que importan. Con `size=2` o `min_size=1` ganas capacidad, pero un fallo doble puede perder datos o aceptar escrituras sin copia redundante.
- **Erasure coding**: ahorra capacidad, pero cada escritura pequeña pesa más. Evítalo en OLTP; úsalo para objetos fríos o backups.
- **Un pool por tipo de carga**: un pool para bases de datos, otro para discos de VM, otro para datos fríos, cada uno con su regla CRUSH (por ejemplo, restringida a una clase de dispositivo).
- **PGs**: deja el autoscaler en `on` y anota a Ceph cuánto debería ocupar cada pool con `target_size_ratio`; así reparte los PGs desde el principio y no reorganiza cuando el pool crezca.

```bash
# Réplicas del pool de bases de datos
ceph osd pool set db-rbd size 3
ceph osd pool set db-rbd min_size 2

# Autoscaler activo y proporción esperada del clúster
ceph osd pool set db-rbd pg_autoscale_mode on
ceph osd pool set db-rbd target_size_ratio 0.3

# Etiquetar el pool para RBD
ceph osd pool application enable db-rbd rbd
```

!!! tip "Revisa tras cada cambio de PGs"
    Un cambio en el número de PGs dispara movimiento de datos. Hazlo en horas valle y vigila `ceph -s` hasta que todo vuelva a `active+clean`.

## BlueStore: WAL/DB y memoria

BlueStore guarda los datos en el dispositivo principal y los metadatos (RocksDB) y el registro de escritura (WAL) donde le digas. En discos rotativos, mover DB/WAL a NVMe o SSD es el cambio con más impacto sobre la latencia.

- **DB/WAL en dispositivo rápido**: se separan al crear el OSD (con `cephadm` mediante una especificación de servicio de OSD, que asigna dispositivos de datos y de DB). Dimensiona el DB con margen: si se llena, RocksDB desborda al disco lento y la latencia se desploma.
- **Memoria por OSD**: `osd_memory_target` fija cuánta memoria intenta usar cada OSD; el caché de BlueStore se autoajusta alrededor de ese valor. El total de todos los OSD de un nodo más el resto de servicios no debe pasar de la RAM física, o el nodo entra en swap.
- **Compresión**: se activa por pool o por OSD. Ayuda con datos compresibles y cuesta CPU; mídelo con tus datos reales.

```bash
# Memoria objetivo por OSD (valor en bytes; 4 GiB)
ceph config set osd osd_memory_target 4294967296

# Autoajuste del caché de BlueStore
ceph config set osd bluestore_cache_autotune true

# Ver el valor efectivo de una opción
ceph config get osd osd_memory_target

# Opciones modificadas respecto al valor por defecto
ceph config dump
```

El cálculo práctico: RAM del nodo, menos lo que usan el SO y otros servicios (monitor, manager, contenedores), dividido entre el número de OSD. Si el resultado queda por debajo del valor por defecto de tu versión, es mejor reducir OSD por nodo que forzar un valor mínimo.

!!! warning "Compresión y versión"
    `bluestore_compression_mode` admite varios modos y su comportamiento por defecto depende de la versión. En bases de datos con páginas ya comprimidas o cifradas no aporta nada y consume CPU. Pruébalo primero en un pool de prueba.

## Red

- **Ancho de banda**: 25 GbE o más es lo razonable para NVMe. Con 1 GbE, la red es el cuello de botella antes que los discos.
- **Red pública y de clúster**: separar el tráfico de replicación del de clientes reduce interferencias. En un clúster pequeño, una red única con ancho de banda suficiente es más sencilla de operar.
- **MTU 9000**: solo si **toda** la ruta (NIC, switches, VLAN) lo soporta. Un salto a 1500 en medio provoca fallos intermitentes difíciles de diagnosticar.
- **IPv6**: si no lo usas, no lo enlaces (`ms_bind_ipv6=false`); si lo usas, hazlo de forma consistente en todo el clúster.
- **Latencia entre nodos**: Ceph escribe en todas las réplicas antes de confirmar, así que la latencia de la red suma a cada escritura.

## RBD y cliente

- **Features de la imagen**: `exclusive-lock`, `object-map`, `fast-diff` y `deep-flatten` aceleran snapshots, clones y diferencias. Actívalas en imágenes de producción y comprueba la compatibilidad con el kernel o la librería del cliente.
- **Caché de RBD** (librbd): en bases de datos suele convenir `rbd_cache` activo con escritura segura (`rbd_cache_writethrough_until_flush`); ajusta tamaños con medidas, no por intuición.
- **QEMU/libvirt**: `cache=none`, `io=native` y `discard=on`, con `virtio-scsi` y varias colas. Alinea las particiones del guest a 4K.
- **Sistema de ficheros del guest**: `ext4` o `xfs` con `noatime`; no desactives las barreras.
- **Devolver espacio**: `discard` en el guest y `fstrim` periódico permiten que Ceph libere los bloques; sin ellos, el espacio de imágenes finas solo crece.

```bash
# Features de una imagen
rbd info db-rbd/pg-data

# Activar features en una imagen existente
rbd feature enable db-rbd/pg-data exclusive-lock object-map fast-diff

# Espacio real usado por la imagen
rbd du db-rbd/pg-data
```

!!! warning "Orden de las features"
    `object-map` y `fast-diff` dependen de `exclusive-lock`. En imágenes ya en uso, tras activarlas puede hacer falta reconstruir el mapa de objetos (`rbd object-map rebuild`). Hazlo con la imagen sin carga.

## Prueba con fio

Mide siempre con un patrón parecido al real. Para una base de datos OLTP: bloques pequeños, mezcla lectura/escritura y concurrencia moderada. Ejecútalo sobre una imagen de prueba, no sobre datos reales.

```bash
fio --name=db-randrw --filename=/dev/rbd0 --ioengine=libaio --direct=1 \
	--bs=8k --rw=randrw --rwmixread=70 --iodepth=32 --numjobs=4 --time_based \
	--runtime=120 --group_reporting
```

Fíjate en la **latencia de cola** (percentiles altos), no solo en IOPS medios. Una media buena con cola mala se nota en la base de datos como saltos esporádicos. Repite la prueba tras cada cambio de uno en uno, y de nuevo con el clúster ocupado (recuperación en curso) para saber el peor caso.

## Planificación de capacidad

Ceph no es un array: la capacidad utilizable es menor que la suma de los discos.

- **Replicación x3**: la capacidad útil es un tercio de la bruta. Con erasure coding es mayor, a costa de rendimiento.
- **Reserva para fallos**: el clúster debe poder reconstruir la pérdida de un nodo (o de un dominio de fallo) con el espacio que queda. Planifica para que, tras perder lo que tu diseño tolera, el uso siga por debajo de los umbrales.
- **Umbrales**: Ceph avisa en `nearfull`, deja de rebalancear en `backfillfull` y bloquea escrituras en `full`. Los valores por defecto son conservadores; no los subas para ganar espacio, añade capacidad.
- **Desequilibrio entre OSD**: el OSD más lleno marca el límite. El módulo `balancer` redistribuye PGs para igualar el uso; revisa que esté activo.
- **Crecimiento**: añadir OSD provoca rebalanceo. Hazlo en lotes y con límites de recuperación si hay cargas sensibles.

```bash
# Uso de cada OSD y desviación
ceph osd df tree

# Estado del módulo balancer
ceph balancer status

# Uso por pool
ceph df
```

## Recuperación y rebalanceo

Recuperar y rebalancear compiten con los clientes por disco y red. Dos palancas:

- **Límite de recuperación**: reducir la prioridad de backfill y recovery protege la latencia de clientes a costa de tardar más en volver a la redundancia total. Los nombres de las opciones de scheduler cambian entre versiones; consúltalos con `ceph config help`.
- **`mon_osd_down_out_interval`**: tiempo que espera el monitor antes de marcar `out` un OSD caído y empezar a reconstruir. Un valor mayor evita rebalanceos por reinicios cortos, y uno menor reduce la ventana sin redundancia.

```bash
# Esperar 10 minutos antes de marcar out un OSD caído
ceph config set mon mon_osd_down_out_interval 600

# Antes de una parada planificada de un nodo
ceph osd set noout
# ... mantenimiento ...
ceph osd unset noout
```

Si hay rebalanceos frecuentes sin cambios en el clúster, revisa los pesos CRUSH, la red entre nodos y los OSD que flapean.

## Monitorización y alertas

- **Métricas**: el módulo `prometheus` del manager exporta las métricas a Prometheus. En Grafana: latencia de lectura y escritura de OSD, I/O de clientes, saturación de NIC y uso por OSD.
- **Alertas útiles**: PG degradados o en backfill durante mucho tiempo, `nearfull`, `slow ops`, OSD caídos y desviación de reloj entre monitores.
- **Umbrales conservadores**: alerta de uso con margen suficiente para reconstruir un nodo, no cuando ya está casi lleno.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---------|----------------|---------|
| Latencia de escritura alta en HDD | DB/WAL en el mismo disco rotativo | Mover DB/WAL a NVMe/SSD al recrear el OSD |
| `slow ops` repetidos | Disco o red saturados, OSD con problemas | `ceph -s`, localizar el OSD afectado y revisar el disco y la red del nodo |
| Un OSD mucho más lleno que el resto | Distribución de PGs desigual | Revisar `ceph balancer status`; activar el balancer o ajustar pesos |
| Aviso `nearfull` | Capacidad cerca del límite | Añadir OSD, borrar datos o reducir réplicas solo si el diseño lo permite |
| Nodo en swap, OSD lentos | La suma de `osd_memory_target` supera la RAM | Bajar `osd_memory_target` o reducir OSD por nodo |
| Clientes lentos durante la recuperación | Backfill compite con el tráfico de clientes | Reducir la prioridad de recuperación y programar los cambios en horas valle |
| Rebalanceos tras reiniciar un nodo | `down_out_interval` demasiado bajo | Subirlo, o usar `noout` en mantenimientos planificados |
| El espacio de la imagen no baja al borrar datos | El guest no envía `discard` | Activar `discard` y ejecutar `fstrim` |

## Buenas prácticas

- Mide antes y después de cada cambio, de uno en uno, y guarda las salidas.
- Un pool por tipo de carga, con `size=3` y `min_size=2` para lo importante.
- DB/WAL en NVMe cuando el almacenamiento principal es rotativo, con margen de tamaño.
- Calcula `osd_memory_target` con la RAM real del nodo, no con la cifra de otro clúster.
- No subas los umbrales de `full` para ganar espacio: añade capacidad antes de llegar.
- Usa `noout` en mantenimientos planificados y quítalo después.
- Revisa `ceph config help <opción>` en tu versión antes de copiar ajustes de tutoriales.
- Prueba la recuperación en un clúster de laboratorio antes de necesitarla en producción.

## Referencias

- [Documentación oficial de Ceph](https://docs.ceph.com/)
- [Ceph — Guía base](ceph_base.md)
- [Troubleshooting Ceph](troubleshooting_ceph.md)
- [PostgreSQL sobre Ceph](../postgresql_ceph.md)
- [Kubernetes CSI](../kubernetes_csi.md)
