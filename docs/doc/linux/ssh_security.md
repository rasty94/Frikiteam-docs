---
title: "Seguridad SSH"
description: "Endurecer OpenSSH en servidores y homelabs: claves ed25519, sshd_config, Match, jump hosts, certificados SSH y fail2ban."
keywords: "ssh, sshd_config, openssh, ed25519, ssh-keygen, certificados ssh, fail2ban, ProxyJump, hardening, homelab"
tags: ['linux', 'hardening']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 16 min
category: Linux
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Servidor Linux con OpenSSH instalado y acceso por consola alternativo"
  - "Conocimientos básicos de usuarios y permisos Linux"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Seguridad SSH

## El problema

Abres el puerto 22 en el router para llegar a tu servidor desde fuera, y en cuestión de horas `/var/log/auth.log` se llena de intentos de login como `root`, `admin` y `ubuntu` desde medio mundo. Con contraseña débil, es cuestión de tiempo. Y aunque nadie entre, una clave privada sin passphrase copiada en cinco portátiles y un `authorized_keys` que nadie revisa son una puerta trasera esperando su momento.

SSH es la llave maestra de la infraestructura: quien lo controla controla el resto. Asegurarlo es el primer paso crítico en cualquier servidor Linux, y casi todo se resuelve con un `sshd_config` meditado, claves modernas y un par de mecanismos de contención.

!!! warning "Antes de tocar `sshd_config`"
    Un error de configuración puede dejarte sin acceso. Mantén **una sesión SSH abierta** mientras pruebas y abre una segunda para verificar el cambio. Ten además una vía alternativa (consola del hipervisor, IPMI, pantalla física). Valida siempre con `sudo sshd -t` antes de recargar.

## 📋 Tabla de Contenidos

