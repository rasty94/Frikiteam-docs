---
title: "PostgreSQL en Docker"
description: "Desplegar y operar PostgreSQL en contenedores sobre infraestructura propia: Compose con secretos, roles y pg_hba.conf, ajuste de memoria y conexiones, diagnóstico con pg_stat_activity y EXPLAIN ANALYZE, backups con pg_dump y actualizaciones mayores."
keywords: "postgresql, postgres, docker, compose, pg_dump, pg_restore, pg_hba.conf, shared_buffers, work_mem, max_connections, roles, explain analyze, pg_stat_activity, backup, quadlet"
tags: ['databases', 'docker']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 21 min
category: Bases de Datos
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Docker o Podman instalado"
  - "[Docker Base](../docker/docker_base.md)"
  - "SQL básico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# PostgreSQL en Docker

## El problema

Levantas PostgreSQL con un `docker-compose.yml` copiado de un tutorial: usuario `postgres`, contraseña en texto plano dentro del fichero, puerto 5432 publicado y la aplicación conectando como superusuario. Funciona hasta que hace falta operarlo. Un día el contenedor se queda sin conexiones libres porque cada petición abre una nueva. Otro, una consulta tarda minutos y nadie sabe cuál es. Y el día que actualizas la imagen a la siguiente versión mayor, el contenedor se niega a arrancar con los datos antiguos.

PostgreSQL es el sistema de gestión de bases de datos relacional de objetos de código abierto más avanzado y ejecutarlo en contenedores simplifica el despliegue, pero no elimina la operación. Esta página cubre la base: un despliegue razonable, usuarios con permisos mínimos, los parámetros que de verdad importan, cómo diagnosticar lo que va lento, backups que se pueden restaurar y cómo afrontar una actualización mayor.

!!! note "Qué cubre y qué no"
    Aquí se trata una instancia única. La replicación, el failover automático y el enrutado de conexiones están en [PostgreSQL en Alta Disponibilidad](postgresql_ha.md). Para colocar los datos sobre almacenamiento distribuido consulta [PostgreSQL sobre Ceph](../storage/postgresql_ceph.md).

## 📋 Tabla de Contenidos

