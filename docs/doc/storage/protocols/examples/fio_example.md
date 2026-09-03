---
title: "fio — medir IOPS, latencia y ancho de banda sin engañarte"
description: "Cómo medir almacenamiento con fio en lugar de dd: anatomía de un job, los cuatro perfiles canónicos, lectura de percentiles de latencia, errores que invalidan una prueba y comparación entre NFS e iSCSI."
keywords: "fio, iops, latencia, p99, percentiles, benchmark, almacenamiento, nfs, iscsi, direct io, iodepth, numjobs, libaio"
tags: ['storage', 'benchmarks', 'performance']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 18 min
category: Almacenamiento
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "Un dispositivo o punto de montaje de pruebas donde puedas destruir datos"
  - "[Protocolos y métricas de almacenamiento](../protocols.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# fio — medir IOPS, latencia y ancho de banda sin engañarte

## El problema

Alguien pregunta "¿cuánto rinde este disco?" y la respuesta llega en forma de `dd`:

```bash
dd if=/dev/zero of=/mnt/datos/test bs=1M count=1024
# 1073741824 bytes copied, 0.9 s, 1.2 GB/s
```

Ese número no describe el disco. Describe la velocidad a la que el kernel copió un gigabyte a la caché de página y devolvió el control antes de que la mitad hubiera tocado el medio físico. Aunque añadas `oflag=direct`, sigues midiendo **una** cosa: escritura secuencial, un hilo, profundidad de cola 1, un único tamaño de bloque y sin ninguna estadística de latencia. Ninguna carga real se parece a eso.

`fio` (Flexible I/O Tester) existe precisamente para lo contrario: describir el patrón de acceso que te interesa y medirlo con estadísticas que se pueden defender ante alguien que sepa del tema.

!!! warning "fio escribe de verdad"
    Apuntar `filename=` a un dispositivo de bloque **destruye su contenido**. Usa un dispositivo vacío, un fichero dentro de un sistema de ficheros de pruebas, o `readonly=1` si solo vas a leer. Comprueba dos veces la ruta antes de pulsar Intro.

## 📋 Tabla de Contenidos

