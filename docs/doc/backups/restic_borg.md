---
title: "Backups Agnósticos: Restic y Borg"
description: "Backup de ficheros con deduplicación y cifrado en cualquier Linux: elegir entre restic y borg, repositorios locales y remotos (SFTP, S3, rest-server), retención, verificación, automatización con systemd y restauraciones que funcionan."
keywords: "restic, borg, borgbackup, backup, deduplicación, cifrado, sftp, s3, rest-server, prune, forget, systemd timer, restore"
tags: ['backups', 'linux']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 20 min
category: Copias de Seguridad
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Shell de Linux y SSH con claves"
  - "systemd básico (units, timers, journalctl)"
  - "[Estrategia de Backup 3-2-1](strategy_321.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Backups Agnósticos: Restic y Borg

## El problema

El backup típico de un homelab es un `rsync` nocturno a un disco USB o a un NAS. Funciona hasta que no: el `rsync` replica el borrado accidental de ayer, el ransomware cifra el origen y a la noche siguiente el destino, y nadie ha probado nunca a restaurar. No hay histórico, no hay cifrado y no hay forma de saber si la copia está íntegra.

`restic` y `borg` resuelven exactamente eso. Los dos parten ficheros en bloques, guardan cada bloque una sola vez (**deduplicación**), cifran todo antes de que salga de la máquina y conservan **snapshots** independientes: puedes volver al estado de hace tres semanas sin que cada copia ocupe el tamaño completo. Son herramientas de línea de comandos, agnósticas del sistema y sin daemon: un binario, un repositorio y un cron.

!!! note "Qué cubre y qué no"
    Aquí se trata el **uso**: crear el repositorio, hacer copias, retener, verificar y restaurar. La regla de cuántas copias y dónde está en [Estrategia 3-2-1](strategy_321.md); la capa de seguridad (repositorios append-only, modelo de amenaza frente a ransomware, pruebas de restauración) vive en [Backup seguro](../cybersecurity/backup_seguro.md). Para máquinas virtuales de Proxmox la herramienta adecuada es [PBS](pbs.md), no esta.

## 📋 Tabla de Contenidos

