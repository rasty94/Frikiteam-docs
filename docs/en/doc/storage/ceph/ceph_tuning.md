---
title: "Ceph — Optimization and Capacity Planning"
description: "Ceph tuning for RBD block storage and databases: pools, BlueStore, OSD memory, network, client, capacity and maintenance in self-hosted clusters."
keywords: "ceph, rbd, bluestore, osd_memory_target, pg autoscaler, crush, nearfull, fio, wal, db, performance, capacity"
tags: ['storage']
updated: 2026-10-10
difficulty: expert
estimated_time: 15 min
category: Storage
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "A working Ceph cluster"
  - "[Ceph — Base Guide](ceph_base.md)"
  - "Networking and block storage knowledge"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ceph — Optimization and Capacity Planning

## The problem

Ceph starts with reasonable defaults and a small cluster runs fine for months. Then the database on RBD arrives and tail latencies show up, or usage grows and one day an OSD hits 95% and the cluster stops accepting writes. Neither is a Ceph failure: they are design decisions (replicas, DB on NVMe, network, capacity reserves) that were left at their defaults.

This page gathers the settings that weigh most in a self-hosted cluster with block and database workloads, and how to check with commands whether what you changed helped. Measure first, then touch.

!!! note "What this covers and what it does not"
    This is tuning and capacity planning. Installation and architecture are in [Ceph — Base Guide](ceph_base.md); incident diagnosis, in [Ceph Troubleshooting](troubleshooting_ceph.md); and usage with PostgreSQL, in [PostgreSQL on Ceph](../postgresql_ceph.md).

!!! warning "Options change between versions"
    The names, defaults and behavior of many options (BlueStore cache, autoscaler, `bluestore_compression_mode`) vary between Ceph versions. Before applying a setting, check with `ceph config help <option>` what it means in your version and do not copy values from another cluster without measuring.

## 📋 Table of Contents