- [Por qué dd no sirve](#por-que-dd-no-sirve)
- [Anatomía de un job](#anatomia-de-un-job)
- [Los cuatro perfiles canónicos](#los-cuatro-perfiles-canonicos)
- [Leer la salida](#leer-la-salida)
- [Errores que invalidan una medición](#errores-que-invalidan-una-medicion)
- [Comparar protocolos de red](#comparar-protocolos-de-red)
- [Guardar resultados en JSON](#guardar-resultados-en-json)
- [Plantilla de informe](#plantilla-de-informe)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Por qué dd no sirve

| Aspecto | `dd` | `fio` |
|---|---|---|
| Patrón de acceso | Solo secuencial | Secuencial, aleatorio o mixto |
| Concurrencia | Un hilo, cola 1 | `numjobs` × `iodepth` |
| Caché de página | Activa salvo `oflag=direct` | `direct=1` explícito |
| Latencia | No la mide | Media, desviación y percentiles |
| Duración | Depende del tamaño | `runtime` + `time_based` |
| Salida procesable | No | JSON |

`dd` sigue valiendo para lo que fue escrito: copiar bloques. Como herramienta de medida solo responde a "¿cuánto tarda en copiar esto?", que casi nunca es la pregunta.

## Anatomía de un job

Un fichero de job es un INI: `[global]` fija lo común y cada sección con nombre es un trabajo independiente.

```ini
# base.fio
[global]
ioengine=libaio
direct=1
time_based=1
runtime=60
ramp_time=10
group_reporting=1
filename=/mnt/pruebas/fio.dat
size=16G

[randread-4k]
rw=randread
bs=4k
iodepth=32
numjobs=4
```

Lo lanzas con `fio base.fio`. Los parámetros que de verdad mueven el resultado son pocos:

| Parámetro | Qué hace | Por qué importa |
|---|---|---|
| `rw` | Patrón: `read`, `write`, `randread`, `randwrite`, `randrw` | Es la diferencia entre medir ancho de banda y medir IOPS |
| `bs` | Tamaño de bloque | 4k mide operaciones; 1M mide caudal. No son la misma prueba |
| `iodepth` | Peticiones en vuelo por job | Con cola 1 mides latencia; con cola alta mides techo de IOPS |
| `numjobs` | Procesos concurrentes | Paralelismo real; multiplica la cola total |
| `direct` | `1` evita la caché de página | Sin esto mides RAM |
| `ioengine` | Cómo se envían las peticiones | Decide si `iodepth` significa algo |
| `runtime` + `time_based` | Duración fija | Sin `time_based`, el job acaba al recorrer `size` |
| `ramp_time` | Descarta los primeros segundos | Evita contaminar la media con el calentamiento |

Tres detalles que se pasan por alto una y otra vez:

**`iodepth` solo tiene efecto con un motor asíncrono.** Con `ioengine=sync` o `psync` cada hilo envía una petición y espera; la cola efectiva es 1 por job, por mucho que escribas `iodepth=64`. El paralelismo entra entonces solo por `numjobs`.

**`libaio` en Linux necesita `direct=1`.** La AIO nativa del kernel no es realmente asíncrona sobre I/O bufferizada, así que `ioengine=libaio` con `direct=0` degenera en comportamiento síncrono y la cola vuelve a ser 1. Es la combinación que produce esos resultados "raros" que nadie sabe explicar.

**La cola total es `numjobs × iodepth`.** Cuatro jobs con `iodepth=32` mantienen 128 peticiones en vuelo. Comparar dos sistemas exige igualar esa cifra, no solo uno de los dos números.

!!! tip "io_uring como alternativa"
    En kernels y compilaciones de fio que lo soportan, `ioengine=io_uring` reduce el coste por operación frente a `libaio`. Comprueba disponibilidad antes de usarlo en un job que quieras repetir en otra máquina:
    ```bash
    fio --enghelp | grep -i uring
    ```
    Si el objetivo es comparar dos sistemas, usa el mismo motor en ambos. Cambiar de motor entre ejecuciones cambia el resultado por sí solo.

## Los cuatro perfiles canónicos

Cuatro pruebas cubren la mayoría de decisiones. Guárdalas como fichero y no las improvises en línea de comandos: un job file es reproducible, un comando de tres pantallas de ancho no.

```ini
# perfiles.fio — ejecutar uno cada vez con: fio --section=randread-4k perfiles.fio
[global]
ioengine=libaio
direct=1
time_based=1
group_reporting=1
filename=/mnt/pruebas/fio.dat
size=64G

# 1. Lectura secuencial — techo de ancho de banda
[seqread-1M]
rw=read
bs=1M
iodepth=16
numjobs=1
runtime=60
ramp_time=10

# 2. Escritura secuencial — ingesta, backups, restauraciones
[seqwrite-1M]
rw=write
bs=1M
iodepth=16
numjobs=1
runtime=60
ramp_time=10

# 3. Lectura aleatoria 4k — el perfil de una base de datos leyendo
[randread-4k]
rw=randread
bs=4k
iodepth=32
numjobs=4
runtime=120
ramp_time=15

# 4. Escritura aleatoria 4k — la prueba dura, y la que más se falsea
[randwrite-4k]
rw=randwrite
bs=4k
iodepth=32
numjobs=4
runtime=300
ramp_time=60
```

Ejecuta las secciones **de una en una** con `--section=`. Lanzarlas todas juntas las hace competir por el mismo dispositivo y ninguna mide lo que dice medir.

El `runtime` largo del cuarto perfil no es capricho: la escritura aleatoria sostenida es donde un SSD agota su caché rápida y cae a su rendimiento de régimen. Sesenta segundos suelen medir la caché; cinco minutos empiezan a medir el disco.

## Leer la salida

fio imprime, por dirección de I/O, cuatro bloques: IOPS, ancho de banda, latencias y percentiles.

!!! note "Salida ilustrativa"
    El fragmento siguiente es **inventado para explicar el formato**. Los valores concretos dependen por completo del hardware, del sistema de ficheros, del protocolo y de los parámetros del job: no los uses como referencia de nada ni los compares con los tuyos.

```text
randread-4k: (groupid=0, jobs=4): err= 0: pid=1234
  read: IOPS=XXXk, BW=YYYMiB/s (ZZZMB/s)(...)
    slat (usec): min=..., max=..., avg=..., stdev=...
    clat (usec): min=..., max=..., avg=A, stdev=S
     lat (usec): min=..., max=..., avg=B, stdev=S
    clat percentiles (usec):
     |  1.00th=[  p1], 50.00th=[ p50], 90.00th=[ p90],
     | 95.00th=[ p95], 99.00th=[ p99], 99.90th=[p999]
```

- **IOPS** — operaciones por segundo. La cifra que importa con bloques pequeños y acceso aleatorio.
- **BW** — ancho de banda. La cifra que importa con bloques grandes y acceso secuencial. Es, aproximadamente, `IOPS × bs`: si el job es de 4k, un ancho de banda alto sería sospechoso.
- **slat** (*submission latency*) — lo que tarda la petición en entrar en la cola. Si es apreciable, el cuello de botella está en el host, no en el almacenamiento.
- **clat** (*completion latency*) — desde la cola hasta que se completa: la latencia del dispositivo o del protocolo. **lat** es el total visto por la aplicación, aproximadamente `slat + clat`.

### Por qué el percentil 99 pesa más que la media

La media esconde exactamente el comportamiento que hace que un usuario se queje. Una latencia media excelente es compatible con que una de cada cien operaciones tarde un orden de magnitud más, y una petición HTTP que toca veinte veces el almacenamiento tiene una probabilidad alta de tropezar al menos una vez con esa cola. La latencia percibida de un servicio la fija su percentil alto, no su media.

Práctica mínima: publica siempre p50, p95 y p99 juntos. Si p99 está muy por encima de p50, hay algo que se satura de forma intermitente — caché que se vacía, *garbage collection* del SSD, contención de red — y ese "algo" es el hallazgo, no un ruido a promediar. Y para medir latencia limpia usa `iodepth=1` con `numjobs=1`: con cola profunda estás midiendo el tiempo de espera que tú mismo has creado, no el del dispositivo.

## Errores que invalidan una medición

| Error | Síntoma | Arreglo |
|---|---|---|
| Sin `direct=1` | Cifras imposiblemente altas, latencias de microsegundos | `direct=1` en `[global]` |
| Fichero más pequeño que la RAM | La segunda ejecución vuela | `size` ≥ 2× RAM, o `direct=1` |
| SSD sin precondicionar | Rendimiento que cae a mitad de prueba | `ramp_time` largo y `runtime` de minutos |
| Volumen con *thin provisioning* | Lecturas instantáneas de bloques nunca escritos | Rellenar el volumen antes de leer |
| Datos comprimibles | Cifras infladas en cabinas con compresión | `refill_buffers`, `buffer_compress_percentage` |
| Otra carga en la máquina | Resultados que no se repiten | Medir en reposo y repetir tres veces |

La **caché de página** es el fallo número uno y el más fácil de arreglar: `direct=1` y listo. El resto merece detalle.

**Fichero más pequeño que la RAM.** Un `size=1G` en una máquina con 64 GB de RAM cabe entero en caché. La primera pasada mide el disco; la segunda mide memoria. Si por lo que sea no puedes usar `direct=1`, tira la caché entre ejecuciones:

```bash
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

**Precondicionamiento.** Un SSD recién formateado tiene todos sus bloques libres y absorbe escrituras a la velocidad de su caché rápida. Cuando esa caché se llena y el controlador tiene que reciclar bloques, el rendimiento baja a su valor de régimen — el único que se sostiene en producción. Por eso el perfil de escritura aleatoria lleva `runtime` de minutos y `ramp_time` generoso: quieres medir después de la caída, no antes.

**Thin provisioning y ficheros dispersos.** Un bloque que nunca se ha escrito no está en ningún sitio: la capa de almacenamiento devuelve ceros sin tocar el medio, así que medir lectura aleatoria sobre un volumen recién creado mide la velocidad a la que se generan ceros. Rellena primero con una pasada de escritura secuencial y mide después.

**Datos comprimibles.** fio escribe patrones que se comprimen muy bien. En una cabina con compresión o deduplicación en línea eso da cifras que jamás verás con datos reales:

```ini
[global]
refill_buffers=1
buffer_compress_percentage=50
dedupe_percentage=20
```

## Comparar protocolos de red

Los mismos cuatro perfiles sobre un punto de montaje NFS y sobre un LUN iSCSI describen dos comportamientos distintos. Cualitativamente, y sin números porque dependen por completo del montaje concreto:

- **iSCSI** presenta un dispositivo de bloque. El sistema de ficheros es local, así que los metadatos no cruzan la red y el patrón aleatorio 4k se parece más al del disco subyacente, con la latencia de red sumada.
- **NFS** presenta un sistema de ficheros remoto. Las operaciones de metadatos (abrir, cerrar, `stat`) son idas y vueltas por red, de modo que las cargas con muchos ficheros pequeños sufren más que las de un fichero grande. El comportamiento en escritura depende mucho de `sync` frente a `async` en el export y del uso de `wsize`/`rsize`.
- **En ambos**, la latencia de red se suma a cada operación y por tanto el impacto es proporcionalmente mucho mayor en bloques de 4k que en bloques de 1M. Un enlace que apenas afecta al caudal secuencial puede recortar los IOPS aleatorios de forma severa.
- **La MTU y el descarte de paquetes** aparecen antes en el percentil 99 que en la media. Un p99 disparado con p50 normal es, muchas veces, un problema de red y no de disco.

Contexto de protocolos y métricas en [Protocolos y métricas de almacenamiento](../protocols.md); si mides sobre volúmenes de Kubernetes, ten en cuenta la capa CSI descrita en [Kubernetes CSI](../../kubernetes_csi.md).

!!! warning "Mide el protocolo, no el cliente"
    Antes de culpar a NFS o a iSCSI, comprueba que la red da lo que crees (`iperf3`) y que el cliente no está saturado de CPU. Un `slat` alto en la salida de fio apunta al host; un `clat` alto, al camino hacia el almacenamiento.

## Guardar resultados en JSON

La salida de texto sirve para mirarla una vez. Para comparar entre ejecuciones, guarda JSON desde el principio.

```bash
for s in seqread-1M seqwrite-1M randread-4k randwrite-4k; do
  fio --section="$s" perfiles.fio \
    --output-format=json --output="resultados/$(date +%F)-$s.json"
done
```

Extraer lo esencial con `jq`:

```bash
jq -r '.jobs[] | [.jobname,
                  .read.iops, .read.bw,
                  .write.iops, .write.bw,
                  .read.clat_ns.percentile."99.000000"] | @tsv' \
  resultados/*.json
```

Guarda junto al JSON el fichero de job y la salida de `fio --version`, `uname -r` y `lsblk`. Un resultado sin el contexto que lo produjo no es comparable con nada, ni siquiera consigo mismo dentro de seis meses.

## Plantilla de informe

```markdown
## Medición de almacenamiento — <sistema> — <fecha>

**Objetivo:** (dimensionar / validar cambio / comparar A y B)

### Entorno
- Hardware / cabina, sistema de ficheros, opciones de montaje
- Kernel, versión de fio, y resultado de iperf3 si hay red por medio

### Método
- Fichero de job (adjunto), size, runtime, ramp_time, numjobs × iodepth
- Precondicionamiento: sí / no, cómo. Repeticiones: N

### Resultados
| Perfil | IOPS | BW | lat p50 | lat p95 | lat p99 |
|---|---|---|---|---|---|
| seqread 1M | | | | | |
| seqwrite 1M | | | | | |
| randread 4k | | | | | |
| randwrite 4k | | | | | |

### Observaciones
- Variación entre repeticiones, comportamiento del p99
- Limitaciones conocidas de esta medición

### Conclusión
```

La sección de limitaciones no es relleno: es lo que evita que el número se cite dentro de un año en un contexto en el que no vale.

## Troubleshooting

| Síntoma | Causa probable | Comprobación |
|---|---|---|
| IOPS absurdamente altos | Falta `direct=1`, o el fichero cabe en RAM | Revisar `direct` y subir `size` |
| `iodepth` no cambia nada | Motor síncrono, o `direct=0` con `libaio` | `ioengine=libaio` **y** `direct=1` |
| `Operation not supported` con `libaio` | El sistema de ficheros no soporta AIO directa | Probar `ioengine=psync` y documentarlo |
| Resultados distintos en cada pasada | Otra carga en la máquina, o falta `ramp_time` | Medir en reposo, repetir 3 veces |
| El rendimiento cae a mitad de prueba | Caché del SSD agotada — comportamiento normal | Alargar `runtime`; ese es el dato real |
| Lecturas instantáneas | Bloques nunca escritos en volumen *thin* | Rellenar con escritura secuencial primero |
| `Permission denied` sobre un dispositivo | Falta privilegio o el dispositivo está en uso | `lsblk`, `lsof`, ejecutar con permisos |

Un `err=` distinto de 0 en la cabecera del job invalida el resultado completo: fio sigue imprimiendo estadísticas aunque haya habido errores de I/O. Míralo siempre antes de leer las cifras.

## Buenas prácticas

- **Job files versionados en Git**, nunca comandos de una línea reconstruidos de memoria: la reproducibilidad es la mitad del valor de una medición.
- **`direct=1` por defecto.** Si quieres medir con caché, dilo explícitamente en el informe.
- **`ramp_time` siempre**, y proporcional al `runtime`. Sin él, la media incluye el calentamiento.
- **Publica p50, p95 y p99**, no medias sueltas. Una media sin percentiles es una cifra de marketing.
- **Tres repeticiones mínimo** y la dispersión anotada. Un solo número no distingue una mejora de una casualidad.
- **Precondiciona antes de medir escritura** en cualquier medio flash, y di cómo lo has hecho.
- **JSON desde el primer día**, con el job file y el contexto guardados al lado.
- **No compares cifras de fabricante con las tuyas**: están medidas con otro job, otra cola y otro medio. Compárate contigo mismo antes y después de un cambio.

## Referencias

- [Documentación oficial de fio](https://fio.readthedocs.io/en/latest/fio_doc.html)
- [Repositorio de fio](https://github.com/axboe/fio) · [Ejemplos de job files](https://github.com/axboe/fio/tree/master/examples)
- [Protocolos y métricas de almacenamiento](../protocols.md) · [Kubernetes CSI](../../kubernetes_csi.md)
