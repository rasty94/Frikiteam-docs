---
title: "nftables + fail2ban — Wall and doorman"
description: "A persistent nftables ruleset with sets and verdict maps, real fail2ban integration (systemd backend, nftables banaction), the recidive jail and custom filters."
keywords: "nftables, fail2ban, firewall, linux, banaction, recidive, journald, sets, hardening"
tags: ['cybersecurity', 'firewall', 'linux']
updated: 2026-08-03
difficulty: intermediate
estimated_time: 22 min
category: Cybersecurity
status: published
last_reviewed: 2026-08-03
prerequisites:
  - "Intermediate Linux (systemd, journalctl)"
  - "Basic networking (TCP/IP, ports)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# nftables + fail2ban — Wall and doorman

## The problem

You open port 22 to the internet and within an hour your logs hold thousands of login attempts. A well-configured firewall doesn't help: port 22 **has** to be open for you to get in. And fail2ban alone isn't enough either, because it only reacts to what already arrived.

The two pieces are complementary, and most guides treat them separately: **nftables decides what may arrive** (static policy) and **fail2ban decides who stops being allowed** (dynamic reaction to what does arrive). This page is about how they actually fit together, which is where nearly every configuration goes wrong.

!!! note "Relationship to other pages"
    [Network Firewall](firewall_red.md) compares UFW, iptables and nftables and introduces Suricata and Zeek. [SSH Hardening](../linux/ssh_security.md) covers configuring `sshd` itself. This page covers **the persistent ruleset and its fail2ban integration**, which neither of those covers in depth.

## 📋 Table of Contents

