---
title: "3-2-1 Backup Strategy"
description: "Design a backup plan for self-hosted infrastructure with the 3-2-1 rule: what counts as a copy, what counts as a different medium, how to choose RPO, RTO and retention, and how to build it with PBS, restic and object storage."
keywords: "backup, 3-2-1, 3-2-1-1-0, RPO, RTO, retention, offsite, restic, PBS, homelab, recovery"
tags: ['backups', 'best-practices']
updated: 2026-10-11
difficulty: advanced
estimated_time: 18 min
category: Backups
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Basic DevOps knowledge"
  - "Basic Linux administration (cron or systemd timers, SSH)"
  - "Some storage destination: NAS, second disk or an object storage account"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# 3-2-1 Backup Strategy

## The problem

Almost everyone has "backups". What almost nobody has is a backup that survives the scenario that is actually going to happen to them. The external disk hanging off the same server goes with it in the power surge. The nightly `rsync` to the NAS faithfully replicates the ransomware the moment it encrypts the first folder. The ZFS snapshot that feels so reassuring lives in the same pool as the data, and a pool that fails to import takes the snapshots with it. And the copy "in the cloud" sits in the same account, with the same API key the compromised server holds.

The 3-2-1 rule is not a tool or a product: it is a criterion for checking that your plan has no hidden single point of failure. This page explains what each number means **in self-hosted infrastructure**, what counts as a copy and what does not, how to decide how much to lose and how long to take to come back, and how to build it with the pieces already documented on this site.

!!! note "What this covers and what it does not"
    This page is about **designing the plan**: copies, media, location, retention and verification. Using the tools lives in [Restic and Borg](restic_borg.md) and [Proxmox Backup Server](pbs.md). The security layer on top of the plan (encryption, immutability, credential separation) is in [Secure Backup](../cybersecurity/backup_seguro.md).

## 📋 Table of Contents

