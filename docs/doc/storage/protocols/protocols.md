---
description: Resumen de protocolos (iSCSI, NFS, SMB, Ceph RBD, S3), métricas clave (IOPS, latencia, throughput), y buenas prácticas de medición.
keywords: iops, latencia, throughput, iSCSI, NFS, SMB, rbd, s3, storage protocols, métricas
updated: 2026-01-25
---

# Protocolos y Métricas de Almacenamiento

Este documento recoge una visión práctica sobre protocolos de almacenamiento comunes y las métricas que debes medir para dimensionar y operar sistemas de almacenamiento:

## Protocolos comunes

- **iSCSI**: Bloque sobre IP, uso típico en entornos VM y bases de datos.
- **NFS**: Sistema de archivos en red, usado por aplicaciones que necesitan compartir ficheros.
- **SMB/CIFS**: Protocolos de archivos orientados a entornos Windows y archivos compartidos.
- **RBD (Ceph RADOS Block Device)**: Bloque distribuido nativo de Ceph.
- **S3 / Object Storage**: Interfaz de objetos, adecuada para backups, datos no estructurados y lakes.

## Métricas clave

- **IOPS** (operaciones por segundo): mide la cantidad de operaciones de E/S.
- **Latencia** (ms): tiempo medio de respuesta por operación (p99, p95).
- **Throughput** (MB/s): ancho de banda efectivo para operaciones secuenciales.
- **Queue depth**: profundidad de colas en hosts y controladoras.
- **Utilización**: uso de CPU/Red/Disco en nodos de almacenamiento.

## Buenas prácticas de medición

- Establecer picos y patrones: medir tanto cargas sostenidas como picos.
- Usar herramientas: `fio` para bloque, `rclone`/`s3bench` para object, `iperf` para red.
- Medir percentiles de latencia (p50/p95/p99) no sólo medias.
- Correlacionar con métricas de red y CPU para identificar cuellos de botella.

## Recomendaciones operativas

- Reservar headroom para picos (ej. +30% IOPS/throughput).
- Evitar sobreaproporcionamiento en capas críticas.
- Usar QoS/limits cuando sea necesario para aislar cargas.

## Profundización en NFS: versiones y pNFS

- **NFSv3**: muy extendido, diseño esencialmente stateless (locks se manejan via lockd), sencillo pero limitado en features como delegations y sesiones.

- **NFSv4 (4.0 / 4.1 / 4.2)**: NFSv4 unifica autenticación, locking y estado en el propio protocolo. Las versiones posteriores añaden:

  - **NFSv4.1**: introduce sesiones y, entre otras extensiones, implementa pNFS (Parallel NFS) que permite acceder a datos en paralelo directamente en los data servers usando distintos layouts (file, block, object).

  - **NFSv4.2**: añade operaciones avanzadas como server-side copy, sparse files, y mejoras en atributos y performance.

> pNFS (Parallel NFS): permite escalar I/O repartiendo datos en múltiples servidores de datos. Requiere soporte en cliente, metadata server y data servers; existen layouts de tipo **FILE**, **BLOCK** y **OBJECT**. Es útil para cargas con alto paralelismo (HPC, grandes clústeres de datos).

## `fio` — ejemplos prácticos

Ejecuta `fio` contra un punto de montaje NFS o un dispositivo de bloque para medir comportamiento. Ejemplos comunes:

1) Random mixed read/write (4k):

```bash
fio --name=randrw --ioengine=libaio --direct=1 --rw=randrw --bs=4k --size=1G \
  --numjobs=4 --runtime=60 --time_based --iodepth=32 --group_reporting \
  --output-format=json --output=randrw.json
```

1) Sequential read (1M) — medir throughput:

```bash
fio --name=seqread --ioengine=libaio --direct=1 --rw=read --bs=1M --size=10G \
  --numjobs=1 --runtime=60 --time_based --group_reporting --output-format=json
```

1) Random write stress (4k):

```bash
fio --name=randwrite --ioengine=libaio --direct=1 --rw=randwrite --bs=4k --size=2G \
  --numjobs=8 --runtime=120 --time_based --iodepth=64 --group_reporting --output-format=json
```

1) Ejemplo de job file (`fio_job.ini`):

```ini
[global]
ioengine=libaio
direct=1
time_based
runtime=60
group_reporting
size=1G

[randread]
bs=4k
rw=randread
iodepth=32
numjobs=4

[randwrite]
bs=4k
rw=randwrite
iodepth=32
numjobs=4
```

Interpretación básica de resultados:

- **IOPS** y **BW** (bandwidth) informan sobre capacidad.
- **lat (latency)** en percentiles (p50/p95/p99) muestra estabilidad y picos.
- Correlacionar iodepth/numjobs para entender si el sistema es CPU/IO/Network bound.

Recomendaciones para pruebas en NFS

- Montar con opciones apropiadas en el cliente (ej. `noatime,nodiratime`, ajustar `rsize`/`wsize` si es necesario).
- Realizar pruebas desde varios clientes para simular concurrencia real.
- Asegurarse de que la red (MTU, switch buffers) no se convierta en cuello de botella.

---

