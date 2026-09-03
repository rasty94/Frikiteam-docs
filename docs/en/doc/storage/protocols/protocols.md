---
title: "Storage Protocols and Metrics"
tags: ['storage']
description: Overview of storage protocols (iSCSI, NFS, SMB, Ceph RBD, S3), key metrics (IOPS, latency, throughput), and measurement best practices.
keywords: iops, latency, throughput, iSCSI, NFS, SMB, rbd, s3, storage protocols, metrics
updated: 2026-09-03
difficulty: advanced
estimated_time: 10 min
category: Storage
status: published
last_reviewed: 2026-09-03
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Storage Protocols and Metrics

This document gathers a practical overview of common storage protocols and the metrics you should measure to size and operate storage systems:

## Common protocols

- **iSCSI**: Block over IP, typically used in VM environments and databases.
- **NFS**: Network file system, used by applications that need to share files.
- **SMB/CIFS**: File protocols oriented toward Windows environments and shared files.
- **RBD (Ceph RADOS Block Device)**: Ceph's native distributed block device.
- **S3 / Object Storage**: Object interface, suitable for backups, unstructured data and lakes.

## Key metrics

- **IOPS** (operations per second): measures the number of I/O operations.
- **Latency** (ms): average response time per operation (p99, p95).
- **Throughput** (MB/s): effective bandwidth for sequential operations.
- **Queue depth**: queue depth on hosts and controllers.
- **Utilization**: CPU/network/disk usage on storage nodes.

## Measurement best practices

- Establish peaks and patterns: measure both sustained loads and peaks.
- Use tools: `fio` for block, `rclone`/`s3bench` for object, `iperf` for network.
- Measure latency percentiles (p50/p95/p99), not just averages.
- Correlate with network and CPU metrics to identify bottlenecks.

## Operational recommendations

- Reserve headroom for peaks (e.g., +30% IOPS/throughput).
- Avoid overprovisioning in critical tiers.
- Use QoS/limits when needed to isolate workloads.

## Deep dive into NFS: versions and pNFS

- **NFSv3**: very widespread, essentially stateless design (locks are handled via lockd), simple but limited in features such as delegations and sessions.

- **NFSv4 (4.0 / 4.1 / 4.2)**: NFSv4 unifies authentication, locking and state into the protocol itself. Later versions add:

  - **NFSv4.1**: introduces sessions and, among other extensions, implements pNFS (Parallel NFS), which allows data to be accessed in parallel directly on the data servers using different layouts (file, block, object).

  - **NFSv4.2**: adds advanced operations such as server-side copy, sparse files, and improvements in attributes and performance.

> pNFS (Parallel NFS): allows I/O to scale by spreading data across multiple data servers. It requires support on the client, metadata server and data servers; there are **FILE**, **BLOCK** and **OBJECT** layout types. It's useful for workloads with high parallelism (HPC, large data clusters).

## `fio` — practical examples

Run `fio` against an NFS mount point or a block device to measure behavior. Common examples:

1) Random mixed read/write (4k):

```bash
fio --name=randrw --ioengine=libaio --direct=1 --rw=randrw --bs=4k --size=1G \
  --numjobs=4 --runtime=60 --time_based --iodepth=32 --group_reporting \
  --output-format=json --output=randrw.json
```

1) Sequential read (1M) — measuring throughput:

```bash
fio --name=seqread --ioengine=libaio --direct=1 --rw=read --bs=1M --size=10G \
  --numjobs=1 --runtime=60 --time_based --group_reporting --output-format=json
```

1) Random write stress (4k):

```bash
fio --name=randwrite --ioengine=libaio --direct=1 --rw=randwrite --bs=4k --size=2G \
  --numjobs=8 --runtime=120 --time_based --iodepth=64 --group_reporting --output-format=json
```

1) Example job file (`fio_job.ini`):

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

Basic interpretation of results:

- **IOPS** and **BW** (bandwidth) report on capacity.
- **lat (latency)** in percentiles (p50/p95/p99) shows stability and spikes.
- Correlate iodepth/numjobs to understand whether the system is CPU/IO/network bound.

Recommendations for NFS testing

- Mount with appropriate client options (e.g. `noatime,nodiratime`, adjust `rsize`/`wsize` if needed).
- Run tests from several clients to simulate real concurrency.
- Make sure the network (MTU, switch buffers) doesn't become a bottleneck.

## Quick choice: iSCSI vs NFS vs SMB
- **Databases/VMs**: iSCSI/RBD (block) for latency and queue control; multipath and ALUA enabled.
- **Shared between apps**: NFSv4.1 (pNFS if applicable) for file workloads or RWX in containers.
- **Users/Office**: SMB for desktop and profiles; enable signing/encryption per policy.
- **RWX containers**: NFS (CSI) or SMB CSI if the app requires Windows ACLs.
- **RWO containers**: RBD/iSCSI CSI for databases on Kubernetes.

## Restic/Borg with distributed storage (Ceph/MinIO)
- **Repository**: S3 (Ceph RGW/MinIO) with versioning enabled; use dedicated buckets per environment.
- **Concurrency**: limit `--limit-upload`/`--max-repack-size` to avoid saturating OSDs during recompaction.
- **Encryption**: keys managed outside the cluster; periodic rotation and restore testing.
- **Retention**: `keep-daily/weekly/monthly` policies; schedule `restic forget --prune` off peak hours.
- **Health**: monthly restore tests into an isolated bucket; validate backend latency/throughput.

## Storage optimization for containers (Kubernetes + CSI)
- **StorageClasses**: define per tier (`gold/silver/bronze`) with the appropriate `reclaimPolicy` (`Retain` prod, `Delete` dev).
- **Binding**: `volumeBindingMode: WaitForFirstConsumer` to avoid scheduling on nodes without storage connectivity.
- **RWX**: NFS/SMB CSI or RWX-type provisioner solutions; validate `fsGroup` and permissions.
- **Snapshots/clones**: create a `VolumeSnapshotClass` and use clones for quick testing.
- **Topology**: use `allowedTopologies` and zone/rack labels to avoid unnecessary cross-rack mounts.

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

## Related links

- [fio Example](examples/fio_example.md) — how to measure IOPS, latency and bandwidth without fooling yourself, with the four canonical profiles and the mistakes that invalidate a measurement.
- [Kubernetes CSI](../kubernetes_csi.md) — these same protocols seen from dynamic volume provisioning.

---
