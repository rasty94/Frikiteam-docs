---
title: "NetApp — Introducción"
date: 2025-12-07
tags: [storage, netapp]
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

# NetApp — Guía base

## Resumen
Diseños rápidos para virtualización (VMware/Proxmox) y optimización de capacidad con deduplicación y compresión en ONTAP.

## Virtualización (VMware / Proxmox)
- **Protocolos**: NFSv3/v4.1 para simplicidad y clones rápidos; iSCSI multipath para bases de datos o VMs sensibles a latencia.
- **Datastores**: un FlexVol por datastore; export-policy específica; `volume autosize` habilitado con límites.
- **VMware**: activar VAAI y NFSv4.1 con sesiones múltiples; usar `snapmirror-label` en snapshots para DR.
- **Proxmox**: NFS con `no_root_squash` y `rsize/wsize` altos; iSCSI con `multipath` y `queue_depth` ajustado en hosts.

## Eficiencia (dedupe/compresión) y snapshots
- Habilitar **inline dedupe + inline compression** en FlexVol; usar `storage efficiency` en AFF/ASA.
- Snapshots por política: por ejemplo `cada hora 24`, `diario 7`, `semanal 4`; etiquetar para SnapMirror/Backup.
- Thin provisioning habilitado; controlar crecimiento con cuotas en qtrees si compartes datasets.

## DR y replicación
- **SnapMirror** asíncrono entre clústeres; usar etiquetas de snapshots para seleccionar qué replicar.
- **SnapVault** para retención larga; programar `Update` después de snapshots críticos (post-backup DB).
- **FabricPool**: tiering a S3 (on-prem o cloud) para datos fríos; políticas `auto` o `snapshot-only` según el workload.

## Kubernetes (CSI Astra Trident)
- Usar Trident CSI con StorageClasses por tier (`ontap-san`, `ontap-nas`, `ontap-san-economy`).
- `volumeBindingMode: WaitForFirstConsumer` y `allowVolumeExpansion: true` para crecimiento online.
- Export-policies dedicadas para nodos de Kubernetes; QoS adaptado por StorageClass (`gold/silver/bronze`).
