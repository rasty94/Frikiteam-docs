```markdown
---
title: Protocolos y Métricas de Almacenamiento
description: Resumen de protocolos (iSCSI, NFS, SMB, Ceph RBD, S3), métricas clave (IOPS, latencia, throughput), y buenas prácticas de medición.
keywords: iops, latencia, throughput, iSCSI, NFS, SMB, rbd, s3, storage protocols, métricas
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

---

Si quieres, puedo generar ejemplos de `fio` y plantillas de dashboard para Prometheus/Grafana.
```
