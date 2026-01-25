---
title: "Ceph — Optimization and Capacity Planning"
description: "Ceph tuning for high-performance block workloads and database pools."
tags: ['storage']
updated: 2026-01-25
difficulty: expert
estimated_time: 1 min
category: Storage
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ceph — Optimization and Capacity Planning

## Summary
Minimal tuning for Ceph clusters running high-performance block workloads (databases and VMs).

## Quick checklist (databases on RBD)
- **Pools**: replicas `size=3` (minimum `min_size=2`), `pg_num` sized for OSDs; avoid EC for OLTP.
- **WAL/DB on NVMe**: place `bluestore_block_db`/`bluestore_block_wal` on low-latency NVMe/SSD devices.
- **Network**: 25/40G recommended, MTU 9000 only if the full path supports it; set `ms_bind_ipv4=true` and `ms_bind_ipv6=false` when IPv6 is unused.
- **RBD features**: enable `exclusive-lock, object-map, fast-diff, deep-flatten` to accelerate snapshots and resyncs.
- **Client (qemu/libvirt)**: `cache=none`, `io=native`, `discard=on`, 4K alignment; prefer `virtio-scsi` with multiqueue.
- **Guest FS**: `ext4` or `xfs` with `noatime`; avoid disabling barriers.

## Pool and RBD tuning for PostgreSQL/MySQL
- Create a dedicated OLTP pool (e.g., `db-rbd`) with replicas, `target_size_ratio` for autoscaler hints, and enable `pg_autoscaler`.
- Set `rbd_cache=true`, `rbd_cache_writethrough_until_flush=false`, `rbd_cache_max_dirty=33554432` for low latency (verify against your librbd version).
- Enable `rbd exclusive-lock` and `rbd feature enable ...` per image; enable `discard` in the guest to reclaim blocks.

Example `ceph config set` (adjust to your version):

```bash
ceph config set osd osd_memory_target 4096M
ceph config set osd bluestore_cache_autotune true
ceph config set osd bluestore_compression_mode aggressive
ceph config set mon mon_osd_down_out_interval 600
```

Quick `fio` smoke test (image mapped as block device):

```bash
fio --name=db-randrw --filename=/dev/rbd0 --ioengine=libaio --direct=1 \
	--bs=8k --rw=randrw --rwmixread=70 --iodepth=32 --numjobs=4 --time_based \
	--runtime=120 --group_reporting
```

## Monitoring and operations
- Grafana: watch `osd.op_r_lat`, `osd.op_w_lat`, `client_io_rate`, and NIC saturation.
- Alerts: `pg_degraded`, `pg_backfill`, `nearfull`, `slow ops` with conservative thresholds.
- Rebalance hygiene: if rebalances are frequent, tune `mon_osd_min_down_reporters` and review CRUSH weights/placement groups.
