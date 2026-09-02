---
title: "nftables + fail2ban — Muralla y portero"
description: "Ruleset nftables persistente con sets y verdict maps, integración real con fail2ban (backend systemd, banaction nftables), jail recidive y filtros propios."
keywords: "nftables, fail2ban, firewall, linux, banaction, recidive, journald, sets, hardening"
tags: ['cybersecurity', 'firewall', 'linux']
updated: 2026-08-03
difficulty: intermediate
estimated_time: 22 min
category: Ciberseguridad
status: published
last_reviewed: 2026-08-03
prerequisites:
  - "Linux intermedio (systemd, journalctl)"
  - "Redes básicas (TCP/IP, puertos)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# nftables + fail2ban — Muralla y portero

## El problema

Abres el puerto 22 a Internet y en menos de una hora tienes miles de intentos de login en los logs. Un firewall bien configurado no ayuda: el 22 **tiene** que estar abierto para que puedas entrar tú. Y fail2ban por sí solo tampoco basta, porque solo reacciona a lo que ya ha llegado.

Las dos piezas son complementarias y la mayoría de guías las tratan por separado: **nftables decide qué puede llegar** (política estática) y **fail2ban decide quién deja de poder** (reacción dinámica ante lo que sí llega). Esta página va sobre cómo encajan de verdad, que es donde fallan casi todas las configuraciones.

!!! note "Relación con otras páginas"
    [Firewall de Red](firewall_red.md) compara UFW, iptables y nftables e introduce Suricata y Zeek. [SSH Hardening](../linux/ssh_security.md) cubre la configuración del propio `sshd`. Aquí se trata **el ruleset persistente y su integración con fail2ban**, que es lo que ninguna de las dos cubre en profundidad.

## 📋 Tabla de Contenidos

