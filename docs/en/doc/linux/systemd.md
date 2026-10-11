---
title: "Systemd: Service Management"
description: "Units, timers, drop-ins, sandboxing and journalctl in systemd: how to run, monitor and harden your own services on a Linux server or homelab."
keywords: "systemd, systemctl, journalctl, unit, timer, drop-in, sandboxing, systemd-analyze, service, homelab"
tags: ['linux', 'systemd']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 20 min
category: Linux
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Linux terminal with sudo access"
  - "Basic knowledge of Linux processes and users"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Systemd: Service Management

## The problem

You left a script in a `tmux` session, or launched it from `/etc/rc.local`, or with a `nohup` that worked "for now". One day the server reboots, the script does not come back, and nobody notices until someone asks why there have been no backups for three weeks. And when you finally investigate there are no logs, no exit code, and no way to tell who killed it.

Systemd is PID 1 on almost every modern distribution and is already supervising everything else. Turning your script into a *unit* gives it automatic startup, sensible restarts, dependencies, centralised logs and isolation from the rest of the system for a few lines of configuration.

!!! note "What this covers and what it does not"
    This page deals with **your own services and timers**: writing, debugging and hardening them. For containers as services, see [Podman Quadlet](../docker/quadlets.md), which builds on everything explained here.

## 📋 Table of Contents

