---
title: "Local storage on Linux: ZFS and LVM"
description: "The local disk of a server or Proxmox node: LVM (PV, VG, LV, thin provisioning, snapshots) and ZFS (pools, vdevs, datasets, snapshots, send/receive, ARC), when to pick each one and what to monitor."
keywords: "zfs, lvm, lvm-thin, thin provisioning, raidz, mirror, zpool, datasets, snapshots, zfs send, arc, zvol, mdadm, proxmox, smartctl"
tags: ['storage', 'linux', 'proxmox']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 24 min
category: Storage
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Linux with root access and basic disk handling (lsblk, partitions)"
  - "[Proxmox base](../proxmox/proxmox_base.md)"
  - "RAID concepts (mirror, parity)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Local storage on Linux: ZFS and LVM

## The problem

You install Proxmox, accept the wizard's defaults and suddenly you have a `local-lvm` you don't remember creating. Or you pick "ZFS (RAID1)" and the installer asks about an `ashift` you have never needed. The guides for [Proxmox](../proxmox/proxmox_base.md), [Proxmox Backup Server](../backups/pbs.md) and the [3-2-1 strategy](../backups/strategy_321.md) take ZFS and LVM for granted: they talk about snapshots, datasets, thin pools. If you don't know them, the first time a pool shows up as `DEGRADED` or a thin pool fills up, you are improvising on the data of all your machines.

This page explains both systems from the angle of the **local disk of a server or homelab node**: what each piece is, which commands you use daily, when one fits better than the other and what to watch so you hear about problems before they become problems.

!!! note "What this covers and what it doesn't"
    **Local** storage on a single host. Distributed storage is in [Ceph](ceph/ceph_base.md) and consuming it from Kubernetes in [CSI on Kubernetes](kubernetes_csi.md). Encryption is mentioned, but the LUKS details live in [Applied cryptography](../cybersecurity/criptografia_aplicada.md).

## 📋 Table of Contents