- [Un ruleset nftables que se entiende](#un-ruleset-nftables-que-se-entiende)
- [Sets: listas que se consultan en O(1)](#sets-listas-que-se-consultan-en-o1)
- [Aplicar sin quedarte fuera](#aplicar-sin-quedarte-fuera)
- [fail2ban: la parte que suele estar mal](#fail2ban-la-parte-que-suele-estar-mal)
- [La jail recidive](#la-jail-recidive)
- [Filtros propios](#filtros-propios)
- [Operación diaria](#operacion-diaria)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Un ruleset nftables que se entiende

La diferencia práctica frente a iptables no es la sintaxis: es que **el ruleset es un fichero**, se carga atómicamente y se lee de arriba abajo como un programa.

```nft
#!/usr/sbin/nft -f
# /etc/nftables.conf

flush ruleset

table inet filter {
    # Puertos TCP abiertos a todo el mundo
    set public_tcp {
        type inet_service
        elements = { 80, 443 }
    }

    # Redes de confianza para administración
    set admin_nets {
        type ipv4_addr
        flags interval
        elements = { 192.168.1.0/24, 10.8.0.0/24 }
    }

    chain input {
        type filter hook input priority filter; policy drop;

        # 1. Tráfico ya establecido: lo más frecuente, va primero
        ct state established,related accept
        ct state invalid drop

        # 2. Loopback
        iif lo accept

        # 3. ICMP: no lo bloquees entero, rompe PMTU y diagnóstico
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded } accept
        ip6 nexthdr icmpv6 accept

        # 4. Servicios públicos
        tcp dport @public_tcp accept

        # 5. Administración, solo desde redes de confianza
        ip saddr @admin_nets tcp dport 22 accept

        # 6. Lo que llegue aquí se registra antes de caer
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

Tres decisiones que marcan la diferencia:

- **`policy drop` en `input` y `forward`.** Lo que no está permitido, no pasa. La alternativa (`policy accept` con reglas de bloqueo) exige acertar en todo lo que quieres prohibir, para siempre.
- **`ct state established,related accept` en primera posición.** Es la regla que evalúa la inmensa mayoría de los paquetes; ponerla al final significa recorrer todo el ruleset por cada paquete de una conexión ya aceptada.
- **`log` con `limit rate`.** Sin el límite, un escaneo llena `/var/log` y convierte un incidente menor en un disco lleno.

!!! warning "No bloquees todo ICMP"
    Es el reflejo clásico de "ping = peligro". Bloquear `destination-unreachable` rompe el descubrimiento de MTU, y el síntoma es conexiones TCP que se cuelgan a mitad de transferencia con paquetes grandes — un fallo que cuesta días diagnosticar. Ver [MTU/MSS](../networking/mtu_mss_values.md).

## Sets: listas que se consultan en O(1)

Un set es una tabla hash en el kernel. Da igual si tiene 5 elementos o 50 000: el coste de consulta es el mismo. Es exactamente lo que necesitas para listas de bloqueo.

```nft
    # Bloqueo con caducidad automática
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
# Añadir una IP con caducidad propia
sudo nft add element inet filter blackhole '{ 203.0.113.7 timeout 24h }'

# Ver qué hay y cuánto le queda
sudo nft list set inet filter blackhole
```

`flags timeout` hace que el kernel expire las entradas solo: no hay cron que limpiar ni fichero que crezca sin control. Es el mecanismo sobre el que fail2ban trabaja cuando usa el backend nativo.

## Aplicar sin quedarte fuera

El error que todo el mundo comete una vez: cargar un ruleset con `policy drop` que no permite tu SSH, desde SSH.

```bash
# 1. Validar la sintaxis sin aplicar nada
sudo nft -c -f /etc/nftables.conf

# 2. Red de seguridad: restaura el ruleset anterior en 2 minutos
sudo nft list ruleset > /root/nft-backup.conf
sudo systemd-run --on-active=120 --timer-property=AccuracySec=1s \
    nft -f /root/nft-backup.conf

# 3. Ahora sí, aplicar
sudo nft -f /etc/nftables.conf

# 4. Si sigues conectado y todo funciona, cancelar la restauración
sudo systemctl list-timers --all | grep run-
sudo systemctl stop run-rXXXX.timer
```

Persistencia entre reinicios:

```bash
sudo systemctl enable --now nftables
```

## fail2ban: la parte que suele estar mal

La configuración que circula por todas partes lleva años desactualizada en dos puntos que hacen que **la jail no funcione y no te enteres**.

```ini
# /etc/fail2ban/jail.local

[DEFAULT]
# 1. En Debian 12+, Ubuntu 24.04+ y RHEL 9+ no existe /var/log/auth.log:
#    rsyslog ya no se instala por defecto y todo va al journal.
backend  = systemd

# 2. Si tu firewall es nftables, el banaction también debe serlo.
banaction      = nftables-multiport
banaction_allports = nftables-allports

bantime  = 1h
findtime = 10m
maxretry = 5

# Nunca te banees a ti mismo
ignoreip = 127.0.0.1/8 ::1 192.168.1.0/24

[sshd]
enabled = true
mode    = aggressive
```

- **`backend = systemd`**: con `logpath = /var/log/auth.log` sobre una distro moderna, fail2ban arranca, la jail no encuentra el fichero y queda inactiva. `systemctl status fail2ban` sigue en verde. Es un fallo silencioso, que es el peor tipo.
- **`banaction = nftables-multiport`**: con el valor por defecto de iptables sobre un sistema nftables, los baneos se aplican en la capa de compatibilidad `iptables-nft` y conviven mal con tu ruleset. Que funcione a veces es peor que que no funcione nunca.

Comprueba que la jail está viva de verdad:

```bash
sudo fail2ban-client status            # jails activas
sudo fail2ban-client status sshd       # fallos detectados y baneos
```

Si `Currently failed: 0` y `Total failed: 0` tras horas expuesto a Internet, la jail no está leyendo nada. No es que no te ataquen.

## La jail recidive

Un atacante serio no hace 5 intentos y se va: hace 4, espera, vuelve. Nunca dispara `maxretry`. `recidive` vigila el propio log de fail2ban y castiga a quien reincide entre jails.

```ini
[recidive]
enabled  = true
logpath  = /var/log/fail2ban.log
banaction = %(banaction_allports)s
bantime  = 1w
findtime = 1d
maxretry = 3
```

Tres baneos en 24 horas → una semana fuera, y en **todos** los puertos, no solo en el que falló. Es la jail con mejor relación entre esfuerzo y efecto.

!!! note "recidive lee un fichero, no el journal"
    Aunque el resto use `backend = systemd`, `recidive` necesita `/var/log/fail2ban.log`. Verifica que exista y que `logtarget = /var/log/fail2ban.log` esté en `fail2ban.local`; si tu instalación loguea al journal, esta jail no detectará nada.

## Filtros propios

Para cualquier servicio que escriba intentos fallidos en un log: un regex y una jail.

```ini
# /etc/fail2ban/filter.d/miapp.conf
[Definition]
failregex = ^.*Failed login attempt from <HOST>.*$
ignoreregex =
```

```ini
# En jail.local
[miapp]
enabled  = true
port     = http,https
filter   = miapp
logpath  = /var/log/miapp/access.log
maxretry = 5
```

Prueba el regex contra el log real **antes** de activarlo:

```bash
sudo fail2ban-regex /var/log/miapp/access.log /etc/fail2ban/filter.d/miapp.conf
```

La salida dice cuántas líneas casan. Si es 0, el filtro es decorativo. `<HOST>` es la macro que captura la IP: sin ella el filtro no puede banear a nadie.

## Operación diaria

```bash
# Quién está baneado ahora mismo
sudo fail2ban-client status sshd

# Desbanear (el usuario que se ha equivocado tres veces con la clave)
sudo fail2ban-client set sshd unbanip 203.0.113.7

# Banear a mano
sudo fail2ban-client set sshd banip 203.0.113.7

# Ver los baneos en el firewall, desde el otro lado
sudo nft list set inet f2b-table addr-set-sshd
```

Contadores del ruleset, para saber qué regla está haciendo el trabajo:

```bash
sudo nft -a list ruleset          # con handles, para borrar reglas concretas
sudo nft list ruleset | grep -A3 counter
```

Añade `counter` a las reglas que quieras medir; sin esa palabra clave nftables no cuenta nada (a diferencia de iptables, que cuenta siempre).

## Troubleshooting

| Síntoma | Causa | Comprobación |
|---|---|---|
| fail2ban activo pero nunca banea | `backend` incorrecto para la distro | `fail2ban-client status sshd` → `Total failed: 0` |
| Banea pero la IP sigue entrando | `banaction` de iptables sobre nftables | `nft list ruleset \| grep f2b` |
| Te has quedado fuera | Regla de SSH ausente o tras el `drop` | Consola física / KVM; `nft flush ruleset` |
| El filtro propio no detecta nada | Regex sin `<HOST>` o que no casa | `fail2ban-regex` sobre el log real |
| Reglas perdidas al reiniciar | Servicio `nftables` deshabilitado | `systemctl is-enabled nftables` |
| Conexiones que se cuelgan con ficheros grandes | ICMP bloqueado, PMTU roto | `ping -M do -s 1472 <destino>` |

## Buenas prácticas

- **`policy drop` por defecto**, y la regla de `established` la primera.
- **Valida con `nft -c` y arranca siempre con la red de seguridad temporizada.** El coste es un comando; el de no hacerlo es un desplazamiento al datacenter.
- **`backend = systemd` y `banaction = nftables-*`** en cualquier instalación moderna. Copia y pega de guías antiguas es la causa número uno de fail2ban decorativo.
- **`ignoreip` con tu red de administración**, antes de tocar nada más.
- **Activa `recidive`.** Es donde está el retorno.
- **`fail2ban-regex` antes de confiar en un filtro propio.**
- **Alimenta tu monitorización con los baneos.** Un pico de baneos es una señal, no ruido. Ver [monitoreo de seguridad](monitoreo_seguridad.md) y [Wazuh](../monitoring/wazuh_logs.md).
- **El firewall no sustituye a lo demás.** SSH con claves y sin contraseña ([SSH Hardening](../linux/ssh_security.md)) elimina la clase de ataque entera; fail2ban solo reduce el ruido.

## Referencias

- [Wiki oficial de nftables](https://wiki.nftables.org/)
- [Manual de fail2ban](https://github.com/fail2ban/fail2ban/wiki)
- [Firewall de Red](firewall_red.md) · [Hardening Linux](hardening_linux.md)
- [SSH Hardening](../linux/ssh_security.md) · [Monitoreo de Seguridad](monitoreo_seguridad.md)