- [The rule](#the-rule)
- [What counts as a copy](#what-counts-as-a-copy)
- [What counts as a different medium](#what-counts-as-a-different-medium)
- [What counts as off-site](#what-counts-as-off-site)
- [The 3-2-1-1-0 variant](#the-3-2-1-1-0-variant)
- [Deciding RPO, RTO and retention](#deciding-rpo-rto-and-retention)
- [Practical application in a homelab](#practical-application-in-a-homelab)
- [Data flow](#data-flow)
- [Automate and verify](#automate-and-verify)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## The rule

| Number | Meaning | What it protects against |
|---|---|---|
| **3** copies | Production data plus **two** independent backups | Disk failure, accidental deletion, a bug that corrupts data |
| **2** media | Copies live on at least two different technologies or failure domains | The same kind of failure repeating (disk batch, controller, filesystem bug) |
| **1** off-site | At least one copy in another physical and administrative location | Fire, theft, flood, ransomware reaching the whole local network |

What the rule does **not** say, and what is usually forgotten: the copies have to be **restorable**. Three identical copies of a corrupt file satisfy 3-2-1 and are useless. That is why the modern variant adds a zero at the end (see below).

## What counts as a copy

A copy is a set of data you can restore **even if the source disappears completely** and that **does not change when the source changes**. By that criterion, several things sold as backup stop being one:

| This | Is it a copy? | Why |
|---|---|---|
| RAID 1/5/6/10, ZFS mirror | **No** | Protects against disk failure, not against deletion or corruption: an `rm -rf` is replicated to every disk instantly |
| ZFS/Btrfs/LVM snapshot in the same pool | **No** (but useful) | Lets you roll back in seconds, but dies with the pool. It is the first line of defence, not a copy |
| `rsync` or Syncthing to the NAS, without versions | **Partially** | Protects against server failure, but propagates deletions and encryption. Only counts if the destination keeps previous versions |
| ZFS snapshot sent with `zfs send` to another pool | **Yes** | Lives on another device and preserves the state at that moment |
| Backup with restic/borg/PBS to another host | **Yes** | Versioned, deduplicated, independent of the source |
| Database replication (PostgreSQL replica) | **No** | A `DROP TABLE` reaches the replica in milliseconds. It serves high availability, not recovery |

!!! warning "Syncing is not backing up"
    The difference is **history**. A backup keeps how the data looked yesterday, a week ago and a month ago; a sync only knows how it looks now. Nextcloud, Dropbox or an `rsync --delete` are synchronisation. If you delete something by mistake and take two days to notice, the sync has already deleted it everywhere.

## What counts as a different medium

When the rule was formulated, "two media" literally meant disk and tape. Today the useful reading is **two different failure domains**: the failure that takes one copy must not be able to take the other for the same cause.

Combinations that count:

- Local NVMe disk in the server + HDD in a NAS or a PBS.
- ZFS pool on the hypervisor + object storage (S3, B2, MinIO somewhere else).
- Disk in the server + external disk that is **disconnected** after the backup.

Combinations that do **not** count, even if they look like they do:

- Two directories in the same ZFS pool: same failure domain.
- Two disks from the same batch, bought together, on the same controller: they fail together uncomfortably often.
- Two buckets in the same cloud account: one compromised API key deletes both.

The medium with the best cost/safety ratio for a homelab is still a **disk that gets unplugged**. Nothing over the network reaches a powered-off disk in a drawer. Its problem is discipline: someone has to plug it in, and if the reminder is not automated it stops happening by the second month.

## What counts as off-site

"Off-site" protects against whatever affects the **whole** location: fire, theft, flood, a long power outage, or the ransomware that came in through a VM and moves laterally across the LAN.

Common options, from cheapest to most convenient:

| Option | Cost | Bandwidth | Notes |
|---|---|---|---|
| Disk rotated at a relative's house or at the office | Just the disk | None (carried by hand) | Encrypt, no exceptions. Manual rotation, easy to abandon |
| Second PBS or NAS in another house, over [WireGuard](../linux/wireguard.md) | Hardware ×2 | Home upload | You control both ends. Ideal if someone you trust also wants backups |
| Object storage (B2, S3, Wasabi, Scaleway, Hetzner Storage Box) | Cents per GB/month | Home upload | No hardware. Watch the **download** costs when restoring |
| VPS with a large disk | Fixed monthly | Good | More expensive per GB, but also serves as a remote PBS or an `rclone` destination |

The usual mistake is treating "off-site" as a geographic question. It also has to be **outside the credential domain**: if the key that writes to the bucket is the same one that can delete it and lives on the production server, the attacker who gets into production destroys the remote copy with two commands. The credential separation table is in [Secure Backup: offsite with real separation](../cybersecurity/backup_seguro.md#offsite-with-real-separation).

## The 3-2-1-1-0 variant

The original rule dates from when the threat was hardware. With ransomware as the main threat, two conditions are added:

- **1** copy **offline or immutable**: an unplugged disk, a tape, a bucket with *object lock*, a borg repository in `--append-only` mode (`prune` and `delete` are still accepted but do not free space until `borg compact`) or a PBS datastore with snapshot protection. Something an attacker with administrator access to the server **cannot delete**.
- **0** verification errors: every backup is checked (`restic check`, datastore verification in PBS) and at least one **test restore** is done periodically. A backup that has never been restored is a hypothesis.

The "0" is the one most often broken. It costs no hardware, it costs discipline. The way to make it stick is to automate it and have it **fail loudly** when it is not met: the scheduled verification that sends an alert if it does not finish cleanly, not the one that writes a log nobody reads.

## Deciding RPO, RTO and retention

Before choosing a tool you have to answer three questions **per type of data**, because not all of it is worth the same:

| Concept | Question | Homelab example |
|---|---|---|
| **RPO** (Recovery Point Objective) | How much data can I afford to lose? | Family photos: a day. Nextcloud database: an hour. Downloadable ISOs: any amount |
| **RTO** (Recovery Time Objective) | How long can I be without the service? | Internal DNS: minutes. Media server: days |
| **Retention** | How far back do I need to be able to go? | Configuration: months (to find when something broke). Personal data: years |

RPO sets the **frequency**: an RPO of one hour demands hourly backups, and that rules out tools that take longer than that or that hammer the source disk. RTO sets the **type of copy**: to restore in minutes you need a full VM image ready to boot (PBS, `vzdump`), not a file repository you have to reinstall and reconfigure on top of.

For retention, the standard scheme is **GFS** (*Grandfather-Father-Son*): keep the last N daily, M weekly and K monthly. With restic it is expressed directly:

```bash
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --keep-yearly 2 --prune
```

This keeps one copy per day for the last week, one per week for the last month, one per month for the last half year and one per year for the last two. Thanks to deduplication, the space cost of long retention is far smaller than the snapshot count suggests: only the blocks that changed are stored. PBS uses exactly the same model in its *prune jobs*; see [PBS: retention and prune](pbs.md#prune-and-garbage-collection).

!!! tip "Classify before you back up"
    What makes a plan cheapest is deciding what **not** to back up. Container images, downloaded packages, build caches and the media library you can download again do not need three copies; they need a list of how to get them back. Save the full 3-2-1 for what is irreplaceable: personal data, databases, configuration and secrets.

## Practical application in a homelab

A typical topology with a Proxmox hypervisor and services in containers:

- **Copy 1 (Production):** live data on the server (NVMe, ZFS pool). Hourly ZFS snapshots as the first line for "I just deleted that", **without counting them as a copy**.
- **Copy 2 (Local, different medium):** daily backup of VMs and containers to a [PBS](pbs.md) on another physical machine with HDDs. Files from hosts that are not VMs (the hypervisor itself, a Raspberry Pi) with [restic or borg](restic_borg.md) to the same destination.
- **Copy 3 (Remote, off-site):** the PBS syncs its datastore to a remote PBS over [WireGuard](../linux/wireguard.md) (*sync job* in *pull* mode from the remote), or the restic repositories are uploaded to object storage with write-only credentials.

And to meet the extra **1**: the remote copy has immutability (*object lock*, or a remote PBS that the production server **cannot** connect to: it is the remote that pulls the data). For the **0**: weekly datastore verification and a monthly test restore of a VM to a different ID.

The intermediate step, with a single server and no second machine:

- External USB disk for copy 2, mounted only during the backup and unmounted afterwards.
- Object storage for copy 3.
- ZFS snapshots for quick day-to-day recovery.

It is not perfect (the USB disk hangs off the same host and is vulnerable while mounted), but it is infinitely better than a single `rsync` to the NAS, and it can be improved piece by piece.

## Data Flow

```mermaid
flowchart LR
    Prod[Production Data] -->|Backup| Local[Local Copy]
    Local -->|Sync| Remote[Remote Copy]
    style Prod fill:#f96,stroke:#333
    style Local fill:#9f6,stroke:#333
    style Remote fill:#69f,stroke:#333
```

The direction of the arrows matters more than it looks. Production **pushes** to the local copy; that is unavoidable, because someone has to read the data. But the remote copy should **pull** from the local one, not the other way round: if the local one connects to the remote with write-and-delete credentials, an attacker who compromises it reaches all three copies. With *pull*, the remote holds read credentials over the local copy, and the local copy holds none over the remote.

## Automate and verify

A backup that depends on someone launching it is not a plan. The minimum is a timer and an alert when something does not finish cleanly. With systemd:

```ini
# /etc/systemd/system/backup-restic.service
[Unit]
Description=Daily backup with restic
OnFailure=notify-failure@%n.service

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/env
ExecStart=/usr/bin/restic backup /srv/datos /etc
ExecStart=/usr/bin/restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
```

```ini
# /etc/systemd/system/backup-restic.timer
[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

`Persistent=true` runs the backup at boot if the machine was off at the scheduled time, something classic `cron` does not do. `OnFailure=` triggers another unit when the service exits with an error; that unit is the one that sends the notice through whatever channel you use (email, ntfy, a webhook). The `%n` specifier passes it the name of the service that failed. How units and timers are written is in [Systemd](../linux/systemd.md).

Periodic verification, with another weekly timer:

```bash
restic check                          # integrity of the repository structure
restic check --read-data-subset=10%   # additionally reads and verifies 10 % of the data
```

Full verification (`--read-data`) downloads the entire repository, which on object storage costs money and time. `--read-data-subset` spreads that check out: at 10 % per week, everything has been read in ten weeks.

And the test that really counts, at least once a month:

```bash
restic restore latest --target /tmp/restore-test --include /srv/datos/critico
```

Compare what was restored with the original and, above all, time it. That time is your **real RTO**, and it is usually quite a bit longer than you assumed. For VMs, restore in PBS to a new ID and boot it without network. The full procedure and what to check is in [Secure Backup: restore testing](../cybersecurity/backup_seguro.md#restore-testing).

!!! danger "Monitor absence, not just failure"
    A backup that fails sends an alert. A backup that **does not run** (the timer is disabled, the host was off, the unit no longer exists after a reinstall) sends nothing. Monitor the *heartbeat*: have every backup send a ping when it finishes and let a tool like [Uptime Kuma](../monitoring/uptime_kuma.md) warn you if the ping does not arrive within the expected window.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| The backup "works" but the restore brings empty or corrupt files | A database or an open file is backed up live | Do a prior `dump`, or back up from a consistent snapshot; for VMs, use *snapshot* mode with the guest agent |
| The repository keeps growing even though the data does not change | `forget --prune` is not running, or the policy keeps too many copies | Review the retention policy; check that the prune finishes (it is long and sometimes killed by a timeout) |
| The remote copy holds the files encrypted by the ransomware | The copy is a sync, not a versioned backup | Switch to a tool with history; add immutability at the destination |
| The daily backup takes more than 24 hours | First copy with no incremental, slow network, or deduplication onto a spinning disk without cache | Do the first send locally and carry the disk; split into sets; review destination I/O |
| Restoring from the cloud costs more than months of storage | Download (*egress*) costs not considered | Pick a provider with free or cheap egress for copy 3; keep copy 2 local for routine restores |
| Nobody noticed the backups had not run for weeks | Only a failure alert exists, no absence alert | Heartbeat to an external monitor with a maximum interval between pings |
| The "offline" external disk never gets unplugged any more | Lack of discipline, manual process | Automate the reminder, or replace with immutability at the destination (object lock, append-only) |
| The restore needs a password that was on the lost server | Repository key only in production | Keep the key in a password manager and on paper, off-site. See [secrets management](../cybersecurity/gestion_secretos.md) |

## Best practices

- **Classify first.** Decide what is irreplaceable and what can be downloaded again. Full 3-2-1 only for the former.
- **Snapshots and RAID do not count as a copy.** Use them, but do not number them.
- **History always.** Any destination without previous versions is sync, not backup.
- **Pull rather than push for the remote copy.** Production should hold no credentials for the final destination.
- **One copy nobody can delete** from production: unplugged disk, object lock or append-only.
- **GFS retention**, with prune automated and watched: deduplication makes long retention cheap.
- **Encrypt everything that leaves the house**, and keep the key off the server and outside the backup itself.
- **Actually restore once a month** and time it: that is your RTO, not the one in the spreadsheet.
- **Alert on absence**, not just on failure. A heartbeat with a deadline catches the timer someone disabled.
- **Document the restore procedure** outside the system you back up. If the server burns, the wiki that lived on it burns too.

## References

- [Proxmox Backup Server](pbs.md) · [Restic and Borg](restic_borg.md)
- [Secure Backup: encryption, immutability and testing](../cybersecurity/backup_seguro.md)
- [WireGuard](../linux/wireguard.md) · [Systemd](../linux/systemd.md) · [Uptime Kuma](../monitoring/uptime_kuma.md)
- [restic documentation: removing snapshots according to a policy](https://restic.readthedocs.io/en/stable/060_forget.html)
- [Backblaze: the 3-2-1 rule explained](https://www.backblaze.com/blog/the-3-2-1-backup-strategy/)