- [Measure before touching](#measure-before-touching)
- [Pools and placement groups](#pools-and-placement-groups)
- [BlueStore: WAL/DB and memory](#bluestore-waldb-and-memory)
- [Network](#network)
- [RBD and client](#rbd-and-client)
- [Testing with fio](#testing-with-fio)
- [Capacity planning](#capacity-planning)
- [Recovery and rebalancing](#recovery-and-rebalancing)
- [Monitoring and alerts](#monitoring-and-alerts)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Measure before touching

Three commands give the baseline picture. Keep their output before and after each change to compare.

```bash
# Global state: health, OSDs, PGs, client I/O
ceph -s

# Usage per OSD and per class; look for imbalances
ceph osd df

# What the PG autoscaler does with each pool
ceph osd pool autoscale-status
```

In `ceph osd df`, look at the usage column (`%USE`) and the spread between OSDs: if one OSD is well above the average, the cluster's usable capacity is set by it, not by the average. In `ceph -s`, any `slow ops` or any PG that is not `active+clean` must be resolved before tuning anything.

## Pools and placement groups

- **Replicas**: `size=3` and `min_size=2` for data that matters. With `size=2` or `min_size=1` you gain capacity, but a double failure can lose data or accept writes without a redundant copy.
- **Erasure coding**: saves capacity, but every small write costs more. Avoid it for OLTP; use it for cold objects or backups.
- **One pool per workload type**: one pool for databases, another for VM disks, another for cold data, each with its own CRUSH rule (for example, restricted to a device class).
- **PGs**: leave the autoscaler `on` and tell Ceph how much each pool should take with `target_size_ratio`; that way it distributes PGs from the start and does not reshuffle as the pool grows.

```bash
# Replicas for the database pool
ceph osd pool set db-rbd size 3
ceph osd pool set db-rbd min_size 2

# Active autoscaler and expected share of the cluster
ceph osd pool set db-rbd pg_autoscale_mode on
ceph osd pool set db-rbd target_size_ratio 0.3

# Tag the pool for RBD
ceph osd pool application enable db-rbd rbd
```

!!! tip "Review after every PG change"
    A change in the number of PGs triggers data movement. Do it during off-peak hours and watch `ceph -s` until everything is back to `active+clean`.

## BlueStore: WAL/DB and memory

BlueStore stores data on the main device and the metadata (RocksDB) and write-ahead log (WAL) wherever you tell it. On spinning disks, moving DB/WAL to NVMe or SSD is the change with the most impact on latency.

- **DB/WAL on a fast device**: they are split when creating the OSD (with `cephadm`, through an OSD service specification that assigns data and DB devices). Size the DB with headroom: if it fills up, RocksDB spills over to the slow disk and latency collapses.
- **Memory per OSD**: `osd_memory_target` sets how much memory each OSD tries to use; the BlueStore cache auto-tunes around that value. The total across all OSDs on a node plus the other services must not exceed physical RAM, or the node starts swapping.
- **Compression**: enabled per pool or per OSD. It helps with compressible data and costs CPU; measure it with your real data.

```bash
# Target memory per OSD (value in bytes; 4 GiB)
ceph config set osd osd_memory_target 4294967296

# BlueStore cache autotuning
ceph config set osd bluestore_cache_autotune true

# See the effective value of an option
ceph config get osd osd_memory_target

# Options changed from the default
ceph config dump
```

The practical calculation: node RAM, minus what the OS and other services use (monitor, manager, containers), divided by the number of OSDs. If the result falls below your version's default, it is better to reduce OSDs per node than to force a minimal value.

!!! warning "Compression and version"
    `bluestore_compression_mode` accepts several modes and its default behavior depends on the version. On databases with already compressed or encrypted pages it adds nothing and burns CPU. Try it first on a test pool.

## Network

- **Bandwidth**: 25 GbE or more is reasonable for NVMe. With 1 GbE, the network is the bottleneck before the disks.
- **Public and cluster network**: separating replication traffic from client traffic reduces interference. In a small cluster, a single network with enough bandwidth is simpler to operate.
- **MTU 9000**: only if the **whole** path (NICs, switches, VLAN) supports it. A single 1500 hop in the middle causes intermittent failures that are hard to diagnose.
- **IPv6**: if you do not use it, do not bind it (`ms_bind_ipv6=false`); if you do, use it consistently across the whole cluster.
- **Latency between nodes**: Ceph writes to all replicas before acknowledging, so network latency adds to every write.

## RBD and client

- **Image features**: `exclusive-lock`, `object-map`, `fast-diff` and `deep-flatten` speed up snapshots, clones and diffs. Enable them on production images and check compatibility with the client kernel or library.
- **RBD cache** (librbd): on databases, `rbd_cache` enabled with safe writes (`rbd_cache_writethrough_until_flush`) usually fits; adjust sizes with measurements, not intuition.
- **QEMU/libvirt**: `cache=none`, `io=native` and `discard=on`, with `virtio-scsi` and multiple queues. Align the guest partitions to 4K.
- **Guest filesystem**: `ext4` or `xfs` with `noatime`; do not disable barriers.
- **Returning space**: `discard` in the guest and periodic `fstrim` let Ceph free blocks; without them, the space of thin images only grows.

```bash
# Features of an image
rbd info db-rbd/pg-data

# Enable features on an existing image
rbd feature enable db-rbd/pg-data exclusive-lock object-map fast-diff

# Real space used by the image
rbd du db-rbd/pg-data
```

!!! warning "Feature order"
    `object-map` and `fast-diff` depend on `exclusive-lock`. On images already in use, after enabling them you may need to rebuild the object map (`rbd object-map rebuild`). Do it with the image idle.

## Testing with fio

Always measure with a pattern close to the real one. For an OLTP database: small blocks, mixed read/write and moderate concurrency. Run it on a test image, not on real data.

```bash
fio --name=db-randrw --filename=/dev/rbd0 --ioengine=libaio --direct=1 \
	--bs=8k --rw=randrw --rwmixread=70 --iodepth=32 --numjobs=4 --time_based \
	--runtime=120 --group_reporting
```

Look at the **tail latency** (high percentiles), not just average IOPS. A good average with a bad tail shows up in the database as sporadic stalls. Repeat the test after each change, one at a time, and again with the cluster busy (recovery in progress) to learn the worst case.

## Capacity planning

Ceph is not an array: usable capacity is lower than the sum of the disks.

- **3x replication**: usable capacity is a third of raw. With erasure coding it is higher, at the cost of performance.
- **Failure reserve**: the cluster must be able to rebuild the loss of a node (or a failure domain) with the space left. Plan so that, after losing what your design tolerates, usage stays below the thresholds.
- **Thresholds**: Ceph warns at `nearfull`, stops rebalancing at `backfillfull` and blocks writes at `full`. The defaults are conservative; do not raise them to gain space, add capacity.
- **Imbalance between OSDs**: the fullest OSD sets the limit. The `balancer` module redistributes PGs to even out usage; check it is active.
- **Growth**: adding OSDs triggers rebalancing. Do it in batches and with recovery limits if there are sensitive workloads.

```bash
# Usage of each OSD and deviation
ceph osd df tree

# Balancer module state
ceph balancer status

# Usage per pool
ceph df
```

## Recovery and rebalancing

Recovery and rebalancing compete with clients for disk and network. Two levers:

- **Recovery limit**: lowering backfill and recovery priority protects client latency at the cost of taking longer to return to full redundancy. Scheduler option names change between versions; look them up with `ceph config help`.
- **`mon_osd_down_out_interval`**: time the monitor waits before marking a down OSD `out` and starting to rebuild. A higher value avoids rebalancing on short restarts, and a lower one shortens the window without redundancy.

```bash
# Wait 10 minutes before marking a down OSD out
ceph config set mon mon_osd_down_out_interval 600

# Before a planned node shutdown
ceph osd set noout
# ... maintenance ...
ceph osd unset noout
```

If there is frequent rebalancing without cluster changes, check the CRUSH weights, the network between nodes and OSDs that flap.

## Monitoring and alerts

- **Metrics**: the manager's `prometheus` module exports metrics to Prometheus. In Grafana: OSD read and write latency, client I/O, NIC saturation and per-OSD usage.
- **Useful alerts**: PGs degraded or in backfill for a long time, `nearfull`, `slow ops`, down OSDs and clock skew between monitors.
- **Conservative thresholds**: alert on usage with enough margin to rebuild a node, not when it is almost full.

## Troubleshooting

| Symptom | Probable cause | Fix |
|---------|----------------|-----|
| High write latency on HDD | DB/WAL on the same spinning disk | Move DB/WAL to NVMe/SSD when recreating the OSD |
| Repeated `slow ops` | Saturated disk or network, misbehaving OSD | `ceph -s`, locate the affected OSD and check the node's disk and network |
| One OSD much fuller than the rest | Uneven PG distribution | Check `ceph balancer status`; enable the balancer or adjust weights |
| `nearfull` warning | Capacity near the limit | Add OSDs, delete data or reduce replicas only if the design allows it |
| Node swapping, slow OSDs | Sum of `osd_memory_target` exceeds RAM | Lower `osd_memory_target` or reduce OSDs per node |
| Slow clients during recovery | Backfill competes with client traffic | Lower recovery priority and schedule changes off-peak |
| Rebalancing after rebooting a node | `down_out_interval` too low | Raise it, or use `noout` for planned maintenance |
| Image space does not drop after deleting data | The guest does not send `discard` | Enable `discard` and run `fstrim` |

## Best Practices

- Measure before and after each change, one at a time, and keep the outputs.
- One pool per workload type, with `size=3` and `min_size=2` for what matters.
- DB/WAL on NVMe when the main storage is spinning, with headroom in size.
- Calculate `osd_memory_target` from the node's real RAM, not from another cluster's figure.
- Do not raise the `full` thresholds to gain space: add capacity before reaching them.
- Use `noout` for planned maintenance and remove it afterwards.
- Check `ceph config help <option>` on your version before copying settings from tutorials.
- Test recovery on a lab cluster before you need it in production.

## References

- [Official Ceph documentation](https://docs.ceph.com/)
- [Ceph — Base Guide](ceph_base.md)
- [Ceph Troubleshooting](troubleshooting_ceph.md)
- [PostgreSQL on Ceph](../postgresql_ceph.md)
- [Kubernetes CSI](../kubernetes_csi.md)
