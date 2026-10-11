---
title: "Docker — Seguridad: hardening, secretos y escaneo"
description: "Endurecer imágenes y contenedores Docker: por qué el daemon es root equivalente, usuario no-root, capabilities, filesystem de solo lectura, no-new-privileges, límites de recursos, seccomp/AppArmor, secretos fuera de la imagen, escaneo con Trivy y publicación segura de puertos."
keywords: "docker, seguridad, hardening, contenedores, capabilities, seccomp, apparmor, no-new-privileges, read-only, secretos, trivy, escaneo, cosign, dockerfile"
tags: ['docker', 'containers', 'hardening', 'cybersecurity']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 25 min
category: Contenedores
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "[Docker — Base](docker_base.md)"
  - "Linux intermedio (usuarios, permisos, procesos)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Docker — Seguridad: hardening, secretos y escaneo

## El problema

Un contenedor no es una máquina virtual. Es un proceso del host con namespaces, cgroups y unos cuantos filtros encima. Todo lo que separa "una aplicación comprometida" de "un host comprometido" son opciones que **tú** activas: casi todas están desactivadas por defecto, porque los valores por defecto de Docker priorizan que las cosas arranquen a la primera. El resultado habitual es un contenedor que corre como root, con las capabilities que Docker concede por defecto, filesystem escribible, sin límites de memoria, con la clave de la base de datos en una variable de entorno visible en `docker inspect`, y publicando el puerto en todas las interfaces de la máquina. Cada una de esas cosas se arregla con una línea.

!!! note "Qué cubre y qué no"
    Aquí se trata el **endurecimiento de imágenes y contenedores** con el runtime por defecto (`runc`). El modelo de privilegios sin daemon está en [Podman Rootless](podman_rootless.md); el aislamiento del kernel con gVisor o Kata, en [Docker — Seguridad Runtime](docker_runtime_security.md). Son complementarios, no alternativos.

## 📋 Tabla de Contenidos

