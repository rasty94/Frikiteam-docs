---
title: "Simulacro de restauración: probar que el backup vuelve"
description: "Planificar y ejecutar un ensayo de restauración en un homelab: RPO y RTO realistas, qué restaurar, máquina aislada, restic check, borg check y verificación en PBS, PostgreSQL con dump o copia en caliente, cronometrar, registrar el simulacro y automatizar parte con un timer de systemd."
keywords: "simulacro de restauración, restore drill, backup, restic check, read-data-subset, borg check, PBS, qmrestore, pg_restore, RTO, RPO, systemd timer"
tags: ['backups', 'best-practices', 'proxmox', 'troubleshooting']
updated: 2026-11-25
difficulty: intermediate
estimated_time: 27 min
category: Copias de Seguridad
status: published
last_reviewed: 2026-11-25
prerequisites:
  - "[Estrategia de Backup 3-2-1](strategy_321.md)"
  - "Backups funcionando con [restic o Borg](restic_borg.md) o [PBS](pbs.md)"
  - "Una máquina o VM libre para restaurar"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Simulacro de restauración: probar que el backup vuelve

## El problema

Tienes backups. El timer se ejecuta cada noche, el log dice que termina bien y el repositorio crece lo que tiene que crecer. Lo que no sabes es si, el día que se muera el disco, eso se convierte en un servicio funcionando otra vez. ¿Está la contraseña del repositorio en algún sitio que no sea el servidor muerto? ¿El volcado de la base de datos está completo? ¿El `docker-compose.yml` estaba dentro del backup o solo los datos? ¿Cuánto tardas de verdad?

Un backup que nunca se ha restaurado no es un backup: es una hipótesis. La única forma de convertirlo en un hecho es hacer lo mismo que harías en un desastre, en frío, en otra máquina y con el cronómetro en marcha. Eso es un simulacro de restauración, y lo que sigue es cómo prepararlo, ejecutarlo y repetirlo sin que se convierta en un proyecto.

