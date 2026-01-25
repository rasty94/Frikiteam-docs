---
title: "Hardening de Servidores Linux"
date: 2025-01-25
updated: 2026-01-25
tags: [security, linux, hardening, ssh, firewall]
difficulty: intermediate
estimated_time: 8 min
category: Ciberseguridad
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Linux intermedio"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Hardening de Servidores Linux

## Introducción

Esta guía proporciona un checklist completo para securizar servidores Linux en producción, siguiendo las mejores prácticas de seguridad y estándares CIS (Center for Internet Security).

## Checklist de Hardening

### 1. Actualizaciones y Parches

#### Debian/Ubuntu
```bash
# Actualizar sistema
apt update && apt upgrade -y

# Configurar actualizaciones automáticas
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades

# Verificar integridad de paquetes
debsums -c
```

#### RHEL/CentOS/Rocky
```bash
# Actualizar sistema
yum update -y

# Configurar actualizaciones automáticas
yum install dnf-automatic -y
systemctl enable --now dnf-automatic.timer

# Verificar integridad
rpm -Va
```

### 2. Gestión de Usuarios y Contraseñas

#### Crear usuario administrativo
```bash
# Crear usuario con sudo
useradd -m -s /bin/bash admin
passwd admin
usermod -aG sudo admin  # Debian/Ubuntu
usermod -aG wheel admin # RHEL/CentOS

# Remover usuarios por defecto innecesarios
userdel -r games
userdel -r irc
```

#### Configurar políticas de contraseñas fuertes
```bash
# /etc/security/pwquality.conf
minlen = 14
dcredit = -1
ucredit = -1
ocredit = -1
lcredit = -1
minclass = 4

# Expiración de contraseñas
chage -M 90 -m 7 -W 14 admin

# Bloqueo de cuenta tras intentos fallidos
# /etc/pam.d/common-auth (Debian) o /etc/pam.d/system-auth (RHEL)
auth required pam_faillock.so preauth silent audit deny=5 unlock_time=900
```

### 3. SSH Hardening Avanzado

#### Configuración completa SSH
```bash
# /etc/ssh/sshd_config
Port 2222                              # Cambiar puerto por defecto
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
AllowUsers admin                       # Solo usuarios específicos

# Criptografía fuerte
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
KexAlgorithms curve25519-sha256,diffie-hellman-group-exchange-sha256

# Reiniciar SSH
systemctl restart sshd
```

#### Autenticación con claves SSH
```bash
# En el cliente, generar clave SSH
ssh-keygen -t ed25519 -C "admin@server"

# Copiar clave al servidor
ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@server -p 2222

# En el servidor, asegurar permisos
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

#### Implementar 2FA con Google Authenticator
```bash
# Instalar
apt install libpam-google-authenticator -y

# Configurar para usuario
google-authenticator

# /etc/pam.d/sshd (añadir)
auth required pam_google_authenticator.so

# /etc/ssh/sshd_config
ChallengeResponseAuthentication yes
AuthenticationMethods publickey,keyboard-interactive
```

### 4. Firewall (UFW y firewalld)

#### UFW (Debian/Ubuntu)
```bash
# Instalar y habilitar
apt install ufw -y
ufw default deny incoming
ufw default allow outgoing

# Permitir servicios específicos
ufw allow 2222/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Limitar intentos SSH
ufw limit 2222/tcp

# Habilitar
ufw enable
ufw status verbose
```

#### firewalld (RHEL/CentOS)
```bash
# Instalar y habilitar
yum install firewalld -y
systemctl enable --now firewalld

# Configurar zona por defecto
firewall-cmd --set-default-zone=public

# Permitir servicios
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-port=2222/tcp

# Rate limiting para SSH
firewall-cmd --permanent --add-rich-rule='rule service name="ssh" limit value="3/m" accept'

# Aplicar cambios
firewall-cmd --reload
```

### 5. Kernel y Sysctl - Configuración Completa

```bash
# /etc/sysctl.conf o /etc/sysctl.d/99-hardening.conf

# IP Forwarding (deshabilitar si no es router)
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# Protección contra IP spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignorar ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# No enviar ICMP redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Protección contra SYN flood
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# Ignorar pings (opcional)
net.ipv4.icmp_echo_ignore_all = 1

# ASLR (Address Space Layout Randomization)
kernel.randomize_va_space = 2

# Core dumps (deshabilitar)
kernel.core_uses_pid = 1
fs.suid_dumpable = 0

# Aplicar cambios
sysctl -p
```

### 6. Logging y Auditoría Avanzada

#### Configurar auditd
```bash
# Instalar
apt install auditd audispd-plugins -y

# /etc/audit/rules.d/hardening.rules
# Monitorear cambios en archivos de configuración
-w /etc/passwd -p wa -k passwd_changes
-w /etc/group -p wa -k group_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/sudoers -p wa -k sudoers_changes

# Monitorear intentos de login
-w /var/log/faillog -p wa -k logins
-w /var/log/lastlog -p wa -k logins

# Monitorear comandos privilegiados
-a always,exit -F arch=b64 -S execve -F euid=0 -k root_commands

# Cargar reglas
auditctl -R /etc/audit/rules.d/hardening.rules
systemctl restart auditd
```

#### Configurar logrotate
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

#### Enviar logs a servidor centralizado
```bash
# /etc/rsyslog.conf
*.* @@log-server.example.com:514  # TCP
*.* @log-server.example.com:514   # UDP

systemctl restart rsyslog
```

### 7. Gestión de Servicios

#### Listar y deshabilitar servicios innecesarios
```bash
# Listar servicios activos
systemctl list-units --type=service --state=running

