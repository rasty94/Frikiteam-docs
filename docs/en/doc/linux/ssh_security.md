---
title: "SSH Security"
description: "Hardening OpenSSH on servers and homelabs: ed25519 keys, sshd_config, Match, jump hosts, SSH certificates and fail2ban."
keywords: "ssh, sshd_config, openssh, ed25519, ssh-keygen, ssh certificates, fail2ban, ProxyJump, hardening, homelab"
tags: ['linux', 'hardening']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 16 min
category: Linux
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Linux server with OpenSSH installed and an alternative console access"
  - "Basic knowledge of Linux users and permissions"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# SSH Security

## The problem

You open port 22 on the router to reach your server from outside, and within hours `/var/log/auth.log` fills up with login attempts as `root`, `admin` and `ubuntu` from half the world. With a weak password, it is a matter of time. And even if nobody gets in, a private key without a passphrase copied onto five laptops and an `authorized_keys` that nobody reviews are a backdoor waiting for its moment.

SSH is the master key of the infrastructure: whoever controls it controls the rest. Securing it is the critical first step on any Linux server, and almost everything is solved with a well-thought-out `sshd_config`, modern keys and a couple of containment mechanisms.

!!! warning "Before touching `sshd_config`"
    A configuration mistake can lock you out. Keep **one SSH session open** while you test and open a second one to verify the change. Also have an alternative route (hypervisor console, IPMI, physical screen). Always validate with `sudo sshd -t` before reloading.

## 📋 Table of Contents

