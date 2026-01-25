---
description: Overview of common storage protocols (iSCSI, NFS, SMB, RBD, S3), key metrics (IOPS, latency, throughput), and measurement best practices.
keywords: iops, latency, throughput, iSCSI, NFS, SMB, rbd, s3, storage protocols, metrics
---

# Storage Protocols and Metrics

This page provides a practical view on common storage protocols and the metrics you should monitor for sizing and operating storage systems:

## Common protocols

- **iSCSI**: Block over IP, common for VMs and databases.
- **NFS**: Network file system for file sharing among apps.
- **SMB/CIFS**: File protocol commonly used in Windows environments.
- **RBD (Ceph RADOS Block Device)**: Ceph native block device.
- **S3 / Object Storage**: Object interface for backups, unstructured data and data lakes.

## Key metrics

- **IOPS** (operations/sec): measures number of I/O operations.
- **Latency** (ms): response time per operation (p99, p95).
- **Throughput** (MB/s): effective bandwidth for sequential ops.
- **Queue depth**: queue depths at hosts and controllers.
- **Utilization**: CPU/Network/Disk utilization on storage nodes.

## Measurement best practices

- Capture both steady-state and peak patterns.
- Use tools: `fio` for block, `rclone`/`s3bench` for object, `iperf` for network.
- Measure latency percentiles (p50/p95/p99) not only averages.
- Correlate with network/CPU metrics to find bottlenecks.

## Operational recommendations

- Design headroom for peaks (e.g., +30% IOPS/throughput).
- Avoid oversubscription in critical tiers.
- Use QoS/limits to isolate noisy neighbors.

## Quick choice: iSCSI vs NFS vs SMB
- **Databases/VMs**: iSCSI/RBD (block) for latency and queue control; multipath + ALUA enabled.
- **Shared apps**: NFSv4.1 (pNFS if available) for file workloads or RWX containers.
- **End-user shares**: SMB with signing/encryption as policy requires.
- **Containers RWX**: NFS/SMB CSI when POSIX/ACL semantics are needed.
- **Containers RWO**: RBD/iSCSI CSI for statefulsets and databases.

## Restic/Borg with distributed storage (Ceph/MinIO)
- **Repo**: S3 (Ceph RGW/MinIO) with versioning on; separate buckets per environment.
- **Concurrency**: cap `--limit-upload`/`--max-repack-size` to avoid overloading OSDs during prune/compact.
- **Encryption**: manage keys outside the cluster; rotate and test restores regularly.
- **Retention**: `keep-daily/weekly/monthly`; schedule `restic forget --prune` off-peak.
- **Health**: monthly restore tests into an isolated bucket; measure backend latency/throughput.

## Container storage optimization (Kubernetes + CSI)
- **StorageClasses**: per tier (`gold/silver/bronze`) with proper `reclaimPolicy` (`Retain` prod, `Delete` dev).
- **Binding**: `volumeBindingMode: WaitForFirstConsumer` to avoid scheduling on nodes without storage paths.
- **RWX**: NFS/SMB CSI or RWX provisioners; verify `fsGroup`/permissions.
- **Snapshots/clones**: define `VolumeSnapshotClass` and use clones for fast dev/test.
- **Topology**: `allowedTopologies` with zone/rack labels to prevent cross-rack mounts.

Example StorageClass (block):

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
	name: gold-rbd
provisioner: rook-ceph.rbd.csi.ceph.com
parameters:
	pool: rbd-gold
	imageFeatures: layering,exclusive-lock,object-map,fast-diff,deep-flatten
allowVolumeExpansion: true
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
```
