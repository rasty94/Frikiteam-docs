---
title: "Digital forensics on Linux: evidence, memory and timeline"
description: "How to collect and analyze evidence on a compromised Linux server or Proxmox VM: order of volatility, chain of custody, live triage, memory and disk acquisition, Volatility 3, timeline and YARA."
keywords: "digital forensics, dfir, linux, volatility, chain of custody, lime, avml, volatility 3, yara, timeline, mactime, proxmox, dc3dd"
tags: ['forensics', 'incident-response', 'cybersecurity', 'linux']
updated: 2026-10-11
difficulty: advanced
estimated_time: 33 min
category: Cybersecurity
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "[Incident response](respuesta_incidentes.md)"
  - "Linux administration (processes, systemd, mounting disks)"
  - "Root access to the server or the Proxmox hypervisor"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Digital forensics on Linux: evidence, memory and timeline

## The problem

You have contained the incident and case management is going well: there is a severity, a channel, an Incident Commander and an open case. Then someone asks the important question: **how did they get in, what did they touch and since when?** And you find out your "evidence" is a handful of screenshots, a `history` the attacker already wiped and a server somebody rebooted "to see if it fixes itself". Without data collected methodically there is no answer, and without an answer eradication is a gamble.

Digital forensics is the discipline that answers those questions without destroying what holds the answers. In a homelab or a small infrastructure you do not need a lab: you need a working order, a few standard tools and the discipline not to improvise.

!!! note "What this covers and what it does not"
    This page covers the **collection and analysis** of evidence on your own Linux servers and Proxmox VMs. Case management (severity, roles, containment, TheHive, MISP, post-mortem) lives in [Incident response](respuesta_incidentes.md) and is not repeated here. The approach is strictly defensive: no offensive techniques.

## 📋 Table of Contents

