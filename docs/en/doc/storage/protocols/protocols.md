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

---

I can generate `fio` examples and Prometheus/Grafana dashboard templates if you want.
