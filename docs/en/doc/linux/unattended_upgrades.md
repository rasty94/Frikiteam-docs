---
title: "Unattended upgrades on Debian with unattended-upgrades"
description: "unattended-upgrades on Debian 13 (trixie): what it installs by default, Origins-Pattern, package blacklist, apt-daily timers, controlled automatic reboot, notifications, dry run and what you should not upgrade unattended."
keywords: "unattended-upgrades, debian, trixie, apt-daily, apt-daily-upgrade, origins-pattern, package-blacklist, automatic-reboot, needrestart, homelab"
tags: ['linux', 'hardening', 'automation', 'best-practices']
updated: 2026-11-25
difficulty: intermediate
estimated_time: 21 min
category: Linux
status: published
last_reviewed: 2026-11-25
prerequisites:
  - "Debian 13 (trixie) with sudo access"
  - "Basic systemd (units, timers, journalctl)"
  - "[Systemd](systemd.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Unattended upgrades on Debian with unattended-upgrades

## The problem

You have a Debian server at home that works and that you don't log into for weeks. Meanwhile security advisories come out for OpenSSL, OpenSSH or libc, and the fix sits in the repository waiting for someone to type `apt upgrade`. That someone is you, and you are not going to do it every day.

The obvious fix, an `apt upgrade -y` in a cron job, is worse than doing nothing: it upgrades anything from any repository, it can't stop if dpkg is left half-done, and it tells you nothing. `unattended-upgrades` is Debian's tool for this: it only installs what comes from the origins you allow, leaves out the packages you name, logs every run and, if you want, reboots at the time you choose.

!!! warning "Not tested in the homelab yet"
    This article has been checked against the official documentation (the `50unattended-upgrades` file from the trixie 2.12 package, the apt 3.0.4 units, the Debian wiki and the Proxmox VE administration guide), but I haven't tried it on a homelab machine yet. If something doesn't behave as described here, please open an erratum.

## 📋 Table of Contents

