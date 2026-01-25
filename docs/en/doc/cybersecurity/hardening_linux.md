---
title: "Linux Server Hardening"
date: 2025-01-25
updated: 2025-01-25
tags: [security, linux, hardening, ssh, firewall]
---

# Linux Server Hardening

## Introduction

This guide provides a complete checklist for securing production Linux servers, following security best practices and CIS (Center for Internet Security) standards.

## Hardening Checklist

### 1. Updates and Patches

#### Debian/Ubuntu
```bash
# Update system
apt update && apt upgrade -y

# Configure automatic updates
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades

# Verify package integrity
debsums -c
```

#### RHEL/CentOS/Rocky
```bash
# Update system
yum update -y

# Configure automatic updates
yum install dnf-automatic -y
systemctl enable --now dnf-automatic.timer

# Verify integrity
rpm -Va
```

### 2. User and Password Management

#### Create administrative user
```bash
# Create user with sudo
useradd -m -s /bin/bash admin
passwd admin
usermod -aG sudo admin  # Debian/Ubuntu
usermod -aG wheel admin # RHEL/CentOS

# Remove unnecessary default users
userdel -r games
userdel -r irc
```

#### Configure strong password policies
```bash
# /etc/security/pwquality.conf
minlen = 14
dcredit = -1
ucredit = -1
ocredit = -1
lcredit = -1
minclass = 4

# Password expiration
chage -M 90 -m 7 -W 14 admin

# Account lockout after failed attempts
# /etc/pam.d/common-auth (Debian) or /etc/pam.d/system-auth (RHEL)
auth required pam_faillock.so preauth silent audit deny=5 unlock_time=900
```

### 3. Advanced SSH Hardening

#### Complete SSH configuration
```bash
# /etc/ssh/sshd_config
Port 2222                              # Change default port
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 2
LoginGraceTime 60
AllowUsers admin                       # Specific users only

# Strong cryptography
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
KexAlgorithms curve25519-sha256,diffie-hellman-group-exchange-sha256

# Restart SSH
systemctl restart sshd
```

#### SSH key authentication
```bash
# On client, generate SSH key
ssh-keygen -t ed25519 -C "admin@server"

# Copy key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@server -p 2222

# On server, secure permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

#### Implement 2FA with Google Authenticator
```bash
# Install
apt install libpam-google-authenticator -y

# Configure for user
google-authenticator

# /etc/pam.d/sshd (add)
auth required pam_google_authenticator.so

# /etc/ssh/sshd_config
ChallengeResponseAuthentication yes
AuthenticationMethods publickey,keyboard-interactive
```

### 4. Firewall (UFW and firewalld)

#### UFW (Debian/Ubuntu)
```bash
# Install and enable
apt install ufw -y
ufw default deny incoming
ufw default allow outgoing

# Allow specific services
ufw allow 2222/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Rate limit SSH
ufw limit 2222/tcp

# Enable
ufw enable
ufw status verbose
```

#### firewalld (RHEL/CentOS)
```bash
# Install and enable
yum install firewalld -y
systemctl enable --now firewalld

# Configure default zone
firewall-cmd --set-default-zone=public

# Allow services
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-port=2222/tcp

# SSH rate limiting
firewall-cmd --permanent --add-rich-rule='rule service name="ssh" limit value="3/m" accept'

# Apply changes
firewall-cmd --reload
```

### 5. Kernel and Sysctl - Complete Configuration

```bash
# /etc/sysctl.conf or /etc/sysctl.d/99-hardening.conf

# IP Forwarding (disable if not a router)
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# IP spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Don't send ICMP redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# Ignore pings (optional)
net.ipv4.icmp_echo_ignore_all = 1

# ASLR (Address Space Layout Randomization)
kernel.randomize_va_space = 2

# Core dumps (disable)
kernel.core_uses_pid = 1
fs.suid_dumpable = 0

# Apply changes
sysctl -p
```

### 6. Advanced Logging and Auditing

#### Configure auditd
```bash
# Install
apt install auditd audispd-plugins -y

# /etc/audit/rules.d/hardening.rules
# Monitor config file changes
-w /etc/passwd -p wa -k passwd_changes
-w /etc/group -p wa -k group_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/sudoers -p wa -k sudoers_changes

# Monitor login attempts
-w /var/log/faillog -p wa -k logins
-w /var/log/lastlog -p wa -k logins

# Monitor privileged commands
-a always,exit -F arch=b64 -S execve -F euid=0 -k root_commands