- [How it works](#how-it-works)
- [Creating a custom service](#creating-a-custom-service)
- [Everyday commands](#everyday-commands)
- [Dependencies and boot order](#dependencies-and-boot-order)
- [Restart policy](#restart-policy)
- [Modifying units with drop-ins](#modifying-units-with-drop-ins)
- [Timers: the cron alternative](#timers-the-cron-alternative)
- [Logs with journalctl](#logs-with-journalctl)
- [Sandboxing and hardening](#sandboxing-and-hardening)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## How it works

Systemd works with *units*, declarative text files whose suffix indicates the type: `.service` (a process), `.timer` (scheduled activation), `.socket`, `.mount`, `.target` (a group of units, equivalent to the old runlevels), among others.

Units live in three places, from lowest to highest priority:

| Path | Managed by | Purpose |
|------|------------|---------|
| `/usr/lib/systemd/system/` | The distro package | System units; not edited by hand |
| `/run/systemd/system/` | Systemd, at runtime | Transient units, gone after a reboot |
| `/etc/systemd/system/` | You | Your own units and *overrides* of packaged ones |

Systemd reads the files at boot or on `daemon-reload`, not every time you query the status. Editing a unit without reloading changes nothing: `systemctl status` warns that the unit has changed on disk.

## Creating a custom service

To run a script or binary as a service, create a file at `/etc/systemd/system/my-service.service`:

```ini
[Unit]
Description=My Custom Service
After=network.target

[Service]
Type=simple
User=my_user
ExecStart=/usr/bin/python3 /home/my_user/script.py
Restart=always

[Install]
WantedBy=multi-user.target
```

What each block does:

- **`[Unit]`**: metadata and relationships with other units (description, ordering, dependencies).
- **`[Service]`**: how the process runs. `Type=simple` assumes `ExecStart` is the main process and stays in the foreground; it is right for almost any script or binary that does not fork into the background. `User=` prevents it from running as root.
- **`[Install]`**: what happens on `systemctl enable`. `WantedBy=multi-user.target` hooks it into the normal boot of a server.

`ExecStart` expects an **absolute path** to the executable (systemd also accepts a plain name without slashes, which it looks up in `/usr/bin` and similar; an absolute path leaves no ambiguity). There is no shell `PATH` and no expansion of `~`, pipes or redirections: if you need a shell, invoke it explicitly with `/bin/sh -c '...'`.

To pass variables without writing them in the unit, point to an environment file:

```ini
[Service]
EnvironmentFile=/etc/my-service/env
WorkingDirectory=/opt/my-service
ExecStart=/opt/my-service/bin/app --config /etc/my-service/config.yml
```

The `env` file contains `KEY=value` lines. Restrict read access (`chmod 600`, owned by root) if it holds credentials; see [secrets management](../cybersecurity/gestion_secretos.md).

!!! warning "`Type=` depends on the program"
    If the program daemonises itself (forks and the original process exits), `Type=simple` will make systemd consider it dead. Today the usual approach is the opposite: configure the program to stay in the foreground. `Type=notify` only works if the program notifies systemd with `sd_notify`; check its documentation before using it.

## Everyday commands

After creating or editing a file you must reload and, the first time, enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now my-service
```

`enable` creates the `[Install]` link for the next boot; `--now` also starts it immediately. Other common operations:

- `systemctl start my-service`: Start.
- `systemctl stop my-service`: Stop.
- `systemctl restart my-service`: Stop and start (interrupts the service).
- `systemctl reload my-service`: Reload configuration without stopping, only if the unit defines `ExecReload=`.
- `systemctl enable my-service`: Enable at boot.
- `systemctl disable my-service`: Remove from boot.
- `systemctl status my-service`: View status and recent logs.
- `systemctl list-units --failed`: List everything that has failed.
- `journalctl -u my-service -f`: Follow logs in real time.

`status` shows whether it is `active (running)`, `failed` or `inactive`, the main PID, the tree of child processes and the last journal lines. It is the first command for any incident.

## Dependencies and boot order

There are two independent axes and confusing them is the most common mistake:

- **Ordering**: `After=` and `Before=` only say who starts first. They start nothing.
- **Requirement**: `Wants=` (soft dependency) and `Requires=` (hard) pull another unit in at startup. Without `After=`, they start in parallel.

For a service that needs the network and a local database:

```ini
[Unit]
Description=Application that needs a database
Wants=network-online.target
After=network-online.target postgresql.service
Requires=postgresql.service
```

`network.target` only indicates that the network stack is configured, not that there is connectivity. If your service needs to resolve DNS or reach an NFS share at boot, use `network-online.target` with `Wants=`. It requires the service that waits for the network (NetworkManager or systemd-networkd) to have its "wait-online" enabled; check this on your distribution.

With `Requires=`, if the dependency stops or fails, your service stops too. If you prefer it to survive restarts of the other unit, use `Wants=`.

## Restart policy

`Restart=always` restarts every time, even after an `exit 0`. That is usually too much. These are the most useful options:

| Value | Restarts when |
|-------|---------------|
| `no` | Never (default) |
| `on-failure` | Non-zero exit code, unclean signal or timeout |
| `on-abnormal` | Signal or timeout, but not for a non-zero exit code |
| `always` | Always, except after an explicit `systemctl stop` |

For a long-lived daemon, `on-failure` with a pause is the healthiest choice:

```ini
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Restart=on-failure
RestartSec=5
```

`StartLimitIntervalSec` and `StartLimitBurst` belong in `[Unit]`: if the unit starts more than 5 times in 300 seconds, systemd stops trying and marks it `failed`. Without that limit a service broken in a loop is constant journal noise and wasted CPU. To clear that state you need `systemctl reset-failed my-service`.

## Modifying units with drop-ins

Never edit the files in `/usr/lib/systemd/system/`: a package update overwrites them. A *drop-in* is an additional file that overrides or adds directives and survives updates. The most convenient way:

```bash
sudo systemctl edit nginx
```

It opens an editor on `/etc/systemd/system/nginx.service.d/override.conf` and, when you save, reloads systemd for you. You only write what changes:

```ini
[Service]
Restart=on-failure
RestartSec=5
LimitNOFILE=65536
```

Two things to keep in mind:

- **List directives** such as `ExecStart=`: a drop-in *appends* to them. To replace, first clear with an empty `ExecStart=` line and then write the new one.
- `systemctl edit --full nginx` copies the whole unit to `/etc/systemd/system/`, which from then on ignores any change from the package. Use it only if the override is not enough.

To see the combined result of the unit plus drop-ins:

```bash
systemctl cat nginx
```

And to return to the original behaviour, `sudo systemctl revert nginx` removes the overrides from `/etc`.

## Timers: the cron alternative

A timer is a `.timer` unit that activates a `.service` of the same name. Compared with cron, each run is recorded in the journal with its exit code, inherits sandboxing and dependencies, and you can trigger it by hand with `systemctl start`.

A nightly backup, in two files. The service, `/etc/systemd/system/backup.service`:

```ini
[Unit]
Description=Nightly backup

[Service]
Type=oneshot
User=backup
ExecStart=/usr/local/bin/backup.sh
```

`Type=oneshot` indicates that the process finishes on its own. It has no `[Install]` because the timer activates it. And `/etc/systemd/system/backup.timer`:

```ini
[Unit]
Description=Run the backup every night

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

- `OnCalendar=` uses a systemd-specific format, not cron's.
- `Persistent=true` runs a missed pass if the machine was off at the scheduled time. Very useful in a homelab that is not always on.
- `RandomizedDelaySec=` spreads the load when many hosts schedule the same time.

You enable the **timer**, not the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer
systemctl list-timers
```

`list-timers` shows when it last ran and when the next run is due. To validate a calendar expression before trusting it there is `systemd-analyze calendar "*-*-* 03:00:00"`, which prints the normalised form and the next occurrence. For what the backup does with the tool itself, see [Restic and Borg](../backups/restic_borg.md).

## Logs with journalctl

Everything the service writes to stdout and stderr ends up in the journal, with no configuration. Useful combinations:

```bash
journalctl -u my-service                 # the unit's full history
journalctl -u my-service -f              # follow live
journalctl -u my-service -b              # only since the last boot
journalctl -u my-service --since "1 hour ago"
journalctl -u my-service -p err          # only priority error or worse
journalctl -xeu my-service               # end of the log with explanations
```

The journal is binary and, depending on the distribution, **is not persistent** by default: if `/var/log/journal/` does not exist, it is lost on reboot. To keep it, create that directory or set `Storage=persistent` in `/etc/systemd/journald.conf` and restart `systemd-journald`. Limit its size with `SystemMaxUse=` in that same file; `journalctl --disk-usage` tells you how much it takes.

A service that writes to its own log file should write to stdout and let the journal do the rest; if you need to forward it to a central stack, see [security monitoring](../cybersecurity/monitoreo_seguridad.md).

## Sandboxing and hardening

A normal service sees the whole filesystem, can escalate privileges and talk to any socket. Systemd offers directives that trim that down without touching the application. A reasonable starting point for a network service running as an unprivileged user:

```ini
[Service]
User=my_user
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/my-service
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
```

| Directive | Effect |
|-----------|--------|
| `NoNewPrivileges=true` | The process and its children cannot gain privileges (setuid, capabilities) |
| `PrivateTmp=true` | Private `/tmp` and `/var/tmp`, invisible to the rest of the system |
| `ProtectSystem=strict` | Whole filesystem read-only except `/dev`, `/proc` and `/sys` |
| `ProtectHome=true` | `/home`, `/root` and `/run/user` inaccessible |
| `ReadWritePaths=` | Write exceptions for `ProtectSystem=strict` |
| `StateDirectory=` | Creates `/var/lib/<name>` and assigns it to the service user, already writable |

`ProtectSystem=strict` is the one that breaks the most: any path where the application writes (data, sockets, caches) must be declared with `ReadWritePaths=` or, better, with `StateDirectory=`, `CacheDirectory=` or `LogsDirectory=`. If the service does not start after enabling it, the journal message usually names the path with the permission denied.

To measure how exposed a unit is, systemd includes an analyser:

```bash
systemd-analyze security my-service
```

It shows a table with each directive evaluated and an overall exposure score from 0.0 to 10.0 (higher means less isolation) with a label such as `OK` or `UNSAFE`. It does not aim for zero: it helps you see what is missing and compare before and after. The exact detail of the output and of the available directives depends on the installed systemd version, so check with `man systemd.exec` on your system.

!!! warning "Version dependent"
    Some sandboxing directives (for example, system call filtering such as `SystemCallFilter=`, or `ProtectProc=`, added in systemd 247) appeared in specific versions. An unknown directive is ignored with a warning in the journal, so enabling it does not guarantee that it is doing anything.

The same least-privilege approach applies to the whole system; see [Linux hardening](../cybersecurity/hardening_linux.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Unit my-service.service not found` | File in the wrong path or no `daemon-reload` | Check the path and the `.service` suffix; run `systemctl daemon-reload` |
| `status` warns the unit changed on disk | Edited without reloading | `systemctl daemon-reload` and restart the service |
| `failed` state with `status=203/EXEC` | `ExecStart` points to a missing path or a file without execute permission | Use an absolute path, check `chmod +x` and the script's shebang |
| `start request repeated too quickly` | `StartLimitBurst` exceeded | Fix the cause, then `systemctl reset-failed my-service` |
| Service starts and stops immediately | Process that forks with `Type=simple` | Configure it to run in the foreground or adjust `Type=` per its documentation |
| Works by hand, fails as a service | Different environment: no shell `PATH`, no HOME, another user | Absolute paths, `Environment=`/`EnvironmentFile=`, `WorkingDirectory=` |
| `Permission denied` after adding `ProtectSystem=strict` | The app writes to a read-only path | Declare it with `ReadWritePaths=` or `StateDirectory=` |
| Timer does not fire | The `.service` was enabled instead of the `.timer`, or `OnCalendar` is wrong | `systemctl list-timers`, validate with `systemd-analyze calendar` |
| Starts before the network | Missing `After=network-online.target` | Add `Wants=` and `After=` for that target |

General diagnostic steps: `systemctl status`, then `journalctl -xeu <unit>`, and finally reproduce the `ExecStart` command by hand as the same user (`sudo -u my_user ...`). `systemd-analyze verify /etc/systemd/system/my-service.service` catches syntax errors and unknown directives before starting.

## Best practices

- **Dedicated user, never root.** A compromised service inherits the permissions of whoever runs it.
- **Changes go in `/etc/systemd/system/` or in drop-ins**, versioned in Git and deployed with [Ansible](../ansible/ansible_base.md). Nothing in `/usr/lib`.
- **`Restart=on-failure` with `RestartSec` and `StartLimitBurst`** instead of a bare `Restart=always`.
- **Timers before cron** for anything you want to observe, retry or isolate.
- **Sandboxing from day one.** Adding `NoNewPrivileges`, `PrivateTmp` and `ProtectSystem` is cheap when creating the service and painful to retrofit.
- **Secrets in `EnvironmentFile=` with 600 permissions** or in systemd credentials, never inside the unit, which is world-readable.
- **Persistent, size-capped journal** so logs survive a reboot without filling the disk.

## References

- [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) · [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) — sandboxing directives
- [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) · [systemd-analyze(1)](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html)
- [Podman Quadlet](../docker/quadlets.md) · [Linux hardening](../cybersecurity/hardening_linux.md)
- [SSH Security](ssh_security.md) · [WireGuard](wireguard.md)