!!! warning "Contrastado con la documentación, sin probar aún en el homelab"
    Los comandos y opciones de esta página están contrastados con la documentación oficial de restic, Borg, Proxmox Backup Server, Proxmox VE y PostgreSQL (enlaces en [Referencias](#referencias)), pero el procedimiento completo todavía no se ha ejecutado en el homelab. Revisa la versión de cada herramienta antes de copiar nada.

!!! note "Qué cubre y qué no"
    Aquí se trata el **ensayo**: qué restaurar, dónde, cómo comprobarlo y cómo dejarlo registrado. La regla 3-2-1 y cómo elegir RPO y RTO están en [Estrategia de Backup 3-2-1](strategy_321.md); cómo hacer los backups, en [Restic y Borg](restic_borg.md) y [PBS](pbs.md); los volcados de PostgreSQL, en [PostgreSQL en Docker](../databases/postgres.md).

## 📋 Tabla de Contenidos

- [Antes del simulacro: RPO y RTO que puedas cumplir](#antes-del-simulacro-rpo-y-rto-que-puedas-cumplir)
- [Qué restaurar](#que-restaurar)
- [Dónde restaurar: una máquina aislada](#donde-restaurar-una-maquina-aislada)
- [Comprobar la integridad del repositorio](#comprobar-la-integridad-del-repositorio)
- [Restaurar un fichero](#restaurar-un-fichero)
- [Restaurar un servicio Docker con PostgreSQL](#restaurar-un-servicio-docker-con-postgresql)
- [Restaurar una VM entera desde PBS](#restaurar-una-vm-entera-desde-pbs)
- [Medir el tiempo real](#medir-el-tiempo-real)
- [Checklist y registro del simulacro](#checklist-y-registro-del-simulacro)
- [Automatizar parte de la verificación](#automatizar-parte-de-la-verificacion)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Antes del simulacro: RPO y RTO que puedas cumplir

Un simulacro sin objetivo solo dice «ha funcionado» o «no ha funcionado». Con objetivo dice si cumples lo que esperabas. Antes de empezar, escribe para cada servicio que vayas a ensayar dos números:

- **RPO**: cuántos datos aceptas perder. Lo marca la frecuencia del backup; un backup diario a las 03:00 da, en el peor caso, casi 24 horas de pérdida.
- **RTO**: cuánto tiempo aceptas estar sin el servicio, contado desde que decides restaurar hasta que el servicio responde.

En un homelab, realista significa con lo que tienes: si la única copia de 800 GB está en almacenamiento de objetos y tu conexión baja a 100 Mbit/s, solo la descarga son horas, y ningún RTO de «media hora» lo arregla. Cómo elegir estos números por tipo de dato está en [Decidir RPO, RTO y retención](strategy_321.md#decidir-rpo-rto-y-retencion). Aquí basta con tenerlos apuntados antes de empezar, porque el simulacro los va a medir.

## Qué restaurar

No hace falta restaurarlo todo cada vez. Tres niveles, de menos a más coste:

| Nivel | Qué se restaura | Qué demuestra | Frecuencia orientativa |
|---|---|---|---|
| **Fichero** | Uno o varios ficheros conocidos | Que el repositorio se abre, la clave funciona y los datos descifran | Semanal, automatizable |
| **Servicio** | Un servicio Docker con su configuración, su volumen y su base de datos | Que el backup incluye todo lo necesario para arrancar, no solo los datos | Mensual o trimestral |
| **Máquina** | Una VM o contenedor entero | Que el RTO de una máquina completa es el que crees | Trimestral o semestral |

Empieza por el servicio que más te dolería perder y que menos has tocado últimamente. Rota cada vez: el servicio que se restauró el último trimestre es justo el que menos sorpresas va a dar.

## Dónde restaurar: una máquina aislada

Restaurar encima del original no es un simulacro, es un riesgo: si algo sale mal, has convertido un ensayo en un incidente. Y restaurar en la misma máquina tampoco prueba lo importante, porque ahí siguen los paquetes instalados, las claves SSH, el fichero de contraseñas del repositorio y la configuración que nunca entró en el backup.

La máquina del simulacro debería cumplir tres condiciones:

1. **Distinta de la original.** Una VM recién instalada en el hipervisor, un portátil viejo o una Raspberry Pi. Lo que no esté en el backup o en tu documentación no debe estar en ella.
2. **Aislada de la red de producción.** Un servicio restaurado puede empezar a enviar correos, a sincronizar contra el mismo bucket o a pelear por la misma IP que el original. Sin red, o en una VLAN o bridge aislado, eso no pasa.
3. **Sin acceso al original durante la prueba.** Si a mitad del ensayo entras en el servidor de producción a copiar un fichero, acabas de encontrar algo que no estaba en el backup. Apúntalo: es el resultado más valioso del simulacro.

La máquina necesita, eso sí, poder leer el repositorio. Si el repositorio es remoto, deja salida solo hacia él; si es local, conecta el disco. Las credenciales salen de donde las tendrías en un desastre (el gestor de contraseñas, el sobre en papel), no del servidor original.

## Comprobar la integridad del repositorio

La integridad dice que los bytes del repositorio están bien. No dice que el servicio arranque, pero es barato y detecta el bit rot antes de que lo descubras restaurando. Conviene hacerlo antes de cada simulacro y, de forma automática, entre simulacros.

**restic.** `check` sin opciones revisa la estructura y los índices; para leer de verdad los datos hay que pedirlo:

```bash
restic check                          # estructura e índices, sin leer los datos
restic check --read-data-subset=1/5   # la primera de cinco partes de los pack files
restic check --read-data-subset=5%    # un 5 % elegido al azar
restic check --read-data              # todos los datos; caro en almacenamiento de objetos
```

Con la forma `n/t`, ejecutar de `1/5` a `5/5` en cinco ejecuciones recorre el repositorio entero. Con un porcentaje o un tamaño (`--read-data-subset=10G`), el subconjunto es aleatorio en cada ejecución. `--read-data` y `--read-data-subset` no se pueden combinar.

**Borg** (sintaxis de Borg 1.4; Borg 2 cambia la forma de indicar el repositorio y varios comandos):

```bash
borg check /ruta/al/repo                                       # repositorio y metadatos de los archivos
borg check --verify-data /ruta/al/repo                         # además descifra y verifica cada bloque
borg check --repository-only --max-duration 3600 /ruta/al/repo # comprobación parcial de una hora
```

`--max-duration` reparte una comprobación larga en varias ejecuciones, cada una continúa donde lo dejó la anterior; exige `--repository-only` y solo hace comprobaciones de checksum, no criptográficas. Para un repositorio remoto por SSH, la parte de repositorio se ejecuta en el servidor y la de archivos en el cliente, que necesita la clave.

**PBS.** La verificación vive en el servidor y se programa como *verify job* (ver [PBS: verificación](pbs.md#verificacion)). Antes del simulacro puedes lanzarla a mano sobre un datastore:

```bash
proxmox-backup-manager verify main --ignore-verified false
```

Por defecto, `verify` se salta los snapshots ya verificados cuya verificación no ha caducado; con `--ignore-verified false` los vuelve a leer todos, así que en un datastore grande tarda.

## Restaurar un fichero

El nivel más simple, y el que conviene automatizar. Restaura algo que sepas cómo debe ser, a un directorio vacío:

```bash
# restic: restaura y vuelve a leer lo restaurado para comprobarlo
restic restore latest --target /srv/simulacro --include /etc/nginx --verify

# Borg 1.4: extrae en el directorio actual
cd /srv/simulacro && borg extract /ruta/al/repo::servidor-2026-11-24 etc/nginx

# PBS: un archivo .pxar de un snapshot del cliente
proxmox-backup-client restore host/servidor/2026-11-24T03:00:00Z etc.pxar /srv/simulacro/etc
```

`--verify` en `restic restore` lee de nuevo los ficheros escritos y los compara con el repositorio. En Borg, `borg extract --dry-run` hace todo el proceso (leer, comprobar el hash, descifrar, descomprimir) sin escribir nada, útil cuando no tienes espacio para extraer. El nombre del snapshot de PBS se copia literalmente de `proxmox-backup-client snapshot list`.

Después, compara con lo que esperas: que el fichero exista, que no esté vacío y que contenga lo que debe. `nginx -t -c /srv/simulacro/etc/nginx/nginx.conf` dice más que un `ls`.

## Restaurar un servicio Docker con PostgreSQL

Aquí aparecen casi todos los fallos reales: el `.env` que no estaba en el backup, la imagen con la etiqueta `latest` que ya no es la misma, los roles que faltan. Supón un servicio con este esquema en `/srv/app`: `docker-compose.yml`, `.env`, los ficheros de la aplicación y, en `dumps/`, el volcado nocturno de PostgreSQL hecho como en [PostgreSQL en Docker](../databases/postgres.md#backups-y-restauracion).

### Dump o copia de ficheros en caliente

La forma en que se respaldó la base de datos decide cómo se restaura, y el simulacro es el momento de descubrir cuál tienes:

| Cómo se respaldó | Cómo se restaura | Qué tener en cuenta |
|---|---|---|
| `pg_dump -Fc` + `pg_dumpall --globals-only` | Base vacía, globals con `psql`, datos con `pg_restore` | Consistente aunque la base estuviera en uso. Es el camino recomendado |
| Copia del directorio de datos con la base **parada** | Se restaura el directorio y se arranca | Válido, pero exige parar la base en cada backup |
| Snapshot atómico del volumen (ZFS, LVM) con la base en marcha | Se restaura el directorio y se arranca | PostgreSQL arranca como tras una caída y reproduce el WAL. Datos y WAL deben estar en el mismo snapshot |
| Copia de ficheros con la base en marcha, sin snapshot | No hay garantía | La documentación de PostgreSQL lo descarta: `tar` o similares no hacen una copia atómica |

Si el simulacro revela que el último caso es el tuyo, no hace falta seguir: cambia el backup a volcados y repite.

### Restaurar desde un volcado

En la máquina aislada, con Docker instalado:

```bash
mkdir -p /srv/simulacro && cd /srv/simulacro
restic restore latest --target /srv/simulacro --include /srv/app

cd /srv/simulacro/srv/app
pg_restore --list dumps/app.dump > /dev/null   # lee el índice del volcado, sin restaurar nada

docker compose up -d db                        # solo la base, con un volumen vacío
docker compose exec -T db psql -U myuser -d postgres < dumps/globals.sql
docker compose exec -T db createdb -U myuser app
docker compose exec -T db pg_restore -U myuser -d app --exit-on-error --no-owner < dumps/app.dump
```

`pg_restore --list` lee el índice del volcado: si el fichero está truncado o corrupto, falla en segundos sin tocar ninguna base. `--exit-on-error` detiene la restauración en el primer error en lugar de continuar y dejar una base a medias que parece buena. Para bases grandes, `pg_restore -j` restaura en paralelo, pero necesita leer el volcado desde un fichero (no desde la entrada estándar), así que hay que copiarlo dentro del contenedor o montarlo.

Con la base restaurada, arranca el resto y comprueba como lo haría un usuario:

```bash
docker compose up -d
docker compose ps                                       # todo en marcha y sano
docker compose exec -T db psql -U myuser -d app -c '\dt'
curl -fsS http://localhost:8080/ > /dev/null && echo "responde"
```

Elige una comprobación de datos que tenga sentido para la aplicación: el número de filas de una tabla principal, el último registro creado o un usuario que sepas que existe. La fecha de ese último registro es, además, tu **RPO real**.

### Restaurar desde una copia de ficheros

Si el backup es un snapshot atómico del directorio de datos, restaura el directorio completo en la ruta que monta el contenedor y arranca solo la base:

```bash
docker compose up -d db
docker compose logs -f db
```

En los logs debería aparecer que el sistema de bases de datos no se cerró correctamente y que inicia la recuperación automática, seguida de que está listo para aceptar conexiones. Si en cambio aparecen errores de ficheros de WAL ausentes o de páginas inválidas, la copia no era consistente. La versión mayor de PostgreSQL de la imagen tiene que coincidir con la del directorio de datos: con otra versión mayor, el servidor se niega a arrancar.

## Restaurar una VM entera desde PBS

Para una VM respaldada en PBS desde Proxmox VE, restaura a un **ID nuevo** y nunca sobre la original. Desde la línea de comandos del nodo PVE:

```bash
pvesm list pbs-storage --vmid 100     # snapshots de la VM 100 en el almacenamiento PBS
qmrestore pbs-storage:backup/vm/100/2026-11-24T03:00:00Z 9100 --storage local-zfs --unique 1
```

`--unique 1` asigna direcciones MAC nuevas para que la copia no choque con la original. Antes de arrancarla, desconecta la red: consulta la línea `net0` con `qm config 9100` y vuelve a fijarla con `link_down=1` añadido, por ejemplo `qm set 9100 --net0 virtio=<MAC>,bridge=vmbr0,link_down=1` con la MAC que muestra `qm config`. Después:

```bash
qm start 9100
# comprobar por la consola de PVE que arranca, que los servicios suben y que los datos están
qm stop 9100
qm destroy 9100 --purge
```

Para contenedores LXC el equivalente es `pct restore`. Si el RTO aprieta, `qmrestore` tiene `--live-restore 1` (solo con PBS): la VM arranca en cuanto empieza la restauración y los datos se leen bajo demanda, con lecturas lentas hasta que termina. Merece la pena medirlo en el simulacro antes de contar con ello en un incidente.

## Medir el tiempo real

El RTO real no es lo que tarda `restic restore`: es todo lo que pasa desde que decides restaurar. Mide por fases, porque la suma suele estar repartida donde no esperabas:

```bash
t0=$(date +%s)
# ... preparar la máquina, recuperar credenciales
t1=$(date +%s)
# ... restaurar los ficheros
t2=$(date +%s)
# ... restaurar la base y arrancar el servicio
t3=$(date +%s)
echo "preparación: $(( (t1-t0)/60 )) min, restauración: $(( (t2-t1)/60 )) min, arranque y comprobación: $(( (t3-t2)/60 )) min"
```

Apunta también lo que no es un comando: el tiempo buscando la contraseña, leyendo tu propia documentación o descargando una imagen de Docker que ya no está en caché. Si el total supera el RTO que escribiste al principio, el simulacro ha cumplido su función: ahora sabes qué parte acortar (una copia local además de la remota, una VM preparada, la documentación más clara).

## Checklist y registro del simulacro

Una lista corta, la misma cada vez:

1. Objetivo escrito: servicio, nivel (fichero, servicio o máquina), RPO y RTO esperados.
2. Máquina aislada preparada, sin acceso al original.
3. Credenciales del repositorio obtenidas de la copia de emergencia, no del servidor.
4. Integridad comprobada (`restic check`, `borg check` o verify de PBS).
5. Restauración hecha siguiendo solo la documentación existente.
6. Comprobación funcional: el servicio responde y los datos tienen sentido.
7. RPO real (fecha del último dato) y RTO real (tiempo total por fases) anotados.
8. Problemas encontrados y acción para cada uno.
9. Máquina del simulacro destruida y datos restaurados borrados.

Y un registro por simulacro, en el mismo repositorio que la documentación del homelab:

```text
Fecha:            2026-11-25
Servicio:         app (Docker + PostgreSQL)
Nivel:            servicio
Snapshot:         latest (2026-11-25 03:00)
Objetivo:         RPO 24 h, RTO 2 h
Resultado:        OK / FALLO / OK con incidencias
RPO real:         último registro 2026-11-24 23:41
RTO real:         preparación __ min, restauración __ min, arranque __ min, total __ min
Problemas:        - .env no estaba en el backup (recuperado del gestor de contraseñas)
Acciones:         - añadir .env a la lista de rutas del backup
Próximo:          2026-12 (otro servicio)
```

El ejemplo de «Problemas» es ilustrativo: es el tipo de hallazgo que conviene anotar. Comparar el tercer registro con el primero es lo que demuestra que el plan mejora.

## Automatizar parte de la verificación

El simulacro completo es manual por diseño: lo que prueba es que una persona puede restaurar con lo que hay. Pero la parte mecánica (integridad, restaurar un fichero, leer el volcado) se puede ejecutar sola cada semana. Un script mínimo:

```bash
#!/usr/bin/env bash
# /usr/local/bin/restore-check.sh
set -euo pipefail
source /etc/restic/env                      # RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

restic check --read-data-subset=5%
restic restore latest --target "$work" --include /srv/app/dumps --verify
pg_restore --list "$work/srv/app/dumps/app.dump" > /dev/null
curl -fsS -m 10 "$PING_URL" > /dev/null     # avisa al monitor de que ha terminado bien
```

`pg_restore` tiene que estar instalado en el host (paquete cliente de PostgreSQL de la misma versión mayor o superior a la del volcado). `PING_URL` es la URL de un monitor de tipo *push*, por ejemplo en [Uptime Kuma](../monitoring/uptime_kuma.md), y puede ir en el mismo fichero de entorno. El servicio y el timer de systemd:

```ini
# /etc/systemd/system/restore-check.service
[Unit]
Description=Verificación semanal de restauración
OnFailure=notify-failure@%n.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/restore-check.sh
```

```ini
# /etc/systemd/system/restore-check.timer
[Timer]
OnCalendar=Sun *-*-* 05:00:00
RandomizedDelaySec=30min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now restore-check.timer
systemctl list-timers restore-check.timer
```

`OnFailure=` cubre el fallo y el ping cubre el silencio: si el timer deja de ejecutarse, el monitor avisa porque el ping no llega. La unit `notify-failure@.service` es la misma que usa [Estrategia de Backup 3-2-1](strategy_321.md#automatizar-y-verificar); un script más completo, con antigüedad del snapshot y comparación de hashes, está en [Backup Seguro](../cybersecurity/backup_seguro.md#automatizar-el-test-periodico). Programa la verificación lejos de la hora del backup para que no compitan por el repositorio.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| No se puede abrir el repositorio en la máquina del simulacro | La contraseña o la clave solo estaban en el servidor original | Guardar la contraseña del repositorio (y la clave de Borg o de PBS si cifra en cliente) en un gestor de contraseñas y en papel, fuera del sitio |
| `restic check` pasa pero la restauración falla al descifrar | `check` sin `--read-data` no lee los datos | Añadir `--read-data-subset` a la verificación periódica |
| El servicio no arranca: falta configuración | `.env`, `docker-compose.yml` o certificados fuera de las rutas del backup | Respaldar el directorio completo del servicio, no solo el volumen de datos |
| `pg_restore` falla con roles inexistentes | Falta el volcado de globals | Añadir `pg_dumpall --globals-only` al backup, o restaurar con `--no-owner` |
| PostgreSQL no arranca con el directorio restaurado | Copia en caliente sin snapshot, o versión mayor de la imagen distinta | Pasar a volcados; fijar la etiqueta de la imagen a la versión mayor |
| La VM restaurada choca con la original en la red | Misma MAC o misma IP | Restaurar con `--unique 1` y arrancar con `link_down=1` |
| El RTO medido es el triple del esperado | Descarga desde la copia remota, imágenes que bajar, documentación incompleta | Copia local para restauraciones habituales; documentar los pasos que faltaron |
| La verificación semanal dejó de ejecutarse y nadie lo notó | Solo hay aviso de fallo, no de ausencia | Ping a un monitor *push* al terminar bien |

## Buenas prácticas

- **Restaura en otra máquina, sin red de producción y sin acceso al original.** Lo que tengas que ir a buscar al servidor original es lo que falta en el backup.
- **Pon números antes de empezar.** RPO y RTO esperados por escrito; el simulacro los confirma o los corrige.
- **Rota el servicio y el nivel.** Un fichero cada semana de forma automática, un servicio cada mes o trimestre, una máquina entera un par de veces al año.
- **Sigue tu documentación al pie de la letra.** Si un paso no está escrito, el simulacro ha encontrado un fallo aunque lo resuelvas de memoria.
- **Fija versiones.** La etiqueta de imagen de la base de datos y la versión de la herramienta de backup forman parte de lo que se restaura.
- **Registra cada simulacro**, incluidos los que salen bien. El registro es lo que convierte «creo que funciona» en «funcionó el día tal, en tanto tiempo».
- **Limpia al terminar.** Una copia restaurada con datos reales olvidada en una VM de pruebas es un problema de seguridad.

## Referencias

- [restic: Checking integrity and consistency](https://restic.readthedocs.io/en/stable/045_working_with_repos.html#checking-integrity-and-consistency)
- [restic: Restoring from backup](https://restic.readthedocs.io/en/stable/050_restore.html)
- [borg check](https://borgbackup.readthedocs.io/en/stable/usage/check.html) · [borg extract](https://borgbackup.readthedocs.io/en/stable/usage/extract.html)
- [Proxmox Backup Server: Backup Client Usage](https://pbs.proxmox.com/docs/backup-client.html) · [proxmox-backup-manager](https://pbs.proxmox.com/docs/proxmox-backup-manager/synopsis.html)
- [qmrestore(1)](https://pve.proxmox.com/pve-docs/qmrestore.1.html) · [qm(1)](https://pve.proxmox.com/pve-docs/qm.1.html) · [Backup and Restore en Proxmox VE](https://pve.proxmox.com/pve-docs/chapter-vzdump.html)
- [PostgreSQL: pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html) · [File System Level Backup](https://www.postgresql.org/docs/current/backup-file.html)
- [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
- [Estrategia de Backup 3-2-1](strategy_321.md) · [Restic y Borg](restic_borg.md) · [PBS](pbs.md) · [Backup Seguro](../cybersecurity/backup_seguro.md)
- [PostgreSQL en Docker](../databases/postgres.md) · [Systemd](../linux/systemd.md)
