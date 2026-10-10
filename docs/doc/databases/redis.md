---
title: "Redis: Caché de Alto Rendimiento"
description: "Desplegar y operar Redis en infraestructura propia: contenedor con volumen, persistencia RDB y AOF, límite de memoria y política de expulsión, control de acceso con ACL, backups y diagnóstico con redis-cli. Incluye el cambio de licencia y Valkey."
keywords: "redis, valkey, cache, rdb, aof, maxmemory, eviction, acl, redis-cli, persistencia, contenedores, systemd, backup"
tags: ['databases']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 20 min
category: Bases de Datos
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Docker o Podman instalado"
  - "[Docker Base](../docker/docker_base.md)"
  - "Nociones de redes y systemd"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Redis: Caché de Alto Rendimiento

## El problema

Pones Redis delante de la aplicación con `docker run redis`, todo vuela, y semanas después aparecen tres sorpresas. Reinicias el contenedor y la caché desaparece (nunca montaste un volumen). Un día el proceso muere sin aviso porque la memoria del servidor se agotó (nadie fijó `maxmemory`). Y un escaneo de red descubre que el puerto 6379 responde a cualquiera, sin contraseña, porque lo publicaste en todas las interfaces.

Redis es sencillo de arrancar y fácil de dejar mal configurado. Esta página cubre lo que hay que decidir antes de ponerlo en producción en tu propia infraestructura: dónde viven los datos, cuánta memoria puede usar, qué pasa cuando se llena, quién puede conectar y cómo se recupera tras un fallo.

!!! note "Qué cubre y qué no"
    Aquí se trata una instancia única bien operada. La alta disponibilidad (Sentinel, Cluster) queda fuera. Para el despliegue de contenedores como servicios consulta [Podman Quadlet](../docker/quadlets.md) y [Docker Base](../docker/docker_base.md).

## 📋 Tabla de Contenidos

