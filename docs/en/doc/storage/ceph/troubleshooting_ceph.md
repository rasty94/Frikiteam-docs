---
title: "Ceph Troubleshooting: Common Issues and Solutions"
description: "Comprehensive guide to diagnose and fix common Ceph problems. OSDs down, PG issues, slow operations, and cluster health recovery."
keywords: Ceph, troubleshooting, debugging, OSD down, PG stuck, slow ops, cluster health, recovery, ceph health
date: 2026-01-25
updated: 2026-01-25
difficulty: intermediate
estimated_time: 8 min
category: Storage
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Troubleshooting Ceph

## 🎯 Initial Diagnosis

### Essential Commands

```bash
# Cluster status
ceph -s
ceph health detail

# OSD status
ceph osd tree
ceph osd stat
ceph osd df

# PG status
ceph pg stat
ceph pg dump | grep -v "^version"

# Performance
ceph osd perf
ceph tell osd.* bench

# Logs
journalctl -u ceph-osd@* -f
journalctl -u ceph-mon@* -f
```

## 🔴 HEALTH_WARN and HEALTH_ERR

### HEALTH_WARN: OSDs near full

**Symptom**:
```bash
$ ceph -s
  health: HEALTH_WARN
          1 nearfull osd(s)
          OSD.5 is near full (85%)
```

**Diagnosis**:

```bash
# Check usage per OSD
ceph osd df tree

# Check the largest pools
ceph df

# Find out what is taking up space
for pool in $(ceph osd pool ls); do
  echo "Pool: $pool"
  rbd du $pool 2>/dev/null || rados df -p $pool
done
```

**Solutions**:

```bash
# 1. Add more OSDs
ceph orch daemon add osd <host>:<device>

# 2. Temporarily adjust thresholds
ceph osd set-full-ratio 0.95
ceph osd set-nearfull-ratio 0.90

# 3. Remove unnecessary data
# Delete old snapshots
rbd snap ls <pool>/<image>
rbd snap rm <pool>/<image>@<snapshot>

# 4. Rebalance
ceph osd reweight <osd-id> 0.95  # Reduce the weight of the full OSD
```

### HEALTH_ERR: OSDs down

**Symptom**:
```bash
$ ceph -s
  health: HEALTH_ERR
          3 osds down
          Degraded data redundancy (...)
```

**Diagnosis**:

```bash
# Identify the OSDs that are down
ceph osd tree | grep down

# Find out why they are down
systemctl status ceph-osd@5
journalctl -u ceph-osd@5 -n 100

# Check the disk
lsblk
smartctl -a /dev/sdb
```

**Solutions by root cause**:

#### OSD crashed (software failure):

```bash
# Restart the OSD
systemctl restart ceph-osd@5

# If it does not start, check the logs
journalctl -u ceph-osd@5 --since "10 minutes ago"

# Try a repair
ceph-objectstore-tool --data-path /var/lib/ceph/osd/ceph-5 --op fsck
```

#### Failed disk:

```bash
# Mark the OSD as out
ceph osd out 5

# Remove the OSD from the cluster
ceph osd purge 5 --yes-i-really-mean-it

# Replace the disk
# 1. Physically replace it
# 2. Add the new OSD
ceph orch daemon add osd <host>:/dev/sdb

# Wait for the cluster to rebalance
watch ceph -s
```

#### Network problems:

```bash
# Check connectivity
ping <osd-host>
ceph tell osd.* version  # See which ones respond

# Check the interfaces
ip addr show
ip link show

# Restart networking if needed
systemctl restart networking
```

### HEALTH_WARN: PGs stuck

**Common symptoms**:
- `X pgs stuck unclean`
- `X pgs stuck inactive`  
- `X pgs stuck degraded`
- `X pgs stuck undersized`

**Diagnosis**:

```bash
# List the problematic PGs
ceph pg dump | grep -E "stuck|stale|inactive"

# Details for a specific PG
ceph pg <pg-id> query

# Check the PG to OSD mapping
ceph pg map <pg-id>
```

**Solutions**:

#### PGs stuck inactive/unclean:

```bash
# Force a scrub
ceph pg scrub <pg-id>
ceph pg deep-scrub <pg-id>

# Force recovery
ceph pg force-recovery <pg-id>

# If the problem persists, check the OSDs responsible for it
ceph pg <pg-id> query | grep acting
```

#### PGs stuck undersized:

```bash
# This means replicas are missing
# Check how many replicas the pool has
ceph osd pool get <pool-name> size
ceph osd pool get <pool-name> min_size

# If you have fewer OSDs than the pool size:
# Option 1: Add OSDs
# Option 2: Reduce the size (testing only)
ceph osd pool set <pool-name> size 2
```

