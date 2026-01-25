---
title: "Ceph — Optimización y Planificación de Capacidad"
description: "Documentación sobre ceph — optimización y planificación de capacidad"
tags: ['storage']
updated: 2026-01-25
difficulty: expert
estimated_time: 1 min
category: Almacenamiento
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ceph — Optimización y Planificación de Capacidad

## Resumen
Tuning mínimo para clústeres Ceph con cargas de bases de datos y bloques de alto rendimiento.

## Checklist rápido (bases de datos sobre RBD)
- **Pools**: réplicas `size=3` (mínimo `min_size=2`), `pg_num` calculado por OSDs y tamaño; evitar EC para OLTP.
- **WAL/DB en NVMe**: separar `bluestore_block_db`/`bluestore_block_wal` en NVMe/SSD de baja latencia.
- **Red**: 25/40G recomendado, MTU 9000 opcional si la red completa lo soporta; `ms_bind_ipv4=true` y `ms_bind_ipv6=false` si no usas IPv6.
- **RBD features**: habilitar `exclusive-lock, object-map, fast-diff, deep-flatten` para snapshots y replays rápidos.
- **Cliente (qemu/libvirt)**: `cache=none`, `io=native`, `discard=on`, align 4K; preferir `virtio-scsi` con multiqueue.
- **FS invitado**: `ext4` o `xfs` con `noatime`; evitar `barrier=0`.

## Pool y RBD tuning para PostgreSQL/MySQL
- Crear un pool dedicado para DB OLTP (ej. `db-rbd`) con réplicas, `target_size_ratio` para balanceo, y `pg_autoscaler` activado.
- Establecer `rbd_cache=true`, `rbd_cache_writethrough_until_flush=false`, `rbd_cache_max_dirty=33554432` para latencias bajas; validar con la versión de librbd.
- Usar `rbd exclusive-lock` y `rbd feature enable ...` en cada imagen; habilitar `discard` en el guest para devolver bloques.

Ejemplo de `ceph config set` (adaptar a tu versión):

```bash
ceph config set osd osd_memory_target 4096M
ceph config set osd bluestore_cache_autotune true
ceph config set osd bluestore_compression_mode aggressive
ceph config set mon mon_osd_down_out_interval 600
```

Prueba rápida con `fio` desde un host (imagen mapeada como bloque):

```bash
fio --name=db-randrw --filename=/dev/rbd0 --ioengine=libaio --direct=1 \
	--bs=8k --rw=randrw --rwmixread=70 --iodepth=32 --numjobs=4 --time_based \
	--runtime=120 --group_reporting
```

## Monitorización y mantenimiento
- Grafana: paneles de latencia `osd.op_r_lat, op_w_lat`, `client_io_rate` y saturación de NIC.
- Alertas: `pg_degraded`, `pg_backfill`, `nearfull` y `slow ops` con umbrales conservadores.
- Revisar rebalanceos: si son frecuentes, ajusta `mon_osd_min_down_reporters` y verifica CRUSH/weights.
