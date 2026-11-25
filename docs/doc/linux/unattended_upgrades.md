---
title: "Actualizaciones desatendidas en Debian con unattended-upgrades"
description: "unattended-upgrades en Debian 13 (trixie): qué instala por defecto, Origins-Pattern, lista negra de paquetes, timers apt-daily, reinicio automático controlado, avisos, prueba en seco y qué no conviene actualizar solo."
keywords: "unattended-upgrades, debian, trixie, apt-daily, apt-daily-upgrade, origins-pattern, package-blacklist, automatic-reboot, needrestart, homelab"
tags: ['linux', 'hardening', 'automation', 'best-practices']
updated: 2026-11-25
difficulty: intermediate
estimated_time: 21 min
category: Linux
status: published
last_reviewed: 2026-11-25
prerequisites:
  - "Debian 13 (trixie) con acceso sudo"
  - "systemd básico (units, timers, journalctl)"
  - "[Systemd](systemd.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Actualizaciones desatendidas en Debian con unattended-upgrades

## El problema

Tienes un servidor en casa con Debian que funciona y al que no entras en semanas. Mientras tanto salen avisos de seguridad de OpenSSL, de OpenSSH o de la libc, y el parche está en el repositorio esperando a que alguien escriba `apt upgrade`. Ese alguien eres tú, y no lo vas a hacer cada día.

La solución obvia, un `apt upgrade -y` en un cron, es peor que no hacer nada: actualiza cualquier cosa de cualquier repositorio, no sabe parar si dpkg se queda a medias y no te dice nada. `unattended-upgrades` es la herramienta de Debian para esto: instala solo lo que viene de los orígenes que tú autorizas, deja fuera los paquetes que le digas, registra cada pasada y, si quieres, reinicia a la hora que elijas.

!!! warning "Sin probar todavía en el homelab"
    Este artículo está contrastado con la documentación oficial (el fichero `50unattended-upgrades` del paquete 2.12 de trixie, las units de apt 3.0.4, la wiki de Debian y la guía de administración de Proxmox VE), pero aún no lo he probado en una máquina del homelab. Si algo no se comporta como aquí se describe, abre una errata.

## 📋 Tabla de Contenidos