- [Licencia y Valkey](#licencia-y-valkey)
- [Despliegue rápido](#despliegue-rapido)
- [Despliegue persistente](#despliegue-persistente)
- [Persistencia: RDB y AOF](#persistencia-rdb-y-aof)
- [Memoria y política de expulsión](#memoria-y-politica-de-expulsion)
- [Seguridad y control de acceso](#seguridad-y-control-de-acceso)
- [Operación con redis-cli](#operacion-con-redis-cli)
- [Como servicio de systemd](#como-servicio-de-systemd)
- [Backups y restauración](#backups-y-restauracion)
- [Casos de uso comunes](#casos-de-uso-comunes)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Licencia y Valkey

Redis es un almacén de estructuras de datos en memoria, usado como base de datos, caché y broker de mensajería. Durante años fue software con licencia BSD. El proyecto cambió después a licencias de código disponible (no aprobadas por la OSI) y, más adelante, añadió de nuevo una licencia de código abierto como opción en versiones posteriores.

Como reacción a ese cambio, la Linux Foundation impulsó **Valkey**, una bifurcación de Redis mantenida por la comunidad con licencia BSD. Valkey conserva el protocolo, los comandos y los ficheros de datos, así que `redis-cli`, los clientes y las configuraciones de esta página funcionan igual.

!!! warning "Comprueba la licencia de la versión que despliegas"
    La licencia depende de la versión de Redis. Antes de empaquetar una imagen para un cliente o un producto, lee el fichero de licencia de esa versión concreta. Si necesitas una licencia permisiva sin ambigüedad, Valkey es la alternativa directa. La compatibilidad es muy alta, pero no está garantizada para funciones nuevas: prueba tu aplicación contra la versión que elijas.

## Despliegue rápido

Para una prueba local:

```bash
docker run --name my-redis -d -p 127.0.0.1:6379:6379 redis:7-alpine
```

Este contenedor sirve para aprender, no para producir: los datos mueren con él y no hay límite de memoria. Observa que el puerto se publica solo en `127.0.0.1`; sin ese prefijo Docker lo abriría en todas las interfaces y, además, saltándose las reglas del firewall del host.

!!! warning "Fija la versión de la imagen"
    `redis:alpine` o `latest` cambian de versión mayor sin avisar. Fija una etiqueta concreta (como `7-alpine`) y actualiza de forma deliberada, leyendo antes las notas de la versión.

## Despliegue persistente

Un `compose.yaml` razonable para un servicio interno: contraseña desde variable de entorno, volumen para los datos y el puerto atado a la IP privada del host.

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command:
      - redis-server
      - --appendonly
      - "yes"
      - --maxmemory
      - 512mb
      - --maxmemory-policy
      - allkeys-lru
      - --requirepass
      - ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "10.0.0.5:6379:6379"
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a \"$$REDIS_PASSWORD\" ping | grep PONG"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  redis_data:
```

La contraseña va en un fichero `.env` junto al compose, con permisos `600`. Si la app corre en la misma red de Compose, ni siquiera publiques el puerto: el resto de servicios llegan por el nombre `redis`.

!!! tip "Contraseña en el healthcheck"
    El healthcheck usa `$$REDIS_PASSWORD` para que Compose no la sustituya. Para que exista dentro del contenedor, añade `environment: REDIS_PASSWORD: ${REDIS_PASSWORD}` al servicio. Con ACL (ver más abajo) puedes crear un usuario solo para `PING`.

## Persistencia: RDB y AOF

Redis guarda en memoria y ofrece dos mecanismos de durabilidad, combinables:

| Modo | Qué hace | Ventaja | Coste |
| --- | --- | --- | --- |
| **RDB** | Snapshot binario cada cierto tiempo o número de cambios | Fichero compacto, arranque rápido, fácil de copiar | Pierdes lo escrito desde el último snapshot |
| **AOF** | Registra cada escritura en un log que se reproduce al arrancar | Pérdida mínima (por defecto, hasta un segundo) | Fichero mayor, arranque más lento |
| **Ninguno** | Solo memoria | Máximo rendimiento | Todo se pierde al reiniciar |

Configuración habitual en `redis.conf`:

```conf
# RDB: snapshot si hay >=1 cambio en 1 h, >=100 en 5 min o >=10000 en 1 min
save 3600 1 300 100 60 10000

# AOF: registrar cada escritura, sincronizar a disco cada segundo
appendonly yes
appendfsync everysec

# Directorio de datos (el volumen)
dir /data
```

`appendfsync everysec` es el equilibrio habitual. `always` sincroniza en cada escritura y es mucho más lento; `no` deja la decisión al sistema operativo.

Elige según el papel de Redis. Si es **solo caché**, la persistencia sobra: desactívala con `save ""` y `appendonly no`, y asume que se arranca vacío. Si guarda **sesiones o colas** que no quieres perder, activa AOF, y deja RDB como copia periódica para backups.

!!! warning "Persistir no es hacer backup"
    AOF y RDB protegen contra reinicios, no contra borrados, corrupción ni la pérdida del disco. El backup es otra cosa; ver [Backups y restauración](#backups-y-restauracion).

## Memoria y política de expulsión

Redis guarda todo en RAM. Sin límite, crece hasta que el kernel mata el proceso (OOM killer). Fija siempre `maxmemory` por debajo de la RAM disponible: deja margen para el sistema, los buffers y el coste de copiar memoria al hacer snapshots.

```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

Cuando se alcanza el límite, la política decide qué ocurre:

| Política | Comportamiento | Cuándo usarla |
| --- | --- | --- |
| `noeviction` | Rechaza las escrituras con error | Redis como base de datos: prefieres un error a perder datos |
| `allkeys-lru` | Expulsa las claves menos usadas recientemente | Caché pura, la opción más común |
| `allkeys-lfu` | Expulsa las menos frecuentes | Caché con claves muy populares y estables |
| `volatile-lru` | Expulsa solo claves con caducidad (TTL) | Mezcla de caché y datos permanentes |
| `volatile-ttl` | Expulsa primero las que caducan antes | Prioridad por vida restante |

`volatile-*` solo actúa sobre claves con TTL: si ninguna lo tiene, se comporta como `noeviction` y las escrituras fallan. Usa `allkeys-*` para una caché y pon TTL a lo que cachees.

En el host conviene `vm.overcommit_memory=1` en `sysctl`; sin él, el `fork` para los snapshots puede fallar con poca memoria libre. Redis lo avisa en sus logs al arrancar.

## Seguridad y control de acceso

Un Redis expuesto sin autenticación es una vía de entrada habitual en incidentes. Tres capas, de fuera adentro:

1. **Red.** Con `bind` limita las interfaces donde escucha (`bind 127.0.0.1 10.0.0.5`). En contenedores, `bind` dentro de la imagen no sustituye a publicar el puerto solo en la IP deseada. Cierra el 6379 en el firewall salvo para los clientes.
2. **Autenticación.** `requirepass` fija una contraseña única. Es lo mínimo.
3. **ACL.** Usuarios con permisos concretos, mejor que compartir una contraseña de administrador.

Ejemplo de usuario para una aplicación limitada a sus claves, sin comandos peligrosos:

```bash
redis-cli ACL SETUSER app on '>cambia-esta-clave' '~app:*' +@read +@write -@dangerous
redis-cli ACL LIST
```

El usuario `app` puede leer y escribir solo claves con prefijo `app:` y no puede ejecutar comandos como `FLUSHALL`, `CONFIG` o `KEYS`. Para que los usuarios sobrevivan al reinicio, defínelos en el fichero de configuración o en un fichero `aclfile`, no solo con `ACL SETUSER`.

!!! warning "Evita la contraseña en la línea de comandos"
    `redis-cli -a clave` deja la contraseña en el historial y en la lista de procesos, y emite un aviso. Usa la variable de entorno `REDISCLI_AUTH`, o ejecuta `AUTH` ya dentro de la sesión.

Redis no cifra el tráfico por defecto. Si cruza redes no confiables, activa TLS en Redis o ponlo detrás de una VPN como [WireGuard](../linux/wireguard.md).

## Operación con redis-cli

Las comprobaciones diarias, en orden de uso:

```bash
redis-cli ping                       # responde PONG si está vivo
redis-cli INFO memory                # used_memory, maxmemory, fragmentación
redis-cli INFO stats                 # evicted_keys, keyspace_hits/misses
redis-cli INFO persistence           # estado del último RDB y del AOF
redis-cli DBSIZE                     # número de claves
redis-cli SLOWLOG GET 10             # las 10 últimas órdenes lentas
redis-cli --latency                  # latencia medida en vivo
redis-cli --bigkeys                  # busca las claves más grandes
redis-cli MEMORY USAGE app:sesion:1  # bytes de una clave concreta
```

Lectura de las métricas clave, en prosa:

- `evicted_keys` creciendo indica que `maxmemory` está en uso y se expulsan claves. Es normal en una caché, grave en una base de datos.
- La relación entre `keyspace_hits` y `keyspace_misses` mide la eficacia de la caché. Si casi todo son fallos, el TTL es muy corto o no se está cacheando lo correcto.
- Un `mem_fragmentation_ratio` muy superior a 1 indica memoria reservada que Redis no usa.

Para recorrer claves, usa `SCAN`, nunca `KEYS *`: este último bloquea el servidor mientras recorre todo el espacio de claves. Redis ejecuta las órdenes en un único hilo, así que una orden lenta frena a todos los clientes.

```bash
redis-cli --scan --pattern 'app:sesion:*' | head
```

Los cambios con `CONFIG SET` se aplican al instante, pero se pierden al reiniciar salvo que los guardes con `CONFIG REWRITE` o los lleves al fichero de configuración.

## Como servicio de systemd

Si prefieres que el contenedor sea el servicio, un fichero Quadlet de Podman (detalles en [Podman Quadlet](../docker/quadlets.md)) evita escribir la unit a mano:

```ini
# ~/.config/containers/systemd/redis.container
[Unit]
Description=Redis

[Container]
Image=docker.io/library/redis:7-alpine
Exec=redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
Volume=redis-data.volume:/data
PublishPort=127.0.0.1:6379:6379
HealthCmd=redis-cli ping
HealthInterval=10s

[Service]
Restart=always

[Install]
WantedBy=default.target
```

```ini
# ~/.config/containers/systemd/redis-data.volume
[Volume]
```

Tras un `systemctl --user daemon-reload` aparece el servicio `redis.service`. Los logs se leen con `journalctl --user -u redis`. Con Docker, `restart: unless-stopped` en Compose cumple el mismo papel.

## Backups y restauración

La estrategia habitual: genera un snapshot RDB consistente y cópialo fuera del host.

```bash
redis-cli BGSAVE                     # snapshot en segundo plano
redis-cli LASTSAVE                   # marca de tiempo del último guardado correcto
docker cp my-redis:/data/dump.rdb ./redis-$(date +%F).rdb
```

`BGSAVE` es asíncrono: espera a que `LASTSAVE` cambie antes de copiar el fichero, o copiarás uno anterior. Con AOF activo, copia todo el directorio de datos con Redis parado, o usa el snapshot RDB.

Para restaurar: para Redis, sustituye `dump.rdb` en el volumen por la copia, comprueba que `appendonly` no esté activado con un AOF antiguo que lo pise y arranca de nuevo. Si Redis tiene AOF habilitado, **carga el AOF y no el RDB**; restaurar un RDB con AOF activo y un AOF vacío da una base vacía. Si el AOF se corrompe por un corte de luz, la herramienta `redis-check-aof` lo diagnostica y puede reparar el final truncado.

Un backup que no se ha restaurado nunca es una suposición. Prueba la restauración en otra máquina de vez en cuando. Para el cifrado, la rotación y la copia externa, aplica lo descrito en [Backup Seguro](../cybersecurity/backup_seguro.md).

## Casos de uso comunes

1.  **Caché de sesiones:** almacenar tokens de usuario con TTL.
2.  **Cola de tareas:** backend para Celery o BullMQ. Aquí sí conviene AOF y `noeviction`.
3.  **Leaderboard:** uso de Sorted Sets (`ZADD`, `ZRANGE`).
4.  **Limitación de peticiones:** contadores con `INCR` y `EXPIRE`.
5.  **Mensajería ligera:** Pub/Sub y Streams, sin garantías de entrega en Pub/Sub.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
| --- | --- | --- |
| Los datos desaparecen al recrear el contenedor | No hay volumen en `/data` o la persistencia está apagada | Monta un volumen y activa `appendonly yes` |
| Error `OOM command not allowed when used memory > 'maxmemory'` | Política `noeviction` (o `volatile-*` sin TTL) con la memoria llena | Cambia a `allkeys-lru`, pon TTL o sube `maxmemory` |
| El contenedor muere sin error aparente | El kernel lo mató por falta de memoria | Fija `maxmemory` por debajo del límite del contenedor y del host |
| `NOAUTH Authentication required` | Falta la contraseña en el cliente | Usa `REDISCLI_AUTH` o `AUTH` en la sesión |
| `DENIED Redis is running in protected mode` | Conexión externa sin contraseña y sin `bind` explícito | Define `requirepass` y `bind`; no desactives el modo protegido sin más |
| Fallan los snapshots o el AOF rewrite | Poca memoria libre para el `fork` | Activa `vm.overcommit_memory=1` y deja margen de RAM |
| Latencia con picos | Órdenes lentas (`KEYS`, claves enormes) o el disco con AOF | Revisa `SLOWLOG GET`, usa `SCAN` y mira `--bigkeys` |
| Arranque lentísimo | AOF muy grande | Comprueba el rewrite automático o combina con RDB |
| Tras restaurar, la base sale vacía | AOF activo ignora el RDB restaurado | Restaura el AOF, o desactiva AOF en el primer arranque |

## Buenas prácticas

1. Fija siempre `maxmemory` y elige la política según el papel: `allkeys-lru` para caché, `noeviction` para datos.
2. Fija la versión de la imagen y actualiza de forma deliberada.
3. Nunca publiques el 6379 a Internet; ata el puerto a una IP privada o no lo publiques.
4. Usa ACL con un usuario por aplicación y permisos mínimos.
5. Guarda la contraseña en un fichero `600` o en un gestor de secretos, no en la línea de comandos.
6. Pon TTL a todo lo que cachees.
7. Monitoriza `used_memory`, `evicted_keys` y la tasa de aciertos.
8. Haz backup fuera del host y prueba la restauración.
9. Evita `KEYS`, `FLUSHALL` y `DEBUG` en producción.
10. Revisa la licencia de la versión y valora Valkey si te importa.

## Referencias

- [Documentación oficial de Redis](https://redis.io/docs/)
- [Persistencia en Redis](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [ACL en Redis](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/)
- [Valkey](https://valkey.io/)
- [Docker Base](../docker/docker_base.md)
- [Podman Quadlet](../docker/quadlets.md)
- [Backup Seguro](../cybersecurity/backup_seguro.md)