# Load rules
auditctl -R /etc/audit/rules.d/hardening.rules
systemctl restart auditd
```

#### Configure logrotate
```bash
# /etc/logrotate.d/syslog
/var/log/syslog
/var/log/auth.log
{
    rotate 90
    daily
    missingok
    notifempty
    compress
    delaycompress
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
```

#### Send logs to centralized server
```bash
# /etc/rsyslog.conf
*.* @@log-server.example.com:514  # TCP
*.* @log-server.example.com:514   # UDP

systemctl restart rsyslog
```

### 7. Service Management

#### List and disable unnecessary services
```bash
# List active services
systemctl list-units --type=service --state=running

# Disable unnecessary services
systemctl disable --now avahi-daemon
systemctl disable --now cups
systemctl disable --now bluetooth

# Check services listening on network
ss -tulpn
netstat -tulpn
```

#### Configure SELinux (RHEL/CentOS)
```bash
# Check status
sestatus

# Enable SELinux in enforcing mode
# /etc/selinux/config
SELINUX=enforcing
SELINUXTYPE=targeted

# Apply contexts
restorecon -Rv /var/www/html

# Troubleshooting
audit2allow -a -M custom_policy
semodule -i custom_policy.pp
```

#### Configure AppArmor (Debian/Ubuntu)
```bash
# Check status
aa-status

# Create profile for application
aa-genprof /usr/bin/myapp

# Enable profile
aa-enforce /etc/apparmor.d/usr.bin.myapp
```

### 8. Malware Protection

#### ClamAV
```bash
# Install
apt install clamav clamav-daemon -y

# Update definitions
freshclam

# Scan system
clamscan -r --infected --remove /home

# Scheduled scan (crontab)
0 2 * * * /usr/bin/clamscan -r --quiet --infected --log=/var/log/clamav/scan.log /home
```

#### rkhunter and chkrootkit
```bash
# Install
apt install rkhunter chkrootkit -y

# Run rkhunter
rkhunter --update
rkhunter --check

# Run chkrootkit
chkrootkit
```

### 9. Filesystem Protection

#### Configure partitions with secure mount options
```bash
# /etc/fstab
/dev/sda1 /tmp    ext4 defaults,noexec,nosuid,nodev 0 0
/dev/sda2 /var    ext4 defaults,nosuid                0 0
/dev/sda3 /home   ext4 defaults,nodev,nosuid          0 0

# Apply changes
mount -o remount /tmp
```

#### Configure critical permissions
```bash
# Protect sensitive files
chmod 600 /etc/shadow
chmod 600 /etc/gshadow
chmod 644 /etc/passwd
chmod 644 /etc/group

# Remove unnecessary SUID/SGID
find / -perm /4000 -type f -exec ls -ld {} \;
find / -perm /2000 -type f -exec ls -ld {} \;

# Remove SUID from non-essential files
chmod u-s /usr/bin/wall
```

## Automated Hardening Script

```bash
#!/bin/bash
# hardening.sh - Automated hardening script

set -euo pipefail

LOGFILE="/var/log/hardening.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

log "Starting system hardening..."

# Update system
log "Updating packages..."
apt update && apt upgrade -y

# Configure firewall
log "Configuring UFW..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp
ufw --force enable

# SSH hardening
log "Configuring SSH..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# Kernel hardening
log "Applying kernel configuration..."
cat >> /etc/sysctl.d/99-hardening.conf <<EOF
net.ipv4.ip_forward=0
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.all.accept_redirects=0
net.ipv4.tcp_syncookies=1
kernel.randomize_va_space=2
EOF
sysctl -p /etc/sysctl.d/99-hardening.conf

# Install security tools
log "Installing tools..."
apt install -y fail2ban auditd rkhunter

log "Hardening completed. Review $LOGFILE"
```

## Automation and Audit Tools

### Lynis
```bash
# Install
apt install lynis -y

# Run full audit
lynis audit system

# Review recommendations
cat /var/log/lynis.log
```

### OpenSCAP
```bash
# Install
apt install libopenscap8 -y

# Download CIS profiles
wget https://github.com/ComplianceAsCode/content/releases/download/v0.1.66/scap-security-guide-0.1.66.zip
unzip scap-security-guide-0.1.66.zip

# Scan system
oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_cis \
  --results scan-results.xml \
  ssg-ubuntu2004-ds.xml

# Generate HTML report
oscap xccdf generate report scan-results.xml > report.html
```

### Ansible for Hardening
```yaml
# hardening.yml
---
- name: Linux Server Hardening
  hosts: all
  become: yes
  tasks:
    - name: Update all packages
      apt:
        upgrade: dist
        update_cache: yes

    - name: Configure SSH
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: "{% raw %}{{ item.regexp }}{% endraw %}"
        line: "{% raw %}{{ item.line }}{% endraw %}"
      loop:
        - { regexp: '^PermitRootLogin', line: 'PermitRootLogin no' }
        - { regexp: '^PasswordAuthentication', line: 'PasswordAuthentication no' }
      notify: restart ssh

    - name: Configure UFW
      ufw:
        rule: allow
        port: '{% raw %}{{ item }}{% endraw %}'
        proto: tcp
      loop:
        - 2222
        - 80
        - 443

  handlers:
    - name: restart ssh
      service:
        name: sshd
        state: restarted
```

## Continuous Monitoring

### Fail2Ban for brute-force protection
```bash
# Install
apt install fail2ban -y

# /etc/fail2ban/jail.local
[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600

systemctl restart fail2ban

# Check bans
fail2ban-client status sshd
```

### AIDE (Advanced Intrusion Detection Environment)
```bash
# Install
apt install aide -y

# Initialize database
aideinit

# Move database
mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Check integrity (run daily)
aide --check

# Cron job
0 3 * * * /usr/bin/aide --check | mail -s "AIDE Report" admin@example.com
```

## Final Validation Checklist

- [ ] Automatic updates configured
- [ ] SSH configured on non-standard port with keys
- [ ] Root login disabled
- [ ] Firewall active with minimal rules
- [ ] SELinux/AppArmor in enforcing mode
- [ ] Auditd configured and functional
- [ ] Fail2Ban active for SSH
- [ ] Unnecessary services disabled
- [ ] Security kernel parameters applied
- [ ] Logs rotating correctly
- [ ] AIDE or similar for intrusion detection
- [ ] Lynis scan passed
- [ ] Backups configured and tested

## References

- [CIS Linux Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [Lynis](https://cisofy.com/lynis/)
- [OpenSCAP](https://www.open-scap.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Debian Security Manual](https://www.debian.org/doc/manuals/securing-debian-manual/)
- [Red Hat Security Guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/security_hardening/index)