- [Order of volatility](#order-of-volatility)
- [Practical chain of custody](#practical-chain-of-custody)
- [Live triage](#live-triage)
- [Memory acquisition](#memory-acquisition)
- [Disk acquisition](#disk-acquisition)
- [Memory analysis with Volatility 3](#memory-analysis-with-volatility-3)
- [Timeline with MAC times](#timeline-with-mac-times)
- [Searching with YARA](#searching-with-yara)
- [Centralized logs: the best evidence](#centralized-logs-the-best-evidence)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Order of volatility

Evidence is not lost all at once: some of it disappears in seconds and some lasts years. You collect it **from the most fragile to the most stable** (the RFC 3227 criterion):

| Order | Evidence | How long it lasts | How to collect it |
| --- | --- | --- | --- |
| 1 | RAM | Until reboot | Dump with LiME/AVML or from the hypervisor |
| 2 | Network connections and ARP/route tables | Seconds or minutes | `ss`, `ip neigh`, `ip route` |
| 3 | Processes, modules, open files | Until they exit | `ps`, `/proc`, `lsof`, `lsmod` |
| 4 | Disk | Persistent, but modifiable | Image or snapshot of the volume |
| 5 | Remote logs and backups | Months or years | Export from the central collector |

I leave local logs out of the order on purpose: an attacker with root can rewrite them. The ones that count are those that already left the machine (see [below](#centralized-logs-the-best-evidence)).

!!! danger "Do not power the machine off right away"
    A shutdown (or a reboot) wipes memory, connections and processes, and can trigger cleanups scheduled by the attacker. An abrupt power-off does not guarantee a consistent disk either. **Isolate the network, leave the machine running and collect in order.** Powering off is the last step, and only if you already have an image and a dump. On a Proxmox VM you also have a better option than powering off: capture from the hypervisor without touching the guest.

Isolating without powering off, on a Proxmox VM, means disconnecting the virtual NIC link:

```bash
# Show the current network card configuration of VM 100
qm config 100 | grep ^net

# Add link_down=1 keeping the remaining options (MAC included)
qm set 100 --net0 virtio=BC:24:11:AA:BB:CC,bridge=vmbr0,link_down=1
```

Copy the `net0` line as it appears in `qm config` and add only `link_down=1`: if you change the MAC, you alter evidence. On a physical host, the alternative is to cut the switch port or apply a firewall rule at the edge, not on the machine itself. The concrete network rules are in [Firewall and network](firewall_red.md).

## Practical chain of custody

An artifact without traceability is an anecdote. The minimal, practical part, without bureaucracy:

1. **Hash everything at the moment you collect it**, and again after every copy.
2. **A record** of who collected what, when (in UTC), from where and with which command.
3. **Read-only storage** for the originals; analysis is always done on copies.

```bash
# Case directory on the forensic workstation (NOT on the compromised machine)
CASO=INC-2026-0042
mkdir -p /evidencia/$CASO/{memoria,disco,triaje,logs}

# Hash of every artifact + manifest
cd /evidencia/$CASO
sha256sum memoria/* disco/* triaje/* logs/* > MANIFIESTO.sha256

# Check it whenever needed (after copying, before analyzing)
sha256sum -c MANIFIESTO.sha256

# Custody log: one line per action, appended, never edited
echo "$(date -u +%FT%TZ) | $(whoami) | memory collected web-prod-01 | avml" >> CUSTODIA.log
```

When you finish collecting, switch the originals to read-only. With permissions and the immutable attribute on your own ext4 system:

```bash
chmod -R a-w /evidencia/$CASO/{memoria,disco}
sudo chattr +i /evidencia/$CASO/memoria/* /evidencia/$CASO/disco/*
```

`chattr +i` protects against accidental deletion, not against someone with root on the forensic workstation. For evidence that may end up with an insurer or in front of a regulator, use truly immutable storage (object-lock, WORM) as in [Incident response](respuesta_incidentes.md#chain-of-custody), which also has the `custody.yaml` template. Backups of the forensic material itself follow the guidelines in [Secure backup](backup_seguro.md).

!!! warning "The forensic workstation is also a risk"
    Do not analyze on the compromised machine or on a laptop holding your production keys. Use a dedicated workstation or VM, with no access to production, and treat the images as hostile code: do not execute anything that comes out of them.

## Live triage

The goal of triage is to capture the volatile state and decide whether a full dump is worth it. On the compromised machine **do not trust its binaries**: a replaced `ps` or `ls` can hide exactly what you are looking for. Whenever you can, run from a trusted medium (read-only USB or mounted ISO) with static binaries or binaries copied from a clean system of the same distribution, and write the output to external media, never to the compromised disk.

!!! warning "Trusted binaries are not enough against a kernel rootkit"
    If the attacker loaded a kernel module, the kernel lies to any binary, however clean. That is why the live view is always compared with the memory dump and with the disk analyzed off the machine. A process that shows up in one and not in the other is a lead.

A capture script that does not modify the system (read-only, output to an external directory):

```bash
#!/bin/bash
# triaje.sh — run from a trusted medium. Usage: ./triaje.sh /mnt/usb/triaje
OUT="$1"; mkdir -p "$OUT"
ts() { date -u +%FT%TZ; }

{ ts; uname -a; uptime; } > "$OUT/00-sistema.txt"
ss -tupan                > "$OUT/10-conexiones.txt"
{ ip neigh; ip route; }  > "$OUT/11-vecinos-rutas.txt" 2>&1
ps auxf                  > "$OUT/20-procesos.txt"
lsof -nP +L1             > "$OUT/21-ficheros-borrados-abiertos.txt" 2>&1
lsmod                    > "$OUT/22-modulos.txt"
last -F                  > "$OUT/30-last.txt" 2>&1
lastb -F                 > "$OUT/31-lastb.txt" 2>&1
w                        > "$OUT/32-sesiones.txt"
cat /etc/ld.so.preload   > "$OUT/40-ld-so-preload.txt" 2>&1
sha256sum "$OUT"/*       > "$OUT/MANIFIESTO.sha256"
```

What you then look at calmly, on the forensic workstation, in those files and with targeted live queries:

- **Connections** (`ss -tupan`): established connections to unknown IPs, listening ports that should not exist, and which PID they belong to.
- **Processes** (`ps auxf`): the tree (`f`) shows who launched whom. An `sh` hanging off a web server, or processes with a kernel-style name (`[kworker]`) but a user-space path, are classics.
- **Real binary of a process**: `ls -l /proc/<pid>/exe` shows which file it points to. If the executable was deleted after launch, the link shows as `(deleted)`, and the content is still reachable through `/proc/<pid>/exe`. It is one of the most valuable pieces of evidence, copy it:

```bash
PID=4242
ls -l /proc/$PID/exe /proc/$PID/cwd
tr '\0' ' ' < /proc/$PID/cmdline; echo
cp /proc/$PID/exe /evidencia/INC-2026-0042/triaje/pid-$PID.bin
sha256sum /evidencia/INC-2026-0042/triaje/pid-$PID.bin
```

- **Open files** (`lsof`): `lsof -nP +L1` lists open files that no longer have a link on disk, that is, deleted binaries and logs that are still alive. `lsof -p <pid>` gives the detail for a specific process.
- **Access** (`last -F`, `lastb`, `w`): logins with full date, failed ones and live sessions. Compare with who *should* have logged in.

### Logs with time ranges

Always bound by window: a "since when" sentence keeps you from drowning in the journal. Use `--utc` so times match the rest of the case.

```bash
# Everything that happened in the suspicious window
journalctl --utc --since "2026-10-10 22:00" --until "2026-10-11 02:00" -o short-iso

# SSH only (the unit name is ssh or sshd depending on the distribution)
journalctl --utc -u ssh --since "2026-10-10" -o short-iso | grep -E "Accepted|Failed|Invalid"

# Analyze a copy of the journal off the compromised machine
journalctl --utc --file /evidencia/INC-2026-0042/logs/system.journal --since "2026-10-10"
```

### Users, SSH keys, cron and systemd units

Persistence is what the attacker almost always leaves behind. The places to check, all read-only:

```bash
# Users with a shell or unexpected UID 0
awk -F: '$3==0 || $7 !~ /(nologin|false)$/ {print $1, $3, $7}' /etc/passwd

# Authorized SSH keys: content and modification time
ls -l --time-style=full-iso /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null
cat /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null

# System and user cron, and systemd timers
ls -la /etc/cron.* /var/spool/cron/ 2>/dev/null
systemctl list-timers --all --no-pager

# Units created or modified recently (adjust the date to your window)
find /etc/systemd/system /usr/lib/systemd/system -type f -newermt "2026-10-01" -ls
systemctl list-unit-files --state=enabled --no-pager
```

For what is normal and what is not in SSH, see [SSH security](../linux/ssh_security.md); for the units and timers model, [Systemd](../linux/systemd.md). If the distribution uses packages, also check the integrity of installed binaries with `debsums -c` (Debian/Ubuntu, if installed) or `rpm -Va` (RHEL and derivatives): modified package files are suspicious.

## Memory acquisition

RAM holds what the disk does not: fileless processes, cleartext keys, connections and the command history that was never written out. There are two paths depending on whether you have a hypervisor underneath.

### Inside the machine: LiME or AVML

- **LiME** is a kernel module that dumps memory to a file. It has to be compiled against the headers of the *exact* kernel the machine is running.
- **AVML** is a standalone binary that does not require compiling a module, and for that reason it is usually the convenient option on servers with distribution kernels.

```bash
# AVML: a single binary, run from the trusted medium
sudo ./avml acquire /mnt/usb/memoria/web-prod-01.lime

# LiME: module compiled BEFORE (on a clean VM with the same kernel)
sudo insmod ./lime-$(uname -r).ko "path=/mnt/usb/memoria/web-prod-01.lime format=lime"

# In both cases, hash immediately
sha256sum /mnt/usb/memoria/web-prod-01.lime | tee -a /mnt/usb/memoria/MANIFIESTO.sha256
```

!!! warning "Kernel dependency"
    LiME needs a module compiled for the exact version of the running kernel, and compiling on the compromised machine changes the system and relies on a compiler you cannot trust. Compile it ahead of time on an identical VM. AVML spares you the module, but **the later analysis still needs the symbols of that same kernel** (see Volatility 3 below). Record `uname -r` in the custody log: without it the dump may end up uninterpretable.

Writing the dump to a USB drive or a mounted network share avoids overwriting whatever may remain unallocated on the disk. Either tool alters some memory when it runs; that is unavoidable, and it gets documented in the custody log.

### On Proxmox: from the hypervisor, without touching the guest

If the machine is a VM, the hypervisor sees its memory without running anything inside it, so the attacker can neither interfere nor detect it. Two options, to choose according to space and whether you need to preserve the state:

**Snapshot with RAM state.** It saves the VM memory inside the snapshot, in addition to the disk, and the VM keeps running:

```bash
qm snapshot 100 INC-2026-0042 --vmstate 1 --description "IR evidence"
```

The RAM state ends up on the snapshot storage in a QEMU-specific format, not as a flat dump that Volatility reads directly. It is useful for restoring the exact state in an isolated environment (see below) and analyzing it there.

**Guest memory dump through the QEMU monitor.** QEMU has a monitor command to write guest memory to a file, reachable from `qm monitor`:

```bash
qm monitor 100
# inside the monitor (HMP):
# dump-guest-memory /var/tmp/vm100-mem.elf
```

!!! warning "Version-dependent and not tested here"
    The `dump-guest-memory` command and its behavior (whether it pauses the VM while writing, which formats it supports, how the result is converted into something Volatility can read) depend on the QEMU and Proxmox VE version. Check it in a lab before the bad day and read `help dump-guest-memory` in the monitor itself. The file is written on the **host**, so it needs free space there and must be moved and hashed immediately.

Whichever method you use, the procedure is the same: copy the artifact out of the hypervisor, compute the `sha256sum`, record it in the custody log and work on the copy.

## Disk acquisition

With memory already collected, it is the disk's turn. Two rules: **do not mount the original** and **do not write to it**.

### Bit-for-bit image

If it is a physical disk (attached as a block device, preferably with the machine powered off after the dump, or from a boot of a forensic system):

```bash
# dc3dd computes the hash while copying and writes a log
sudo dc3dd if=/dev/sdb of=/evidencia/INC-2026-0042/disco/sdb.img \
  hash=sha256 log=/evidencia/INC-2026-0042/disco/sdb.log

# Alternative with standard dd
sudo dd if=/dev/sdb of=/evidencia/INC-2026-0042/disco/sdb.img bs=4M status=progress
sha256sum /dev/sdb /evidencia/INC-2026-0042/disco/sdb.img
```

If you copy a disk that is still mounted and in use, the source and copy hashes **will not match** because the original changes while you read it. For live systems, the correct copy is the one taken from a snapshot, which is frozen.

### Snapshot of the VM volume

On Proxmox you do not need to touch the guest's disk: freeze it on the hypervisor and export from there.

```bash
# Consistent backup of the VM without stopping it; result: a single backup file
vzdump 100 --mode snapshot --storage forense --compress zstd
```

The result is a backup file you can copy to the forensic workstation and restore as a new VM **without a network** (`qmrestore`, then remove the NIC or leave it with `link_down=1` before starting it). It is far safer than analyzing on the original VM. If your storage is ZFS or LVM-thin, you can also snapshot the underlying volume; local storage details are in [ZFS and LVM](../storage/zfs_lvm.md), and platform features in [Proxmox basics](../proxmox/proxmox_base.md).

### Read-only mount on a copy

Never mount the original image: work on a copy of the copy, and even so mount with the bare minimum.

```bash
# Read-only loop device, with partitions exposed
LOOP=$(sudo losetup --find --show --read-only --partscan copia-sdb.img)

# ext4: read-only, no exec, no devices, without replaying the journal
sudo mkdir -p /mnt/evidencia
sudo mount -o ro,noexec,nodev,noload ${LOOP}p1 /mnt/evidencia
```

The `noload` option stops ext4 from replaying the journal at mount time; without it, even an `ro` mount can write. If the filesystem was dirty, `noload` lets you see the state as is, although some recent files may look incomplete. With LVM inside the image, activate the volumes read-only before mounting. When you finish: `umount /mnt/evidencia` and `losetup -d "$LOOP"`.

## Memory analysis with Volatility 3

Volatility 3 is the standard framework for interpreting memory dumps: it reconstructs processes, connections and modules from the kernel's structures. On Linux it needs to know **what the kernel that produced the dump looks like**, and a symbol table (ISF) specific to that version provides that.

!!! warning "Depends on the version and on the kernel symbols"
    The Linux plugins of Volatility 3 only work if it has the symbols of the exact kernel of the dump: either an ISF file already built for that version, or one generated with `dwarf2json` from the kernel with debug symbols. Without them the dump cannot be interpreted. The plugin names below are the usual ones, but they **change between versions**: check which ones are available with `-h` on your installation before relying on them.

```bash
# List the Linux plugins available in your version
python3 vol.py -h | grep -i linux

# Common examples (names to verify per version)
python3 vol.py -f web-prod-01.lime linux.pslist.PsList
python3 vol.py -f web-prod-01.lime linux.pstree.PsTree
python3 vol.py -f web-prod-01.lime linux.bash.Bash
python3 vol.py -f web-prod-01.lime linux.lsmod.Lsmod
python3 vol.py -f web-prod-01.lime linux.sockstat.Sockstat
```

What to look for with each one, without going into specific output:

- **Process list and tree**: compare with the `ps auxf` from triage. A process present in memory and absent from the live `ps` points to hiding; odd child processes of network services are the pattern of an intrusion through a web vulnerability.
- **Bash history in memory**: recovers commands the attacker deleted from `.bash_history` or that were never written because of `unset HISTFILE`.
- **Kernel modules**: a module you do not recognize is the sign of a rootkit; check it against the `lsmod` from triage.
- **Sockets**: the connections and listening ports at the moment of the dump, tied to PIDs.

AVML and LiME dumps in `lime` format are read directly by Volatility. The result of a QEMU ELF dump may need a conversion step depending on version: that is another reason to test the full flow in a lab.

## Timeline with MAC times

Every file stores three times: **M**odification of content (`mtime`), **A**ccess (`atime`) and metadata **C**hange (`ctime`). Sorted, they tell the story of the intrusion: when the binary arrived, when the unit was edited, when `authorized_keys` was touched.

```bash
# Quick timeline with find over the read-only mounted system
# Columns: mtime | ctime | atime | user | mode | path
sudo find /mnt/evidencia -xdev -type f \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS | %CY-%Cm-%Cd %CH:%CM:%CS | %AY-%Am-%Ad %AH:%AM:%AS | %u | %m | %p\n' \
  | sort > /evidencia/INC-2026-0042/linea-temporal.txt

# Everything changed within the intrusion window
sudo find /mnt/evidencia -xdev -newermt "2026-10-10 22:00" ! -newermt "2026-10-11 03:00" -ls
```

For a complete timeline that includes the filesystem's own metadata, The Sleuth Kit (`fls` + `mactime`) works directly on the image, without mounting it, and includes deleted files:

```bash
# 1. Body file with all files, deleted ones included (use -o <sector> if the image has partitions)
fls -r -m / copia-sdb.img > cuerpo.txt

# 2. Sorted timeline, as CSV, in UTC
mactime -b cuerpo.txt -d -z UTC > linea-temporal.csv
```

To correlate several sources at once (disk, journal, web logs) into a single timeline there is Plaso (`log2timeline`), although it is heavier and for a small incident it is usually overkill.

Two things to keep in mind when interpreting times:

- **`mtime` and `atime` can be forged** with `touch`, and it is trivial. `ctime` cannot be set from user space: it changes whenever the inode is touched, so a `ctime` later than an "old" `mtime` gives the tampering away.
- **`atime` may be disabled or updated rarely**: most systems mount with `relatime`, so it is not a reliable source for "who read what".

A clue that almost always pays off: find the first new file of the window and the last, and cross those instants with the access logs and the journal.

## Searching with YARA

YARA looks for patterns (strings, byte sequences) in files and dumps. It is useful for finding every copy of a suspicious binary, or for sweeping a mounted system and a memory image with the signatures of what you have already identified.

```yara
rule minero_cripto_cadenas
{
    meta:
        descripcion = "Typical strings of a cryptocurrency miner"
        caso = "INC-2026-0042"
    strings:
        $a = "stratum+tcp://" ascii
        $b = "xmrig" ascii nocase
        $c = "cryptonight" ascii nocase
    condition:
        2 of them
}
```

```bash
# Over the read-only mounted filesystem, recursively
yara -r minero.yar /mnt/evidencia

# Over a memory dump (treated as just another binary file)
yara minero.yar /evidencia/INC-2026-0042/memoria/web-prod-01.lime
```

Apply the IoC rules that come out of the case: the hashes and strings you have already loaded as observables in TheHive/MISP (see [Incident response](respuesta_incidentes.md#misp-threat-intelligence)) are easily turned into rules. Watch out for false positives: a rule that is too generic flags legitimate software, and on a memory image of several gigabytes it is also slow.

## Centralized logs: the best evidence

Everything on the compromised machine is, strictly speaking, the suspect's testimony: with root, the attacker edits `auth.log`, empties the journal and wipes the history. **Logs that left the machine before the compromise are the only evidence the attacker could not rewrite.**

That is why the most profitable forensic investment is made before anything happens:

- **A central collector** (Wazuh, rsyslog, `systemd-journal-remote`) that receives events in near real time, with enough retention to cover an attacker's typical dwell time (months, not days).
- **A collector that is append-only** and has credentials different from the rest of the infrastructure: if the same access wipes everything, it is not evidence.
- **Synchronized clocks** (NTP/chrony) on every host. A timeline with skewed clocks cannot be correlated.
- **Kernel auditing** (`auditd`) with rules on binary execution and changes to `/etc` and `authorized_keys`, which answers "what did user X run".

How to set up collection and rules in Wazuh is in [Wazuh: logs and rules](../monitoring/wazuh_logs.md), and the full detection stack (Falco, Wazuh, alerts) in [Security monitoring](monitoreo_seguridad.md). If the manager is configured to archive all events (not just alerts), it keeps the history for forensic queries; check in your version which option enables it and how much space it uses. The measures that make those logs exist by default, such as `auditd` and system hardening, are in [Linux hardening](hardening_linux.md), and the retention requirements in [Compliance and auditing](cumplimiento_auditoria.md).

## Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Volatility does not recognize the Linux dump | Symbols for the exact kernel are missing | Obtain or generate the ISF for that version (`uname -r` recorded in the custody log) |
| LiME `insmod` fails with "Invalid module format" | Module compiled for another kernel | Recompile against the headers of the running version, on an identical VM |
| The image hash does not match the source disk | The source was mounted and changing | Acquire from a snapshot, not from the disk in use |
| When mounting the image, ext4 modifies the filesystem | `noload` missing or the original was mounted | Mount a copy with `ro,noexec,nodev,noload` |
| Live `ps` does not show a process that is in the dump | Rootkit or replaced binaries | Trust the dump and the disk analyzed off the machine; treat the machine as untrustworthy |
| `ls -l /proc/<pid>/exe` shows `(deleted)` | The executable was deleted after launch | Copy it from `/proc/<pid>/exe` before the process exits |
| Timeline times do not line up across sources | Mixed time zones or skewed clock | Normalize everything to UTC and note each host's clock offset |
| Volatility cannot read the dump from the QEMU monitor | Unconverted QEMU ELF format, or different version | Test the flow in a lab; as an alternative, use AVML inside the guest |

## Best practices

- **Prepare before you need it.** Have the USB with trusted binaries, AVML and a LiME module compiled for your kernels, and the forensic workstation ready. At 03:14 nobody compiles anything.
- **Record the kernels in use** (`uname -r` per host in the inventory): without that there are no symbols for Volatility.
- **Order of volatility, always.** Memory before disk; disk before powering off.
- **Hash and record at the moment**, not at the end. What was not hashed when collected cannot be shown to be intact.
- **Never analyze on the original.** Work on copies, mount read-only and no-exec.
- **Prefer the hypervisor.** On Proxmox, a snapshot or a backup of the running VM does not depend on a guest you cannot trust.
- **Ship logs off the machine from day one**, with synchronized clocks. It is the evidence that survives the compromise.
- **Rehearse the flow once** in a lab with a disposable VM. What is untested fails exactly when it matters.
- **Document what you do not know.** An honest open question is worth more than an invented conclusion.

## References

- [RFC 3227 — Guidelines for Evidence Collection and Archiving](https://www.rfc-editor.org/rfc/rfc3227)
- [NIST SP 800-86 — Guide to Integrating Forensic Techniques into Incident Response](https://csrc.nist.gov/pubs/sp/800/86/final)
- [Volatility 3 — documentation](https://volatility3.readthedocs.io/)
- [LiME](https://github.com/504ensicsLabs/LiME) · [AVML](https://github.com/microsoft/avml)
- [The Sleuth Kit](https://www.sleuthkit.org/sleuthkit/) · [YARA](https://yara.readthedocs.io/)
- [Incident response](respuesta_incidentes.md) · [Security monitoring](monitoreo_seguridad.md) · [Linux hardening](hardening_linux.md)
- [Wazuh: logs and rules](../monitoring/wazuh_logs.md) · [SSH security](../linux/ssh_security.md) · [Systemd](../linux/systemd.md)
- [Secure backup](backup_seguro.md) · [Compliance and auditing](cumplimiento_auditoria.md)
