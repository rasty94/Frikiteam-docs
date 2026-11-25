---
title: "Restore drill: proving the backup comes back"
description: "Planning and running a restore drill in a homelab: realistic RPO and RTO, what to restore, an isolated machine, restic check, borg check and PBS verification, PostgreSQL from a dump or a hot file copy, timing it, logging the drill and automating part of it with a systemd timer."
keywords: "restore drill, restore test, backup, restic check, read-data-subset, borg check, PBS, qmrestore, pg_restore, RTO, RPO, systemd timer"
tags: ['backups', 'best-practices', 'proxmox', 'troubleshooting']
updated: 2026-11-25
difficulty: intermediate
estimated_time: 27 min
category: Backups
status: published
last_reviewed: 2026-11-25
prerequisites:
  - "[3-2-1 Backup Strategy](strategy_321.md)"
  - "Working backups with [restic or Borg](restic_borg.md) or [PBS](pbs.md)"
  - "A spare machine or VM to restore into"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Restore drill: proving the backup comes back

## The problem

You have backups. The timer runs every night, the log says it finishes fine and the repository grows by as much as it should. What you don't know is whether, on the day the disk dies, all of that turns back into a working service. Is the repository password stored anywhere other than the dead server? Is the database dump complete? Was the `docker-compose.yml` inside the backup, or only the data? How long does it really take?

A backup that has never been restored is not a backup: it is a hypothesis. The only way to turn it into a fact is to do what you would do in a disaster, cold, on another machine and with the clock running. That is a restore drill, and what follows is how to prepare it, run it and repeat it without turning it into a project.