# Deshabilitar servicios innecesarios
systemctl disable --now avahi-daemon
systemctl disable --now cups
systemctl disable --now bluetooth

# Verificar servicios escuchando en red
ss -tulpn
netstat -tulpn
```

#### Configurar SELinux (RHEL/CentOS)
```bash
# Verificar estado
sestatus

# Habilitar SELinux en modo enforcing
# /etc/selinux/config
SELINUX=enforcing
SELINUXTYPE=targeted

# Aplicar contextos
restorecon -Rv /var/www/html

# Troubleshooting
audit2allow -a -M custom_policy
semodule -i custom_policy.pp
```

#### Configurar AppArmor (Debian/Ubuntu)
```bash
# Verificar estado
aa-status

# Crear perfil para aplicación
aa-genprof /usr/bin/myapp

# Habilitar perfil
aa-enforce /etc/apparmor.d/usr.bin.myapp
```

### 8. Protección contra Malware

#### ClamAV
```bash
# Instalar
apt install clamav clamav-daemon -y

# Actualizar definiciones
freshclam

# Escanear sistema
clamscan -r --infected --remove /home

# Escaneo programado (crontab)
0 2 * * * /usr/bin/clamscan -r --quiet --infected --log=/var/log/clamav/scan.log /home
```

#### rkhunter y chkrootkit
```bash
# Instalar
apt install rkhunter chkrootkit -y

# Ejecutar rkhunter
rkhunter --update
rkhunter --check

# Ejecutar chkrootkit
chkrootkit
```

### 9. Protección de Filesystem

#### Configurar particiones con opciones de montaje seguras
```bash
# /etc/fstab
/dev/sda1 /tmp    ext4 defaults,noexec,nosuid,nodev 0 0
/dev/sda2 /var    ext4 defaults,nosuid                0 0
/dev/sda3 /home   ext4 defaults,nodev,nosuid          0 0

# Aplicar cambios
mount -o remount /tmp
```

#### Configurar permisos críticos
```bash
# Proteger archivos sensibles
chmod 600 /etc/shadow
chmod 600 /etc/gshadow
chmod 644 /etc/passwd
chmod 644 /etc/group

# Eliminar permisos SUID/SGID innecesarios
find / -perm /4000 -type f -exec ls -ld {} \;
find / -perm /2000 -type f -exec ls -ld {} \;

# Remover SUID de archivos no esenciales
chmod u-s /usr/bin/wall
```

## Script de Hardening Automatizado

```bash
#!/bin/bash
# hardening.sh - Script automatizado de hardening

set -euo pipefail

LOGFILE="/var/log/hardening.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

log "Iniciando hardening de sistema..."

# Actualizar sistema
log "Actualizando paquetes..."
apt update && apt upgrade -y

# Configurar firewall
log "Configurando UFW..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp
ufw --force enable

# SSH hardening
log "Configurando SSH..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# Kernel hardening
log "Aplicando configuración de kernel..."
cat >> /etc/sysctl.d/99-hardening.conf <<EOF
net.ipv4.ip_forward=0
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.all.accept_redirects=0
net.ipv4.tcp_syncookies=1
kernel.randomize_va_space=2
EOF
sysctl -p /etc/sysctl.d/99-hardening.conf

# Instalar herramientas de seguridad
log "Instalando herramientas..."
apt install -y fail2ban auditd rkhunter

log "Hardening completado. Revisar $LOGFILE"
```

## Herramientas de Automatización y Auditoría

### Lynis
```bash
# Instalar
apt install lynis -y

# Ejecutar auditoría completa
lynis audit system

# Revisar recomendaciones
cat /var/log/lynis.log
```

### OpenSCAP
```bash
# Instalar
apt install libopenscap8 -y

# Descargar perfiles CIS
wget https://github.com/ComplianceAsCode/content/releases/download/v0.1.66/scap-security-guide-0.1.66.zip
unzip scap-security-guide-0.1.66.zip

# Escanear sistema
oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_cis \
  --results scan-results.xml \
  ssg-ubuntu2004-ds.xml

# Generar reporte HTML
oscap xccdf generate report scan-results.xml > report.html
```

### Ansible para Hardening
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

## Monitoreo Continuo

### Fail2Ban para protección contra brute-force
```bash
# Instalar
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

# Verificar bans
fail2ban-client status sshd
```

### AIDE (Advanced Intrusion Detection Environment)
```bash
# Instalar
apt install aide -y

# Inicializar base de datos
aideinit

# Mover base de datos
mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Verificar integridad (ejecutar diariamente)
aide --check

# Cron job
0 3 * * * /usr/bin/aide --check | mail -s "AIDE Report" admin@example.com
```

## Checklist Final de Validación

- [ ] Actualizaciones automáticas configuradas
- [ ] SSH configurado en puerto no estándar con claves
- [ ] Root login deshabilitado
- [ ] Firewall activo con reglas mínimas
- [ ] SELinux/AppArmor en modo enforcing
- [ ] Auditd configurado y funcional
- [ ] Fail2Ban activo para SSH
- [ ] Servicios innecesarios deshabilitados
- [ ] Kernel parameters de seguridad aplicados
- [ ] Logs rotando correctamente
- [ ] AIDE o similar para detección de intrusiones
- [ ] Escaneo con Lynis pasado
- [ ] Backups configurados y probados

## Referencias

- [CIS Linux Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [Lynis](https://cisofy.com/lynis/)
- [OpenSCAP](https://www.open-scap.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Debian Security Manual](https://www.debian.org/doc/manuals/securing-debian-manual/)
- [Red Hat Security Guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/security_hardening/index)