# Pure Storage — Quick Guide

## Summary
Reference designs for mixed workloads using Pure Storage arrays, plus quick integration notes for Kubernetes and virtualization.

## Architecture at a glance
- **FlashArray//X or //XL**: NVMe performance tier for databases, VMs, and latency-sensitive apps.
- **FlashArray//C**: capacity/QLC tier for colder data or replicas; cost/TB similar to hybrid.
- **FlashBlade/Object**: S3/NFS repository for backups, logs, and analytics.
- **ActiveCluster / ActiveDR**: synchronous/asynchronous protection between sites.

## Hybrid layout (SSD + capacity/QLC) for mixed workloads
1) **Hot tier (SSD/NVMe)**: volumes on FlashArray//X with thin provisioning, data reduction on, optional QoS.
2) **Capacity tier (QLC or external HDD target)**: scheduled snapshots/replicas to FlashArray//C or a low-cost NFS/S3 target.
3) **Policies**: protection groups with hourly snapshots + daily replicas; adjust retention by workload tier.
4) **VMware/Proxmox**: use `iSCSI` with multipath or `NFSv3/v4.1`; enable `VMware VAAI` / `vSphere Plugin` for clone/offload.

## Quick best practices
- **Kubernetes**: use the official CSI; `volumeBindingMode: WaitForFirstConsumer`; `allowVolumeExpansion: true` for online growth.
- **Volume classes**: tag volumes by performance (`gold/silver/bronze`) with QoS and map them to StorageClasses.
- **Reclaiming**: frequent snapshots/clones (`purevol copy`) for dev/test; `reclaimPolicy: Delete` in dev, `Retain` in prod.
- **Observability**: Purity exporter for Prometheus to track latency, IOPS, and data reduction.

## Minimal CLI provisioning example

```bash
purevol create db-prod 2T --thin
purevol setattr --qos 20000 --latency 1ms db-prod
purevol connect --host esx01 db-prod
```