- [Despliegue con Compose](#despliegue-con-compose)
- [Inicialización y datos](#inicializacion-y-datos)
- [Roles y permisos](#roles-y-permisos)
- [Acceso de red y pg_hba.conf](#acceso-de-red-y-pg_hbaconf)
- [Ajuste de parámetros](#ajuste-de-parametros)
- [Diagnóstico de consultas lentas](#diagnostico-de-consultas-lentas)
- [Mantenimiento](#mantenimiento)
- [Backups y restauración](#backups-y-restauracion)
- [Actualizar a una versión mayor](#actualizar-a-una-version-mayor)
- [Como servicio de systemd](#como-servicio-de-systemd)
- [Alta disponibilidad y almacenamiento](#alta-disponibilidad-y-almacenamiento)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Despliegue con Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password
      POSTGRES_DB: mydatabase
    secrets:
      - pg_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myuser -d mydatabase"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:

secrets:
  pg_password:
    file: ./pg_password.txt
```

Qué cambia respecto a la versión mínima y por qué:

- **`POSTGRES_PASSWORD_FILE`** lee la contraseña de un fichero montado como secreto, así no aparece en `docker inspect` ni en el fichero compose. El fichero `pg_password.txt` debe tener permisos `600` y quedar fuera de git.
- **Volumen con nombre** en lugar de `./pgdata`: evita problemas de permisos y de propietario del directorio en el host.
- **Puerto en `127.0.0.1`**: si la aplicación está en la misma red de Compose, no publiques nada; llega por el nombre `db`. Si necesitas acceso externo, usa la IP privada y no `0.0.0.0`.
- **`pg_isready`** permite que otros servicios esperen a que la base esté lista con `depends_on` y `condition: service_healthy`.

!!! warning "Fija la versión mayor y comprueba la ruta de datos"
    Usa siempre una etiqueta con la versión mayor (`16-alpine`, no `latest`). Además, la ruta donde la imagen espera el directorio de datos puede variar entre versiones mayores de la imagen: consulta la documentación de la imagen de la versión que despliegues antes de montar el volumen.

Para entrar a una sesión interactiva:

```bash
docker compose exec db psql -U myuser -d mydatabase
```

## Inicialización y datos

La imagen ejecuta los ficheros `.sql`, `.sql.gz` y `.sh` que encuentre en `/docker-entrypoint-initdb.d/`, en orden alfabético. Es el sitio para crear roles, extensiones y el esquema inicial.

```yaml
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro
```

Detalle que causa muchos tickets: estos scripts **solo se ejecutan la primera vez**, cuando el directorio de datos está vacío. Si cambias un script y reinicias, no ocurre nada. Para repetirlo en un entorno de pruebas hay que borrar el volumen; en producción, aplica los cambios con migraciones sobre la base ya creada.

Los datos viven en el volumen, no en el contenedor. Recrear el contenedor (`docker compose up -d` tras cambiar la imagen) conserva la base; `docker compose down -v` la borra junto con el volumen.

## Roles y permisos

El usuario de `POSTGRES_USER` es superusuario. La aplicación no debería conectar con él. Crea un rol por aplicación con los permisos justos:

```sql
CREATE ROLE app LOGIN PASSWORD 'cambia-esta-clave';
CREATE DATABASE appdb OWNER app;
REVOKE CONNECT ON DATABASE appdb FROM PUBLIC;
GRANT CONNECT ON DATABASE appdb TO app;
```

Para un rol de solo lectura (informes, Grafana, un analista), conectado a `appdb`:

```sql
CREATE ROLE lector LOGIN PASSWORD 'otra-clave';
GRANT USAGE ON SCHEMA public TO lector;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lector;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO lector;
```

El último comando es el que se olvida: sin `ALTER DEFAULT PRIVILEGES`, las tablas que se creen después no serán legibles para `lector`. En `psql`, `\du` lista los roles y `\l` las bases con sus propietarios. Cambia contraseñas con `ALTER ROLE app PASSWORD '...'`.

## Acceso de red y pg_hba.conf

Dos ajustes controlan quién entra: `listen_addresses` (en qué interfaces escucha el servidor) y `pg_hba.conf` (quién puede autenticarse, desde dónde y cómo). La imagen oficial escucha en todas las interfaces *del contenedor*; la exposición real la decide cómo publicas el puerto.

Cada línea de `pg_hba.conf` tiene el formato tipo, base de datos, usuario, dirección y método. Se evalúan de arriba abajo y vale la primera que coincide:

```conf
# TYPE  DATABASE  USER    ADDRESS         METHOD
local   all       all                     scram-sha-256
host    appdb     app     10.0.0.0/24     scram-sha-256
host    all       all     0.0.0.0/0       reject
```

Usa `scram-sha-256` y no `md5` ni, desde luego, `trust`, que deja entrar sin contraseña. Una línea `host ... reject` al final deja explícito que lo no listado queda fuera.

!!! warning "Depende de la versión y de la imagen"
    El método por defecto para las contraseñas nuevas depende de `password_encryption` y de la versión. Si migras desde una base antigua con hashes `md5`, las contraseñas deben volver a establecerse para pasar a SCRAM. Con la imagen oficial, el `pg_hba.conf` vive en el directorio de datos y se genera al inicializar; para sustituirlo, móntalo con `-c hba_file=...` o edítalo y recarga con `SELECT pg_reload_conf();`.

Cuando conecte desde fuera del host, cifra la conexión con TLS (`ssl = on` y certificados) o usa una VPN como [WireGuard](../linux/wireguard.md).

## Ajuste de parámetros

Los valores por defecto están pensados para una máquina pequeña. Se pasan a la imagen con `command: ["postgres", "-c", "clave=valor"]` o se guardan con `ALTER SYSTEM`. Los más importantes:

| Parámetro | Qué controla | Punto de partida habitual |
| --- | --- | --- |
| `shared_buffers` | Memoria de caché propia de PostgreSQL | Alrededor del 25 % de la RAM dedicada |
| `effective_cache_size` | Pista al planificador sobre la caché total (incluida la del sistema) | Entre el 50 y el 75 % de la RAM |
| `work_mem` | Memoria por **operación** de ordenación o hash | Pocos MB; se multiplica por operaciones y conexiones |
| `maintenance_work_mem` | Memoria para `VACUUM` y creación de índices | Bastante mayor que `work_mem` |
| `max_connections` | Conexiones simultáneas máximas | Lo mínimo necesario; usa un pooler |

```yaml
    command:
      - postgres
      - -c
      - shared_buffers=1GB
      - -c
      - effective_cache_size=3GB
      - -c
      - work_mem=16MB
      - -c
      - max_connections=100
```

Dos trampas. `work_mem` no es un límite por conexión: una consulta compleja puede usarlo varias veces, y con cientos de conexiones se dispara el consumo hasta que el kernel mata el proceso. Y subir `max_connections` no es la solución a una app que abre demasiadas conexiones: cada una consume memoria. Pon un pooler como PgBouncer delante (ver [PostgreSQL en Alta Disponibilidad](postgresql_ha.md)) y mantén un número moderado.

`shared_buffers` y `max_connections` exigen reiniciar; otros se aplican con `SELECT pg_reload_conf();`. La columna `pending_restart` de la vista `pg_settings` indica cuáles esperan un reinicio. Recuerda que el contenedor tiene su propio límite de memoria: calcula los valores sobre ese límite, no sobre la RAM del host.

## Diagnóstico de consultas lentas

Primero, ¿qué está pasando ahora mismo? La vista `pg_stat_activity` muestra cada conexión:

```sql
SELECT pid, usename, state, now() - query_start AS duracion, left(query, 80) AS consulta
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duracion DESC;
```

Leer el resultado: las filas con mayor `duracion` son las candidatas. Un estado `idle in transaction` prolongado es sospechoso, porque retiene bloqueos y frena el `VACUUM`. Para parar una consulta usa `SELECT pg_cancel_backend(pid);`, y si no responde, `pg_terminate_backend(pid)`, que cierra la conexión entera.

Segundo, ¿por qué es lenta esa consulta? `EXPLAIN ANALYZE` ejecuta la consulta de verdad y muestra el plan con tiempos reales:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM pedidos WHERE cliente_id = 42;
```

En el resultado busca tres cosas: un recorrido secuencial (`Seq Scan`) sobre una tabla grande cuando esperabas un índice, una gran diferencia entre las filas estimadas y las reales (estadísticas obsoletas: ejecuta `ANALYZE`) y los nodos que concentran el tiempo. Cuidado: como ejecuta la consulta, envuélvela en `BEGIN; ... ROLLBACK;` si es un `UPDATE` o `DELETE`.

Para ver las consultas más costosas acumuladas existe la extensión `pg_stat_statements`. Hay que cargarla con `shared_preload_libraries=pg_stat_statements` (requiere reinicio) y activarla con `CREATE EXTENSION pg_stat_statements;`.

## Mantenimiento

PostgreSQL no borra las filas muertas al instante: las limpia `VACUUM`, que el proceso de autovacuum lanza solo. Déjalo activado. Lo que sí conviene vigilar:

- Tablas con muchas filas muertas, visibles en `pg_stat_user_tables` (columna `n_dead_tup`).
- Transacciones abiertas durante horas, que impiden limpiar.
- `VACUUM (ANALYZE)` manual tras una carga masiva, para refrescar las estadísticas del planificador.
- Crecimiento del volumen: vigila el espacio libre del disco, porque una base llena puede quedarse en solo lectura o parar.

`pg_size_pretty(pg_database_size('appdb'))` da el tamaño de una base en un formato legible.

## Backups y restauración

`pg_dump` genera una copia lógica de una base, consistente aunque esté en uso. El formato personalizado (`-Fc`) está comprimido y permite restaurar de forma selectiva:

```bash
docker compose exec -T db pg_dump -U myuser -Fc mydatabase > backup-$(date +%F).dump
docker compose exec -T db pg_dumpall -U myuser --globals-only > globals-$(date +%F).sql
```

`pg_dump` no incluye los roles ni los tablespaces; `pg_dumpall --globals-only` los guarda aparte. Sin ese segundo fichero, restaurar en una máquina nueva falla por roles inexistentes.

Para restaurar con `pg_restore`:

```bash
docker compose exec -T db createdb -U myuser nueva
docker compose exec -T db pg_restore -U myuser -d nueva --no-owner < backup-2026-10-10.dump
```

Un volcado en formato SQL plano (`-Fp`, el predeterminado) se restaura con `psql -f` en lugar de `pg_restore`. La copia lógica sirve para una base de tamaño moderado; para bases grandes o para recuperar a un punto exacto en el tiempo hacen falta copias físicas (`pg_basebackup`) y archivado de WAL, que se tratan junto a la replicación en [PostgreSQL en Alta Disponibilidad](postgresql_ha.md).

Programa los volcados con un temporizador de systemd o un cron, guárdalos fuera del host y cífralos; los criterios de retención y cifrado están en [Backup Seguro](../cybersecurity/backup_seguro.md). Y, sobre todo, prueba la restauración: un backup sin restaurar nunca es más que una suposición.

## Actualizar a una versión mayor

Las versiones menores (por ejemplo, dentro de la 16) se actualizan cambiando la etiqueta de la imagen. Las **mayores** no: el formato del directorio de datos cambia y la nueva versión rechaza el volumen de la anterior. Dos caminos:

1. **Volcado y restauración.** Haz `pg_dump` (y `--globals-only`) con la versión vieja, levanta un volumen nuevo con la versión nueva y restaura. Es el más sencillo y seguro, con tiempo de parada proporcional al tamaño.
2. **`pg_upgrade`.** Convierte el directorio de datos en el sitio y es más rápido en bases grandes. En contenedores exige tener los binarios de ambas versiones, por lo que es más delicado.

En cualquier caso, ensaya primero con una copia, revisa las notas de la versión por cambios incompatibles y conserva el volumen antiguo hasta validar el nuevo. Tras actualizar, ejecuta `ANALYZE` para regenerar las estadísticas.

## Como servicio de systemd

Con Podman, un fichero Quadlet convierte el contenedor en un servicio (detalles en [Podman Quadlet](../docker/quadlets.md)):

```ini
# ~/.config/containers/systemd/postgres.container
[Container]
Image=docker.io/library/postgres:16-alpine
Environment=POSTGRES_USER=myuser POSTGRES_DB=mydatabase
Secret=pg_password,type=env,target=POSTGRES_PASSWORD
Volume=pgdata.volume:/var/lib/postgresql/data
PublishPort=127.0.0.1:5432:5432
HealthCmd=pg_isready -U myuser -d mydatabase

[Service]
Restart=always

[Install]
WantedBy=default.target
```

El secreto se crea antes con `podman secret create pg_password -`, leyendo la contraseña de la entrada estándar. Con Docker, `restart: unless-stopped` y un servicio de systemd que invoque `docker compose up` cumplen una función parecida. Las bases de datos paran bien: dale a systemd un `TimeoutStopSec` generoso para que PostgreSQL cierre limpio.

## Alta disponibilidad y almacenamiento

Una sola instancia es un punto único de fallo. Para replicación en streaming, Patroni, failover automático y prevención de split-brain, sigue [PostgreSQL en Alta Disponibilidad](postgresql_ha.md). Para ejecutar PostgreSQL con el volumen sobre un clúster Ceph (rendimiento de E/S, modo de acceso, snapshots) consulta [PostgreSQL sobre Ceph](../storage/postgresql_ceph.md). Ninguna de las dos sustituye a los backups lógicos de la sección anterior.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
| --- | --- | --- |
| `FATAL: sorry, too many clients already` | Se alcanzó `max_connections`, normalmente por falta de pooler | Cierra conexiones ociosas, añade PgBouncer y ajusta el pool de la app |
| `FATAL: password authentication failed` | Contraseña incorrecta, o el rol se creó con otra | `ALTER ROLE ... PASSWORD`; recuerda que `POSTGRES_PASSWORD` solo se aplica en el primer arranque |
| `FATAL: no pg_hba.conf entry for host` | Ninguna regla admite esa IP, usuario o base | Añade la línea en `pg_hba.conf` y recarga con `pg_reload_conf()` |
| Los cambios del script en `initdb.d` no se aplican | Solo se ejecutan con el directorio de datos vacío | Aplica una migración, o recrea el volumen en pruebas |
| El contenedor no arranca tras cambiar de versión mayor | El volumen es de otra versión mayor | Vuelve a la versión anterior y haz volcado y restauración |
| Permisos denegados al montar `./pgdata` | El propietario del directorio no coincide con el usuario del contenedor | Usa un volumen con nombre, o corrige el propietario |
| Consulta que antes iba bien ahora tarda mucho | Estadísticas obsoletas o un índice ausente | `ANALYZE`, y revisa el plan con `EXPLAIN ANALYZE` |
| El disco se llena | Tablas hinchadas, WAL acumulado o logs enormes | Revisa `pg_size_pretty`, el autovacuum y las transacciones largas |
| El contenedor muere sin error | Falta de memoria por `work_mem` o `shared_buffers` excesivos | Recalcula sobre el límite del contenedor y baja las conexiones |
| `pg_restore` falla por roles inexistentes | Se restauró sin los roles globales | Restaura antes el fichero de `pg_dumpall --globals-only` |

## Buenas prácticas

1. Fija la versión mayor de la imagen y planifica las actualizaciones mayores.
2. Usa `POSTGRES_PASSWORD_FILE` o un secreto, nunca la contraseña en el compose.
3. Un rol por aplicación con permisos mínimos; la app nunca conecta como superusuario.
4. `scram-sha-256` en `pg_hba.conf`, sin `trust`, y puerto atado a una IP privada.
5. Usa un pooler en lugar de subir `max_connections` sin límite.
6. Calcula la memoria sobre el límite del contenedor y recuerda que `work_mem` se multiplica.
7. Deja el autovacuum activado y vigila las transacciones largas.
8. Haz `pg_dump` más `pg_dumpall --globals-only`, fuera del host, y prueba la restauración.
9. Monitoriza el espacio de disco, las conexiones y las consultas lentas.
10. Para producción crítica, no te quedes en una instancia: pasa a [Alta Disponibilidad](postgresql_ha.md).

## Referencias

- [Documentación oficial de PostgreSQL](https://www.postgresql.org/docs/)
- [Imagen oficial de PostgreSQL en Docker Hub](https://hub.docker.com/_/postgres)
- [pg_hba.conf](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)
- [PostgreSQL en Alta Disponibilidad](postgresql_ha.md)
- [PostgreSQL sobre Ceph](../storage/postgresql_ceph.md)
- [Podman Quadlet](../docker/quadlets.md)
- [Backup Seguro](../cybersecurity/backup_seguro.md)