#### PGs remapped:

```bash
# Normal during rebalancing
# Watch the progress
ceph -w

# Speed up recovery (carefully, it impacts performance)
ceph tell 'osd.*' injectargs '--osd-max-backfills 8'
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 4'

# Restore the default values afterwards
ceph tell 'osd.*' injectargs '--osd-max-backfills 1'
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 3'
```

## ⚡ Performance Problems

### Slow Operations (slow ops)

**Symptom**:
```bash
$ ceph -s
  health: HEALTH_WARN
          30 slow ops, oldest one blocked for 45 sec
```

**Diagnosis**:

```bash
# List slow operations
ceph daemon osd.5 dump_historic_slow_ops

# Check OSD latency
ceph osd perf

# Check pool stats
ceph df detail

# Benchmark a specific OSD
ceph tell osd.5 bench
```

**Causes and solutions**:

#### Slow or failing disks:

```bash
# Disk I/O test
fio --filename=/dev/sdb --direct=1 --rw=randread --bs=4k \
    --ioengine=libaio --iodepth=64 --runtime=60 --name=test

# Check SMART health
smartctl -a /dev/sdb | grep -E "Reallocated|Pending|Uncorrectable"

# If the disk is failing, replace it (see the OSDs down section)
```

#### Saturated network:

```bash
# Bandwidth test between nodes
iperf3 -s  # On one node
iperf3 -c <ip-del-nodo> -t 30  # On another node

# Check network traffic
iftop -i eth0

# Solution: Improve the network (10GbE, bonding, jumbo frames)
```

#### Journal/WAL on a slow disk:

```bash
# Check where the journal lives
ceph-volume lvm list

# Migrate the journal/WAL to an SSD
ceph-volume lvm new-wal /dev/nvme0n1 --osd-id 5
```

#### Badly balanced PGs:

```bash
# Check PG distribution per OSD
ceph osd df tree

# If there is an imbalance:
ceph balancer on
ceph balancer mode upmap
ceph balancer eval
```

### High CPU usage on OSDs

**Diagnosis**:

```bash
# Check the processes
top -b -n 1 | grep ceph-osd
htop

# Check the active operations
ceph daemon osd.5 dump_ops_in_flight
```

**Solutions**:

```bash
# Limit scrubbing
ceph tell osd.* injectargs '--osd-max-scrubs 1'
ceph config set osd osd_scrub_begin_hour 2
ceph config set osd osd_scrub_end_hour 6

# Reduce concurrent recovery
ceph tell 'osd.*' injectargs '--osd-max-backfills 1'

# Add resources (more cores, more RAM)
```

## 🗄️ Pool and RBD Problems

### Error: "pool has too few PGs"

**Symptom**:
```bash
$ ceph -s
  health: HEALTH_WARN
          pool 'volumes' has too few pgs
```

**Solution**:

```bash
# Calculate the right number of PGs
# Formula: (OSDs * 100) / pool_size / num_pools
# Example: (30 * 100) / 3 / 4 = 250 → round up to 256

# Increase the PGs (automatic in Octopus+)
ceph osd pool set volumes pg_num 256

# Wait for autoscaling
ceph osd pool autoscale-status

# Enable autoscaling if it is not active
ceph osd pool set volumes pg_autoscale_mode on
```

### Cannot delete a pool

**Symptom**:
```bash
$ ceph osd pool delete mypool mypool --yes-i-really-really-mean-it
Error EPERM: pool deletion is disabled; configure mon_allow_pool_delete
```

**Solution**:

```bash
# Enable deletion
ceph config set mon mon_allow_pool_delete true

# Delete the pool
ceph osd pool delete mypool mypool --yes-i-really-really-mean-it

# Disable deletion again (good practice)
ceph config set mon mon_allow_pool_delete false
```

### Corrupted RBD image

**Diagnosis**:

```bash
# Check the image
rbd info <pool>/<image>
rbd check <pool>/<image>

# List the snapshots
rbd snap ls <pool>/<image>
```

**Solution**:

```bash
# Try a repair
rbd repair <pool>/<image>

# If there are snapshots, flatten the image
rbd flatten <pool>/<image>

# Restore from a valid snapshot
rbd snap rollback <pool>/<image>@<snapshot-name>

# Last resort: export and reimport
rbd export <pool>/<image> /tmp/image_backup.raw
rbd rm <pool>/<image>
rbd import /tmp/image_backup.raw <pool>/<image>
```

## 🔧 MON (Monitor) Problems

### MON down or clock skew

**Symptom**:
```bash
$ ceph -s
  health: HEALTH_WARN
          clock skew detected on mon.node2
```

**Solution**:

