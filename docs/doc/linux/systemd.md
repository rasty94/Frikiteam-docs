---
title: "Systemd: Gestión de Servicios"
description: "Units, timers, drop-ins, sandboxing y journalctl en systemd: cómo ejecutar, supervisar y endurecer servicios propios en un servidor o homelab Linux."
keywords: "systemd, systemctl, journalctl, unit, timer, drop-in, sandboxing, systemd-analyze, servicio, homelab"
tags: ['linux', 'systemd']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 20 min
category: Linux
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Terminal Linux con permisos de sudo"
  - "Conocimientos básicos de procesos y usuarios Linux"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Systemd: Gestión de Servicios

## El problema

Dejaste un script en una sesión `tmux`, o lo lanzaste desde `/etc/rc.local`, o con un `nohup` que funcionó "de momento". Un día el servidor se reinicia, el script no vuelve, nadie se entera hasta que alguien pregunta por qué no hay backups desde hace tres semanas. Y cuando por fin lo investigas no hay logs, ni código de salida, ni forma de saber quién lo mató.

Systemd es el PID 1 de casi cualquier distribución moderna y ya está supervisando todo lo demás. Convertir tu script en una *unit* le da arranque automático, reinicios con criterio, dependencias, logs centralizados y aislamiento del sistema por unas pocas líneas de configuración.

!!! note "Qué cubre y qué no"
    Esta página trata **servicios y timers propios**: escribirlos, depurarlos y endurecerlos. Para contenedores como servicios, ver [Podman Quadlet](../docker/quadlets.md), que se apoya en todo lo que aquí se explica.

## 📋 Tabla de Contenidos