- [LVM: PV, VG and LV](#lvm-pv-vg-and-lv)
- [Growing online](#growing-online)
- [Thin provisioning](#thin-provisioning)
- [LVM snapshots and their limits](#lvm-snapshots-and-their-limits)
- [ZFS: pools and vdevs](#zfs-pools-and-vdevs)
- [Datasets and properties](#datasets-and-properties)
- [Snapshots and replication with send/receive](#snapshots-and-replication-with-sendreceive)
- [Scrub, ARC and zvols](#scrub-arc-and-zvols)
- [When to pick each one](#when-to-pick-each-one)
- [Encryption](#encryption)
- [Minimal monitoring](#minimal-monitoring)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## LVM: PV, VG and LV

LVM (Logical Volume Manager) adds a layer between the disks and the filesystem. It has three levels and it pays to keep them straight:

| Level | What it is | Listing command |
|---|---|---|
| **PV** (*Physical Volume*) | A disk or partition handed over to LVM | `pvs` |
| **VG** (*Volume Group*) | Pool of space made of one or more PVs | `vgs` |
| **LV** (*Logical Volume*) | A "partition" carved out of the VG, where you put the filesystem | `lvs` |

The key idea: the LV is not tied to a specific disk. You can grow it with space from another disk, move it and take snapshots without touching the filesystem.

```bash
# Hand two disks to LVM and create a group
pvcreate /dev/sdb /dev/sdc
vgcreate vg_datos /dev/sdb /dev/sdc

# Create a 100 GiB volume with a filesystem
lvcreate -L 100G -n lv_backups vg_datos
mkfs.ext4 /dev/vg_datos/lv_backups
mount /dev/vg_datos/lv_backups /srv/backups
```

!!! warning "LVM is not redundancy"
    A VG with two disks and linear LVs **adds capacity, it doesn't protect**: if a disk fails, you lose the LVs with extents on it. Redundancy goes underneath (mdadm, hardware RAID) or in LVM's own RAID options. And LVM computes no checksums: it won't detect silent corruption.

## Growing online

This is the reason almost everyone uses LVM. With the LV mounted and in use:

```bash
# If the VG runs out of free space, add a disk
pvcreate /dev/sdd
vgextend vg_datos /dev/sdd

# Grow the LV and its filesystem in a single step
lvextend -r -L +50G /dev/vg_datos/lv_backups
# Or take all the free space: lvextend -r -l +100%FREE ...
```

The `-r` option (`--resizefs`) calls the right tool for the filesystem (ext4, XFS…). Without it, the LV grows but the filesystem keeps its old size and `df` doesn't change.

Shrinking is a different story: ext4 only shrinks **unmounted**, XFS cannot shrink, and an `lvreduce` without shrinking the filesystem first destroys data.

## Thin provisioning

A regular LV reserves all its space at creation. With *thin provisioning* you create a **thin pool** and the thin LVs consume only what they write from the pool, so you can promise more space than exists (overprovisioning).

```bash
# A 500 GiB pool and two thin volumes of 300 GiB each
lvcreate -L 500G --thinpool tpool vg_datos
lvcreate -V 300G --thin -n vm1 vg_datos/tpool
lvcreate -V 300G --thin -n vm2 vg_datos/tpool
```

That is 600 GiB promised on 500 real ones. While what is written fits, all is well; when it doesn't, writes fail.

!!! danger "A full thin pool is an outage, not a warning"
    When it fills up, the machines and filesystems on top of the pool start throwing I/O errors and, in the worst case, get corrupted. A thin pool also has a **metadata LV** that can fill up too. Watch both percentages.

```bash
# Data and metadata usage of the pool
lvs -o lv_name,lv_size,data_percent,metadata_percent vg_datos
```

Two measures that make it manageable:

- **Auto-extension**: in `/etc/lvm/lvm.conf`, `activation` section, the `thin_pool_autoextend_threshold` and `thin_pool_autoextend_percent` parameters make the pool grow by itself as it nears the threshold, as long as the VG has free space and the event monitor (`dmeventd`) is active.
- **Giving space back**: deleting files inside the thin LV does not free blocks in the pool unless discards are issued. Run `fstrim -a` periodically or mount with `discard`.

### LVM-thin as a Proxmox backend

The Proxmox installer with ext4 creates a `pve` VG with a root LV and a `data` thin pool, exposed as the `local-lvm` storage. Each VM disk is a thin LV and Proxmox snapshots are thin snapshots. A typical entry in `/etc/pve/storage.cfg` (it inherits all the risks above; the panel shows pool usage, but you want your own alert on `data_percent`):

```ini
lvmthin: local-lvm
        thinpool data
        vgname pve
        content rootdir,images
```

## LVM snapshots and their limits

A snapshot freezes the state of an LV at a point in time. There are two kinds and they behave very differently:

| | Classic snapshot (*thick*) | Thin LV snapshot (*thin*) |
|---|---|---|
| Size | Fixed, you choose it at creation | No size of its own, consumes from the pool |
| If it fills up | It is **invalidated** and lost | Competes with the rest for the pool |
| Origin performance | Drops: every write copies the old block | Almost no penalty |

```bash
# Classic snapshot: you must reserve space for the changes
lvcreate -s -n snap_pre_upgrade -L 10G /dev/vg_datos/lv_backups
# Thin LV snapshot: no size
lvcreate -s -n snap_vm1 vg_datos/vm1
# Roll back: merge the snapshot into the origin
lvconvert --merge vg_datos/snap_pre_upgrade
```

Limits to keep in mind:

- A snapshot is **not a backup**: it lives in the same VG on the same disks. If the disk dies, it goes with the original.
- Long-lived classic snapshots degrade performance; use them for a specific operation and delete them.
- Thin LV snapshots are created with the "skip activation" flag: to activate them by hand, `lvchange -ay -K`.

## ZFS: pools and vdevs

ZFS combines volume manager and filesystem in one. Its defining trait is that it **verifies everything it reads with checksums** and, if it has redundancy, repairs what is corrupt from the good copy. LVM plus ext4 or XFS don't do that.

The hierarchy is different: a **pool** (`zpool`) is made of one or more **vdevs**, and each vdev is made of disks.

| Vdev type | Minimum disks | Tolerates | When |
|---|---|---|---|
| **mirror** | 2 | All but one | VMs, databases, small nodes |
| **raidz1** | 3 | 1 disk | Cold data on small disks |
| **raidz2** | 4 | 2 disks | Large file store |
| **raidz3** | 5 | 3 disks | Very wide vdevs |

Redundancy is **per vdev**, and the pool spreads data across its vdevs. Losing a whole vdev loses the whole pool, so mixing a non-redundant vdev with a mirror voids the mirror's protection.

```bash
# Two disks in a mirror; always use stable by-id paths
zpool create -o ashift=12 tank mirror \
  /dev/disk/by-id/ata-DISK_A /dev/disk/by-id/ata-DISK_B

# Six disks in raidz2: same command with "raidz2" and six paths
```

`ashift` is the sector size ZFS assumes, as a power of 2 (`12` = 4 KiB). **It cannot be changed after the vdev is created.** Many modern disks advertise 512 B sectors even though they use 4 KiB; an `ashift` that is too low causes misaligned writes and a permanent loss of performance. With `12` you are right on almost every current disk.

### Growing a pool

Unlike a classic RAID, **a raidz vdev is not grown by adding a disk to it**. The usual ways to grow are:

- **Add another vdev** with `zpool add` (for example, another mirror), preferably of the same type as the existing ones.
- **Replace the disks with larger ones** one by one with `zpool replace`; the extra space appears once all the vdev's disks are replaced (with `autoexpand=on` on the pool, or `zpool online -e`).
- **Mirrors**: `zpool attach` adds a disk to a mirror and `zpool detach` removes one.

!!! warning "raidz expansion depends on the version"
    Recent OpenZFS versions (the 2.3 series onwards, according to the project) include raidz expansion, which lets you add a disk to an existing raidz vdev with `zpool attach`. Check with `zfs version` what you have before counting on it: Proxmox and distributions usually lag behind the project. Also, data written before expanding keeps the old parity ratio until it is rewritten.

## Datasets and properties

Inside a pool you create **datasets**: they look like directories, but each one has its own properties, quotas and snapshots. Unlike LVM, you don't reserve size up front: they share the pool's free space.

```bash
zfs create tank/vms
zfs create tank/backups
zfs set quota=500G tank/backups
zfs get compression,recordsize,atime tank/backups

zfs set compression=lz4 tank
zfs set atime=off tank
zfs set recordsize=16K tank/postgres
```

The properties that matter most on a server:

| Property | Usual value | What for |
|---|---|---|
| `compression` | `lz4` (or `zstd`) | Inline compression. With `lz4` it almost always **improves** performance by writing less |
| `recordsize` | `128K` by default; `1M` for large files; `16K` for databases | Maximum block size of a file |
| `atime` | `off` | Avoids a write on every read |
| `quota` / `reservation` | case by case | Cap or guaranteed space for a dataset |

Properties are inherited from the parent. `recordsize` only affects data written after the change. `zstd` as a `compression` value requires an OpenZFS version that includes it (the 2.x series).

## Snapshots and replication with send/receive

ZFS snapshots are instantaneous and, as long as data doesn't change, take up nothing. They sit in the same pool, so they are worth the same as an LVM snapshot: not a backup until they leave that disk.

```bash
zfs snapshot tank/vms@2026-10-11
zfs list -t snapshot tank/vms
zfs rollback tank/vms@2026-10-11    # go back to that moment
zfs destroy tank/vms@2026-10-11
```

What turns them into replication is `zfs send`/`zfs receive`: it serializes a snapshot and rebuilds it in another pool, local or remote.

```bash
# First, full replica
zfs send tank/vms@snap1 | ssh nas zfs receive reserva/vms

# Following replicas: only what changed between two snapshots
zfs send -i tank/vms@snap1 tank/vms@snap2 | ssh nas zfs receive reserva/vms
```

An incremental send only works if the destination keeps the base snapshot. It is the piece the [3-2-1](../backups/strategy_321.md) strategy uses to keep a copy off the machine. To measure how the pool behaves under load, use [fio](protocols/examples/fio_example.md).

## Scrub, ARC and zvols

**Scrub.** It walks all the pool's data, verifies the checksums and repairs what it can using redundancy. It is the way to detect degradation before you need the data.

```bash
zpool scrub tank
zpool status tank     # progress and result
```

Schedule a periodic scrub and review the result. It loads the disks: don't start it at peak hours.

**ARC.** It is ZFS's read cache in RAM and the reason behind "ZFS eats all the memory". Its default maximum size has changed between OpenZFS versions, and some installers, such as Proxmox's, already set their own cap: check the effective value with `arc_summary` instead of assuming it. It releases memory when the system needs it, but you will see little "free" memory in `free`. If the node runs VMs, cap it to leave room for them:

```bash
# 4 GiB limit (value in bytes), persistent
echo "options zfs zfs_arc_max=4294967296" > /etc/modprobe.d/zfs.conf
update-initramfs -u -k all      # Debian/Proxmox; reboot afterwards
# Live: echo 4294967296 > /sys/module/zfs/parameters/zfs_arc_max
```

There is no universal figure: tune it by looking at the cache hit rate (`arc_summary`) and the memory your VMs need. With deduplication enabled, RAM usage skyrockets: leave it off unless you have a clear reason.

**Zvols.** A zvol is a dataset that behaves as a block device (`/dev/zvol/...`). It is what Proxmox uses for VM disks on ZFS: each disk is a zvol, with its own snapshots and clones.

```bash
zfs create -V 32G tank/vm-100-disk-0    # shows up in /dev/zvol/tank/
```

The block size (`volblocksize`) is set when the zvol is created and its default value changes between versions. On raidz, zvols can take up more than expected because of parity padding; mirrors are recommended for VMs.

## When to pick each one

| Criterion | LVM (+ ext4/XFS) | LVM-thin | ZFS | mdadm + LVM |
|---|---|---|---|---|
| **Data integrity** | No checksums | No checksums | Checksums and self-healing | No checksums |
| **RAM** | Minimal | Minimal | High (ARC, tunable) | Minimal |
| **Snapshots** | Classic, with a cost | Fast, cheap | Instantaneous, no practical limit | LVM's own |
| **Growth** | Very flexible, online | Very flexible | Add vdevs; raidz limited | Flexible; growing the array is slower |
| **Performance** | High, predictable | High; fragmentation risk | Very good with RAM and tuning | High, predictable |
| **Complexity** | Low | Medium (watch the pool) | Medium-high (own model) | Medium (two layers) |

A practical rule:

- **ZFS** when the data matters more than the last MiB/s: file store, backups, a Proxmox node with two disks in a mirror. Integrity and `send/receive` justify the RAM.
- **LVM-thin** on a node with little RAM, a single disk or a hardware RAID controller, where you want cheap VM snapshots. Accept the risk and alert on the pool.
- **mdadm + LVM** is the third way: mdadm provides software RAID and LVM the flexibility on top. It is the classic, sober combination, without checksums. You create the array with `mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc`, hand it over with `pvcreate /dev/md0` and continue as in the LVM section.
- **Avoid ZFS on top of hardware RAID** that hides the disks: it needs to see them (HBA in passthrough mode) to detect and repair errors.

## Encryption

Both support encryption, by different routes:

- **LUKS under LVM**: you encrypt the disk or partition with `cryptsetup`, and mount the PV on the decrypted device. Everything above it (VG, LV, snapshots) ends up encrypted in one go.
- **Native ZFS encryption**: enabled per dataset at creation (`zfs create -o encryption=on -o keyformat=passphrase tank/privado`). It lets you encrypt some datasets and not others, and replicate snapshots without them leaving decrypted, as long as they are sent raw with `zfs send -w`: a plain `zfs send` transmits the data already decrypted.

Key management, LUKS headers and recovery are in [Applied cryptography](../cybersecurity/criptografia_aplicada.md); they are not repeated here.

## Minimal monitoring

You don't need Prometheus to start; these commands, by hand or in a cron job, cover almost every scare:

```bash
# ZFS
zpool status -x      # "all pools are healthy" or the problem detail
zpool list           # capacity, usage and health of each pool
zfs list             # space per dataset

# LVM
pvs ; vgs ; lvs      # disks, groups and volumes
lvs -a -o+data_percent,metadata_percent    # includes pools and metadata

smartctl -H /dev/sda        # SMART: overall verdict
smartctl -a /dev/sda        # SMART: full attributes
```

What to watch: a pool that is not `ONLINE`, read/write/checksum errors in `zpool status`, a pool above 80 % usage (ZFS performance drops as it fills), `data_percent` or `metadata_percent` of a thin pool near 100 %, and growing reallocated or pending sectors in SMART. For NVMe, `smartctl -a /dev/nvme0` gives wear and temperature. The `smartd` daemon from `smartmontools` can alert by email.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `zpool status` shows `DEGRADED` | A disk has failed or disconnected | Identify the disk in `zpool status`, swap it and `zpool replace tank old new` |
| VMs suddenly throw I/O errors | Thin pool full (data or metadata) | Grow the pool (`lvextend` on the thin pool), free space with `fstrim`, delete snapshots |
| `lvextend` says there are no free extents | The VG is full | `vgextend` with another PV, or trim what is not needed |
| The LV grows but `df` doesn't change | `-r` was omitted | `lvextend -r` or, by hand, `resize2fs` (ext4) / `xfs_growfs` (XFS) |
| A classic LVM snapshot disappears or becomes invalid | Its reserved space filled up | Reserve more, or use thin LV snapshots; delete it after the operation |
| "It eats all the RAM" after installing ZFS | ARC grows while memory is available | Set `zfs_arc_max` and check with `free` and the ARC counters |
| The pool is slow as it nears 90 % | Fragmentation and little free space | Free space, grow with another vdev, keep headroom |
| `zpool import` refuses a pool from another installation | The pool was not exported and shows as in use | Verify it is not in use and `zpool import -f name`; beforehand, `zpool export` |

## Best practices

- **Use `/dev/disk/by-id/`** when creating pools and VGs. `/dev/sdX` names change between boots.
- **Redundancy underneath everything.** LVM without RAID adds capacity but doesn't protect; and in neither case is there a backup until there is another copy off the host ([3-2-1](../backups/strategy_321.md), [PBS](../backups/pbs.md)).
- **Alert on pool and thin pool usage** before 80 %, not after 100 %.
- **`ashift=12` and `compression=lz4`** from day one: `ashift` can't be fixed later and compression only affects what is written from then on.
- **Monthly scrub and periodic SMART** with email alerts. **Cap the ARC** on nodes with VMs. **Test the restore**, not just the copy.

## References

- [OpenZFS — documentation](https://openzfs.github.io/openzfs-docs/) · [zpool(8)](https://openzfs.github.io/openzfs-docs/man/master/8/zpool.8.html) · [zfs(8)](https://openzfs.github.io/openzfs-docs/man/master/8/zfs.8.html)
- [lvmthin(7)](https://man7.org/linux/man-pages/man7/lvmthin.7.html) · [Proxmox VE — Storage](https://pve.proxmox.com/wiki/Storage)
- [Proxmox base](../proxmox/proxmox_base.md) · [Proxmox Backup Server](../backups/pbs.md) · [3-2-1 strategy](../backups/strategy_321.md)
- [Ceph](ceph/ceph_base.md) · [CSI on Kubernetes](kubernetes_csi.md) · [fio benchmarks](protocols/examples/fio_example.md) · [Applied cryptography](../cybersecurity/criptografia_aplicada.md)