- [How it works](#how-it-works)
- [Install and enable](#install-and-enable)
- [What it upgrades by default](#what-it-upgrades-by-default)
- [Adding origins with Origins-Pattern](#adding-origins-with-origins-pattern)
- [Package blacklist](#package-blacklist)
- [The timers and how to move them](#the-timers-and-how-to-move-them)
- [Controlled automatic reboot](#controlled-automatic-reboot)
- [Notifications: mail and needrestart](#notifications-mail-and-needrestart)
- [Dry run and logs](#dry-run-and-logs)
- [What you should not upgrade unattended](#what-you-should-not-upgrade-unattended)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## How it works

There are three pieces and it pays not to mix them up:

1. **Two systemd timers shipped by `apt`**: `apt-daily.timer` starts `apt-daily.service`, which runs `/usr/lib/apt/apt.systemd.daily update` (refreshes package lists and, if asked to, downloads). `apt-daily-upgrade.timer` starts `apt-daily-upgrade.service`, which runs `apt.systemd.daily install` (installs and cleans up).
2. **`/etc/apt/apt.conf.d/20auto-upgrades`**: tells `apt.systemd.daily` what to do on each run. Without it the timers fire but nothing gets upgraded.
3. **`/etc/apt/apt.conf.d/50unattended-upgrades`**: the policy for `unattended-upgrade`, the program that actually picks and installs packages: from which origins, what to exclude, whether to reboot, whom to notify.

If systemd timers are new to you, the mechanics are in [Systemd: timers](systemd.md#timers-the-cron-alternative). This page only covers the APT side.

## Install and enable

Many Debian installs already ship the package, though not always enabled. Installing it again does no harm:

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

The debconf question is "Automatically download and install stable updates?" and the default answer is yes. Accepting it writes `/etc/apt/apt.conf.d/20auto-upgrades` with this content:

```text
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

The number is the interval in days; `0` disables it. `apt.systemd.daily` accepts more `APT::Periodic::*` keys (they are documented in the header of the script itself), for example `AutocleanInterval` to clear obsolete `.deb` files from the cache:

```text
APT::Periodic::AutocleanInterval "7";
```

## What it upgrades by default

The active part of `Origins-Pattern` in the trixie `50unattended-upgrades` is this:

```text
Unattended-Upgrade::Origins-Pattern {
//      "origin=Debian,codename=${distro_codename}-updates";
//      "origin=Debian,codename=${distro_codename}-proposed-updates";
        "origin=Debian,codename=${distro_codename},label=Debian";
        "origin=Debian,codename=${distro_codename},label=Debian-Security";
        "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
//      "o=Debian Backports,n=${distro_codename}-backports,l=Debian Backports";
};
```

In plain words: **security updates** (`trixie-security`) and **updates to the stable release itself** (`trixie`, which changes with every *point release*, 13.1, 13.2…). Not included: `trixie-updates`, `trixie-proposed-updates`, backports, or any third-party repository (Docker, Proxmox, Grafana…). Mind the first part: it is not "security only", you also get the fixes in each Debian minor revision, which go through the same stability filter.

`${distro_codename}` is replaced by the installed codename (`trixie`), so a major release upgrade (to forky) is **never** done on its own.

## Adding origins with Origins-Pattern

Don't edit `50unattended-upgrades`: it is a package *conffile* and every upgrade will ask you what to do with your changes. The Debian wiki suggests your own file that is read afterwards, for example `52unattended-upgrades-local`. APT reads `apt.conf.d` in lexical order and, for lists, **a new entry is added to the previous ones**; there is no need to copy everything.

To add `trixie-updates` (urgent fixes that don't wait for the next *point release*):

```text
// /etc/apt/apt.conf.d/52unattended-upgrades-local
Unattended-Upgrade::Origins-Pattern {
        "origin=Debian,codename=${distro_codename}-updates";
};
```

Each line is a comma-separated list of `key=value`, and a package only qualifies if **all** of them match its repository metadata. The accepted keys, according to the file itself: `a`/`archive`/`suite`, `c`/`component`, `l`/`label`, `o`/`origin`, `n`/`codename` and `site`.

For a third-party repository you don't guess the values: you read them.

```bash
apt-cache policy
```

Each repository shows up with a `release` line carrying its fields (`o=`, `a=`, `n=`, `l=`, `c=`). Copy the ones that identify that origin unambiguously (usually `o=` and `n=`) and add a line with them. Prefer `codename` over `archive`: the file warns that matching by `archive` ("stable") silently jumps to another release when stable changes.

If you want to **replace** the list instead of extending it, `apt.conf(5)` has the `#clear` command:

```text
#clear Unattended-Upgrade::Origins-Pattern;
Unattended-Upgrade::Origins-Pattern {
        "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
};
```

That way the machine only gets security updates, without point releases.

## Package blacklist

`Unattended-Upgrade::Package-Blacklist` is a list of **Python regular expressions** compared with `re.match`, that is, from the start of the name. The examples in the original file make it clear:

```text
Unattended-Upgrade::Package-Blacklist {
    // everything starting with linux-
    "linux-";
    // $ marks the end: without it, "libc6" would also match libc6-dev
    "libc6$";
    // special characters must be escaped
    "libstdc\+\+6$";
};
```

On a home server with PostgreSQL and MariaDB installed from Debian, `52unattended-upgrades-local` would look like this:

```text
Unattended-Upgrade::Package-Blacklist {
    "postgresql-";
    "mariadb-";
};
```

Blacklisted packages still show up in `apt list --upgradable`; you upgrade them yourself when you have time and a recent backup. There is also the opposite option, `Package-Whitelist` (with `Package-Whitelist-Strict`), to upgrade only a closed list, but on an ordinary server the blacklist is easier to maintain.

!!! tip "apt-mark hold is not the same"
    `apt-mark hold package` locks the package for the whole system, including your manual `apt upgrade`. The blacklist only affects unattended runs.

## The timers and how to move them

The units shipped by apt 3.0.4 in trixie:

```ini
# apt-daily.timer
[Timer]
OnCalendar=*-*-* 6,18:00
RandomizedDelaySec=12h
Persistent=true

# apt-daily-upgrade.timer
[Timer]
OnCalendar=*-*-* 6:00
RandomizedDelaySec=60m
Persistent=true
```

The download can land at any time of day because of the 12-hour random delay; the install, between 06:00 and 07:00. `Persistent=true` means that if the machine was off at that time, the run happens at boot. Both services carry `ConditionACPower=true`, so on a laptop running on battery they do nothing.

To move the install to 04:00, the Debian wiki recommends a drop-in with `systemctl edit`:

```bash
sudo systemctl edit apt-daily-upgrade.timer
```

```ini
[Timer]
OnCalendar=
OnCalendar=04:00
RandomizedDelaySec=15m
```

The empty `OnCalendar=` clears the original value; without it you would have two trigger times. Check the result:

```bash
systemctl list-timers 'apt-daily*'
systemctl cat apt-daily-upgrade.timer
```

Don't remove the random delay from `apt-daily.timer` altogether: the wiki points out that it exists to spread the load on Debian's servers.

## Controlled automatic reboot

A new kernel is useless until you reboot. On Debian, the package installs a hook at `/etc/kernel/postinst.d/unattended-upgrades` that creates `/var/run/reboot-required` (and records the package in `reboot-required.pkgs`) every time a kernel is installed. With these options, `unattended-upgrade` picks it up when it finishes:

```text
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
Unattended-Upgrade::Automatic-Reboot-Time "05:00";
```

- `Automatic-Reboot` is `false` by default. The file itself warns about it: it reboots **without confirmation**.
- `Automatic-Reboot-WithUsers` is `true` by default; set to `false`, it won't reboot if someone is logged in and leaves a note in the log.
- `Automatic-Reboot-Time` is `now` by default. Internally it runs `/sbin/shutdown -r <time>`, so a scheduled reboot can be cancelled with `sudo shutdown -c`.

Fit the times to the timer: if the install starts at 04:00 with up to 15 minutes of delay, a 05:00 reboot leaves some slack. If the install takes longer than that, the reboot command will be issued after the planned time; check in the logs how long a normal run takes before tightening it.

## Notifications: mail and needrestart

`unattended-upgrade` can send a summary by mail:

```text
Unattended-Upgrade::Mail "root";
Unattended-Upgrade::MailReport "only-on-error";
```

`MailReport` accepts `always`, `only-on-error` or `on-change`. Sending uses `/usr/bin/mail` or `/usr/sbin/sendmail`; if neither exists, the program logs an error and carries on. In practice you need an MTA that knows how to get mail out of your house (an SMTP relay to your provider), because a local `root` mailbox nobody reads warns nobody.

For upgraded libraries still loaded in running services there is `needrestart` (3.11 in trixie). It hooks into APT and, after each install, looks for processes using files that have been replaced. Its default configuration is interactive, and the file itself warns that when `unattended-upgrades` runs it without a terminal it **falls back to list mode**: it reports, it restarts nothing. If you want it to restart services on its own, change it in a file under `/etc/needrestart/conf.d/`:

```perl
# /etc/needrestart/conf.d/50-auto.conf
$nrconf{restart} = 'a';
```

Before doing that, check the `override_rc` list in `/etc/needrestart/needrestart.conf`: it holds the services it never restarts by default (dbus, network managers, VPNs…). To check by hand what still needs restarting without touching anything:

```bash
sudo needrestart -r l      # list only
sudo needrestart -b        # script-friendly output, no restarts
```

## Dry run and logs

Before trusting the configuration, simulate a run:

```bash
sudo unattended-upgrade --dry-run --debug
```

`--dry-run` simulates without installing; with `--debug` you see the allowed origins, the initial blacklist and the decision for every package. In simulation mode it doesn't write the log, it only prints to the screen. `unattended-upgrades` (with an s) is a link to the same program.

The logs of real runs:

| File | What it contains |
|---|---|
| `/var/log/unattended-upgrades/unattended-upgrades.log` | Decisions: origins, chosen packages, kept back, reboot |
| `/var/log/unattended-upgrades/unattended-upgrades-dpkg.log` | dpkg output for each install |
| `/var/log/unattended-upgrades/unattended-upgrades-shutdown.log` | The service that waits for a run to finish before shutdown |
| `/var/log/apt/history.log` | The regular APT history, unattended runs included |

And the timers' journal:

```bash
journalctl -u apt-daily.service -u apt-daily-upgrade.service --since today
```

## What you should not upgrade unattended

**The Proxmox VE host.** The Proxmox administration guide says to upgrade with `apt full-upgrade` and warns that an `apt upgrade` may leave the system partially upgraded, because it cannot remove packages to resolve dependencies. `unattended-upgrades` doesn't remove them either. With the default configuration the Proxmox repository is not among the allowed origins, so Proxmox packages and their kernels (`proxmox-kernel-*`) are left alone; don't add it. And on a hypervisor keep `Automatic-Reboot` at `false`: rebooting the host means rebooting every VM and container. The Debian security part can stay unattended, although my recommendation on a Proxmox host is to upgrade it by hand from the web UI or with `apt full-upgrade`, after reading what changes. More context in [Proxmox VE](../proxmox/proxmox_base.md).

**Databases.** An upgrade of PostgreSQL 17 or MariaDB 11.8 within trixie is a minor version and is usually safe, but the package may restart the service in the middle of the night and, if something breaks, you find out in the morning. Put them on the blacklist and upgrade them yourself after a backup. If they run in containers ([PostgreSQL on Docker](../databases/postgres.md)), APT doesn't touch them: their upgrade goes through the image.

**Anything another machine depends on without redundancy.** The virtual router, the home DNS, the VPN server: if you don't have a second instance, let them reboot when you are in front of them.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Timers run but nothing is ever installed | `20auto-upgrades` is missing or has `Unattended-Upgrade "0"` | `dpkg-reconfigure -plow unattended-upgrades` |
| A package with an update is not installed | Its origin doesn't match `Origins-Pattern`, or it is blacklisted | `--dry-run --debug` and compare with `apt-cache policy` |
| Your changes don't apply | You edited a copy under a name read earlier, or a later `#clear` exists | `apt-config dump \| grep Unattended-Upgrade` |
| No mail arrives | No `/usr/bin/mail` or `/usr/sbin/sendmail`, or the MTA can't send outside | Check the error in `unattended-upgrades.log` and try `mail` by hand |
| No reboot after a new kernel | `Automatic-Reboot` is `false`, or `WithUsers` is `false` with open sessions | See the note in the log; `ls /var/run/reboot-required` |
| A run is left half-done after a power cut | Interrupted dpkg | `AutoFixInterruptedDpkg` (on by default) retries on the next run; by hand, `dpkg --configure -a` |
| A laptop never upgrades | `ConditionACPower=true` and `OnlyOnACPower` | Plug it in or, accepting the risk, follow the wiki |

`apt-config dump` prints the already merged configuration from every file, which is what `unattended-upgrade` actually reads.

## Best practices

- **Your own file** (`52unattended-upgrades-local`) with only your changes, version-controlled and deployed with [Ansible](../ansible/ansible_base.md) if you have more than one machine.
- **Dry run after every change** to origins or the blacklist.
- **Security always; the rest, with judgement.** Adding third-party origins means accepting their bugs while you are not around.
- **Automatic reboot only where a reboot doesn't hurt**, and at a time that fits the install timer.
- **Make sure someone reads the notifications.** An `only-on-error` mail that actually arrives is worth more than an `always` that gets lost.
- **Combine it with the rest of your hardening**: see [Linux server hardening](../cybersecurity/hardening_linux.md) and [SSH security](ssh_security.md).

## References

- [50unattended-upgrades.Debian in the 2.12 package (trixie)](https://sources.debian.org/src/unattended-upgrades/2.12/data/50unattended-upgrades.Debian/)
- [unattended-upgrade(8)](https://manpages.debian.org/trixie/unattended-upgrades/unattended-upgrade.8.en.html) · [apt.conf(5)](https://manpages.debian.org/trixie/apt/apt.conf.5.en.html)
- [apt 3.0.4 apt-daily units](https://sources.debian.org/src/apt/3.0.4/debian/) (includes `apt.systemd.daily` with the `APT::Periodic` keys)
- [Debian wiki: PeriodicUpdates](https://wiki.debian.org/PeriodicUpdates)
- [needrestart 3.11 in trixie](https://sources.debian.org/src/needrestart/3.11-1/ex/needrestart.conf/)
- [Proxmox VE administration guide, "System Software Updates" section](https://pve.proxmox.com/pve-docs/pve-admin-guide.html)
- [Systemd](systemd.md) · [Linux server hardening](../cybersecurity/hardening_linux.md)