- [Cómo funciona](#como-funciona)
- [Crear un servicio propio](#crear-un-servicio-propio)
- [Comandos del día a día](#comandos-del-dia-a-dia)
- [Dependencias y orden de arranque](#dependencias-y-orden-de-arranque)
- [Política de reinicio](#politica-de-reinicio)
- [Modificar units con drop-ins](#modificar-units-con-drop-ins)
- [Timers: la alternativa a cron](#timers-la-alternativa-a-cron)
- [Logs con journalctl](#logs-con-journalctl)
- [Sandboxing y hardening](#sandboxing-y-hardening)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Cómo funciona

Systemd trabaja con *units*, ficheros de texto declarativos cuyo sufijo indica el tipo: `.service` (un proceso), `.timer` (activación programada), `.socket`, `.mount`, `.target` (agrupación de units, equivalente a los antiguos runlevels), entre otros.

Las units viven en tres sitios, de menor a mayor prioridad:

| Ruta | Quién la gestiona | Para qué |
|------|-------------------|----------|
| `/usr/lib/systemd/system/` | El paquete de la distro | Units del sistema; no se editan a mano |
| `/etc/systemd/system/` | Tú | Units propias y *overrides* de las del paquete |
| `/run/systemd/system/` | Systemd, en tiempo de ejecución | Units transitorias, desaparecen al reiniciar |

Systemd lee los ficheros al arrancar o en `daemon-reload`, no cada vez que consultas el estado. Editar una unit sin recargar no cambia nada: `systemctl status` avisa de que la unit ha cambiado en disco.

## Crear un servicio propio

Para ejecutar un script o binario como servicio, crea un archivo en `/etc/systemd/system/mi-servicio.service`:

```ini
[Unit]
Description=Mi Servicio Personalizado
After=network.target

[Service]
Type=simple
User=mi_usuario
ExecStart=/usr/bin/python3 /home/mi_usuario/script.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Qué hace cada bloque:

- **`[Unit]`**: metadatos y relaciones con otras units (descripción, orden, dependencias).
- **`[Service]`**: cómo se ejecuta el proceso. `Type=simple` asume que `ExecStart` es el proceso principal y se queda en primer plano; es lo correcto para casi cualquier script o binario que no haga *fork* a segundo plano. `User=` evita que corra como root.
- **`[Install]`**: qué ocurre con `systemctl enable`. `WantedBy=multi-user.target` lo engancha al arranque normal de un servidor.

`ExecStart` exige **ruta absoluta** al ejecutable. No hay `PATH` de shell ni expansión de `~`, pipes o redirecciones: si necesitas una shell, invócala de forma explícita con `/bin/sh -c '...'`.

Para pasar variables sin escribirlas en la unit, apunta a un fichero de entorno:

```ini
[Service]
EnvironmentFile=/etc/mi-servicio/env
WorkingDirectory=/opt/mi-servicio
ExecStart=/opt/mi-servicio/bin/app --config /etc/mi-servicio/config.yml
```

El fichero `env` contiene líneas `CLAVE=valor`. Restringe su lectura (`chmod 600`, propietario root) si guarda credenciales; ver [gestión de secretos](../cybersecurity/gestion_secretos.md).

!!! warning "`Type=` según el programa"
    Si el programa se demoniza solo (hace *fork* y el proceso original termina), `Type=simple` hará que systemd lo dé por muerto. Lo habitual hoy es lo contrario: configurar el programa para que se quede en primer plano. `Type=notify` solo sirve si el programa avisa a systemd con `sd_notify`; consulta su documentación antes de usarlo.

## Comandos del día a día

Tras crear o editar un fichero hay que recargar y, la primera vez, habilitar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mi-servicio
```

`enable` crea el enlace del `[Install]` para el próximo arranque; `--now` además lo inicia ya. Resto de operaciones habituales:

- `systemctl start mi-servicio`: Iniciar.
- `systemctl stop mi-servicio`: Detener.
- `systemctl restart mi-servicio`: Parar y arrancar (corta el servicio).
- `systemctl reload mi-servicio`: Recargar configuración sin parar, solo si la unit define `ExecReload=`.
- `systemctl enable mi-servicio`: Habilitar al arranque.
- `systemctl disable mi-servicio`: Quitarlo del arranque.
- `systemctl status mi-servicio`: Ver estado y logs recientes.
- `systemctl list-units --failed`: Listar todo lo que ha fallado.
- `journalctl -u mi-servicio -f`: Ver logs en tiempo real.

`status` muestra si está `active (running)`, `failed` o `inactive`, el PID principal, el árbol de procesos hijos y las últimas líneas del journal. Es el primer comando ante cualquier incidencia.

## Dependencias y orden de arranque

Hay dos ejes independientes y confundirlos es el error más frecuente:

- **Orden**: `After=` y `Before=` solo dicen quién arranca antes. No arrancan nada.
- **Requisito**: `Wants=` (dependencia blanda) y `Requires=` (dura) arrastran otra unit al arrancar. Sin `After=`, se inician en paralelo.

Para un servicio que necesita red y una base de datos local:

```ini
[Unit]
Description=Aplicación que necesita base de datos
Wants=network-online.target
After=network-online.target postgresql.service
Requires=postgresql.service
```

`network.target` solo indica que la pila de red está configurada, no que haya conectividad. Si tu servicio necesita resolver DNS o alcanzar un NFS al arrancar, usa `network-online.target` con `Wants=`. Requiere que el servicio que espera a la red (NetworkManager o systemd-networkd) tenga activado su "wait-online"; compruébalo en tu distribución.

Con `Requires=`, si la dependencia se para o falla, tu servicio también se para. Si prefieres que sobreviva a reinicios de la otra unit, usa `Wants=`.

## Política de reinicio

`Restart=always` reinicia siempre, incluso tras un `exit 0`. Suele ser demasiado. Estas son las opciones más útiles:

| Valor | Reinicia cuando |
|-------|-----------------|
| `no` | Nunca (valor por defecto) |
| `on-failure` | Código de salida distinto de 0, señal no limpia o timeout |
| `on-abnormal` | Señal o timeout, pero no por un código de salida distinto de 0 |
| `always` | Siempre, salvo parada explícita con `systemctl stop` |

Para un daemon de larga vida, `on-failure` con una pausa es lo más sano:

```ini
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Restart=on-failure
RestartSec=5
```

`StartLimitIntervalSec` y `StartLimitBurst` pertenecen a `[Unit]`: si la unit arranca más de 5 veces en 300 segundos, systemd deja de intentarlo y la marca como `failed`. Sin ese límite un servicio roto en bucle es ruido constante en el journal y CPU desperdiciada. Para sacarlo de ese estado hace falta `systemctl reset-failed mi-servicio`.

## Modificar units con drop-ins

Nunca edites los ficheros de `/usr/lib/systemd/system/`: una actualización del paquete los pisa. Un *drop-in* es un fichero adicional que sobrescribe o añade directivas y sobrevive a las actualizaciones. Lo más cómodo:

```bash
sudo systemctl edit nginx
```

Abre un editor sobre `/etc/systemd/system/nginx.service.d/override.conf` y, al guardar, recarga systemd por ti. Solo escribes lo que cambia:

```ini
[Service]
Restart=on-failure
RestartSec=5
LimitNOFILE=65536
```

Dos cosas a tener en cuenta:

- **Directivas de lista** como `ExecStart=`: un drop-in las *añade*. Para reemplazar, vacía primero con una línea `ExecStart=` y escribe después la nueva.
- `systemctl edit --full nginx` copia la unit entera a `/etc/systemd/system/`, que a partir de ahí ignora cualquier cambio del paquete. Úsalo solo si el override no es suficiente.

Para ver el resultado combinado de unit más drop-ins:

```bash
systemctl cat nginx
```

Y para volver al comportamiento original basta con `sudo systemctl revert nginx`, que borra los overrides de `/etc`.

## Timers: la alternativa a cron

Un timer es una unit `.timer` que activa una `.service` del mismo nombre. Frente a cron, cada ejecución queda en el journal con su código de salida, hereda el sandboxing y las dependencias, y puedes lanzarla a mano con `systemctl start`.

Un backup nocturno, en dos ficheros. El servicio, `/etc/systemd/system/backup.service`:

```ini
[Unit]
Description=Backup nocturno

[Service]
Type=oneshot
User=backup
ExecStart=/usr/local/bin/backup.sh
```

`Type=oneshot` indica que el proceso termina por sí mismo. No lleva `[Install]` porque lo activa el timer. Y `/etc/systemd/system/backup.timer`:

```ini
[Unit]
Description=Ejecuta el backup cada noche

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

- `OnCalendar=` usa un formato propio de systemd, no el de cron.
- `Persistent=true` ejecuta una pasada perdida si el equipo estaba apagado a la hora prevista. Muy útil en un homelab que no está siempre encendido.
- `RandomizedDelaySec=` reparte la carga cuando muchos hosts programan la misma hora.

Se habilita el **timer**, no el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer
systemctl list-timers
```

`list-timers` muestra cuándo se ejecutó por última vez y cuándo toca la siguiente. Para validar una expresión de calendario antes de fiarte de ella existe `systemd-analyze calendar "*-*-* 03:00:00"`, que imprime la forma normalizada y la próxima ocurrencia. Para ver qué backup hace con la herramienta, consulta [Restic y Borg](../backups/restic_borg.md).

## Logs con journalctl

Todo lo que el servicio escriba en stdout y stderr acaba en el journal, sin configurar nada. Combinaciones útiles:

```bash
journalctl -u mi-servicio                 # todo el histórico de la unit
journalctl -u mi-servicio -f              # seguir en vivo
journalctl -u mi-servicio -b              # solo desde el último arranque
journalctl -u mi-servicio --since "1 hour ago"
journalctl -u mi-servicio -p err          # solo prioridad error o peor
journalctl -xeu mi-servicio               # final del log con explicaciones
```

El journal es binario y, según la distribución, **no es persistente** por defecto: si `/var/log/journal/` no existe, se pierde al reiniciar. Para conservarlo, crea ese directorio o fija `Storage=persistent` en `/etc/systemd/journald.conf` y reinicia `systemd-journald`. Limita su tamaño con `SystemMaxUse=` en ese mismo fichero; `journalctl --disk-usage` indica cuánto ocupa.

Un servicio que escribe a su propio fichero de log debería escribir a stdout y dejar que el journal haga el resto; si necesitas reenviarlo a un stack central, consulta [monitoreo de seguridad](../cybersecurity/monitoreo_seguridad.md).

## Sandboxing y hardening

Un servicio normal ve todo el sistema de ficheros, puede escalar privilegios y hablar con cualquier socket. Systemd ofrece directivas que recortan eso sin tocar la aplicación. Punto de partida razonable para un servicio de red que corre como usuario no privilegiado:

```ini
[Service]
User=mi_usuario
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/mi-servicio
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
```

| Directiva | Efecto |
|-----------|--------|
| `NoNewPrivileges=true` | El proceso y sus hijos no pueden ganar privilegios (setuid, capabilities) |
| `PrivateTmp=true` | `/tmp` y `/var/tmp` propios, invisibles para el resto del sistema |
| `ProtectSystem=strict` | Todo el sistema de ficheros en solo lectura salvo `/dev`, `/proc` y `/sys` |
| `ProtectHome=true` | `/home`, `/root` y `/run/user` inaccesibles |
| `ReadWritePaths=` | Excepciones de escritura para `ProtectSystem=strict` |
| `StateDirectory=` | Crea y asigna `/var/lib/<nombre>` al usuario del servicio, ya escribible |

`ProtectSystem=strict` es la que más rompe cosas: cualquier ruta donde la aplicación escriba (datos, sockets, caches) debe declararse con `ReadWritePaths=` o, mejor, con `StateDirectory=`, `CacheDirectory=` o `LogsDirectory=`. Si el servicio no arranca tras activarla, el mensaje del journal suele nombrar la ruta con permiso denegado.

Para medir cuánto expone una unit, systemd incluye un analizador:

```bash
systemd-analyze security mi-servicio
```

Muestra una tabla con cada directiva evaluada y una puntuación global de exposición, de `UNSAFE` a `SAFE`. No pretende llegar a cero: sirve para ver qué falta y comparar antes y después. El detalle exacto de la salida y de las directivas disponibles depende de la versión de systemd instalada, así que contrasta con `man systemd.exec` en tu sistema.

!!! warning "Dependiente de la versión"
    Algunas directivas de sandboxing (por ejemplo, las de filtrado de llamadas al sistema como `SystemCallFilter=`, o `ProtectProc=`) han ido apareciendo en versiones concretas. Una directiva desconocida se ignora con un aviso en el journal, así que activarla no garantiza que esté haciendo algo.

El mismo enfoque de mínimo privilegio aplica a todo el sistema; ver [hardening de Linux](../cybersecurity/hardening_linux.md).

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---------|----------------|---------|
| `Unit mi-servicio.service not found` | Fichero en ruta incorrecta o sin `daemon-reload` | Comprueba la ruta y el sufijo `.service`; ejecuta `systemctl daemon-reload` |
| `status` avisa de que la unit cambió en disco | Se editó sin recargar | `systemctl daemon-reload` y reiniciar el servicio |
| Estado `failed` con `status=203/EXEC` | `ExecStart` apunta a una ruta inexistente o sin permiso de ejecución | Usa ruta absoluta, verifica `chmod +x` y el shebang del script |
| `start request repeated too quickly` | Superado `StartLimitBurst` | Arregla la causa, luego `systemctl reset-failed mi-servicio` |
| El servicio arranca y se para al instante | Proceso que hace *fork* con `Type=simple` | Configúralo para correr en primer plano o ajusta `Type=` según su documentación |
| Funciona a mano, falla como servicio | Entorno distinto: sin `PATH` de shell, sin HOME, otro usuario | Rutas absolutas, `Environment=`/`EnvironmentFile=`, `WorkingDirectory=` |
| `Permission denied` tras añadir `ProtectSystem=strict` | La app escribe en una ruta de solo lectura | Declárala con `ReadWritePaths=` o `StateDirectory=` |
| El timer no dispara | Se habilitó el `.service` en vez del `.timer`, o `OnCalendar` mal escrito | `systemctl list-timers`, valida con `systemd-analyze calendar` |
| Arranca antes que la red | Falta `After=network-online.target` | Añade `Wants=` y `After=` de esa target |

Pasos generales de diagnóstico: `systemctl status`, luego `journalctl -xeu <unit>`, y por último reproducir el comando de `ExecStart` a mano con el mismo usuario (`sudo -u mi_usuario ...`). `systemd-analyze verify /etc/systemd/system/mi-servicio.service` detecta errores de sintaxis y directivas desconocidas antes de arrancar.

## Buenas prácticas

- **Usuario dedicado, nunca root.** Un servicio comprometido hereda los permisos de quien lo ejecuta.
- **Los cambios van en `/etc/systemd/system/` o en drop-ins**, versionados en Git y desplegados con [Ansible](../ansible/ansible_base.md). Nada en `/usr/lib`.
- **`Restart=on-failure` con `RestartSec` y `StartLimitBurst`** en lugar de `Restart=always` a pelo.
- **Timers antes que cron** para todo lo que quieras observar, reintentar o aislar.
- **Sandboxing desde el primer día.** Añadir `NoNewPrivileges`, `PrivateTmp` y `ProtectSystem` es barato al crear el servicio y doloroso de retrofitear.
- **Los secretos, en `EnvironmentFile=` con permisos 600** o en credenciales de systemd, nunca dentro de la unit, que es legible por todos.
- **Journal persistente y con tope de tamaño** para que los logs sobrevivan a un reinicio sin llenar el disco.

## Referencias

- [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) · [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) — directivas de sandboxing
- [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) · [systemd-analyze(1)](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html)
- [Podman Quadlet](../docker/quadlets.md) · [Hardening de Linux](../cybersecurity/hardening_linux.md)
- [Seguridad SSH](ssh_security.md) · [WireGuard](wireguard.md)