- [Restic o Borg: cómo elegir](#restic-o-borg-como-elegir)
- [Conceptos comunes](#conceptos-comunes)
- [Restic](#restic)
- [BorgBackup](#borgbackup)
- [Repositorios remotos](#repositorios-remotos)
- [Automatizar con systemd](#automatizar-con-systemd)
- [Bases de datos y contenedores](#bases-de-datos-y-contenedores)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Restic o Borg: cómo elegir

| | Restic | BorgBackup |
|---|---|---|
| Lenguaje / instalación | Go, un binario estático | Python + C; paquete de la distro o binario standalone |
| Destinos | Local, SFTP, S3 y compatibles (MinIO, Ceph RGW), REST server, Azure, GCS, rclone (cualquier cosa) | Local y SSH (**necesita `borg` instalado en el destino**) |
| Cifrado | Siempre activo, no se puede desactivar | Opcional: `repokey`, `keyfile` o `none` |
| Compresión | Sí, desde repos v2 (ver aviso de versión) | Sí, `lz4`, `zstd`, `zlib`, `lzma`, configurable por archivo |
| Varios clientes al mismo repo | Sí, con bloqueos cooperativos | Posible pero desaconsejado: un repo por host |
| Append-only | Vía `rest-server --append-only` o políticas del bucket S3 | Nativo con `borg serve --append-only` |
| Montar como filesystem | `restic mount` (FUSE) | `borg mount` (FUSE) |

Regla práctica: **restic** si el destino es S3/MinIO o quieres varios hosts en un repositorio; **borg** si el destino es un servidor Linux tuyo por SSH y te importa exprimir la compresión. Los dos son maduros y los dos restauran; no hay elección mala, hay elección incoherente con el destino.

## Conceptos comunes

- **Repositorio**: el directorio o bucket donde viven los bloques cifrados. Sin la passphrase es ruido; con ella, todo el histórico.
- **Snapshot** (restic) / **archivo** (borg): el estado de los paths copiados en un instante. Cada uno es completo e independiente a efectos de restauración, aunque en disco solo ocupe los bloques nuevos.
- **Deduplicación por contenido**: los ficheros se parten en trozos de tamaño variable según su contenido, así que mover o renombrar un fichero, o insertar bytes al principio, no provoca que se vuelva a subir entero.
- **Retención**: política de cuántos snapshots conservar (`forget`/`prune`). Sin ella el repositorio crece indefinidamente.
- **Verificación**: comprobar que los bloques siguen ahí y descifran bien (`check`). Un repositorio que no se verifica es una esperanza, no un backup.

!!! danger "La passphrase es el backup"
    Si pierdes la passphrase (o el keyfile de borg) pierdes **todas** las copias, sin excepción ni recuperación. Guárdala en el gestor de contraseñas y en un sitio físico, fuera de la máquina que haces copia. Ver [Gestión de secretos](../cybersecurity/gestion_secretos.md).

## Restic

### Repositorio y credenciales

Restic lee repositorio y passphrase de variables de entorno, lo que evita escribirlas en cada comando y en el historial de la shell:

```bash
# /root/.restic-env  (chmod 600)
export RESTIC_REPOSITORY=/srv/backup/restic
export RESTIC_PASSWORD_FILE=/root/.restic-pass
```

```bash
source /root/.restic-env
restic init
```

`init` crea la estructura del repositorio y pide la passphrase si no la encuentra en el entorno. Para no depender de un fichero en claro, `RESTIC_PASSWORD_COMMAND` acepta un comando que la imprima, por ejemplo una consulta a un gestor de secretos.

### Primer backup y exclusiones

```bash
restic backup /etc /home /srv/app \
    --exclude-file=/root/restic-excludes.txt \
    --one-file-system \
    --tag diario
```

```text
# /root/restic-excludes.txt
/home/*/.cache
/home/*/.local/share/Trash
*.tmp
node_modules
```

`--one-file-system` evita que un montaje olvidado (un NFS o el propio disco de backup) acabe dentro de la copia. Los tags son etiquetas libres que luego sirven para filtrar y para aplicar retenciones distintas.

Restic devuelve código de salida 3 cuando ha podido completar el snapshot pero **algún fichero no se pudo leer** (permisos, fichero desaparecido en pleno backup). Es el caso típico de un script que "funciona" y lleva meses sin copiar un directorio: compruébalo en el log.

```bash
restic snapshots                    # listar snapshots, con host, paths y tags
restic snapshots --tag diario --latest 3
restic ls latest /etc               # contenido de un snapshot
restic diff <id-anterior> <id-nuevo> # qué cambió entre dos snapshots
restic stats                        # tamaño lógico y, con --mode raw-data, el real en disco
```

### Restaurar

```bash
# Todo el último snapshot a un directorio limpio
restic restore latest --target /tmp/restore

# Solo un subárbol
restic restore latest --target /tmp/restore --include /etc/nginx

# El último snapshot de un host concreto
restic restore latest --host servidor-web --target /tmp/restore
```

Para buscar un fichero sin saber en qué snapshot está, monta el repositorio: `restic mount /mnt/restic` expone un árbol con `snapshots/`, `hosts/` y `tags/` navegable con las herramientas normales. Requiere FUSE y deja el proceso en primer plano hasta que lo desmontes.

### Retención: forget y prune

`forget` decide qué snapshots sobran y `prune` elimina los bloques que ya no referencia nadie. Son dos pasos porque el segundo es caro:

```bash
restic forget \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 12 \
    --keep-yearly 2 \
    --prune
```

Las reglas `--keep-*` se suman: un snapshot se conserva si **cualquiera** de ellas lo salva. Por defecto agrupa por host y paths, así que dos servidores en el mismo repositorio tienen retenciones independientes. Prueba la política con `--dry-run` antes de la primera ejecución real.

### Verificar: check

```bash
restic check                        # estructura e índices
restic check --read-data-subset=10% # además, descarga y verifica el 10 % de los datos
restic check --read-data            # todo; caro en S3, imprescindible de vez en cuando
```

`check` sin más es rápido y detecta índices rotos; `--read-data` es lo único que demuestra que los bloques descifran. Un subconjunto distinto cada semana recorre el repositorio entero en unos meses sin pagar la factura de una sola vez.

!!! warning "Compresión y versión del repositorio"
    La compresión de restic requiere repositorios en formato v2, que son los que crea `init` en versiones recientes. Un repositorio antiguo sigue funcionando sin comprimir; migrarlo es posible pero es una operación deliberada. Comprueba `restic version` y la documentación de tu versión antes de depender de la compresión en los cálculos de capacidad.

## BorgBackup

### Repositorio y clave

```bash
export BORG_REPO=/srv/backup/borg
export BORG_PASSCOMMAND="cat /root/.borg-pass"

borg init --encryption=repokey
```

Con `repokey` la clave vive dentro del repositorio, protegida por la passphrase; con `keyfile` vive en `~/.config/borg/keys/` del cliente y **sin ese fichero el repositorio no se abre aunque sepas la passphrase**. En ambos casos exporta la clave y guárdala con la passphrase:

```bash
borg key export $BORG_REPO /root/borg-key-backup.txt
```

### Crear archivos

Cada copia es un *archivo* con nombre dentro del repositorio. Borg expande marcadores como `{hostname}` y `{now}` para no tener que inventar nombres:

{% raw %}

```bash
borg create --stats --progress \
    --compression zstd,3 \
    --exclude-caches \
    --exclude '/home/*/.cache' \
    --one-file-system \
    ::'{hostname}-{now:%Y-%m-%d_%H%M}' \
    /etc /home /srv/app
```

{% endraw %}

`--exclude-caches` salta los directorios marcados con un fichero `CACHEDIR.TAG`, que es como señalan su caché pip, cargo o muchos navegadores. `--stats` imprime al final el tamaño original, comprimido y **deduplicado** del archivo: la última cifra es lo que realmente ha crecido el repositorio.

```bash
borg list                           # archivos del repositorio
borg list ::servidor-2026-10-09_0300 | head
borg info                           # tamaño total y deduplicado del repositorio
```

### Restaurar y montar

`borg extract` descomprime **en el directorio actual**, así que sitúate antes en un destino vacío:

```bash
mkdir -p /tmp/restore && cd /tmp/restore
borg extract ::servidor-2026-10-09_0300 etc/nginx
```

Los paths dentro del archivo se guardan sin la barra inicial (`etc/nginx`, no `/etc/nginx`). Para explorar antes de decidir qué recuperar:

```bash
borg mount ::servidor-2026-10-09_0300 /mnt/borg
ls /mnt/borg/etc
borg umount /mnt/borg
```

### Prune y compact

```bash
borg prune --list \
    --keep-daily=7 \
    --keep-weekly=4 \
    --keep-monthly=12 \
    --glob-archives '{hostname}-*'

borg compact
```

`prune` marca qué archivos sobran; en borg 1.2 y posteriores el espacio **no se libera hasta ejecutar `borg compact`**. Si el repositorio no deja de crecer a pesar de la retención, casi siempre falta ese paso. El filtro `--glob-archives` importa cuando varios hosts comparten repositorio: sin él, la política se aplica sobre todos los archivos mezclados.

!!! warning "Versión de borg"
    Esta página describe borg 1.x. En 1.1 el filtro de `prune` se llamaba `--prefix` y no existía `compact` (el propio `prune` liberaba espacio). Borg 2 cambia la sintaxis de varios comandos y el formato de repositorio. Comprueba `borg --version` en cliente **y servidor**: deben ser compatibles entre sí.

Verificación del repositorio:

```bash
borg check                          # metadatos y consistencia
borg check --verify-data            # descifra y comprueba cada bloque; lento
```

## Repositorios remotos

Lo que no está en otra máquina no es un backup. Opciones por orden de sencillez:

**SFTP (restic) / SSH (borg)**. Un servidor Linux con una cuenta dedicada y clave SSH. Restic solo necesita SFTP en el destino; borg necesita el binario `borg` instalado allí, porque el lado remoto hace trabajo real.

```bash
# restic
export RESTIC_REPOSITORY=sftp:backup@nas.lan:/srv/restic/servidor-web

# borg
export BORG_REPO=ssh://backup@nas.lan/srv/borg/servidor-web
```

**S3 y compatibles (solo restic)**. MinIO, Ceph RGW o un proveedor cloud. Las credenciales van en `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` aunque el destino no sea AWS.

```bash
export RESTIC_REPOSITORY=s3:https://minio.lan:9000/backups-servidor-web
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

Los ajustes de concurrencia y la convivencia de restic con un clúster Ceph se tratan en [Protocolos de almacenamiento](../storage/protocols/protocols.md).

**rest-server (restic)**. El servidor HTTP oficial de restic. Su interés principal es la opción `--append-only`: el cliente puede añadir snapshots pero no borrarlos, así que un atacante con las credenciales del servidor no puede destruir el histórico. La retención se ejecuta entonces **desde el servidor**, no desde el cliente.

**`borg serve` restringido**. El equivalente en borg se configura en el `authorized_keys` del destino:

```text
command="borg serve --restrict-to-repository /srv/borg/servidor-web --append-only",restrict ssh-ed25519 AAAA... backup@servidor-web
```

Esa clave solo puede ejecutar `borg serve` sobre ese repositorio, en modo append-only: no se sobrescriben ni borran datos ya confirmados (`prune` y `delete` siguen permitidos, pero solo marcan; el espacio no se libera sin `borg compact`). Ejecuta `prune` y `compact` desde el lado de confianza. El razonamiento completo, y por qué el append-only es la defensa que de verdad importa frente a ransomware, está en [Backup seguro](../cybersecurity/backup_seguro.md).

## Automatizar con systemd

Un timer de systemd da logs en el journal, `Persistent=true` para recuperar ejecuciones perdidas y un sitio único donde mirar si falló. Mejor que cron para esto; el detalle de units está en [Systemd](../linux/systemd.md).

```ini
# /etc/systemd/system/restic-backup.service
[Unit]
Description=Backup con restic
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/root/.restic-env
ExecStart=/usr/bin/restic backup /etc /home /srv/app --exclude-file=/root/restic-excludes.txt --one-file-system --tag diario
ExecStart=/usr/bin/restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
Nice=10
IOSchedulingClass=idle
```

```ini
# /etc/systemd/system/restic-backup.timer
[Unit]
Description=Backup diario con restic

[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now restic-backup.timer
systemctl list-timers restic-backup.timer
systemctl start restic-backup.service        # ejecución manual para probar
journalctl -u restic-backup.service -n 50
```

`EnvironmentFile` con el fichero de variables no es equivalente a `source`: no admite `export` ni expansiones de shell, solo `CLAVE=valor`. Si el fichero reutiliza el que usas en la shell, quita los `export`. Añade `restic check --read-data-subset=5%` en un segundo timer semanal; no lo metas en el diario, alarga la ventana sin necesidad.

## Bases de datos y contenedores

Copiar los ficheros de datos de una base de datos en marcha produce un backup inconsistente que a veces restaura y a veces no. Haz un volcado lógico y pásalo directamente a la herramienta, sin fichero intermedio:

```bash
# restic lee de stdin y guarda el flujo como un fichero con el nombre indicado
pg_dump -Fc mi_base | restic backup --stdin --stdin-filename mi_base.dump --tag postgres
```

Borg tiene el equivalente en `borg create` con `-` como path (lee de stdin). Con una tubería, si `pg_dump` falla la herramienta no lo detecta y puede guardar un volcado truncado: la documentación recomienda `--stdin-from-command` (restic) y `--content-from-command` (borg). La deduplicación funciona también sobre volcados: un `pg_dump` en formato *custom* sin comprimir deduplica mucho mejor que uno comprimido, porque la compresión destruye las coincidencias entre versiones. Deja que comprima la herramienta de backup. Los backups de PostgreSQL en Docker se detallan en [PostgreSQL](../databases/postgres.md).

Para volúmenes de contenedores, lo más robusto es copiar desde el host el directorio del volumen (`/var/lib/docker/volumes/<nombre>/_data`, o la ruta del bind mount) con el contenedor parado o con la aplicación en un estado consistente. Un contenedor con la base de datos dentro sigue la regla anterior: volcado, no ficheros.

Las máquinas virtuales son otro problema: un backup de ficheros dentro de la VM no restaura la VM. Para Proxmox usa [PBS](pbs.md), que hace copia a nivel de disco con deduplicación propia, y deja restic o borg para los datos dentro de las VMs y para todo lo que no sea Proxmox.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `repository is already locked` (restic) | Una ejecución anterior murió sin liberar el lock | Confirmar que no hay otro restic en marcha y `restic unlock` |
| `Failed to create/acquire the lock` (borg) | Lo mismo en borg | `borg break-lock` solo si estás seguro de que no hay otro proceso |
| El backup termina con código 3 | Algún fichero no se pudo leer (permisos, desapareció a mitad) | Revisar el log; ejecutar como root o excluir lo que cambia constantemente |
| El repositorio crece aunque hay retención | Falta `--prune` (restic) o `borg compact` (borg) | Añadir el paso que falta al timer |
| `borg: command not found` al conectar por SSH | borg no instalado en el servidor remoto, o fuera del `PATH` de sesiones no interactivas | Instalarlo; si está en una ruta rara, `BORG_REMOTE_PATH` |
| Backup muy lento la primera vez por S3 | Normal: todo es nuevo. Las siguientes solo suben bloques nuevos | Limitar con `--limit-upload` si satura la red |
| El timer no se ejecutó a su hora | Máquina apagada; sin `Persistent=true` no se recupera | Añadir `Persistent=true` y revisar `systemctl list-timers` |
| `restic check` avisa de *pack files* sin índice | Backup interrumpido a mitad | `restic repair index` y repetir `check`; si persiste, no ignorarlo |
| Restaura ficheros con `root:root` en vez del dueño original | Restauración ejecutada sin privilegios | Restaurar como root, o aceptar la pérdida de propietario conscientemente |

Los errores de passphrase incorrecta son inequívocos en ambas herramientas y no tienen arreglo técnico: la única pregunta es dónde guardaste la copia de la clave.

## Buenas prácticas

- **Restaura algo cada mes.** Un fichero cualquiera a `/tmp/restore` y comprueba su contenido. Es la única prueba de que el backup existe; todo lo demás es fe.
- **Passphrase y clave fuera de la máquina**, en el gestor de contraseñas y en papel. Con `keyfile` de borg, el fichero de clave también.
- **Retención explícita desde el día uno.** Un repositorio sin `forget`/`prune` o sin `prune`/`compact` es un disco que se llena en silencio.
- **`check` periódico con lectura de datos**, aunque sea un subconjunto. Un repositorio con bloques corruptos no avisa hasta que intentas restaurar.
- **Un repositorio por host (borg)** y, si compartes repositorio en restic, agrupa la retención por host y tags.
- **Append-only cuando el destino lo permita**, con la retención ejecutada desde el servidor. Separa quién escribe de quién borra.
- **Timer de systemd, no cron a pelo**: logs en el journal, `Persistent=true` y un `systemctl status` que dice la verdad.
- **Volcados lógicos para bases de datos**, nunca los ficheros de datos en caliente.
- **Mide el ratio real** con `restic stats --mode raw-data` o `borg info`: lo que de verdad ocupa el repositorio, no el tamaño lógico de las copias.

## Referencias

- [Documentación de restic](https://restic.readthedocs.io/) · [restic en GitHub](https://github.com/restic/restic)
- [rest-server](https://github.com/restic/rest-server)
- [Documentación de BorgBackup](https://borgbackup.readthedocs.io/)
- [Estrategia 3-2-1](strategy_321.md) · [Proxmox Backup Server](pbs.md)
- [Backup seguro: ransomware, append-only y pruebas de restauración](../cybersecurity/backup_seguro.md)
- [Gestión de secretos](../cybersecurity/gestion_secretos.md) · [Systemd](../linux/systemd.md)
- [Protocolos de almacenamiento](../storage/protocols/protocols.md) · [PostgreSQL](../databases/postgres.md)
