# NetApp — Quick Guide

## Summary
Actionable guidance for virtualization (VMware/Proxmox) and ONTAP efficiency (dedupe/compression) with DR patterns.

## Virtualization (VMware / Proxmox)
- **Protocols**: NFSv3/v4.1 for simplicity and fast clones; iSCSI multipath for latency-sensitive DB/VMs.
- **Datastores**: one FlexVol per datastore; dedicated export-policy; enable `volume autosize` with limits.
- **VMware**: enable VAAI and NFSv4.1 sessions; use `snapmirror-label` on snapshots for DR selection.
- **Proxmox**: NFS with `no_root_squash`, tuned `rsize/wsize`; iSCSI with multipath and tuned host `queue_depth`.

## Efficiency (dedupe/compress) and snapshots
- Turn on **inline dedupe + inline compression** on FlexVol; use `storage efficiency` (AFF/ASA).
- Snapshot policies: e.g., `hourly 24`, `daily 7`, `weekly 4`; tag snapshots for SnapMirror/backup workflows.
- Thin provisioning on; control growth with qtree quotas when sharing datasets.

## DR and replication
- **SnapMirror** async between clusters; use snapshot labels to decide what to replicate.
- **SnapVault** for long retention; schedule updates after critical snapshots (post-DB-backup).
- **FabricPool**: tier cold blocks to S3 (on-prem/cloud) with `auto` or `snapshot-only` policies based on workload.

## Kubernetes (CSI Astra Trident)
- Use Trident CSI with per-tier StorageClasses (`ontap-san`, `ontap-nas`, `ontap-san-economy`).
- `volumeBindingMode: WaitForFirstConsumer` and `allowVolumeExpansion: true` for online growth.
- Dedicated export-policies for Kubernetes nodes; QoS mapped to StorageClasses (`gold/silver/bronze`).