```bash
# Check NTP/chrony on every node
systemctl status chronyd
chronyc tracking

# Synchronize the clock
sudo chronyc -a makestep

# Check timesync
timedatectl status

# Restart the MON if needed
systemctl restart ceph-mon@node2
```

### Lost quorum

**Symptom**:
`ceph -s` does not respond or reports "no quorum".

**Solution (DANGEROUS)**:

```bash
# Check the MON status
ceph mon stat

# If more than 50% of the MONs are UP, wait for them to form a quorum

# If you have lost the majority, recover manually:
# On the surviving MON:
ceph-mon -i <mon-id> --extract-monmap /tmp/monmap
monmaptool --print /tmp/monmap

# Edit the monmap if needed
monmaptool --rm <mon-id-down> /tmp/monmap

# Inject the monmap
ceph-mon -i <mon-id> --inject-monmap /tmp/monmap

# Restart
systemctl restart ceph-mon@<mon-id>
```

## 🛠️ Diagnostic Tools

### Health Check Script

```bash
#!/bin/bash
# ceph-health-check.sh

echo "=== Ceph Health Check ==="
ceph -s

echo -e "\n=== OSDs Status ==="
ceph osd tree

echo -e "\n=== Disk Usage ==="
ceph osd df tree

echo -e "\n=== PG Status ==="
ceph pg stat

echo -e "\n=== Pool Usage ==="
ceph df

echo -e "\n=== Slow Ops ==="
ceph daemon osd.* dump_historic_slow_ops | grep -A5 "slow_ops"

echo -e "\n=== Network Check ==="
ceph tell mon.* version
ceph tell osd.* version | grep -c "version"
```

### Storage Benchmark

```bash
#!/bin/bash
# benchmark-ceph.sh

POOL="benchmark-pool"

# Create a temporary pool
ceph osd pool create $POOL 128
rados bench -p $POOL 30 write --no-cleanup
rados bench -p $POOL 30 seq
rados bench -p $POOL 30 rand

# Cleanup
ceph osd pool delete $POOL $POOL --yes-i-really-really-mean-it
```

## 📊 Logs and Debugging

### Log Locations

```bash
# OSD logs
/var/log/ceph/ceph-osd.*.log

# MON logs
/var/log/ceph/ceph-mon.*.log

# MGR logs
/var/log/ceph/ceph-mgr.*.log

# Follow them in real time
tail -f /var/log/ceph/ceph-osd.5.log
journalctl -u ceph-osd@5 -f
```

### Enabling Debug

```bash
# Raise the debug level (0-30, default 1)
ceph tell osd.5 injectargs '--debug-osd 20'
ceph tell mon.* injectargs '--debug-mon 20'

# Restore
ceph tell osd.5 injectargs '--debug-osd 1'
```

## 📚 Emergency Commands

### Pausing Recovery/Rebalancing

```bash
# Pause operations (for maintenance)
ceph osd set noout
ceph osd set norebalance
ceph osd set norecover
ceph osd set nobackfill

# Resume
ceph osd unset noout
ceph osd unset norebalance
ceph osd unset norecover
ceph osd unset nobackfill
```

### Forcing Recovery to Complete

```bash
# List the PGs in recovery
ceph pg dump | grep -E "recovery|backfill"

# Speed it up (this impacts performance!)
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 10'
ceph tell 'osd.*' injectargs '--osd-max-backfills 10'
ceph tell 'osd.*' injectargs '--osd-recovery-sleep-hdd 0'

# Restore the defaults
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 3'
ceph tell 'osd.*' injectargs '--osd-max-backfills 1'
ceph tell 'osd.*' injectargs '--osd-recovery-sleep-hdd 0.1'
```

## 🎓 Troubleshooting Best Practices

1. **Always check the logs first**: `journalctl -u ceph-* -f`
2. **Do not make drastic changes without a backup**: especially with `ceph osd purge`
3. **One change at a time**: so you can tell which one fixed the problem
4. **Document everything**: keep a record of the changes and commands you run
5. **Monitor**: use Grafana + Prometheus for proactive detection

## 📚 References

- [Ceph Troubleshooting Guide](https://docs.ceph.com/en/latest/rados/troubleshooting/)
- [Ceph Operations Manual](https://docs.ceph.com/en/latest/rados/operations/)
- [Ceph Health Checks](https://docs.ceph.com/en/latest/rados/operations/health-checks/)

---

!!! danger "Destructive Commands"
    Never run `ceph osd purge`, `ceph osd pool delete` or `--force` without fully understanding the consequences.

!!! tip "Before Making Changes"
    Always run `ceph -s` and `ceph health detail` first so you have a baseline of the cluster state.
