---
title: "Pure Storage — Guía base"
date: 2025-12-07
tags: [storage, pure_storage]
draft: true
updated: 2026-01-25
difficulty: beginner
estimated_time: 1 min
category: Almacenamiento
status: published
last_reviewed: 2026-01-25
prerequisites: ["Ninguno"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Pure Storage — Guía base

## Resumen rápido
Diseños de referencia para workloads mixtos usando arrays Pure Storage y prácticas para integrarlos con Kubernetes y virtualización.

## Arquitectura en breve
- **FlashArray//X o //XL**: tier de alto rendimiento NVMe para bases de datos, VMs y latency-sensitive.
- **FlashArray//C**: tier de capacidad (QLC) para datos fríos o réplicas; útil como “HDD-like” para coste por TB.
- **FlashBlade/Objetos**: repositorio S3/NFS para backups, logs y analítica.
- **ActiveCluster / ActiveDR**: protección síncrona o asíncrona multi-site.

## Implementación híbrida (SSD + HDD/QLC) para workloads mixtos
1) **Tier caliente (SSD/NVMe)**: volúmenes en FlashArray//X, `thin provisioning`, `data reduction` activo, QoS opcional.
2) **Tier capacidad (QLC o destino HDD externo)**: snapshots y réplicas programadas desde FlashArray hacia FlashArray//C o repositorio NFS/S3 de bajo coste.
3) **Políticas**: grupos de protección con snapshots horarios + réplicas diarias; retención diferenciada por workload.
4) **VMware/Proxmox**: usar `iSCSI` con multipath o `NFSv3/v4.1` según preferencia; habilitar `VMware VAAI` / `vSphere Plugin` para offload de clones.

## Buenas prácticas rápidas
- **Kubernetes**: usar el CSI oficial; `volumeBindingMode: WaitForFirstConsumer` para evitar scheduling en nodos sin conectividad; `allowVolumeExpansion: true` para crecimiento online.
- **Volúmenes**: etiquetar por performance (`gold/silver/bronze`) con QoS en FlashArray y mapear a StorageClasses.
- **Reclamación**: snapshots frecuentes y clones (`purevol copy`) para entornos de pruebas; limpiar con `reclaimPolicy: Delete` en dev y `Retain` en prod.
- **Monitoreo**: Purity+Prometheus exporter para latencias, IOPS y data reduction.

## Ejemplo mínimo de provisioning CLI

```bash
purevol create db-prod 2T --thin
purevol setattr --qos 20000 --latency 1ms db-prod
purevol connect --host esx01 db-prod
```
