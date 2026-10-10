---
title: "Agnostic Backups: Restic and Borg"
description: "File backup with deduplication and encryption on any Linux: choosing between restic and borg, local and remote repositories (SFTP, S3, rest-server), retention, verification, systemd automation and restores that actually work."
keywords: "restic, borg, borgbackup, backup, deduplication, encryption, sftp, s3, rest-server, prune, forget, systemd timer, restore"
tags: ['backups', 'linux']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 20 min
category: Backups
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Linux shell and SSH with keys"
  - "Basic systemd (units, timers, journalctl)"
  - "[3-2-1 Backup Strategy](strategy_321.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Agnostic Backups: Restic and Borg

## The problem

The typical homelab backup is a nightly `rsync` to a USB disk or a NAS. It works until it doesn't: `rsync` replicates yesterday's accidental deletion, ransomware encrypts the source and the next night the destination too, and nobody has ever tried a restore. There is no history, no encryption and no way to know whether the copy is intact.

`restic` and `borg` solve exactly that. Both split files into blocks, store each block only once (**deduplication**), encrypt everything before it leaves the machine and keep independent **snapshots**: you can go back to the state of three weeks ago without every copy taking up the full size. They are command-line tools, system-agnostic and daemonless: one binary, one repository and a cron job.

!!! note "What this covers and what it does not"
    This page covers **usage**: creating the repository, taking backups, retention, verification and restores. The rule of how many copies and where is in [3-2-1 Strategy](strategy_321.md); the security layer (append-only repositories, ransomware threat model, restore tests) lives in [Secure backup](../cybersecurity/backup_seguro.md). For Proxmox virtual machines the right tool is [PBS](pbs.md), not this one.

## 📋 Table of Contents