- [An nftables ruleset you can read](#an-nftables-ruleset-you-can-read)
- [Sets: lists looked up in O(1)](#sets-lists-looked-up-in-o1)
- [Applying it without locking yourself out](#applying-it-without-locking-yourself-out)
- [fail2ban: the part that's usually wrong](#fail2ban-the-part-thats-usually-wrong)
- [The recidive jail](#the-recidive-jail)
- [Custom filters](#custom-filters)
- [Day-to-day operation](#day-to-day-operation)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## An nftables ruleset you can read

The practical difference from iptables isn't the syntax: it's that **the ruleset is a file**, loaded atomically and read top to bottom like a program.

```nft
#!/usr/sbin/nft -f
# /etc/nftables.conf

flush ruleset

table inet filter {
    # TCP ports open to everyone
    set public_tcp {
        type inet_service
        elements = { 80, 443 }
    }

    # Trusted administration networks
    set admin_nets {
        type ipv4_addr
        flags interval
        elements = { 192.168.1.0/24, 10.8.0.0/24 }
    }

    chain input {
        type filter hook input priority filter; policy drop;

        # 1. Already-established traffic: the most frequent case, goes first
        ct state established,related accept
        ct state invalid drop

        # 2. Loopback
        iif lo accept

        # 3. ICMP: don't block it wholesale, it breaks PMTU and diagnostics
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded } accept
        ip6 nexthdr icmpv6 accept

        # 4. Public services
        tcp dport @public_tcp accept

        # 5. Administration, only from trusted networks
        ip saddr @admin_nets tcp dport 22 accept

        # 6. Whatever reaches here gets logged before it drops
        limit rate 5/minute burst 10 packets log prefix "nft-drop: " level info
    }

    chain forward {
        type filter hook forward priority filter; policy drop;
    }

    chain output {
        type filter hook output priority filter; policy accept;
    }
}
```

Three decisions that make the difference:

- **`policy drop` on `input` and `forward`.** What isn't allowed doesn't pass. The alternative (`policy accept` plus block rules) requires you to correctly anticipate everything you want to forbid, forever.
- **`ct state established,related accept` first.** It is the rule that evaluates the vast majority of packets; putting it last means walking the whole ruleset for every packet of an already-accepted connection.
- **`log` with `limit rate`.** Without the limit, a port scan fills `/var/log` and turns a minor incident into a full disk.

!!! warning "Don't block all ICMP"
    This is the classic "ping = danger" reflex. Blocking `destination-unreachable` breaks path MTU discovery, and the symptom is TCP connections hanging mid-transfer on large packets — a failure that takes days to diagnose. See [MTU/MSS](../networking/mtu_mss_values.md).

## Sets: lists looked up in O(1)

A set is a hash table in the kernel. Whether it holds 5 elements or 50,000, lookup cost is the same. That is exactly what you want for block lists.

```nft
    # Blocking with automatic expiry
    set blackhole {
        type ipv4_addr
        flags dynamic, timeout
        timeout 1h
    }
```

```nft
        ip saddr @blackhole drop
```

```bash
# Add an IP with its own expiry
sudo nft add element inet filter blackhole '{ 203.0.113.7 timeout 24h }'

# See what's in there and how long it has left
sudo nft list set inet filter blackhole
```

`flags timeout` makes the kernel expire entries by itself: no cron to clean up, no file growing unbounded. It is the mechanism fail2ban works on when using the native backend.

## Applying it without locking yourself out

The mistake everyone makes once: loading a `policy drop` ruleset that doesn't permit your SSH, over SSH.

```bash
# 1. Validate the syntax without applying anything
sudo nft -c -f /etc/nftables.conf

# 2. Safety net: restore the previous ruleset in 2 minutes
sudo nft list ruleset > /root/nft-backup.conf
sudo systemd-run --on-active=120 --timer-property=AccuracySec=1s \
    nft -f /root/nft-backup.conf

# 3. Now apply
sudo nft -f /etc/nftables.conf

# 4. Still connected and everything works? Cancel the restore
sudo systemctl list-timers --all | grep run-
sudo systemctl stop run-rXXXX.timer
```

Persistence across reboots:

```bash
sudo systemctl enable --now nftables
```

## fail2ban: the part that's usually wrong

The configuration circulating everywhere has been outdated for years on two points that make **the jail not work without telling you**.

```ini
# /etc/fail2ban/jail.local

[DEFAULT]
# 1. On Debian 12+, Ubuntu 24.04+ and RHEL 9+ there is no /var/log/auth.log:
#    rsyslog is no longer installed by default and everything goes to the journal.
backend  = systemd

# 2. If your firewall is nftables, the banaction must be too.
banaction      = nftables-multiport
banaction_allports = nftables-allports

bantime  = 1h
findtime = 10m
maxretry = 5

# Never ban yourself
ignoreip = 127.0.0.1/8 ::1 192.168.1.0/24

[sshd]
enabled = true
mode    = aggressive
```

- **`backend = systemd`**: with `logpath = /var/log/auth.log` on a modern distro, fail2ban starts, the jail finds no file and sits idle. `systemctl status fail2ban` stays green. It's a silent failure, which is the worst kind.
- **`banaction = nftables-multiport`**: with the iptables default on an nftables system, bans land in the `iptables-nft` compatibility layer and coexist badly with your ruleset. Working sometimes is worse than never working.

Check the jail is genuinely alive:

```bash
sudo fail2ban-client status            # active jails
sudo fail2ban-client status sshd       # detected failures and bans
```

If `Currently failed: 0` and `Total failed: 0` after hours exposed to the internet, the jail is reading nothing. It isn't that nobody is attacking you.

## The recidive jail

A serious attacker doesn't make 5 attempts and leave: they make 4, wait, come back. They never trigger `maxretry`. `recidive` watches fail2ban's own log and punishes repeat offenders across jails.

```ini
[recidive]
enabled  = true
logpath  = /var/log/fail2ban.log
banaction = %(banaction_allports)s
bantime  = 1w
findtime = 1d
maxretry = 3
```

Three bans in 24 hours → a week out, and on **all** ports, not just the one that failed. It is the jail with the best effort-to-effect ratio.

!!! note "recidive reads a file, not the journal"
    Even when everything else uses `backend = systemd`, `recidive` needs `/var/log/fail2ban.log`. Verify it exists and that `logtarget = /var/log/fail2ban.log` is set in `fail2ban.local`; if your install logs to the journal, this jail will detect nothing.

## Custom filters

For any service that writes failed attempts to a log: one regex and one jail.

```ini
# /etc/fail2ban/filter.d/myapp.conf
[Definition]
failregex = ^.*Failed login attempt from <HOST>.*$
ignoreregex =
```

```ini
# In jail.local
[myapp]
enabled  = true
port     = http,https
filter   = myapp
logpath  = /var/log/myapp/access.log
maxretry = 5
```

Test the regex against the real log **before** enabling it:

```bash
sudo fail2ban-regex /var/log/myapp/access.log /etc/fail2ban/filter.d/myapp.conf
```

The output tells you how many lines matched. If it's 0, the filter is decorative. `<HOST>` is the macro capturing the IP: without it the filter cannot ban anyone.

## Day-to-day operation

```bash
# Who is banned right now
sudo fail2ban-client status sshd

# Unban (the user who mistyped their key three times)
sudo fail2ban-client set sshd unbanip 203.0.113.7

# Ban manually
sudo fail2ban-client set sshd banip 203.0.113.7

# See the bans from the firewall side
sudo nft list set inet f2b-table addr-set-sshd
```

Ruleset counters, to see which rule is doing the work:

```bash
sudo nft -a list ruleset          # with handles, for deleting specific rules
sudo nft list ruleset | grep -A3 counter
```

Add `counter` to the rules you want to measure; without that keyword nftables counts nothing (unlike iptables, which always counts).

## Troubleshooting

| Symptom | Cause | Check |
|---|---|---|
| fail2ban active but never bans | Wrong `backend` for the distro | `fail2ban-client status sshd` → `Total failed: 0` |
| Bans, but the IP still gets in | iptables `banaction` on nftables | `nft list ruleset \| grep f2b` |
| You locked yourself out | SSH rule missing or after the `drop` | Physical console / KVM; `nft flush ruleset` |
| Custom filter detects nothing | Regex without `<HOST>`, or not matching | `fail2ban-regex` against the real log |
| Rules lost after reboot | `nftables` service disabled | `systemctl is-enabled nftables` |
| Connections hang on large files | ICMP blocked, PMTU broken | `ping -M do -s 1472 <target>` |

## Best practices

- **`policy drop` by default**, with the `established` rule first.
- **Validate with `nft -c` and always start with the timed safety net.** The cost is one command; the cost of skipping it is a trip to the datacenter.
- **`backend = systemd` and `banaction = nftables-*`** on any modern install. Copy-pasting from old guides is the number one cause of decorative fail2ban.
- **`ignoreip` with your admin network**, before touching anything else.
- **Enable `recidive`.** That's where the return is.
- **`fail2ban-regex` before trusting a custom filter.**
- **Feed your monitoring with the bans.** A spike in bans is a signal, not noise. See [security monitoring](monitoreo_seguridad.md) and [Wazuh](../monitoring/wazuh_logs.md).
- **The firewall replaces nothing else.** SSH with keys and no passwords ([SSH Hardening](../linux/ssh_security.md)) eliminates the entire attack class; fail2ban only reduces the noise.

## References

- [Official nftables wiki](https://wiki.nftables.org/)
- [fail2ban manual](https://github.com/fail2ban/fail2ban/wiki)
- [Network Firewall](firewall_red.md) · [Linux Hardening](hardening_linux.md)
- [SSH Hardening](../linux/ssh_security.md) · [Security Monitoring](monitoreo_seguridad.md)