- [How it works](#how-it-works)
- [Modern SSH keys](#modern-ssh-keys)
- [Hardening sshd_config](#hardening-sshd_config)
- [Per-user restrictions with Match](#per-user-restrictions-with-match)
- [Access through a jump host](#access-through-a-jump-host)
- [SSH certificates](#ssh-certificates)
- [Fail2ban](#fail2ban)
- [Network exposure](#network-exposure)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## How it works

The configuration lives in two different places and it is worth not mixing them up:

| File | Side | Content |
|------|------|---------|
| `/etc/ssh/sshd_config` | Server | What the `sshd` daemon accepts |
| `/etc/ssh/sshd_config.d/*.conf` | Server | Fragments that many distros include from the main file |
| `~/.ssh/config` | Client | Shortcuts, per-host keys, jump hosts |
| `~/.ssh/authorized_keys` | Server | Public keys allowed to log in as that user |

In `sshd_config`, for each directive **the first occurrence** the daemon reads wins. That is why a fragment included at the top can override what you write further down. To see the final effective configuration:

```bash
sudo sshd -T
```

`sshd -T` dumps the values it will actually apply, and it is the way to check that your change is not being overridden by a fragment in `sshd_config.d/`. If you want to use a file of your own, start its name with a low number (for example `10-hardening.conf`) so it is read first; first check whether your distribution includes that directory from the main file.

## Modern SSH keys

Generate one key per device and per purpose, with **ed25519** and a passphrase:

```bash
ssh-keygen -t ed25519 -C "antonio@laptop-2026"
```

It asks for a path and a passphrase; the `-C` comment helps you identify it later in `authorized_keys`. RSA still works, but ed25519 is shorter, faster and does not depend on choosing the right size. If you need RSA for compatibility with old equipment, use 4096 bits.

Install the public key on the server:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server
```

To avoid typing the passphrase on every connection without giving it up, use `ssh-agent`: it is loaded once with `ssh-add` and subsequent connections reuse it for the session.

Permissions matter, and `sshd` silently ignores files that are too open (with `StrictModes yes`, the default):

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys ~/.ssh/id_ed25519
```

!!! note "Application keys"
    For a key used by a script or a CI runner (deployments, backups), create a dedicated key and limit it in `authorized_keys` with options such as `command="..."`, `from="IP"` or `restrict`. That way, if it leaks, it only works for the one thing it should do.

Review from time to time which keys you have authorised: an `authorized_keys` that keeps growing and nobody prunes is a security debt.

## Hardening sshd_config

A reasonable starting point, applicable in `/etc/ssh/sshd_config` or in a fragment of your own:

```bash
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
AllowUsers antonio deploy
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
```

- **Disable root login**: `PermitRootLogin no`. Log in as a normal user and escalate with `sudo`.
- **Use SSH keys**: `PubkeyAuthentication yes` and `PasswordAuthentication no`. With passwords disabled, a brute-force attack stops making sense. Also disable `KbdInteractiveAuthentication`, which in some PAM setups can reopen password authentication.
- **`AllowUsers`**: explicit allowlist. Anyone not on it does not get in, even with an account and a key.
- **`MaxAuthTries` and `LoginGraceTime`**: cap the attempts per connection and the time to authenticate.
- **`X11Forwarding no`**: no reason to have it on a server.

!!! warning "Version dependent"
    The name `KbdInteractiveAuthentication` is the current one in recent OpenSSH versions; older ones called it `ChallengeResponseAuthentication`. Check with `man sshd_config` which one your version recognises; an unknown directive makes `sshd -t` fail.

Apply the change without cutting existing sessions:

```bash
sudo sshd -t && sudo systemctl reload ssh
```

The unit name is `ssh` on Debian and Ubuntu and `sshd` in the RHEL family; see how it is managed in [Systemd](systemd.md).

**Changing the default port** (using one other than 22) avoids mass scans. It is security by obscurity: it reduces log noise but does not stop a targeted attacker, so it never replaces the above. If you do it, also update the firewall, fail2ban's `port` and your `~/.ssh/config`.

## Per-user restrictions with Match

The `Match` block applies directives only to certain users, groups or addresses, and goes **always at the end** of the file because everything that follows belongs to its condition until the next `Match`.

```bash
# A backup user can only log in from the management VLAN
Match User backup Address 10.0.10.0/24
    PasswordAuthentication no
    AllowTcpForwarding no
    X11Forwarding no
    ForceCommand /usr/local/bin/backup-receiver

# Users in the sftponly group: SFTP only, chrooted
Match Group sftponly
    ChrootDirectory /srv/sftp/%u
    ForceCommand internal-sftp
    AllowTcpForwarding no
```

`ForceCommand` forces that command to always run, ignoring the one the client asks for. It is the basis for giving an external service minimal access. `ChrootDirectory` requires the path and all its parents to be owned by root and not writable by others; otherwise `sshd` rejects the session.

## Access through a jump host

In a homelab or a segmented network, expose **a single entry host** (bastion) over SSH and hop from it to the rest. On the client, `~/.ssh/config`:

```bash
Host bastion
    HostName bastion.example.lan
    User antonio
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

Host internal-db
    HostName 10.0.20.15
    User antonio
    ProxyJump bastion
```

With that, `ssh internal-db` goes through the bastion without the database having any exposed port. It is preferable to `ForwardAgent yes`, which leaves your agent accessible to whoever controls the intermediate host. To reach the bastion without opening ports to the outside, the natural alternative is a VPN: see [WireGuard](wireguard.md).

## SSH certificates

Beyond a certain size, handing out public keys by hand through `authorized_keys` does not scale. OpenSSH supports **certificates**: your own CA signs the users' keys and servers only trust the CA.

Create the CA and sign a user's key:

```bash
ssh-keygen -t ed25519 -f user_ca -C "SSH user CA"
ssh-keygen -s user_ca -I antonio -n antonio -V +1d ~/.ssh/id_ed25519.pub
```

In the signing command, `-I` is an identifier that appears in the logs, `-n` the list of allowed users (principals) and `-V +1d` the validity. The result is `id_ed25519-cert.pub` next to the key. On the server, you declare which CA to trust:

```bash
TrustedUserCAKeys /etc/ssh/user_ca.pub
```

Advantages: certificates expire on their own (validity of hours or days), there is no need to edit `authorized_keys` on every join or leave, and the logs record which certificate was used. To safeguard the CA key and issue certificates on demand there are solutions that automate it; see [secrets management](../cybersecurity/gestion_secretos.md) and [authentication and authorization](../cybersecurity/autenticacion_autorizacion.md).

**Host** certificates work the other way round: the CA signs the server's keys and the client trusts it through `@cert-authority` in `known_hosts`, which removes the unknown-fingerprint warning on first connection.

## Fail2ban

Fail2ban scans logs and bans IPs that show malicious behaviour. If you have already disabled passwords the real risk is lower, but it is still useful to cut the noise and persistent scans.

### Installation (Debian/Ubuntu)

```bash
sudo apt install fail2ban
```

### Configuration (Jail)

Create `/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
```

- Changes go in `jail.local`, never in `jail.conf`, which a package may overwrite.
- If you changed the SSH port, `port` must reflect it.
- `logpath` depends on the distribution: on systems that only use the journal `/var/log/auth.log` may not exist. In that case, check fail2ban's documentation on the `systemd` *backend*.

To apply and check:

```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

The second command lists the IPs currently banned. To unban an IP that was blocked by mistake: `sudo fail2ban-client set sshd unbanip IP`. To integrate banning with the modern firewall, see [nftables and fail2ban](../cybersecurity/nftables_fail2ban.md).

## Network exposure

The safest option is for SSH **not to be reachable from the internet**. Order of preference:

1. Only over a VPN ([WireGuard](wireguard.md)) or an internal management network.
2. Behind a bastion with a jump host, with the other machines having no open port.
3. Open to the internet, with keys, no passwords, `AllowUsers` and fail2ban.

Any of the three needs a firewall that limits the source: see [network firewall](../cybersecurity/firewall_red.md) and the other measures in [Linux hardening](../cybersecurity/hardening_linux.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Permission denied (publickey)` | Key not authorised, `~/.ssh` permissions too open or user outside `AllowUsers` | Check `authorized_keys`, `chmod 700/600` and the `AllowUsers` list |
| Asks for a password even though you disabled `PasswordAuthentication` | A fragment in `sshd_config.d/` or `KbdInteractiveAuthentication` re-enables it | `sudo sshd -T` and look for the effective directive |
| `sshd -t` fails after editing | Directive unknown in your version or syntax error | Read the message; compare with `man sshd_config` |
| You lost access after the change | Not tested in a second session | Log in through the console, revert and validate with `sshd -t` |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | You reinstalled the server or there is a man in the middle | If it was your reinstall, `ssh-keygen -R host`; otherwise investigate |
| `Connection refused` after changing the port | The firewall or the client are still on 22 | Open the new port and use `-p` or `Port` in `~/.ssh/config` |
| SFTP chroot rejects the session | Chroot path not owned by root or writable by others | Fix owner and permissions of the path and its parents |
| fail2ban does not ban | Wrong `logpath` or wrong backend | Check `fail2ban-client status sshd` and fail2ban's logs |
| You banned yourself | Several failed attempts from your IP | `fail2ban-client set sshd unbanip IP` and add your network to `ignoreip` |
| Certificate rejected | Expired, or the principal does not match the user | Reissue and check `-n` and the validity; `ssh-keygen -L -f id_ed25519-cert.pub` shows it |

To debug from the client, `ssh -v user@host` (more `v` for more detail) shows which keys it offers and why each method is rejected. On the server, the reason usually appears in the authentication log or in `journalctl -u ssh`.

## Best practices

- **ed25519 keys with a passphrase**, one per device, and immediate removal of any that is lost.
- **No passwords and no root**: `PasswordAuthentication no` and `PermitRootLogin no` on every server.
- **`AllowUsers` or `AllowGroups`** as an allowlist, not trusting that "nobody else has an account".
- **`sshd -t` and a spare session** before every change; the configuration in Git and deployed with [Ansible](../ansible/ansible_base.md).
- **A single entry point** (VPN or bastion) instead of opening SSH on every host.
- **Restricted automation keys** with `command=`, `from=` and `restrict`, never the personal key.
- **Certificates** when the number of users or machines makes `authorized_keys` unmanageable.
- **Review the logs** of authentication and alert on out-of-pattern access; see [security monitoring](../cybersecurity/monitoreo_seguridad.md).

## References

- [sshd_config(5)](https://man.openbsd.org/sshd_config) · [ssh_config(5)](https://man.openbsd.org/ssh_config)
- [ssh-keygen(1)](https://man.openbsd.org/ssh-keygen) — keys and certificates
- [fail2ban documentation](https://github.com/fail2ban/fail2ban)
- [Linux hardening](../cybersecurity/hardening_linux.md) · [nftables and fail2ban](../cybersecurity/nftables_fail2ban.md)
- [Systemd](systemd.md) · [WireGuard](wireguard.md)