- [Restic or Borg: how to choose](#restic-or-borg-how-to-choose)
- [Common concepts](#common-concepts)
- [Restic](#restic)
- [BorgBackup](#borgbackup)
- [Remote repositories](#remote-repositories)
- [Automating with systemd](#automating-with-systemd)
- [Databases and containers](#databases-and-containers)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Restic or Borg: how to choose

| | Restic | BorgBackup |
|---|---|---|
| Language / installation | Go, a static binary | Python + C; distro package or standalone binary |
| Destinations | Local, SFTP, S3 and compatibles (MinIO, Ceph RGW), REST server, Azure, GCS, rclone (anything) | Local and SSH (**needs `borg` installed on the destination**) |
| Encryption | Always on, cannot be disabled | Optional: `repokey`, `keyfile` or `none` |
| Compression | Yes, since repo v2 (see version warning) | Yes, `lz4`, `zstd`, `zlib`, `lzma`, configurable per archive |
| Several clients on the same repo | Yes, with cooperative locks | Possible but discouraged: one repo per host |
| Append-only | Via `rest-server --append-only` or S3 bucket policies | Native with `borg serve --append-only` |
| Mount as filesystem | `restic mount` (FUSE) | `borg mount` (FUSE) |

Rule of thumb: **restic** if the destination is S3/MinIO or you want several hosts in one repository; **borg** if the destination is your own Linux server over SSH and you care about squeezing out compression. Both are mature and both restore; there is no bad choice, only a choice inconsistent with the destination.

## Common concepts

- **Repository**: the directory or bucket where the encrypted blocks live. Without the passphrase it is noise; with it, the whole history.
- **Snapshot** (restic) / **archive** (borg): the state of the copied paths at one instant. Each one is complete and independent for restore purposes, even though on disk it only takes up the new blocks.
- **Content-based deduplication**: files are split into variable-size chunks based on their content, so moving or renaming a file, or inserting bytes at the start, does not cause it to be uploaded again in full.
- **Retention**: a policy of how many snapshots to keep (`forget`/`prune`). Without it the repository grows indefinitely.
- **Verification**: checking that the blocks are still there and decrypt correctly (`check`). A repository that is not verified is a hope, not a backup.

!!! danger "The passphrase is the backup"
    If you lose the passphrase (or borg's keyfile) you lose **all** the copies, with no exception and no recovery. Keep it in the password manager and in a physical place, outside the machine you are backing up. See [Secrets management](../cybersecurity/gestion_secretos.md).

## Restic

### Repository and credentials

Restic reads the repository and passphrase from environment variables, which avoids typing them in every command and in the shell history:

```bash
# /root/.restic-env  (chmod 600)
export RESTIC_REPOSITORY=/srv/backup/restic
export RESTIC_PASSWORD_FILE=/root/.restic-pass
```

```bash
source /root/.restic-env
restic init
```

`init` creates the repository structure and asks for the passphrase if it does not find it in the environment. To avoid depending on a plaintext file, `RESTIC_PASSWORD_COMMAND` accepts a command that prints it, for example a query to a secrets manager.

### First backup and exclusions

```bash
restic backup /etc /home /srv/app \
    --exclude-file=/root/restic-excludes.txt \
    --one-file-system \
    --tag diario
```

```text
# /root/restic-excludes.txt
/home/*/.cache
/home/*/.local/share/Trash
*.tmp
node_modules
```

`--one-file-system` prevents a forgotten mount (an NFS share or the backup disk itself) from ending up inside the copy. Tags are free-form labels that later serve to filter and to apply different retentions.

Restic returns exit code 3 when it managed to complete the snapshot but **some file could not be read** (permissions, file vanished mid-backup). It is the typical case of a script that "works" and has not copied a directory for months: check it in the log.

```bash
restic snapshots                    # list snapshots, with host, paths and tags
restic snapshots --tag diario --latest 3
restic ls latest /etc               # contents of a snapshot
restic diff <id-anterior> <id-nuevo> # what changed between two snapshots
restic stats                        # logical size and, with --mode raw-data, the real size on disk
```

### Restoring

```bash
# The whole latest snapshot into a clean directory
restic restore latest --target /tmp/restore

# Only a subtree
restic restore latest --target /tmp/restore --include /etc/nginx

# The latest snapshot of a specific host
restic restore latest --host servidor-web --target /tmp/restore
```

To look for a file without knowing which snapshot it is in, mount the repository: `restic mount /mnt/restic` exposes a tree with `snapshots/`, `hosts/` and `tags/` that you can browse with normal tools. It requires FUSE and leaves the process in the foreground until you unmount it.

### Retention: forget and prune

`forget` decides which snapshots are surplus and `prune` removes the blocks nobody references any more. They are two steps because the second one is expensive:

```bash
restic forget \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 12 \
    --keep-yearly 2 \
    --prune
```

The `--keep-*` rules add up: a snapshot is kept if **any** of them saves it. By default it groups by host and paths, so two servers in the same repository have independent retentions. Test the policy with `--dry-run` before the first real run.

### Verifying: check

```bash
restic check                        # structure and indexes
restic check --read-data-subset=10% # additionally, downloads and verifies 10 % of the data
restic check --read-data            # everything; expensive on S3, essential once in a while
```

Plain `check` is fast and detects broken indexes; `--read-data` is the only thing that proves the blocks decrypt. A different subset each week walks the whole repository in a few months without paying the bill all at once.

!!! warning "Compression and repository version"
    Restic's compression requires repositories in v2 format, which are the ones `init` creates in recent versions. An old repository keeps working without compression; migrating it is possible but it is a deliberate operation. Check `restic version` and the documentation for your version before relying on compression in capacity calculations.

## BorgBackup

### Repository and key

```bash
export BORG_REPO=/srv/backup/borg
export BORG_PASSCOMMAND="cat /root/.borg-pass"

borg init --encryption=repokey
```

With `repokey` the key lives inside the repository, protected by the passphrase; with `keyfile` it lives in the client's `~/.config/borg/keys/` and **without that file the repository will not open even if you know the passphrase**. In both cases export the key and store it with the passphrase:

```bash
borg key export $BORG_REPO /root/borg-key-backup.txt
```

### Creating archives

Each copy is a named *archive* inside the repository. Borg expands placeholders such as `{hostname}` and `{now}` so you do not have to invent names:

{% raw %}

```bash
borg create --stats --progress \
    --compression zstd,3 \
    --exclude-caches \
    --exclude '/home/*/.cache' \
    --one-file-system \
    ::'{hostname}-{now:%Y-%m-%d_%H%M}' \
    /etc /home /srv/app
```

{% endraw %}

`--exclude-caches` skips directories marked with a `CACHEDIR.TAG` file, which is how pip, cargo or many browsers flag their cache. `--stats` prints at the end the original, compressed and **deduplicated** size of the archive: the last figure is how much the repository actually grew.

```bash
borg list                           # archives in the repository
borg list ::servidor-2026-10-09_0300 | head
borg info                           # total and deduplicated size of the repository
```

### Restoring and mounting

`borg extract` unpacks **into the current directory**, so move to an empty destination first:

```bash
mkdir -p /tmp/restore && cd /tmp/restore
borg extract ::servidor-2026-10-09_0300 etc/nginx
```

Paths inside the archive are stored without the leading slash (`etc/nginx`, not `/etc/nginx`). To explore before deciding what to recover:

```bash
borg mount ::servidor-2026-10-09_0300 /mnt/borg
ls /mnt/borg/etc
borg umount /mnt/borg
```

### Prune and compact

```bash
borg prune --list \
    --keep-daily=7 \
    --keep-weekly=4 \
    --keep-monthly=12 \
    --glob-archives '{hostname}-*'

borg compact
```

`prune` marks which archives are surplus; in borg 1.2 and later the space is **not freed until you run `borg compact`**. If the repository keeps growing despite retention, that step is almost always missing. The `--glob-archives` filter matters when several hosts share a repository: without it, the policy is applied to all archives mixed together.

!!! warning "Borg version"
    This page describes borg 1.x. In 1.1 the `prune` filter was called `--prefix` and `compact` did not exist (`prune` itself freed space). Borg 2 changes the syntax of several commands and the repository format. Check `borg --version` on client **and server**: they must be compatible with each other.

Repository verification:

```bash
borg check                          # metadata and consistency
borg check --verify-data            # decrypts and checks every block; slow
```

## Remote repositories

What is not on another machine is not a backup. Options in order of simplicity:

**SFTP (restic) / SSH (borg)**. A Linux server with a dedicated account and an SSH key. Restic only needs SFTP on the destination; borg needs the `borg` binary installed there, because the remote side does real work.

```bash
# restic
export RESTIC_REPOSITORY=sftp:backup@nas.lan:/srv/restic/servidor-web

# borg
export BORG_REPO=ssh://backup@nas.lan/srv/borg/servidor-web
```

**S3 and compatibles (restic only)**. MinIO, Ceph RGW or a cloud provider. Credentials go in `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` even if the destination is not AWS.

```bash
export RESTIC_REPOSITORY=s3:https://minio.lan:9000/backups-servidor-web
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

Concurrency settings and how restic coexists with a Ceph cluster are covered in [Storage protocols](../storage/protocols/protocols.md).

**rest-server (restic)**. Restic's official HTTP server. Its main appeal is the `--append-only` option: the client can add snapshots but not delete them, so an attacker with the server's credentials cannot destroy the history. Retention is then run **from the server**, not from the client.

**Restricted `borg serve`**. The borg equivalent is configured in the destination's `authorized_keys`:

```text
command="borg serve --restrict-to-repository /srv/borg/servidor-web --append-only",restrict ssh-ed25519 AAAA... backup@servidor-web
```

That key can only run `borg serve` on that repository and can only append. The full reasoning, and why append-only is the defense that really matters against ransomware, is in [Secure backup](../cybersecurity/backup_seguro.md).

## Automating with systemd

A systemd timer gives you logs in the journal, `Persistent=true` to recover missed runs and a single place to look when it failed. Better than cron for this; unit details are in [Systemd](../linux/systemd.md).

```ini
# /etc/systemd/system/restic-backup.service
[Unit]
Description=Backup con restic
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/root/.restic-env
ExecStart=/usr/bin/restic backup /etc /home /srv/app --exclude-file=/root/restic-excludes.txt --one-file-system --tag diario
ExecStart=/usr/bin/restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
Nice=10
IOSchedulingClass=idle
```

```ini
# /etc/systemd/system/restic-backup.timer
[Unit]
Description=Backup diario con restic

[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now restic-backup.timer
systemctl list-timers restic-backup.timer
systemctl start restic-backup.service        # manual run to test
journalctl -u restic-backup.service -n 50
```

`EnvironmentFile` with the variables file is not equivalent to `source`: it does not accept `export` or shell expansions, only `KEY=value`. If the file reuses the one you use in the shell, remove the `export`s. Add `restic check --read-data-subset=5%` in a second weekly timer; do not put it in the daily one, it lengthens the window for no reason.

## Databases and containers

Copying the data files of a running database produces an inconsistent backup that sometimes restores and sometimes does not. Take a logical dump and pipe it straight into the tool, with no intermediate file:

```bash
# restic reads from stdin and stores the stream as a file with the given name
pg_dump -Fc mi_base | restic backup --stdin --stdin-filename mi_base.dump --tag postgres
```

Borg has the equivalent in `borg create` with `-` as the path (it reads from stdin). Deduplication works on dumps too: an uncompressed *custom*-format `pg_dump` deduplicates much better than a compressed one, because compression destroys the matches between versions. Let the backup tool compress. PostgreSQL backups in Docker are detailed in [PostgreSQL](../databases/postgres.md).

For container volumes, the most robust approach is to copy the volume directory from the host (`/var/lib/docker/volumes/<name>/_data`, or the bind mount path) with the container stopped or the application in a consistent state. A container with the database inside follows the rule above: dump, not files.

Virtual machines are a different problem: a file backup inside the VM does not restore the VM. For Proxmox use [PBS](pbs.md), which makes disk-level copies with its own deduplication, and leave restic or borg for the data inside the VMs and for everything that is not Proxmox.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `repository is already locked` (restic) | A previous run died without releasing the lock | Confirm no other restic is running and `restic unlock` |
| `Failed to create/acquire the lock` (borg) | Same thing in borg | `borg break-lock` only if you are sure no other process is running |
| The backup ends with code 3 | Some file could not be read (permissions, vanished mid-run) | Check the log; run as root or exclude whatever changes constantly |
| The repository grows despite retention | `--prune` (restic) or `borg compact` (borg) is missing | Add the missing step to the timer |
| `borg: command not found` when connecting over SSH | borg not installed on the remote server, or outside the `PATH` of non-interactive sessions | Install it; if it is in an odd location, `BORG_REMOTE_PATH` |
| Very slow backup the first time over S3 | Normal: everything is new. Later runs only upload new blocks | Limit with `--limit-upload` if it saturates the network |
| The timer did not run on time | Machine was off; without `Persistent=true` it is not recovered | Add `Persistent=true` and check `systemctl list-timers` |
| `restic check` warns about *pack files* without index | Backup interrupted midway | `restic rebuild-index` and repeat `check`; if it persists, do not ignore it |
| Restores files as `root:root` instead of the original owner | Restore run without privileges | Restore as root, or consciously accept the loss of ownership |

Wrong-passphrase errors are unmistakable in both tools and have no technical fix: the only question is where you stored the copy of the key.

## Best practices

- **Restore something every month.** Any file into `/tmp/restore` and check its content. It is the only proof that the backup exists; everything else is faith.
- **Passphrase and key outside the machine**, in the password manager and on paper. With borg's `keyfile`, the key file too.
- **Explicit retention from day one.** A repository without `forget`/`prune` or without `prune`/`compact` is a disk that fills up silently.
- **Periodic `check` with data reading**, even if only a subset. A repository with corrupt blocks does not warn you until you try to restore.
- **One repository per host (borg)** and, if you share a repository in restic, group retention by host and tags.
- **Append-only whenever the destination allows it**, with retention run from the server. Separate who writes from who deletes.
- **systemd timer, not bare cron**: logs in the journal, `Persistent=true` and a `systemctl status` that tells the truth.
- **Logical dumps for databases**, never the live data files.
- **Measure the real ratio** with `restic stats --mode raw-data` or `borg info`: what the repository really takes up, not the logical size of the copies.

## References

- [restic documentation](https://restic.readthedocs.io/) · [restic on GitHub](https://github.com/restic/restic)
- [rest-server](https://github.com/restic/rest-server)
- [BorgBackup documentation](https://borgbackup.readthedocs.io/)
- [3-2-1 Strategy](strategy_321.md) · [Proxmox Backup Server](pbs.md)
- [Secure backup: ransomware, append-only and restore tests](../cybersecurity/backup_seguro.md)
- [Secrets management](../cybersecurity/gestion_secretos.md) · [Systemd](../linux/systemd.md)
- [Storage protocols](../storage/protocols/protocols.md) · [PostgreSQL](../databases/postgres.md)