!!! warning "Checked against the documentation, not yet tested in the homelab"
    The commands and options on this page have been checked against the official documentation of restic, Borg, Proxmox Backup Server, Proxmox VE and PostgreSQL (links in [References](#references)), but the full procedure has not yet been run in the homelab. Check the version of each tool before copying anything.

!!! note "What this covers and what it doesn't"
    This page is about the **drill**: what to restore, where, how to check it and how to record it. The 3-2-1 rule and how to choose RPO and RTO are in [3-2-1 Backup Strategy](strategy_321.md); how to make the backups, in [Restic and Borg](restic_borg.md) and [PBS](pbs.md); PostgreSQL dumps, in [PostgreSQL in Docker](../databases/postgres.md).

## 📋 Table of Contents

- [Before the drill: an RPO and RTO you can meet](#before-the-drill-an-rpo-and-rto-you-can-meet)
- [What to restore](#what-to-restore)
- [Where to restore: an isolated machine](#where-to-restore-an-isolated-machine)
- [Checking repository integrity](#checking-repository-integrity)
- [Restoring a file](#restoring-a-file)
- [Restoring a Docker service with PostgreSQL](#restoring-a-docker-service-with-postgresql)
- [Restoring a whole VM from PBS](#restoring-a-whole-vm-from-pbs)
- [Measuring the real time](#measuring-the-real-time)
- [Drill checklist and log](#drill-checklist-and-log)
- [Automating part of the verification](#automating-part-of-the-verification)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Before the drill: an RPO and RTO you can meet

A drill without a target only tells you "it worked" or "it didn't". With a target, it tells you whether you meet what you expected. Before you start, write down two numbers for each service you are going to rehearse:

- **RPO**: how much data you accept losing. The backup frequency sets it; a daily backup at 03:00 means, in the worst case, almost 24 hours of loss.
- **RTO**: how long you accept being without the service, counted from the moment you decide to restore until the service responds.

In a homelab, realistic means with what you have: if the only copy of 800 GB is in object storage and your connection downloads at 100 Mbit/s, the download alone takes hours, and no "half an hour" RTO fixes that. How to choose these numbers per type of data is in [Deciding RPO, RTO and retention](strategy_321.md#deciding-rpo-rto-and-retention). Here it is enough to have them written down before you start, because the drill is going to measure them.

## What to restore

You don't need to restore everything every time. Three levels, from cheapest to most expensive:

| Level | What gets restored | What it proves | Suggested frequency |
|---|---|---|---|
| **File** | One or more known files | That the repository opens, the key works and the data decrypts | Weekly, automatable |
| **Service** | A Docker service with its configuration, its volume and its database | That the backup includes everything needed to start, not just the data | Monthly or quarterly |
| **Machine** | A whole VM or container | That the RTO of a full machine is what you think it is | Quarterly or twice a year |

Start with the service you would miss the most and have touched the least recently. Rotate each time: the service restored last quarter is precisely the one that will give you the fewest surprises.

## Where to restore: an isolated machine

Restoring on top of the original is not a drill, it is a risk: if something goes wrong, you have turned a rehearsal into an incident. And restoring on the same machine doesn't prove the important part either, because the installed packages, the SSH keys, the repository password file and the configuration that never made it into the backup are all still there.

The drill machine should meet three conditions:

1. **Different from the original.** A freshly installed VM on the hypervisor, an old laptop or a Raspberry Pi. Whatever is not in the backup or in your documentation should not be on it.
2. **Isolated from the production network.** A restored service may start sending emails, syncing against the same bucket or fighting over the same IP as the original. With no network, or on an isolated VLAN or bridge, that can't happen.
3. **No access to the original during the test.** If halfway through the drill you log into the production server to copy a file, you have just found something that was not in the backup. Write it down: it is the most valuable result of the drill.

The machine does need to be able to read the repository. If the repository is remote, allow outbound traffic only to it; if it is local, plug in the disk. The credentials come from wherever you would have them in a disaster (the password manager, the paper envelope), not from the original server.

## Checking repository integrity

Integrity tells you the bytes in the repository are fine. It doesn't tell you the service starts, but it is cheap and catches bit rot before you discover it while restoring. It is worth doing before every drill and, automatically, between drills.

**restic.** `check` with no options inspects the structure and the indexes; to actually read the data you have to ask for it:

```bash
restic check                          # structure and indexes, without reading the data
restic check --read-data-subset=1/5   # the first of five parts of the pack files
restic check --read-data-subset=5%    # a randomly chosen 5 %
restic check --read-data              # all the data; expensive on object storage
```

With the `n/t` form, running `1/5` through `5/5` over five runs covers the whole repository. With a percentage or a size (`--read-data-subset=10G`), the subset is random on every run. `--read-data` and `--read-data-subset` cannot be combined.

**Borg** (Borg 1.4 syntax; Borg 2 changes how the repository is specified and several commands):

```bash
borg check /path/to/repo                                       # repository and archive metadata
borg check --verify-data /path/to/repo                         # also decrypts and verifies every chunk
borg check --repository-only --max-duration 3600 /path/to/repo # one-hour partial check
```

`--max-duration` splits a long check across several runs, each one continuing where the previous one stopped; it requires `--repository-only` and only performs checksum checks, not cryptographic ones. For a remote repository over SSH, the repository part runs on the server and the archive part on the client, which needs the key.

**PBS.** Verification lives on the server and is scheduled as a *verify job* (see [PBS: verification](pbs.md#verification)). Before the drill you can run it by hand on a datastore:

```bash
proxmox-backup-manager verify main --ignore-verified false
```

By default, `verify` skips snapshots that are already verified and whose verification has not expired; with `--ignore-verified false` it reads them all again, so on a large datastore it takes a while.

## Restoring a file

The simplest level, and the one worth automating. Restore something you know what it should look like, into an empty directory:

```bash
# restic: restore and read back what was restored to check it
restic restore latest --target /srv/drill --include /etc/nginx --verify

# Borg 1.4: extracts into the current directory
cd /srv/drill && borg extract /path/to/repo::server-2026-11-24 etc/nginx

# PBS: one .pxar archive from a client snapshot
proxmox-backup-client restore host/server/2026-11-24T03:00:00Z etc.pxar /srv/drill/etc
```

`--verify` in `restic restore` reads the written files again and compares them with the repository. In Borg, `borg extract --dry-run` runs the whole process (reading, checking the hash, decrypting, decompressing) without writing anything, which is useful when you don't have room to extract. The PBS snapshot name is copied literally from `proxmox-backup-client snapshot list`.

Then compare with what you expect: that the file exists, that it isn't empty and that it contains what it should. `nginx -t -c /srv/drill/etc/nginx/nginx.conf` tells you more than an `ls`.

## Restoring a Docker service with PostgreSQL

This is where almost all real failures show up: the `.env` that wasn't in the backup, the image tagged `latest` that is no longer the same, the missing roles. Assume a service laid out like this in `/srv/app`: `docker-compose.yml`, `.env`, the application files and, in `dumps/`, the nightly PostgreSQL dump made as in [PostgreSQL in Docker](../databases/postgres.md#backups-and-restore).

### Dump or hot file copy

How the database was backed up decides how it is restored, and the drill is the moment to find out which one you have:

| How it was backed up | How it is restored | What to keep in mind |
|---|---|---|
| `pg_dump -Fc` + `pg_dumpall --globals-only` | Empty database, globals with `psql`, data with `pg_restore` | Consistent even if the database was in use. The recommended path |
| Copy of the data directory with the database **stopped** | Restore the directory and start | Valid, but requires stopping the database on every backup |
| Atomic volume snapshot (ZFS, LVM) with the database running | Restore the directory and start | PostgreSQL starts as after a crash and replays the WAL. Data and WAL must be in the same snapshot |
| File copy with the database running, no snapshot | No guarantee | The PostgreSQL documentation rules it out: `tar` and the like don't take an atomic copy |

If the drill reveals that the last case is yours, there is no point going further: switch the backup to dumps and repeat.

### Restoring from a dump

On the isolated machine, with Docker installed:

```bash
mkdir -p /srv/drill && cd /srv/drill
restic restore latest --target /srv/drill --include /srv/app

cd /srv/drill/srv/app
pg_restore --list dumps/app.dump > /dev/null   # reads the whole dump table of contents, restores nothing

docker compose up -d db                        # only the database, with an empty volume
docker compose exec -T db psql -U myuser -d postgres < dumps/globals.sql
docker compose exec -T db createdb -U myuser app
docker compose exec -T db pg_restore -U myuser -d app --exit-on-error --no-owner < dumps/app.dump
```

`pg_restore --list` reads the dump's table of contents: if the file is truncated or corrupt, it fails in seconds without touching any database. `--exit-on-error` stops the restore at the first error instead of carrying on and leaving a half-restored database that looks fine. For large databases, `pg_restore -j` restores in parallel, but it needs to read the dump from a file (not from standard input), so you have to copy it into the container or mount it.

With the database restored, start the rest and check it the way a user would:

```bash
docker compose up -d
docker compose ps                                       # everything up and healthy
docker compose exec -T db psql -U myuser -d app -c '\dt'
curl -fsS http://localhost:8080/ > /dev/null && echo "responding"
```

Pick a data check that makes sense for the application: the row count of a main table, the last record created or a user you know exists. The date of that last record is also your **real RPO**.

### Restoring from a file copy

If the backup is an atomic snapshot of the data directory, restore the full directory to the path the container mounts and start only the database:

```bash
docker compose up -d db
docker compose logs -f db
```

The logs should show that the database system was not properly shut down and that automatic recovery is in progress, followed by it being ready to accept connections. If instead you see errors about missing WAL files or invalid pages, the copy was not consistent. The PostgreSQL major version of the image has to match the data directory's: with a different major version, the server refuses to start.

## Restoring a whole VM from PBS

For a VM backed up to PBS from Proxmox VE, restore to a **new ID** and never on top of the original. From the PVE node's command line:

```bash
pvesm list pbs-storage --vmid 100     # snapshots of VM 100 in the PBS storage
qmrestore pbs-storage:backup/vm/100/2026-11-24T03:00:00Z 9100 --storage local-zfs --unique 1
```

`--unique 1` assigns new MAC addresses so the copy doesn't clash with the original. Before starting it, disconnect the network: look up the `net0` line with `qm config 9100` and set it again with `link_down=1` added, for example `qm set 9100 --net0 virtio=<MAC>,bridge=vmbr0,link_down=1` with the MAC that `qm config` shows. Then:

```bash
qm start 9100
# check from the PVE console that it boots, that the services come up and that the data is there
qm stop 9100
qm destroy 9100 --purge
```

For LXC containers the equivalent is `pct restore`. If the RTO is tight, `qmrestore` has `--live-restore 1` (PBS only): the VM starts as soon as the restore begins and data is read on demand, with slow reads until it finishes. It is worth measuring in a drill before relying on it in an incident.

## Measuring the real time

The real RTO is not how long `restic restore` takes: it is everything that happens from the moment you decide to restore. Measure in phases, because the total is usually spread where you didn't expect:

```bash
t0=$(date +%s)
# ... prepare the machine, retrieve credentials
t1=$(date +%s)
# ... restore the files
t2=$(date +%s)
# ... restore the database and start the service
t3=$(date +%s)
echo "preparation: $(( (t1-t0)/60 )) min, restore: $(( (t2-t1)/60 )) min, startup and checks: $(( (t3-t2)/60 )) min"
```

Also write down what isn't a command: the time spent looking for the password, reading your own documentation or pulling a Docker image that is no longer cached. If the total exceeds the RTO you wrote down at the start, the drill has done its job: now you know which part to shorten (a local copy as well as the remote one, a prepared VM, clearer documentation).

## Drill checklist and log

A short list, the same every time:

1. Written target: service, level (file, service or machine), expected RPO and RTO.
2. Isolated machine ready, with no access to the original.
3. Repository credentials taken from the emergency copy, not from the server.
4. Integrity checked (`restic check`, `borg check` or PBS verify).
5. Restore done following only the existing documentation.
6. Functional check: the service responds and the data makes sense.
7. Real RPO (date of the last data) and real RTO (total time by phase) recorded.
8. Problems found and an action for each.
9. Drill machine destroyed and restored data deleted.

And one log per drill, in the same repository as the homelab documentation:

```text
Date:             2026-11-25
Service:          app (Docker + PostgreSQL)
Level:            service
Snapshot:         latest (2026-11-25 03:00)
Target:           RPO 24 h, RTO 2 h
Result:           OK / FAILED / OK with issues
Real RPO:         last record 2026-11-24 23:41
Real RTO:         preparation __ min, restore __ min, startup __ min, total __ min
Problems:         - .env was not in the backup (recovered from the password manager)
Actions:          - add .env to the backup path list
Next:             2026-12 (another service)
```

The "Problems" example is illustrative: it is the kind of finding worth writing down. Comparing the third log with the first is what proves the plan is improving.

## Automating part of the verification

The full drill is manual by design: what it proves is that a person can restore with what there is. But the mechanical part (integrity, restoring a file, reading the dump) can run on its own every week. A minimal script:

```bash
#!/usr/bin/env bash
# /usr/local/bin/restore-check.sh
set -euo pipefail
source /etc/restic/env                      # RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

restic check --read-data-subset=5%
restic restore latest --target "$work" --include /srv/app/dumps --verify
pg_restore --list "$work/srv/app/dumps/app.dump" > /dev/null
curl -fsS -m 10 "$PING_URL" > /dev/null     # tells the monitor it finished fine
```

`pg_restore` has to be installed on the host (the PostgreSQL client package, same major version as the dump or newer). `PING_URL` is the URL of a *push* monitor, for example in [Uptime Kuma](../monitoring/uptime_kuma.md), and can live in the same environment file. The systemd service and timer:

```ini
# /etc/systemd/system/restore-check.service
[Unit]
Description=Weekly restore verification
OnFailure=notify-failure@%n.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/restore-check.sh
```

```ini
# /etc/systemd/system/restore-check.timer
[Timer]
OnCalendar=Sun *-*-* 05:00:00
RandomizedDelaySec=30min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now restore-check.timer
systemctl list-timers restore-check.timer
```

`OnFailure=` covers failure and the ping covers silence: if the timer stops running, the monitor alerts because the ping doesn't arrive. The `notify-failure@.service` unit is the same one used in [3-2-1 Backup Strategy](strategy_321.md#automate-and-verify); a more complete script, with snapshot age and hash comparison, is in [Secure Backup](../cybersecurity/backup_seguro.md#automating-the-periodic-test). Schedule the verification well away from the backup time so they don't compete for the repository.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| The repository can't be opened on the drill machine | The password or key was only on the original server | Store the repository password (and the Borg key, or the PBS key if it encrypts client-side) in a password manager and on paper, off-site |
| `restic check` passes but the restore fails to decrypt | `check` without `--read-data` doesn't read the data | Add `--read-data-subset` to the periodic verification |
| The service doesn't start: configuration missing | `.env`, `docker-compose.yml` or certificates outside the backup paths | Back up the service's whole directory, not just the data volume |
| `pg_restore` fails with nonexistent roles | The globals dump is missing | Add `pg_dumpall --globals-only` to the backup, or restore with `--no-owner` |
| PostgreSQL doesn't start with the restored directory | Hot copy without a snapshot, or a different image major version | Switch to dumps; pin the image tag to the major version |
| The restored VM clashes with the original on the network | Same MAC or same IP | Restore with `--unique 1` and start with `link_down=1` |
| The measured RTO is three times the expected one | Download from the remote copy, images to pull, incomplete documentation | Local copy for routine restores; document the missing steps |
| The weekly verification stopped running and nobody noticed | There is only a failure alert, not an absence alert | Ping a *push* monitor on success |

## Best practices

- **Restore on another machine, without the production network and without access to the original.** Whatever you have to fetch from the original server is what's missing from the backup.
- **Put numbers down before you start.** Expected RPO and RTO in writing; the drill confirms or corrects them.
- **Rotate the service and the level.** A file every week automatically, a service every month or quarter, a whole machine a couple of times a year.
- **Follow your documentation to the letter.** If a step isn't written down, the drill has found a flaw even if you solve it from memory.
- **Pin versions.** The database image tag and the backup tool version are part of what gets restored.
- **Log every drill**, including the ones that go well. The log is what turns "I think it works" into "it worked on such a day, in this much time".
- **Clean up afterwards.** A restored copy with real data forgotten on a test VM is a security problem.

## References

- [restic: Checking integrity and consistency](https://restic.readthedocs.io/en/stable/045_working_with_repos.html#checking-integrity-and-consistency)
- [restic: Restoring from backup](https://restic.readthedocs.io/en/stable/050_restore.html)
- [borg check](https://borgbackup.readthedocs.io/en/stable/usage/check.html) · [borg extract](https://borgbackup.readthedocs.io/en/stable/usage/extract.html)
- [Proxmox Backup Server: Backup Client Usage](https://pbs.proxmox.com/docs/backup-client.html) · [proxmox-backup-manager](https://pbs.proxmox.com/docs/proxmox-backup-manager/synopsis.html)
- [qmrestore(1)](https://pve.proxmox.com/pve-docs/qmrestore.1.html) · [qm(1)](https://pve.proxmox.com/pve-docs/qm.1.html) · [Backup and Restore in Proxmox VE](https://pve.proxmox.com/pve-docs/chapter-vzdump.html)
- [PostgreSQL: pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html) · [File System Level Backup](https://www.postgresql.org/docs/current/backup-file.html)
- [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
- [3-2-1 Backup Strategy](strategy_321.md) · [Restic and Borg](restic_borg.md) · [PBS](pbs.md) · [Secure Backup](../cybersecurity/backup_seguro.md)
- [PostgreSQL in Docker](../databases/postgres.md) · [Systemd](../linux/systemd.md)