- [Cómo funciona](#como-funciona)
- [Instalar y activar](#instalar-y-activar)
- [Qué actualiza por defecto](#que-actualiza-por-defecto)
- [Ampliar orígenes con Origins-Pattern](#ampliar-origenes-con-origins-pattern)
- [Lista negra de paquetes](#lista-negra-de-paquetes)
- [Los timers y cómo moverlos](#los-timers-y-como-moverlos)
- [Reinicio automático controlado](#reinicio-automatico-controlado)
- [Avisos: correo y needrestart](#avisos-correo-y-needrestart)
- [Prueba en seco y logs](#prueba-en-seco-y-logs)
- [Qué no conviene actualizar solo](#que-no-conviene-actualizar-solo)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Cómo funciona

Hay tres piezas y conviene no confundirlas:

1. **Dos timers de systemd que trae `apt`**: `apt-daily.timer` lanza `apt-daily.service`, que ejecuta `/usr/lib/apt/apt.systemd.daily update` (refresca listas y, si se le pide, descarga). `apt-daily-upgrade.timer` lanza `apt-daily-upgrade.service`, que ejecuta `apt.systemd.daily install` (instala y limpia).
2. **`/etc/apt/apt.conf.d/20auto-upgrades`**: dice a `apt.systemd.daily` qué hacer en cada pasada. Sin él, los timers se ejecutan pero no actualizan nada.
3. **`/etc/apt/apt.conf.d/50unattended-upgrades`**: la política de `unattended-upgrade`, el programa que de verdad elige e instala los paquetes: de qué orígenes, qué excluir, si reiniciar, a quién avisar.

Si un timer de systemd te suena a chino, la mecánica está en [Systemd: timers](systemd.md#timers-la-alternativa-a-cron). Esta página solo trata lo propio de APT.

## Instalar y activar

En muchas instalaciones de Debian el paquete ya viene, pero no siempre activado. Instalarlo otra vez no hace daño:

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

La pregunta de debconf es «Automatically download and install stable updates?» y su respuesta por defecto es sí. Al aceptar, se escribe `/etc/apt/apt.conf.d/20auto-upgrades` con este contenido:

```text
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

El número es el intervalo en días; `0` lo desactiva. `apt.systemd.daily` admite más claves `APT::Periodic::*` (están documentadas en la cabecera del propio script), por ejemplo `AutocleanInterval` para vaciar la caché de `.deb` obsoletos:

```text
APT::Periodic::AutocleanInterval "7";
```

## Qué actualiza por defecto

La parte activa de `Origins-Pattern` en el `50unattended-upgrades` de trixie es esta:

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

Traducido: **las actualizaciones de seguridad** (`trixie-security`) y **las de la propia versión estable** (`trixie`, que cambia en cada *point release*, la 13.1, 13.2…). No entran `trixie-updates`, `trixie-proposed-updates` ni backports, y nada de repositorios de terceros (Docker, Proxmox, Grafana…). Ojo con esto último: no es «solo seguridad», también te llegan las correcciones de cada revisión menor de Debian, que pasan por el mismo filtro de estabilidad.

`${distro_codename}` lo sustituye el programa por el nombre en clave instalado (`trixie`), así que una actualización de versión mayor (a forky) **nunca** la hace él solo.

## Ampliar orígenes con Origins-Pattern

No edites `50unattended-upgrades`: es un *conffile* del paquete y en cada actualización te preguntará qué hacer con tus cambios. La wiki de Debian propone un fichero propio que se lea después, por ejemplo `52unattended-upgrades-local`. APT lee `apt.conf.d` en orden léxico y, en las listas, **una entrada nueva se suma a las anteriores**; no hace falta copiar todo.

Para añadir `trixie-updates` (correcciones urgentes que no esperan al siguiente *point release*):

```text
// /etc/apt/apt.conf.d/52unattended-upgrades-local
Unattended-Upgrade::Origins-Pattern {
        "origin=Debian,codename=${distro_codename}-updates";
};
```

Cada línea es una lista `clave=valor` separadas por comas, y un paquete entra solo si **todas** coinciden con los metadatos de su repositorio. Las claves aceptadas, según el propio fichero: `a`/`archive`/`suite`, `c`/`component`, `l`/`label`, `o`/`origin`, `n`/`codename` y `site`.

Para un repositorio de terceros, los valores no se adivinan: se leen.

```bash
apt-cache policy
```

Cada repositorio aparece con una línea `release` que lleva sus campos (`o=`, `a=`, `n=`, `l=`, `c=`). Copia los que identifiquen ese origen sin ambigüedad (normalmente `o=` y `n=`) y añade una línea con ellos. Prefiere `codename` a `archive`: el fichero avisa de que el emparejamiento por `archive` («stable») salta en silencio a otra versión cuando la estable cambia.

Si lo que quieres es **sustituir** la lista en vez de ampliarla, `apt.conf(5)` tiene la orden `#clear`:

```text
#clear Unattended-Upgrade::Origins-Pattern;
Unattended-Upgrade::Origins-Pattern {
        "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
};
```

Así el equipo solo recibe seguridad, sin las *point releases*.

## Lista negra de paquetes

`Unattended-Upgrade::Package-Blacklist` es una lista de **expresiones regulares de Python** que se comparan con `re.match`, es decir, desde el principio del nombre. Los ejemplos del fichero original lo dejan claro:

```text
Unattended-Upgrade::Package-Blacklist {
    // todo lo que empiece por linux-
    "linux-";
    // con $ marcas el final: sin él, "libc6" casaría también libc6-dev
    "libc6$";
    // los caracteres especiales se escapan
    "libstdc\+\+6$";
};
```

En un servidor casero con PostgreSQL y MariaDB instalados desde Debian, el `52unattended-upgrades-local` quedaría así:

```text
Unattended-Upgrade::Package-Blacklist {
    "postgresql-";
    "mariadb-";
};
```

Los paquetes en lista negra siguen apareciendo en `apt list --upgradable`; los actualizas tú cuando tengas un rato y una copia de seguridad reciente. Existe también la opción contraria, `Package-Whitelist` (con `Package-Whitelist-Strict`), para actualizar solo una lista cerrada, pero en un servidor normal la lista negra es más fácil de mantener.

!!! tip "apt-mark hold no es lo mismo"
    `apt-mark hold paquete` bloquea el paquete para todo el sistema, incluido tu `apt upgrade` manual. La lista negra solo afecta a las pasadas desatendidas.

## Los timers y cómo moverlos

Las units que trae apt 3.0.4 en trixie:

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

La descarga cae en cualquier momento del día por el retraso aleatorio de 12 horas; la instalación, entre las 06:00 y las 07:00. `Persistent=true` hace que, si el equipo estaba apagado a esa hora, la pasada se ejecute al arrancar. Ambos servicios llevan `ConditionACPower=true`, de modo que en un portátil con batería no hacen nada.

Para mover la instalación a las 04:00, la wiki de Debian recomienda un drop-in con `systemctl edit`:

```bash
sudo systemctl edit apt-daily-upgrade.timer
```

```ini
[Timer]
OnCalendar=
OnCalendar=04:00
RandomizedDelaySec=15m
```

El `OnCalendar=` vacío borra el valor original; sin él tendrías dos horas de disparo. Comprueba el resultado:

```bash
systemctl list-timers 'apt-daily*'
systemctl cat apt-daily-upgrade.timer
```

No quites del todo el retraso aleatorio de `apt-daily.timer`: la wiki recuerda que existe para repartir la carga sobre los servidores de Debian.

## Reinicio automático controlado

Un kernel nuevo no sirve de nada hasta que reinicias. En Debian, el paquete instala un hook en `/etc/kernel/postinst.d/unattended-upgrades` que crea `/var/run/reboot-required` (y apunta el paquete en `reboot-required.pkgs`) cada vez que se instala un kernel. Con estas opciones, `unattended-upgrade` lo detecta al terminar:

```text
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
Unattended-Upgrade::Automatic-Reboot-Time "05:00";
```

- `Automatic-Reboot` está a `false` por defecto. El propio fichero lo advierte: reinicia **sin confirmación**.
- `Automatic-Reboot-WithUsers` vale `true` por defecto; a `false`, no reinicia si hay alguien con sesión abierta y lo deja en el log.
- `Automatic-Reboot-Time` vale `now` por defecto. Internamente se ejecuta `/sbin/shutdown -r <hora>`, así que un reinicio programado se cancela con `sudo shutdown -c`.

Encaja las horas con el timer: si la instalación empieza a las 04:00 con hasta 15 minutos de retraso, un reinicio a las 05:00 deja margen. Si la instalación tarda más que eso, la orden de reinicio se emitirá después de la hora prevista; revisa en los logs cuánto dura una pasada normal antes de apretar.

## Avisos: correo y needrestart

`unattended-upgrade` puede mandar un resumen por correo:

```text
Unattended-Upgrade::Mail "root";
Unattended-Upgrade::MailReport "only-on-error";
```

`MailReport` acepta `always`, `only-on-error` u `on-change`. El envío usa `/usr/bin/mail` o `/usr/sbin/sendmail`; si no existe ninguno, el programa lo registra como error y sigue. En la práctica necesitas un MTA que sepa sacar el correo de casa (un relé SMTP hacia tu proveedor), porque un `root` local que nadie lee no avisa de nada.

Para las bibliotecas actualizadas que siguen cargadas en servicios en marcha está `needrestart` (3.11 en trixie). Se engancha a APT y, tras cada instalación, busca procesos que usan ficheros ya sustituidos. Su configuración por defecto es interactiva, y el propio fichero avisa de que, cuando lo ejecuta `unattended-upgrades` sin terminal, **cae a modo lista**: informa, no reinicia nada. Si quieres que reinicie servicios solo, se cambia en un fichero de `/etc/needrestart/conf.d/`:

```perl
# /etc/needrestart/conf.d/50-auto.conf
$nrconf{restart} = 'a';
```

Antes de hacerlo, revisa en `/etc/needrestart/needrestart.conf` la lista `override_rc`: ahí están los servicios que nunca reinicia por defecto (dbus, gestores de red, VPN…). Para consultar a mano qué falta por reiniciar sin tocar nada:

```bash
sudo needrestart -r l      # solo lista
sudo needrestart -b        # salida para scripts, sin reiniciar
```

## Prueba en seco y logs

Antes de fiarte de la configuración, simula una pasada:

```bash
sudo unattended-upgrade --dry-run --debug
```

`--dry-run` simula sin instalar; con `--debug` verás los orígenes permitidos, la lista negra inicial y la decisión sobre cada paquete. En modo simulación no escribe el log, solo saca la información por pantalla. `unattended-upgrades` (con s) es un enlace al mismo programa.

Los logs de las pasadas reales:

| Fichero | Qué contiene |
|---|---|
| `/var/log/unattended-upgrades/unattended-upgrades.log` | Decisiones: orígenes, paquetes elegidos, retenidos, reinicio |
| `/var/log/unattended-upgrades/unattended-upgrades-dpkg.log` | La salida de dpkg de cada instalación |
| `/var/log/unattended-upgrades/unattended-upgrades-shutdown.log` | El servicio que espera a terminar antes de apagar |
| `/var/log/apt/history.log` | El historial normal de APT, también con las pasadas desatendidas |

Y el journal de los timers:

```bash
journalctl -u apt-daily.service -u apt-daily-upgrade.service --since today
```

## Qué no conviene actualizar solo

**El host de Proxmox VE.** La guía de administración de Proxmox dice que se actualice con `apt full-upgrade` y avisa de que un `apt upgrade` puede dejar el sistema a medio actualizar, porque no puede eliminar paquetes para resolver dependencias. `unattended-upgrades` tampoco los elimina. Con la configuración por defecto, el repositorio de Proxmox no está entre los orígenes permitidos, así que los paquetes de Proxmox y sus kernels (`proxmox-kernel-*`) no se tocan; no lo añadas. Y en un hipervisor deja `Automatic-Reboot` en `false`: reiniciar el host es reiniciar todas las VM y contenedores. La parte de seguridad de Debian puede seguir desatendida, aunque mi recomendación en un host de Proxmox es actualizarlo a mano desde la interfaz o con `apt full-upgrade`, tras leer qué cambia. Más contexto en [Proxmox VE](../proxmox/proxmox_base.md).

**Bases de datos.** Una actualización de PostgreSQL 17 o MariaDB 11.8 dentro de trixie es una versión menor y suele ser segura, pero el paquete puede reiniciar el servicio en mitad de la noche y, si algo falla, te enteras por la mañana. Mételas en la lista negra y actualízalas tú tras un backup. Si corren en contenedores ([PostgreSQL en Docker](../databases/postgres.md)), APT no las toca: su actualización va por la imagen.

**Cualquier cosa de la que dependa otra máquina sin redundancia.** El router virtual, el DNS de la casa, el servidor de la VPN: si no tienes segunda instancia, que se reinicien cuando tú estés delante.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| Los timers corren pero nunca se instala nada | Falta `20auto-upgrades` o tiene `Unattended-Upgrade "0"` | `dpkg-reconfigure -plow unattended-upgrades` |
| Un paquete con actualización no se instala | Su origen no casa con `Origins-Pattern` o está en la lista negra | `--dry-run --debug` y comparar con `apt-cache policy` |
| Tus cambios no se aplican | Editaste una copia en otro nombre que se lee antes, o hay un `#clear` posterior | `apt-config dump \| grep Unattended-Upgrade` |
| No llega ningún correo | No hay `/usr/bin/mail` ni `/usr/sbin/sendmail`, o el MTA no sabe enviar fuera | Revisar el error en `unattended-upgrades.log` y probar `mail` a mano |
| No reinicia tras un kernel nuevo | `Automatic-Reboot` en `false`, o `WithUsers` en `false` con sesiones abiertas | Ver el aviso en el log; `ls /var/run/reboot-required` |
| La pasada se queda a medias tras un corte | dpkg interrumpido | `AutoFixInterruptedDpkg` (activo por defecto) lo reintenta en la siguiente; a mano, `dpkg --configure -a` |
| En un portátil no actualiza nunca | `ConditionACPower=true` y `OnlyOnACPower` | Enchufarlo o, asumiendo el riesgo, lo que explica la wiki |

`apt-config dump` imprime la configuración ya combinada de todos los ficheros, que es lo que de verdad lee `unattended-upgrade`.

## Buenas prácticas

- **Un fichero propio** (`52unattended-upgrades-local`) con solo tus cambios, versionado y desplegado con [Ansible](../ansible/ansible_base.md) si tienes más de un equipo.
- **Prueba en seco tras cada cambio** de orígenes o lista negra.
- **Seguridad siempre; lo demás, con criterio.** Añadir orígenes de terceros es aceptar sus fallos sin estar delante.
- **Reinicio automático solo donde un reinicio no duele**, y a una hora que encaje con el timer de instalación.
- **Que alguien lea los avisos.** Un correo `only-on-error` que llega de verdad vale más que un `always` que se pierde.
- **Combínalo con el resto del bastionado**: ver [Hardening de servidores Linux](../cybersecurity/hardening_linux.md) y [Seguridad SSH](ssh_security.md).

## Referencias

- [50unattended-upgrades.Debian en el paquete 2.12 (trixie)](https://sources.debian.org/src/unattended-upgrades/2.12/data/50unattended-upgrades.Debian/)
- [unattended-upgrade(8)](https://manpages.debian.org/trixie/unattended-upgrades/unattended-upgrade.8.en.html) · [apt.conf(5)](https://manpages.debian.org/trixie/apt/apt.conf.5.en.html)
- [Units apt-daily de apt 3.0.4](https://sources.debian.org/src/apt/3.0.4/debian/) (incluye `apt.systemd.daily` con las claves `APT::Periodic`)
- [Wiki de Debian: PeriodicUpdates](https://wiki.debian.org/PeriodicUpdates)
- [needrestart 3.11 en trixie](https://sources.debian.org/src/needrestart/3.11-1/ex/needrestart.conf/)
- [Guía de administración de Proxmox VE, apartado «System Software Updates»](https://pve.proxmox.com/pve-docs/pve-admin-guide.html)
- [Systemd](systemd.md) · [Hardening de servidores Linux](../cybersecurity/hardening_linux.md)