- [El daemon es root equivalente](#el-daemon-es-root-equivalente)
- [Usuario no-root en la imagen](#usuario-no-root-en-la-imagen)
- [Capabilities: quitar todo y devolver lo justo](#capabilities-quitar-todo-y-devolver-lo-justo)
- [Filesystem de solo lectura](#filesystem-de-solo-lectura)
- [no-new-privileges](#no-new-privileges)
- [Límites de recursos](#limites-de-recursos)
- [seccomp y AppArmor](#seccomp-y-apparmor)
- [Secretos: lo que nunca va en la imagen](#secretos-lo-que-nunca-va-en-la-imagen)
- [Imágenes base mínimas y multi-stage](#imagenes-base-minimas-y-multi-stage)
- [Escaneo con Trivy](#escaneo-con-trivy)
- [Firma y procedencia](#firma-y-procedencia)
- [Red: dónde publicas los puertos](#red-donde-publicas-los-puertos)
- [Troubleshooting](#troubleshooting)
- [Checklist](#checklist)
- [Enlaces relacionados](#enlaces-relacionados)

## El daemon es root equivalente

`dockerd` corre como root y es el padre de todos los contenedores. Quien puede hablar con su socket puede pedirle que haga cualquier cosa **como root**, incluido montar el sistema de ficheros del host:

```bash
docker run -it -v /:/host alpine chroot /host sh
```

Ese comando no explota ningún fallo: es una función documentada. De ahí salen dos consecuencias que conviene tener interiorizadas. La primera, **pertenecer al grupo `docker` equivale a `sudo` sin contraseña**; no es una aproximación retórica, el comando de arriba lo demuestra, así que audita ese grupo como auditas los accesos de administrador. La segunda, **montar `/var/run/docker.sock` dentro de un contenedor le da ese mismo poder**: es el patrón de los agentes de CI, los actualizadores automáticos y los dashboards de contenedores, y todos ellos son, efectivamente, root en el host.

Si una herramienta necesita hablar con Docker, las salidas razonables son un **proxy de socket** que exponga solo los endpoints necesarios, montar el socket en `:ro` sabiendo que eso protege muy poco —el modo lectura afecta al fichero, no a las operaciones de la API— o cambiar de motor: con [Podman rootless](podman_rootless.md) no existe socket privilegiado que montar.

!!! tip "Modo rootless de Docker"
    Docker también tiene un modo rootless en el que el daemon corre bajo tu usuario, con limitaciones parecidas a las de Podman rootless (puertos privilegiados, algunos drivers de red y storage). Consulta la documentación de tu versión antes de migrar un host en producción.

## Usuario no-root en la imagen

Sin instrucción `USER`, el proceso principal corre como root **dentro** del contenedor. Con el daemon rootful y sin `userns-remap`, ese UID 0 es el UID 0 del host: sobre un directorio montado del host, es root de verdad.

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine:3.20
RUN addgroup -g 10001 app && \
    adduser -D -u 10001 -G app app
COPY --chown=10001:10001 app /usr/local/bin/app
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/app"]
```

Cuatro detalles marcan la diferencia: usa **UID y GID numéricos** en `USER` y no el nombre, porque Kubernetes puede comprobar `runAsNonRoot` contra un número pero no contra un nombre que tendría que resolver dentro de la imagen; elige un **UID alto (>10000)** para no colisionar con usuarios reales del host en volúmenes compartidos; prefiere **`COPY --chown`** a un `RUN chown -R` posterior, que duplica los ficheros en una capa nueva; y pon **todo lo que instale paquetes antes del `USER`**, porque después de esa línea el build ya no es root.

Verifica lo construido, que es distinto de lo que creías construir:

{% raw %}

```bash
docker run --rm --entrypoint id miimagen:1.0
docker inspect -f '{{.Config.User}}' miimagen:1.0
```

{% endraw %}

Si el segundo comando devuelve vacío, la imagen corre como root y da igual lo que ponga el README. En ejecución puedes forzarlo con `--user 10001:10001`, útil para imágenes de terceros que no puedes reconstruir.

## Capabilities: quitar todo y devolver lo justo

Root dentro de un contenedor no es root completo: Docker retiene un subconjunto de capabilities (`CHOWN`, `SETUID`, `NET_RAW`, `KILL`…) y descarta las más peligrosas, como `SYS_ADMIN`. Ese subconjunto sigue siendo bastante más de lo que necesita una aplicación web.

```bash
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx:alpine
```

La regla es siempre la misma: **`--cap-drop=ALL` y añadir solo lo que falle**. La mayoría de servicios con `USER` no-root y puertos altos no necesitan ninguna.

| Capability | Cuándo hace falta de verdad |
|---|---|
| `NET_BIND_SERVICE` | Escuchar en un puerto `<1024` |
| `CHOWN`, `FOWNER`, `DAC_OVERRIDE` | Entrypoints que ajustan permisos de volúmenes al arrancar |
| `SETUID`, `SETGID` | El proceso baja de privilegios él mismo tras arrancar |
| `NET_RAW` | `ping`, `traceroute` y sockets crudos |
| `SYS_ADMIN` | Casi nunca; equivale a levantar buena parte del aislamiento |

`--privileged` no es "un poco más de permisos": concede todas las capabilities y acceso a los dispositivos del host, desactivando la mayor parte de las barreras. Si algo lo pide, busca primero el `--cap-add` o el `--device` concreto que necesita.

## Filesystem de solo lectura

Si el atacante no puede escribir, no puede dejar un binario, ni un cron, ni modificar tu aplicación en caliente.

```bash
docker run --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /run:rw,noexec,nosuid,size=8m \
  -v datos:/var/lib/app \
  miimagen:1.0
```

`--read-only` afecta a la capa de escritura del contenedor; los volúmenes y los `--tmpfs` siguen siendo escribibles, que es justo lo que quieres. `noexec` y `nosuid` cortan el truco clásico de descargar algo en `/tmp` y ejecutarlo, y `size` impide que un proceso descontrolado llene la RAM del host. La parte incómoda es descubrir qué directorios necesita escribir la aplicación: arranca en solo lectura, mira dónde falla y añade un `--tmpfs` por cada uno. Sospechosos habituales: `/tmp`, `/run`, `/var/run`, cachés bajo `/var/cache` y directorios de sesión de intérpretes.

## no-new-privileges

Impide que un proceso gane privilegios ejecutando un binario `setuid`. Sin ella, un `sudo` o un bit SUID mal puesto dentro de la imagen es una vía directa de escalada local.

```bash
docker run --security-opt no-new-privileges:true miimagen:1.0
```

Es de las opciones más baratas de esta página: una imagen bien construida no necesita escalar privilegios en tiempo de ejecución, así que no rompe casi nada. Si al activarla algo deja de funcionar, ese "algo" es justo lo que querías saber. En Compose, la clave equivalente es `security_opt: ["no-new-privileges:true"]`, y acompaña bien a `user:`, `read_only:`, `cap_drop:` y `tmpfs:`.

## Límites de recursos

Los límites rara vez aparecen en las listas de seguridad y son, sin embargo, la única defensa frente a que **un contenedor tumbe a todos los demás**. Sin `--memory`, un consumo descontrolado —un bug, una consulta enorme, un ataque— acaba invocando al OOM killer del host, que puede matar procesos sin relación alguna.

```bash
docker run --memory=512m --memory-swap=512m \
  --cpus=1.0 --pids-limit=200 \
  --ulimit nofile=1024:2048 miimagen:1.0
```

Poner **`--memory-swap` al mismo valor que `--memory`** desactiva el swap de ese contenedor: sin eso el límite pasa a ser de RAM+swap y el proceso agoniza en disco en vez de morir rápido. **`--pids-limit`** corta en seco las *fork bombs*, accidentales o no, y **`--ulimit nofile`** evita agotar los descriptores de fichero del host. Elige los números midiendo el consumo real bajo carga y añadiendo margen: un límite demasiado ajustado mata el servicio en el peor momento, y uno demasiado generoso no protege de nada.

## seccomp y AppArmor

Estas dos capas actúan por debajo de las capabilities: sobre las llamadas al sistema y sobre el acceso a ficheros.

**seccomp** filtra syscalls. Docker aplica un perfil por defecto que bloquea un conjunto de llamadas peligrosas y permite el resto, suficiente para la inmensa mayoría de aplicaciones. Puedes indicar uno propio con `--security-opt seccomp=/ruta/perfil.json`, aunque escribir un perfil desde cero es un proyecto en sí mismo: hay que enumerar cada syscall usada en cualquier ruta de código, incluidas las de arranque y cierre. Lo importante en el día a día es lo contrario, **no desactivarlo**: `--security-opt seccomp=unconfined` circula en foros como solución rápida a errores raros y lo que hace es quitar el filtro entero. Antes de copiarlo, averigua con `dmesg` o con la auditoría del host qué syscall concreta se está bloqueando.

**AppArmor** (Debian, Ubuntu, SUSE) o **SELinux** (Fedora, RHEL) restringen a qué ficheros y capacidades llega el proceso. En hosts con AppArmor activo, Docker aplica un perfil `docker-default` a los contenedores; con SELinux, el etiquetado es lo que hace que un volumen sin `:Z` dé "Permission denied".

```bash
# Perfil propio, previamente cargado en el host con apparmor_parser
docker run --security-opt apparmor=mi-perfil miimagen:1.0
# Qué tiene aplicado un contenedor en marcha
{% raw %}docker inspect -f '{{.AppArmorProfile}} {{json .HostConfig.SecurityOpt}}' micontenedor{% endraw %}
```

!!! warning "Depende del host, no de la imagen"
    Estos perfiles los aplica el daemon según lo que soporte el kernel del host. La misma imagen tiene un confinamiento distinto en Ubuntu que en RHEL, y ninguno en un host sin LSM activo. No des por hecho lo que no hayas verificado en la máquina concreta.

## Secretos: lo que nunca va en la imagen

Una imagen es una pila de capas inmutables: lo que aparece en una capa está ahí para siempre, aunque una capa posterior lo borre. Estos dos patrones filtran el secreto a cualquiera que pueda hacer `docker pull`, y los `ARG` de build tampoco son seguros, porque quedan registrados en el historial de la imagen.

```dockerfile
# ❌ Queda en los metadatos, visible en docker inspect
ENV DB_PASSWORD=s3cr3t
# ❌ Queda en la capa, aunque el rm posterior lo "borre"
COPY .npmrc /root/.npmrc
RUN npm install && rm /root/.npmrc
```

La forma correcta con BuildKit es montar el secreto solo durante ese `RUN`, sin que llegue a ninguna capa:

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine
COPY package*.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --omit=dev
```

```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t miimagen:1.0 .
```

En **tiempo de ejecución**, las variables de entorno son legibles en `docker inspect`, en el entorno de cualquier proceso del contenedor y a menudo en los logs de arranque. Prefiere ficheros montados que la aplicación lee al arrancar (Docker Secrets en Swarm, `Secret` de Kubernetes montado como volumen, o un fichero inyectado por tu gestor). El tratamiento completo está en [Gestión de secretos](../cybersecurity/gestion_secretos.md) y, para GitOps, en [Secretos en GitOps](../cybersecurity/secrets_gitops.md).

Cómo auditar una imagen que ya existe:

{% raw %}

```bash
# Comandos completos de cada capa: aquí salen los ARG y los COPY delatores
docker history --no-trunc --format '{{.CreatedBy}}' miimagen:1.0
# Variables de entorno horneadas en la imagen
docker inspect -f '{{json .Config.Env}}' miimagen:1.0
# Escaneo de secretos sobre el filesystem de la imagen
trivy image --scanners secret miimagen:1.0
```

{% endraw %}

!!! danger "Un secreto filtrado en una imagen publicada es un secreto quemado"
    Reconstruir la imagen no lo arregla: la capa antigua sigue en el registro y en el caché de quien la haya descargado. El único remedio real es **rotar la credencial**. Borrar el tag es limpieza, no mitigación.

## Imágenes base mínimas y multi-stage

Cada paquete instalado es superficie de ataque y un CVE potencial que alguien tendrá que triar. Una base con distribución completa arrastra shell, gestor de paquetes y decenas de librerías que tu aplicación no usa.

| Base | Nota |
|---|---|
| `debian`, `ubuntu` | Cómoda para depurar, mucha superficie |
| `alpine` | Pequeña; musl en vez de glibc, cuidado con binarios compilados contra glibc |
| `*-slim` (Debian) | Buen punto medio si musl da problemas |
| Distroless | Solo runtime: sin shell ni gestor de paquetes |
| `scratch` | Solo binarios estáticos; ni certificados TLS ni zona horaria |

El multi-stage separa lo necesario para **compilar** de lo necesario para **ejecutar**: compilador, cabeceras y dependencias de desarrollo se quedan en la primera etapa.

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

Sin shell dentro, `docker exec ... sh` no funciona: es el precio a cambio de que tampoco le funcione a quien entre sin permiso; para depurar, usa un contenedor efímero que comparta los namespaces del que investigas. Las técnicas de capas y caché están en [Optimización de Docker](docker_optimizations.md).

## Escaneo con Trivy

[Trivy](https://trivy.dev/) recorre las capas de la imagen, identifica los paquetes instalados y los cruza con bases de datos de vulnerabilidades.

```bash
# Lo que se puede arreglar hoy, sin ruido de fondo
trivy image --severity CRITICAL,HIGH --ignore-unfixed miregistro/miimagen:1.0
# En CI: código de salida distinto de cero si hay hallazgos que bloquean
trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 miimagen:1.0
# Informe para procesar
trivy image --format json --output informe.json miimagen:1.0
```

La opción que más cambia el día a día es **`--ignore-unfixed`**: filtra las vulnerabilidades sin parche disponible. Sin ella, una imagen basada en Debian trae decenas de CVEs que nadie puede arreglar todavía, y el equipo aprende a ignorar el informe entero. **Qué hacer con los resultados**, en este orden:

1. **¿Hay versión corregida?** Reconstruye con la base actualizada (`docker build --pull`). Buena parte de los CVEs de una imagen desaparecen ahí, sin tocar tu código.
2. **¿El paquete es tuyo?** Actualiza la dependencia en el fichero de bloqueo (`package-lock.json`, `go.sum`, `requirements.txt`) y reconstruye.
3. **¿La vulnerabilidad es alcanzable?** Un CVE en un componente que tu contenedor nunca ejecuta es real pero no urgente. Documenta el razonamiento; no lo dejes en un mensaje de chat.
4. **¿No hay parche?** Anótalo en `.trivyignore` **con fecha y motivo**, y revísalo. Una excepción sin caducidad es una excepción permanente.

Escanea en tres momentos: en local mientras desarrollas, en el pipeline como puerta de calidad, y **periódicamente sobre lo ya desplegado** — una imagen limpia en marzo no lo es en septiembre aunque nadie la haya tocado. El montaje en CI está en [Escaneo de seguridad en CI](../cybersecurity/ci_security_scanning.md), y la variante continua sobre Kubernetes en [Trivy Operator](../cybersecurity/trivy_operator.md).

## Firma y procedencia

Escanear responde a "¿esta imagen tiene fallos conocidos?". Firmar responde a otra cosa: **"¿esta imagen es la que construyó mi pipeline?"**. Un registro comprometido o un tag sobrescrito no los detecta ningún escáner.

- **Firma**: una firma criptográfica ligada al digest de la imagen. La herramienta de referencia hoy es [Cosign](https://docs.sigstore.dev/), del proyecto Sigstore, con firma por clave o *keyless* con identidad OIDC (la del propio pipeline).
- **Procedencia**: metadatos verificables sobre cómo se construyó la imagen —commit, builder, parámetros—, en la línea del marco SLSA. BuildKit puede generar atestaciones de procedencia y SBOM durante el build.
- **Verificación en el despliegue**: la firma solo sirve si algo la comprueba antes de ejecutar. En Kubernetes, un controlador de admisión con una política; en un host suelto, un paso explícito antes del `docker run`.

Referenciar por digest es el paso previo a todo lo demás y no requiere ninguna herramienta nueva: `docker pull miregistro/miimagen@sha256:<digest>`. El tag se puede reasignar, el digest no. El flujo completo de firma, SBOM y verificación está en [Supply Chain Security](../cybersecurity/supply_chain_security.md).

!!! note "Docker Content Trust"
    `DOCKER_CONTENT_TRUST=1` sigue existiendo y se basa en Notary v1. El ecosistema se ha movido hacia Sigstore/Cosign; si empiezas hoy, empieza por ahí, y comprueba qué soporta tu registro antes de decidir.

## Red: dónde publicas los puertos

`-p 8080:80` publica en **todas** las interfaces del host: `0.0.0.0`. Si la máquina tiene IP pública, ese puerto está en Internet. Es la forma más común de exponer sin querer una base de datos o un panel de administración.

```bash
docker run -p 127.0.0.1:8080:80 nginx:alpine   # solo local
docker run -p 8080:80 nginx:alpine             # todas las interfaces
docker ps --format 'table {% raw %}{{.Names}}\t{{.Ports}}{% endraw %}'
```

Para una base de datos que solo consume otro contenedor ni siquiera hace falta publicar: en una red *bridge* definida por el usuario, los contenedores se alcanzan por nombre. La regla operativa es publicar solo lo que atiende tráfico externo y ponerlo detrás de un [proxy inverso](../traefik/traefik_base.md).

!!! danger "Docker y el firewall del host"
    Docker gestiona sus propias reglas de `iptables`/`nftables` para el reenvío de puertos, y esas reglas pueden atravesar la configuración de un firewall gestionado con `ufw`: un puerto publicado sigue siendo accesible aunque `ufw status` diga que está denegado. Verifica siempre desde **otra máquina**, no desde el host. Si necesitas control real del filtrado, publica en `127.0.0.1` y deja que el proxy inverso sea el único servicio expuesto. Ver [nftables y fail2ban](../cybersecurity/nftables_fail2ban.md).

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `Permission denied` al escribir en un volumen | El UID del `USER` no es dueño del directorio del host | `chown` en el host al UID de la imagen, o `--user` con el UID correcto |
| `Read-only file system` al arrancar | La app escribe en un directorio no previsto | Un `--tmpfs` para ese directorio, o un volumen si el dato debe persistir |
| `bind: permission denied` en el puerto 80 con usuario no-root | Falta `NET_BIND_SERVICE` | `--cap-add=NET_BIND_SERVICE`, o escuchar en puerto alto y mapear `-p 80:8080` |
| `Operation not permitted` en una syscall | Perfil seccomp o capability ausente | Identificar la syscall antes de aflojar nada; añadir la capability concreta, nunca `seccomp=unconfined` |
| El contenedor muere con código 137 | OOM: superó `--memory` | Medir el consumo real y ajustar; revisar fugas de memoria |
| Todo falla al añadir `no-new-privileges` | El entrypoint usa `sudo`, `su` o un binario SUID | Reescribir el entrypoint para no escalar; suele delatar un problema de diseño |
| Trivy encuentra CVEs que no puedes arreglar | Base desactualizada o sin parche upstream | `docker build --pull`; `--ignore-unfixed` para separar lo accionable |
| Un servicio interno accesible desde fuera | Publicado en `0.0.0.0` | `-p 127.0.0.1:...`, o no publicar y usar la red interna |
| `docker exec` no funciona en la imagen nueva | Base distroless o `scratch`: no hay shell | Depurar con un contenedor efímero que comparta namespaces |

## Checklist

- [ ] Ningún contenedor con `--privileged` ni con `/var/run/docker.sock` montado sin justificación escrita.
- [ ] Grupo `docker` del host tratado y auditado como acceso de administrador.
- [ ] `USER` con UID numérico no-root, verificado con `docker run --entrypoint id`.
- [ ] `--cap-drop=ALL` y, como mucho, las capabilities demostradas necesarias.
- [ ] `--read-only` con los `--tmpfs` mínimos, montados `noexec,nosuid` y con `size`.
- [ ] `--security-opt no-new-privileges:true` en todos los servicios.
- [ ] `--memory`, `--cpus` y `--pids-limit` con valores medidos, no adivinados.
- [ ] Perfil seccomp por defecto activo; ningún `seccomp=unconfined` sin analizar.
- [ ] Cero secretos en `ENV`, `ARG` o capas; comprobado con `docker history` y `trivy --scanners secret`.
- [ ] Secretos de build con `--mount=type=secret`; secretos de runtime como ficheros.
- [ ] Imagen base mínima y multi-stage, sin toolchain de compilación en la etapa final.
- [ ] `trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1` en el pipeline, y reescaneo periódico de lo ya desplegado.
- [ ] Imágenes referenciadas por digest en producción.
- [ ] Puertos publicados solo donde deben, verificado desde otra máquina.
- [ ] Reconstrucción periódica programada: la base envejece aunque tu código no cambie.

## Referencias

- [Docker — Base](docker_base.md) · [Optimización de Docker](docker_optimizations.md)
- [Podman Rootless](podman_rootless.md) — eliminar el daemon root del modelo de amenaza.
- [Docker — Seguridad Runtime (gVisor/Kata)](docker_runtime_security.md) — aislamiento del kernel.
- [Gestión de secretos](../cybersecurity/gestion_secretos.md) · [Supply Chain Security](../cybersecurity/supply_chain_security.md)
- [Escaneo de seguridad en CI](../cybersecurity/ci_security_scanning.md) · [Trivy Operator](../cybersecurity/trivy_operator.md)
- [Hardening de servidores Linux](../cybersecurity/hardening_linux.md) — el host que sostiene todo lo anterior.
- [Docker — Seguridad (documentación oficial)](https://docs.docker.com/engine/security/) · [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Trivy](https://trivy.dev/)
- [Cosign](https://docs.sigstore.dev/)
