# SSH Security

Securing SSH access is the critical first step for any Linux server.

## Best Practices

1.  **Disable root login**: In `/etc/ssh/sshd_config`, set `PermitRootLogin no`.
2.  **Use SSH keys**: Prefer public key authentication (`PubkeyAuthentication yes`) and disable passwords (`PasswordAuthentication no`).
3.  **Change default port**: Use a port other than 22 to avoid mass scans (security by obscurity, but reduces noise).

## Fail2ban

Fail2ban scans logs and bans IPs that show malicious behavior.

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
