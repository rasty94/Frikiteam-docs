# Seguridad SSH

Asegurar el acceso SSH es el primer paso crítico en cualquier servidor Linux.

## Mejores Prácticas

1.  **Deshabilitar root login**: En `/etc/ssh/sshd_config`, establecer `PermitRootLogin no`.
2.  **Usar claves SSH**: Preferir autenticación por clave pública (`PubkeyAuthentication yes`) y deshabilitar contraseñas (`PasswordAuthentication no`).
3.  **Cambiar el puerto por defecto**: Usar un puerto distinto al 22 para evitar escaneos masivos (seguridad por oscuridad, pero reduce ruido).

## Fail2ban

Fail2ban escanea logs y banea IPs que muestran comportamiento malicioso.

### Instalación (Debian/Ubuntu)

```bash
sudo apt install fail2ban
```

### Configuración (Jail)

Crea `/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
```