- [Cómo funciona](#como-funciona)
- [Claves SSH modernas](#claves-ssh-modernas)
- [Endurecer sshd_config](#endurecer-sshd_config)
- [Restringir por usuario con Match](#restringir-por-usuario-con-match)
- [Acceso por jump host](#acceso-por-jump-host)
- [Certificados SSH](#certificados-ssh)
- [Fail2ban](#fail2ban)
- [Exposición de red](#exposicion-de-red)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Cómo funciona

La configuración vive en dos sitios distintos y conviene no mezclarlos:

| Fichero | Lado | Contenido |
|---------|------|-----------|
| `/etc/ssh/sshd_config` | Servidor | Qué acepta el daemon `sshd` |
| `/etc/ssh/sshd_config.d/*.conf` | Servidor | Fragmentos que muchas distros incluyen desde el principal |
| `~/.ssh/config` | Cliente | Atajos, claves por host, jump hosts |
| `~/.ssh/authorized_keys` | Servidor | Claves públicas que pueden entrar como ese usuario |

En `sshd_config`, para cada directiva **gana la primera aparición** que el daemon lee. Por eso un fragmento incluido al principio puede anular lo que escribes más abajo. Para ver la configuración efectiva final:

```bash
sudo sshd -T
```

`sshd -T` vuelca los valores que realmente aplicará, y es la forma de comprobar que tu cambio no está siendo pisado por un fragmento de `sshd_config.d/`. Si quieres usar un fichero propio, empieza su nombre con un número bajo (por ejemplo `10-hardening.conf`) para que se lea primero; comprueba antes si tu distribución incluye ese directorio desde el fichero principal.

## Claves SSH modernas

Genera una clave por dispositivo y por finalidad, con **ed25519** y passphrase:

```bash
ssh-keygen -t ed25519 -C "antonio@portatil-2026"
```

Pide ruta y passphrase; el comentario `-C` te sirve para identificarla luego en `authorized_keys`. RSA sigue funcionando, pero ed25519 es más corta, más rápida y no depende de elegir bien el tamaño. Si necesitas RSA por compatibilidad con equipos antiguos, usa 4096 bits.

Instalar la clave pública en el servidor:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub usuario@servidor
```

Para no teclear la passphrase en cada conexión sin renunciar a ella, usa `ssh-agent`: se carga una vez con `ssh-add` y las conexiones siguientes la reutilizan durante la sesión.

Los permisos importan, y `sshd` ignora silenciosamente los ficheros demasiado abiertos (con `StrictModes yes`, el valor por defecto):

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys ~/.ssh/id_ed25519
```

!!! note "Claves de aplicación"
    Para una clave que usa un script o un runner de CI (despliegues, backups), crea una clave dedicada y limítala en `authorized_keys` con opciones como `command="..."`, `from="IP"` o `restrict`. Así, si se filtra, solo sirve para lo único que debe hacer.

Revisa de vez en cuando qué claves tienes autorizadas: un `authorized_keys` que crece y nadie poda es una deuda de seguridad.

## Endurecer sshd_config

Un punto de partida razonable, aplicable en `/etc/ssh/sshd_config` o en un fragmento propio:

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

- **Deshabilitar root login**: `PermitRootLogin no`. Entra con un usuario normal y escala con `sudo`.
- **Usar claves SSH**: `PubkeyAuthentication yes` y `PasswordAuthentication no`. Con contraseñas desactivadas, un ataque de fuerza bruta deja de tener sentido. Desactiva también `KbdInteractiveAuthentication`, que en algunas configuraciones PAM puede reabrir la autenticación por contraseña.
- **`AllowUsers`**: lista blanca explícita. Quien no esté en ella no entra, aunque tenga cuenta y clave.
- **`MaxAuthTries` y `LoginGraceTime`**: acotan los intentos por conexión y el tiempo para autenticarse.
- **`X11Forwarding no`**: sin motivo para tenerlo en un servidor.

!!! warning "Dependiente de la versión"
    El nombre `KbdInteractiveAuthentication` es el actual en versiones recientes de OpenSSH; en las más antiguas (antes de OpenSSH 8.7) se llamaba `ChallengeResponseAuthentication`, que hoy sigue como alias obsoleto. Comprueba con `man sshd_config` cuál reconoce tu versión; una directiva desconocida hace fallar `sshd -t`.

Aplica el cambio sin cortar las sesiones existentes:

```bash
sudo sshd -t && sudo systemctl reload ssh
```

El nombre de la unit es `ssh` en Debian y Ubuntu y `sshd` en la familia RHEL; consulta cómo se gestiona en [Systemd](systemd.md).

**Cambiar el puerto por defecto** (usar uno distinto al 22) evita escaneos masivos. Es seguridad por oscuridad: reduce ruido en los logs pero no frena a un atacante dirigido, así que nunca sustituye a lo anterior. Si lo haces, actualiza también el firewall, el `port` de fail2ban y tu `~/.ssh/config`.

## Restringir por usuario con Match

El bloque `Match` aplica directivas solo a ciertos usuarios, grupos o direcciones, y va **siempre al final** del fichero porque todo lo que sigue pertenece a su condición hasta el siguiente `Match`.

```bash
# Un usuario de backups solo puede entrar desde la VLAN de gestión
Match User backup Address 10.0.10.0/24
    PasswordAuthentication no
    AllowTcpForwarding no
    X11Forwarding no
    ForceCommand /usr/local/bin/backup-receiver

# Usuarios del grupo sftponly: solo SFTP, enjaulados
Match Group sftponly
    ChrootDirectory /srv/sftp/%u
    ForceCommand internal-sftp
    AllowTcpForwarding no
```

`ForceCommand` obliga a ejecutar siempre ese comando, ignorando el que pida el cliente. Es la base para dar a un servicio externo acceso mínimo. `ChrootDirectory` exige que la ruta y todos sus padres pertenezcan a root y no sean escribibles por otros; si no, `sshd` rechaza la sesión.

## Acceso por jump host

En un homelab o una red con segmentos, expón por SSH **un solo host de entrada** (bastión) y salta desde él al resto. En el cliente, `~/.ssh/config`:

```bash
Host bastion
    HostName bastion.ejemplo.lan
    User antonio
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

Host db-interna
    HostName 10.0.20.15
    User antonio
    ProxyJump bastion
```

Con eso, `ssh db-interna` atraviesa el bastión sin que la base de datos tenga ningún puerto expuesto. Es preferible a `ForwardAgent yes`, que deja tu agente accesible para quien controle el host intermedio. Para llegar al bastión sin abrir puertos al exterior, la alternativa natural es una VPN: ver [WireGuard](wireguard.md).

## Certificados SSH

A partir de cierto tamaño, repartir claves públicas a mano por `authorized_keys` no escala. OpenSSH soporta **certificados**: una CA propia firma las claves de los usuarios y los servidores solo confían en la CA.

Crear la CA y firmar la clave de un usuario:

```bash
ssh-keygen -t ed25519 -f ca_usuarios -C "CA SSH usuarios"
ssh-keygen -s ca_usuarios -I antonio -n antonio -V +1d ~/.ssh/id_ed25519.pub
```

En la firma, `-I` es un identificador que aparece en los logs, `-n` la lista de usuarios (principals) permitidos y `-V +1d` la validez. El resultado es `id_ed25519-cert.pub` junto a la clave. En el servidor, se declara en qué CA se confía:

```bash
TrustedUserCAKeys /etc/ssh/ca_usuarios.pub
```

Ventajas: los certificados caducan solos (validez de horas o días), no hay que editar `authorized_keys` en cada alta o baja, y los logs registran qué certificado se usó. Para custodiar la clave de la CA y emitir certificados bajo demanda hay soluciones que lo automatizan; ver [gestión de secretos](../cybersecurity/gestion_secretos.md) y [autenticación y autorización](../cybersecurity/autenticacion_autorizacion.md).

Los certificados de **host** funcionan al revés: la CA firma las claves del servidor y el cliente confía en ella mediante `@cert-authority` en `known_hosts`, lo que elimina el aviso de huella desconocida en la primera conexión.

## Fail2ban

Fail2ban escanea logs y banea IPs que muestran comportamiento malicioso. Si ya has desactivado las contraseñas el riesgo real es menor, pero sigue siendo útil para cortar el ruido y los escaneos persistentes.

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

- Los cambios van en `jail.local`, nunca en `jail.conf`, que un paquete puede sobrescribir.
- Si cambiaste el puerto de SSH, `port` debe reflejarlo.
- `logpath` depende de la distribución: en sistemas que solo usan el journal puede no existir `/var/log/auth.log`. En ese caso, usa `backend = systemd` (y quita `logpath`); consulta la documentación de fail2ban.

Para aplicar y comprobar:

```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

El segundo comando lista las IPs actualmente baneadas. Para desbanear una IP que se bloqueó por error: `sudo fail2ban-client set sshd unbanip IP`. Para integrar el baneo con el firewall moderno, ver [nftables y fail2ban](../cybersecurity/nftables_fail2ban.md).

## Exposición de red

Lo más seguro es que SSH **no sea accesible desde internet**. Orden de preferencia:

1. Solo por VPN ([WireGuard](wireguard.md)) o red de gestión interna.
2. Detrás de un bastión con jump host, con el resto de equipos sin puerto abierto.
3. Abierto a internet, con claves, sin contraseñas, `AllowUsers` y fail2ban.

Cualquiera de las tres necesita un cortafuegos que limite el origen: ver [firewall de red](../cybersecurity/firewall_red.md) y el resto de medidas en [hardening de Linux](../cybersecurity/hardening_linux.md).

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---------|----------------|---------|
| `Permission denied (publickey)` | Clave no autorizada, permisos de `~/.ssh` demasiado abiertos o usuario fuera de `AllowUsers` | Revisa `authorized_keys`, `chmod 700/600` y la lista de `AllowUsers` |
| Pide contraseña aunque desactivaste `PasswordAuthentication` | Un fragmento de `sshd_config.d/` o `KbdInteractiveAuthentication` lo reactiva | `sudo sshd -T` y busca la directiva efectiva |
| `sshd -t` falla tras editar | Directiva desconocida en tu versión o error de sintaxis | Lee el mensaje; contrasta con `man sshd_config` |
| Te quedaste sin acceso tras el cambio | No probaste en una segunda sesión | Entra por consola, revierte y valida con `sshd -t` |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Reinstalaste el servidor o hay un intermediario | Si fue tu reinstalación, `ssh-keygen -R host`; si no, investiga |
| `Connection refused` tras cambiar el puerto | El firewall o el cliente siguen en el 22 | Abre el nuevo puerto y usa `-p` o `Port` en `~/.ssh/config` |
| El chroot de SFTP rechaza la sesión | Ruta del chroot no propiedad de root o escribible por otros | Corrige propietario y permisos de la ruta y sus padres |
| fail2ban no banea | `logpath` incorrecto o backend equivocado | Revisa `fail2ban-client status sshd` y los logs de fail2ban |
| Te baneaste a ti mismo | Varios intentos fallidos desde tu IP | `fail2ban-client set sshd unbanip IP` y añade tu red a `ignoreip` |
| Certificado rechazado | Caducado, o el principal no coincide con el usuario | Reemite y comprueba `-n` y la validez; `ssh-keygen -L -f id_ed25519-cert.pub` lo muestra |

Para depurar desde el cliente, `ssh -v usuario@host` (más `v` para más detalle) muestra qué claves ofrece y por qué se rechaza cada método. En el servidor, el motivo suele aparecer en el log de autenticación o en `journalctl -u ssh`.

## Buenas prácticas

- **Claves ed25519 con passphrase**, una por dispositivo, y baja inmediata de la que se pierda.
- **Sin contraseñas ni root**: `PasswordAuthentication no` y `PermitRootLogin no` en cualquier servidor.
- **`AllowUsers` o `AllowGroups`** como lista blanca, no confiar en que "nadie más tiene cuenta".
- **`sshd -t` y sesión de reserva** antes de cada cambio; la configuración, en Git y desplegada con [Ansible](../ansible/ansible_base.md).
- **Un solo punto de entrada** (VPN o bastión) en lugar de abrir SSH en cada host.
- **Claves de automatización restringidas** con `command=`, `from=` y `restrict`, nunca la clave personal.
- **Certificados** cuando el número de usuarios o equipos haga inmanejable `authorized_keys`.
- **Revisa los logs** de autenticación y alerta de accesos fuera de patrón; ver [monitoreo de seguridad](../cybersecurity/monitoreo_seguridad.md).

## Referencias

- [sshd_config(5)](https://man.openbsd.org/sshd_config) · [ssh_config(5)](https://man.openbsd.org/ssh_config)
- [ssh-keygen(1)](https://man.openbsd.org/ssh-keygen) — claves y certificados
- [Documentación de fail2ban](https://github.com/fail2ban/fail2ban/wiki)
- [Hardening de Linux](../cybersecurity/hardening_linux.md) · [nftables y fail2ban](../cybersecurity/nftables_fail2ban.md)
- [Systemd](systemd.md) · [WireGuard](wireguard.md)
