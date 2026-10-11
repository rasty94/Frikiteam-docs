---
title: "Forense digital en Linux: evidencias, memoria y línea temporal"
description: "Cómo recoger y analizar evidencias en un servidor Linux o una VM de Proxmox comprometidos: orden de volatilidad, cadena de custodia, triaje en vivo, adquisición de memoria y disco, Volatility 3, línea temporal y YARA."
keywords: "forense digital, dfir, linux, volatilidad, cadena de custodia, lime, avml, volatility 3, yara, línea temporal, mactime, proxmox, dc3dd"
tags: ['forensics', 'incident-response', 'cybersecurity', 'linux']
updated: 2026-10-11
difficulty: advanced
estimated_time: 33 min
category: Ciberseguridad
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "[Respuesta a incidentes](respuesta_incidentes.md)"
  - "Administración de Linux (procesos, systemd, montaje de discos)"
  - "Acceso root al servidor o al hipervisor Proxmox"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Forense digital en Linux: evidencias, memoria y línea temporal

## El problema

Has contenido el incidente y la gestión del caso va bien: hay severidad, canal, Incident Commander y un caso abierto. Entonces alguien pregunta lo importante: **¿cómo entraron, qué tocaron y desde cuándo?** Y descubres que tu "evidencia" son capturas de pantalla, un `history` que el atacante ya borró y un servidor que alguien reinició "para ver si se arreglaba". Sin datos recogidos con método no hay respuesta, y sin respuesta la erradicación es una apuesta.

La forense digital es la disciplina que responde a esas preguntas sin destruir lo que las contesta. En un homelab o una infraestructura pequeña no necesitas un laboratorio: necesitas un orden de trabajo, unas cuantas herramientas estándar y la disciplina de no improvisar.

!!! note "Qué cubre y qué no"
    Esta página trata la **recolección y el análisis** de evidencias en servidores Linux propios y VMs de Proxmox. La gestión del caso (severidad, roles, contención, TheHive, MISP, post-mortem) vive en [Respuesta a incidentes](respuesta_incidentes.md) y aquí no se repite. Es un enfoque exclusivamente defensivo: nada de técnicas ofensivas.

## 📋 Tabla de Contenidos

- [Orden de volatilidad](#orden-de-volatilidad)
- [Cadena de custodia práctica](#cadena-de-custodia-practica)
- [Triaje en vivo](#triaje-en-vivo)
- [Adquisición de memoria](#adquisicion-de-memoria)
- [Adquisición de disco](#adquisicion-de-disco)
- [Análisis de memoria con Volatility 3](#analisis-de-memoria-con-volatility-3)
- [Línea temporal con fechas MAC](#linea-temporal-con-fechas-mac)
- [Búsqueda con YARA](#busqueda-con-yara)
- [Logs centralizados: la mejor evidencia](#logs-centralizados-la-mejor-evidencia)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Orden de volatilidad

La evidencia no se pierde toda a la vez: unas cosas desaparecen en segundos y otras duran años. Se recoge **de lo más frágil a lo más estable** (el criterio de RFC 3227):

| Orden | Evidencia | Cuánto dura | Cómo se recoge |
| --- | --- | --- | --- |
| 1 | Memoria RAM | Hasta el reinicio | Volcado con LiME/AVML o desde el hipervisor |
| 2 | Conexiones de red y tablas ARP/rutas | Segundos o minutos | `ss`, `ip neigh`, `ip route` |
| 3 | Procesos, módulos, ficheros abiertos | Hasta que terminan | `ps`, `/proc`, `lsof`, `lsmod` |
| 4 | Disco | Persistente, pero modificable | Imagen o snapshot del volumen |
| 5 | Logs remotos y copias de seguridad | Meses o años | Exportar desde el colector central |

Los logs locales los dejo fuera del orden a propósito: el atacante con root los puede reescribir. Los que valen son los que ya salieron de la máquina (ver [más abajo](#logs-centralizados-la-mejor-evidencia)).

!!! danger "No apagues la máquina de entrada"
    Un apagado (o un reinicio) borra la memoria, las conexiones y los procesos, y puede disparar limpiezas programadas por el propio atacante. Un apagado brusco tampoco garantiza un disco consistente. **Aísla la red, deja la máquina encendida y recoge en orden.** Apagar es el último paso, y solo si ya tienes imagen y volcado. En una VM de Proxmox, además, tienes una opción mejor que apagar: capturar desde el hipervisor sin tocar el invitado.

Aislar sin apagar, en una VM de Proxmox, es desconectar el enlace de la interfaz virtual:

```bash
# Ver la configuración actual de la tarjeta de red de la VM 100
qm config 100 | grep ^net

# Añadir link_down=1 conservando el resto de opciones (MAC incluida)
qm set 100 --net0 virtio=BC:24:11:AA:BB:CC,bridge=vmbr0,link_down=1
```

Copia la línea `net0` tal cual sale de `qm config` y añade solo `link_down=1`: si cambias la MAC, alteras evidencia. En un host físico, la alternativa es cortar el puerto del switch o aplicar una regla de firewall en el borde, no en la propia máquina. Las reglas de red concretas están en [Firewall y red](firewall_red.md).

## Cadena de custodia práctica

Un artefacto sin trazabilidad es una anécdota. La parte mínima y práctica, sin burocracia:

1. **Hash de todo, en el momento de recogerlo**, y de nuevo tras cada copia.
2. **Un registro** de quién recogió qué, cuándo (en UTC), desde dónde y con qué comando.
3. **Almacenamiento de solo lectura** para los originales; se analiza siempre sobre copias.

```bash
# Directorio de caso en el equipo forense (NO en la máquina comprometida)
CASO=INC-2026-0042
mkdir -p /evidencia/$CASO/{memoria,disco,triaje,logs}

# Hash de cada artefacto + manifiesto
cd /evidencia/$CASO
sha256sum memoria/* disco/* triaje/* logs/* > MANIFIESTO.sha256

# Comprobarlo cuando haga falta (tras copiar, antes de analizar)
sha256sum -c MANIFIESTO.sha256

# Registro de custodia: una línea por acción, anexado, nunca editado
echo "$(date -u +%FT%TZ) | $(whoami) | recogido memoria web-prod-01 | avml" >> CUSTODIA.log
```

Cuando termines de recoger, pasa los originales a solo lectura. Con permisos y atributo inmutable en un sistema ext4 propio:

```bash
chmod -R a-w /evidencia/$CASO/{memoria,disco}
sudo chattr +i /evidencia/$CASO/memoria/* /evidencia/$CASO/disco/*
```

`chattr +i` protege contra borrados accidentales, no contra alguien con root en el equipo forense. Para evidencia que pueda acabar en una aseguradora o ante un regulador, usa almacenamiento inmutable de verdad (object-lock, WORM) como en [Respuesta a incidentes](respuesta_incidentes.md#chain-of-custody), donde está además la plantilla `custody.yaml`. Los backups del propio material forense siguen las pautas de [Backup seguro](backup_seguro.md).

!!! warning "El equipo forense también es un riesgo"
    No analices en la máquina comprometida ni en un portátil con tus claves de producción. Usa un equipo o VM dedicados, sin acceso a producción, y trata las imágenes como código hostil: no ejecutes nada que salga de ellas.

## Triaje en vivo

El objetivo del triaje es capturar el estado volátil y decidir si merece la pena un volcado completo. Con la máquina comprometida **no te fíes de sus binarios**: un `ps` o un `ls` sustituidos pueden esconder justo lo que buscas. Siempre que puedas, ejecuta desde un medio de confianza (USB de solo lectura o ISO montada) con binarios estáticos o copiados de un sistema limpio de la misma distribución, y escribe la salida en un medio externo, nunca en el disco comprometido.

!!! warning "Los binarios de confianza no bastan contra un rootkit de kernel"
    Si el atacante cargó un módulo de kernel, el kernel miente a cualquier binario, por limpio que sea. Por eso se compara siempre la visión en vivo con la del volcado de memoria y la del disco analizado fuera de la máquina. Un proceso que aparece en uno y no en otro es una pista.

Un script de captura que no modifica el sistema (solo lectura, salida a un directorio externo):

```bash
#!/bin/bash
# triaje.sh — ejecutar desde medio de confianza. Uso: ./triaje.sh /mnt/usb/triaje
OUT="$1"; mkdir -p "$OUT"
ts() { date -u +%FT%TZ; }

{ ts; uname -a; uptime; } > "$OUT/00-sistema.txt"
ss -tupan                > "$OUT/10-conexiones.txt"
{ ip neigh; ip route; }  > "$OUT/11-vecinos-rutas.txt" 2>&1
ps auxf                  > "$OUT/20-procesos.txt"
lsof -nP +L1             > "$OUT/21-ficheros-borrados-abiertos.txt" 2>&1
lsmod                    > "$OUT/22-modulos.txt"
last -F                  > "$OUT/30-last.txt" 2>&1
lastb -F                 > "$OUT/31-lastb.txt" 2>&1
w                        > "$OUT/32-sesiones.txt"
cat /etc/ld.so.preload   > "$OUT/40-ld-so-preload.txt" 2>&1
sha256sum "$OUT"/*       > "$OUT/MANIFIESTO.sha256"
```

Lo que se mira después con calma, en el equipo forense, sobre esos ficheros y con consultas puntuales en vivo:

- **Conexiones** (`ss -tupan`): conexiones establecidas hacia IPs desconocidas, puertos a la escucha que no deberían existir, y a qué PID pertenecen.
- **Procesos** (`ps auxf`): el árbol (`f`) muestra quién lanzó a quién. Un `sh` colgando de un servidor web, o procesos con nombre de kernel (`[kworker]`) pero con ruta de usuario, son clásicos.
- **Binario real de un proceso**: `ls -l /proc/<pid>/exe` enseña a qué fichero apunta. Si el ejecutable se borró tras lanzarlo, el enlace aparece marcado como `(deleted)`, y el contenido sigue accesible en `/proc/<pid>/exe`. Es una de las evidencias más valiosas, cópiala:

```bash
PID=4242
ls -l /proc/$PID/exe /proc/$PID/cwd
tr '\0' ' ' < /proc/$PID/cmdline; echo
cp /proc/$PID/exe /evidencia/INC-2026-0042/triaje/pid-$PID.bin
sha256sum /evidencia/INC-2026-0042/triaje/pid-$PID.bin
```

- **Ficheros abiertos** (`lsof`): `lsof -nP +L1` lista los ficheros abiertos que ya no tienen enlace en disco, o sea, binarios y logs borrados que siguen vivos. `lsof -p <pid>` da el detalle de un proceso concreto.
- **Accesos** (`last -F`, `lastb`, `w`): inicios de sesión con fecha completa, fallidos y sesiones vivas. Compara con quién *debería* haber entrado.

### Logs con rangos de tiempo

Acota siempre por ventana: una frase de "desde cuándo" evita ahogarse en el journal. Usa `--utc` para que las horas coincidan con el resto del caso.

```bash
# Todo lo ocurrido en la ventana sospechosa
journalctl --utc --since "2026-10-10 22:00" --until "2026-10-11 02:00" -o short-iso

# Solo SSH (el nombre de la unit es ssh o sshd según la distribución)
journalctl --utc -u ssh --since "2026-10-10" -o short-iso | grep -E "Accepted|Failed|Invalid"

# Analizar una copia del journal fuera de la máquina comprometida
journalctl --utc --file /evidencia/INC-2026-0042/logs/system.journal --since "2026-10-10"
```

### Usuarios, claves SSH, cron y units de systemd

La persistencia es lo que casi siempre deja el atacante. Los sitios a revisar, todos de solo lectura:

```bash
# Usuarios con shell o UID 0 inesperados
awk -F: '$3==0 || $7 !~ /(nologin|false)$/ {print $1, $3, $7}' /etc/passwd

# Claves SSH autorizadas: contenido y fecha de modificación
ls -l --time-style=full-iso /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null
cat /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null

# Cron de sistema y de usuarios, y timers de systemd
ls -la /etc/cron.* /var/spool/cron/ 2>/dev/null
systemctl list-timers --all --no-pager

# Units creadas o modificadas recientemente (ajusta la fecha a tu ventana)
find /etc/systemd/system /usr/lib/systemd/system -type f -newermt "2026-10-01" -ls
systemctl list-unit-files --state=enabled --no-pager
```

Para qué es normal y qué no en SSH, mira [Seguridad SSH](../linux/ssh_security.md); para el modelo de units y timers, [Systemd](../linux/systemd.md). Si la distribución usa paquetes, comprueba además la integridad de los binarios instalados con `debsums -c` (Debian/Ubuntu, si está instalado) o `rpm -Va` (RHEL y derivadas): los ficheros de paquete modificados son sospechosos.

## Adquisición de memoria

La RAM contiene lo que el disco no: procesos sin fichero, claves en claro, conexiones y el historial de comandos que no llegó a escribirse. Hay dos caminos según tengas o no un hipervisor debajo.

### Dentro de la máquina: LiME o AVML

- **LiME** es un módulo de kernel que vuelca la memoria a un fichero. Hay que compilarlo contra las cabeceras del kernel *exacto* que corre la máquina.
- **AVML** es un binario autónomo que no requiere compilar un módulo, y por eso suele ser la opción cómoda en servidores con kernels de distribución.

```bash
# AVML: un solo binario, ejecutado desde el medio de confianza
sudo ./avml acquire /mnt/usb/memoria/web-prod-01.lime

# LiME: módulo compilado ANTES (en una VM limpia con el mismo kernel)
sudo insmod ./lime-$(uname -r).ko "path=/mnt/usb/memoria/web-prod-01.lime format=lime"

# En ambos casos, hash inmediato
sha256sum /mnt/usb/memoria/web-prod-01.lime | tee -a /mnt/usb/memoria/MANIFIESTO.sha256
```

!!! warning "Dependencia con el kernel"
    LiME necesita un módulo compilado para la versión exacta del kernel en ejecución, y compilar en la máquina comprometida cambia el sistema y se apoya en un compilador que no es de fiar. Compílalo de antemano en una VM idéntica. Con AVML te evitas el módulo, pero **el análisis posterior sigue necesitando los símbolos de ese mismo kernel** (ver Volatility 3 más abajo). Anota `uname -r` en la custodia: sin él, el volcado puede quedar sin interpretar.

Escribir el volcado en un USB o en un recurso de red montado evita sobrescribir lo que quizá quede sin asignar en el disco. Cualquiera de las dos herramientas altera algo de memoria al ejecutarse; es inevitable, y se documenta en la custodia.

### En Proxmox: desde el hipervisor, sin tocar el invitado

Si la máquina es una VM, el hipervisor ve su memoria sin ejecutar nada dentro, de modo que el atacante no puede interferir ni detectarlo. Dos opciones, a elegir según el espacio y si necesitas conservar el estado:

**Snapshot con estado de RAM.** Guarda la memoria de la VM dentro del snapshot, además del disco, y la VM sigue en marcha:

```bash
qm snapshot 100 INC-2026-0042 --vmstate 1 --description "Evidencia IR"
```

El estado de RAM queda en el almacenamiento del snapshot en un formato propio de QEMU, no como un volcado plano que Volatility lea directamente. Sirve para restaurar el estado exacto en un entorno aislado (ver abajo) y analizar allí.

**Volcado de memoria del invitado por el monitor de QEMU.** QEMU tiene un comando de monitor para escribir la memoria del invitado a un fichero, accesible desde `qm monitor`:

```bash
qm monitor 100
# dentro del monitor (HMP):
# dump-guest-memory /var/tmp/vm100-mem.elf
```

!!! warning "Depende de la versión y no está probado aquí"
    Según la documentación de QEMU, `dump-guest-memory` escribe un ELF que pueden leer `crash` o `gdb`, y con `-z`, `-l` o `-s` usa el formato kdump comprimido. Si Volatility lee ese volcado sin conversión depende de su versión: pruébalo en un laboratorio antes del día malo. El fichero se escribe en el **host**, así que necesita espacio libre allí y se debe mover y hashear de inmediato.

Sea cual sea el método, el procedimiento es el mismo: copia el artefacto fuera del hipervisor, calcula el `sha256sum`, regístralo en la custodia y trabaja sobre la copia.

## Adquisición de disco

Con la memoria ya recogida, toca el disco. Dos reglas: **no montes el original** y **no escribas en él**.

### Imagen bit a bit

Si es un disco físico (conectado como dispositivo de bloque, mejor con la máquina apagada tras el volcado, o desde un arranque de un sistema forense):

```bash
# dc3dd calcula el hash mientras copia y escribe un log
sudo dc3dd if=/dev/sdb of=/evidencia/INC-2026-0042/disco/sdb.img \
  hash=sha256 log=/evidencia/INC-2026-0042/disco/sdb.log

# Alternativa con dd estándar
sudo dd if=/dev/sdb of=/evidencia/INC-2026-0042/disco/sdb.img bs=4M status=progress
sha256sum /dev/sdb /evidencia/INC-2026-0042/disco/sdb.img
```

Si copias un disco que sigue montado y en uso, el hash de origen y copia **no coincidirán** porque el original cambia mientras lo lees. Para sistemas en vivo, la copia correcta es la de un snapshot, que está congelado.

### Snapshot del volumen de la VM

En Proxmox no hace falta tocar el disco del invitado: congélalo en el hipervisor y exporta desde ahí.

```bash
# Backup consistente de la VM sin pararla; resultado: un único fichero de backup
vzdump 100 --mode snapshot --storage forense --compress zstd
```

El resultado es un fichero de backup que puedes copiar al equipo forense y restaurar como una VM nueva **sin red** (`qmrestore`, y después quitar o dejar en `link_down=1` la tarjeta antes de arrancarla). Es mucho más seguro que analizar sobre la VM original. Si tu almacenamiento es ZFS o LVM-thin, también puedes hacer un snapshot del volumen subyacente; los detalles del almacenamiento local están en [ZFS y LVM](../storage/zfs_lvm.md), y las características de la plataforma en [Proxmox base](../proxmox/proxmox_base.md).

### Montaje de solo lectura sobre una copia

Nunca montes la imagen original: trabaja sobre una copia de la copia, y aun así monta con lo mínimo.

```bash
# Dispositivo loop de solo lectura, con las particiones expuestas
LOOP=$(sudo losetup --find --show --read-only --partscan copia-sdb.img)

# ext4: solo lectura, sin ejecutar, sin dispositivos, sin reproducir el journal
sudo mkdir -p /mnt/evidencia
sudo mount -o ro,noexec,nodev,noload ${LOOP}p1 /mnt/evidencia
```

La opción `noload` evita que ext4 reproduzca el journal al montar; sin ella, incluso un montaje `ro` puede escribir. Si el sistema de ficheros estaba sucio, `noload` te deja ver el estado tal cual, aunque algunos ficheros recientes parezcan incompletos. Con LVM dentro de la imagen, activa los volúmenes en modo solo lectura antes de montar. Al terminar: `umount /mnt/evidencia` y `losetup -d "$LOOP"`.

## Análisis de memoria con Volatility 3

Volatility 3 es el marco estándar para interpretar volcados de memoria: reconstruye procesos, conexiones y módulos a partir de las estructuras del kernel. En Linux necesita saber **cómo es el kernel que generó el volcado**, y eso se lo da una tabla de símbolos (ISF) específica de esa versión.

!!! warning "Depende de la versión y de los símbolos del kernel"
    Los plugins de Linux de Volatility 3 funcionan solo si tiene los símbolos del kernel exacto del volcado: o bien un fichero ISF ya construido para esa versión, o bien uno generado con `dwarf2json` a partir del kernel con símbolos de depuración. Sin ellos, el volcado no se interpreta. Los nombres de plugin de abajo son los habituales, pero **cambian entre versiones**: comprueba los disponibles con `-h` en tu instalación antes de fiarte de ellos.

```bash
# Ver los plugins de Linux disponibles en tu versión
python3 vol.py -h | grep -i linux

# Ejemplos habituales (nombres a verificar según versión)
python3 vol.py -f web-prod-01.lime linux.pslist.PsList
python3 vol.py -f web-prod-01.lime linux.pstree.PsTree
python3 vol.py -f web-prod-01.lime linux.bash.Bash
python3 vol.py -f web-prod-01.lime linux.lsmod.Lsmod
python3 vol.py -f web-prod-01.lime linux.sockstat.Sockstat
```

Qué buscar con cada uno, sin entrar en salidas concretas:

- **Listado y árbol de procesos**: compara con el `ps auxf` del triaje. Un proceso presente en memoria y ausente en el `ps` en vivo apunta a ocultación; procesos hijo raros de servicios de red son el patrón de una intrusión por una vulnerabilidad web.
- **Historial de bash en memoria**: recupera comandos que el atacante borró del `.bash_history` o que nunca se escribieron al salir con `unset HISTFILE`.
- **Módulos del kernel**: un módulo que no reconoces es la señal de un rootkit; contrástalo con `lsmod` del triaje.
- **Sockets**: las conexiones y puertos a la escucha en el momento del volcado, asociadas a PID.

Los volcados de AVML y LiME en formato `lime` los lee Volatility directamente. El resultado de un volcado de QEMU en ELF puede requerir un paso de conversión según versión: ese es otro motivo para probar el flujo completo en laboratorio.

## Línea temporal con fechas MAC

Cada fichero guarda tres fechas: **M**odificación del contenido (`mtime`), **A**cceso (`atime`) y **C**ambio de metadatos (`ctime`). Ordenadas, cuentan la historia de la intrusión: cuándo llegó el binario, cuándo se editó la unit, cuándo se tocó `authorized_keys`.

```bash
# Línea temporal rápida con find sobre el sistema montado en solo lectura
# Columnas: mtime | ctime | atime | usuario | modo | ruta
sudo find /mnt/evidencia -xdev -type f \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS | %CY-%Cm-%Cd %CH:%CM:%CS | %AY-%Am-%Ad %AH:%AM:%AS | %u | %m | %p\n' \
  | sort > /evidencia/INC-2026-0042/linea-temporal.txt

# Todo lo cambiado dentro de la ventana de la intrusión
sudo find /mnt/evidencia -xdev -newermt "2026-10-10 22:00" ! -newermt "2026-10-11 03:00" -ls
```

Para una línea temporal completa y con los metadatos del propio sistema de ficheros, The Sleuth Kit (`fls` + `mactime`) trabaja directamente sobre la imagen, sin montarla, e incluye ficheros borrados:

```bash
# 1. Body file con todos los ficheros, incluidos los borrados (usa -o <sector> si la imagen tiene particiones)
fls -r -m / copia-sdb.img > cuerpo.txt

# 2. Línea temporal ordenada, en CSV, en UTC
mactime -b cuerpo.txt -d -z UTC > linea-temporal.csv
```

Para correlacionar varias fuentes a la vez (disco, journal, logs web) en una sola línea temporal existe Plaso (`log2timeline`), aunque es más pesado y para un incidente pequeño suele sobrar.

Dos cosas a tener claras al interpretar fechas:

- **`mtime` y `atime` se pueden falsificar** con `touch` y es trivial. `ctime` no se puede fijar desde el espacio de usuario: cambia siempre que se toca el inodo, así que un `ctime` posterior a un `mtime` "antiguo" delata la manipulación.
- **`atime` puede estar desactivada o actualizarse poco**: la mayoría de los sistemas montan con `relatime`, así que no es una fuente fiable de "quién leyó qué".

Una pista que casi siempre da resultado: busca el primer fichero nuevo de la ventana y el último, y cruza esos instantes con los logs de acceso y con el journal.

## Búsqueda con YARA

YARA busca patrones (cadenas, secuencias de bytes) en ficheros y en volcados. Sirve para encontrar todas las copias de un binario sospechoso, o para barrer un sistema montado y una memoria con las firmas de lo que ya has identificado.

```yara
rule minero_cripto_cadenas
{
    meta:
        descripcion = "Cadenas típicas de un minero de criptomonedas"
        caso = "INC-2026-0042"
    strings:
        $a = "stratum+tcp://" ascii
        $b = "xmrig" ascii nocase
        $c = "cryptonight" ascii nocase
    condition:
        2 of them
}
```

```bash
# Sobre el sistema de ficheros montado en solo lectura, recursivo
yara -r minero.yar /mnt/evidencia

# Sobre un volcado de memoria (tratado como un fichero binario más)
yara minero.yar /evidencia/INC-2026-0042/memoria/web-prod-01.lime
```

Aplica las reglas de IoC que salgan del caso: los hashes y cadenas que ya hayas cargado como observables en TheHive/MISP (ver [Respuesta a incidentes](respuesta_incidentes.md#misp-inteligencia-de-amenazas)) se convierten fácilmente en reglas. Cuida los falsos positivos: una regla demasiado general marca software legítimo, y en una memoria de varios gigabytes también tarda.

## Logs centralizados: la mejor evidencia

Todo lo que está en la máquina comprometida es, en rigor, testimonio del sospechoso: con root, el atacante edita `auth.log`, vacía el journal y borra el historial. **Los logs que salieron de la máquina antes del compromiso son la única evidencia que el atacante no pudo reescribir.**

Por eso, la inversión forense más rentable se hace antes de que ocurra nada:

- **Un colector central** (Wazuh, rsyslog, `systemd-journal-remote`) que reciba los eventos en tiempo casi real, con retención suficiente para cubrir el tiempo de permanencia típico de un atacante (meses, no días).
- **Que el colector sea de solo anexado** y con credenciales distintas a las del resto de la infraestructura: si el mismo acceso lo borra todo, no es evidencia.
- **Relojes sincronizados** (NTP/chrony) en todos los hosts. Una línea temporal con relojes desfasados no se puede correlacionar.
- **Auditoría del kernel** (`auditd`) con reglas sobre ejecución de binarios, cambios en `/etc` y `authorized_keys`, que responde a "qué ejecutó el usuario X".

Cómo montar la recolección y las reglas en Wazuh está en [Wazuh: logs y reglas](../monitoring/wazuh_logs.md), y el stack completo de detección (Falco, Wazuh, alertas) en [Monitoreo de seguridad](monitoreo_seguridad.md). Si el manager está configurado para archivar todos los eventos (no solo las alertas), conserva el histórico para consulta forense; revisa en tu versión qué opción lo activa y cuánto espacio consume. Las medidas para que esos logs existan por defecto, como `auditd` y el endurecimiento del sistema, están en [Hardening Linux](hardening_linux.md), y los requisitos de retención en [Cumplimiento y auditoría](cumplimiento_auditoria.md).

## Troubleshooting

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| Volatility no reconoce el volcado de Linux | Faltan los símbolos del kernel exacto | Obtén o genera el ISF de esa versión (`uname -r` anotado en la custodia) |
| `insmod` de LiME falla con "Invalid module format" | Módulo compilado para otro kernel | Recompila contra las cabeceras de la versión en ejecución, en una VM idéntica |
| El hash de la imagen no coincide con el del disco origen | El origen estaba montado y cambiando | Adquiere desde un snapshot, no desde el disco en uso |
| Al montar la imagen, ext4 modifica el sistema de ficheros | Falta `noload` o se montó el original | Monta una copia con `ro,noexec,nodev,noload` |
| `ps` en vivo no muestra un proceso que sí está en el volcado | Rootkit o binarios sustituidos | Confía en el volcado y el disco analizados fuera; trata la máquina como no fiable |
| `ls -l /proc/<pid>/exe` muestra `(deleted)` | El ejecutable se borró tras lanzarse | Cópialo desde `/proc/<pid>/exe` antes de que termine el proceso |
| Las horas de la línea temporal no cuadran entre fuentes | Zonas horarias mezcladas o reloj desfasado | Normaliza todo a UTC y anota el desfase del reloj de cada host |
| El volcado desde el monitor de QEMU no lo lee Volatility | Formato ELF de QEMU sin convertir, o versión distinta | Prueba el flujo en laboratorio; como alternativa, usa AVML dentro del invitado |

## Buenas prácticas

- **Prepara antes de necesitarlo.** Ten el USB con binarios de confianza, AVML y un módulo LiME compilado para tus kernels, y el equipo forense listo. A las 03:14 no se compila nada.
- **Anota los kernels en uso** (`uname -r` por host en el inventario): sin ese dato no hay símbolos para Volatility.
- **Orden de volatilidad, siempre.** Memoria antes que disco; disco antes que apagar.
- **Hash y registro en el momento**, no al final. Lo que no se hashea al recogerlo no se puede demostrar íntegro.
- **Nunca analices sobre el original.** Trabaja sobre copias, monta en solo lectura y sin ejecutar.
- **Prefiere el hipervisor.** En Proxmox, un snapshot o un backup con la VM en marcha no depende de un invitado en el que no puedes confiar.
- **Envía logs fuera de la máquina desde el día uno**, con relojes sincronizados. Es la evidencia que sobrevive al compromiso.
- **Ensaya el flujo una vez** en un laboratorio con una VM desechable. Lo no probado falla justo cuando importa.
- **Documenta lo que no sabes.** Una pregunta abierta honesta vale más que una conclusión inventada.

## Referencias

- [RFC 3227 — Guía para la recolección y archivo de evidencias](https://www.rfc-editor.org/rfc/rfc3227)
- [NIST SP 800-86 — Guía para integrar técnicas forenses en la respuesta a incidentes](https://csrc.nist.gov/pubs/sp/800/86/final)
- [Volatility 3 — documentación](https://volatility3.readthedocs.io/)
- [LiME](https://github.com/504ensicsLabs/LiME) · [AVML](https://github.com/microsoft/avml)
- [The Sleuth Kit](https://www.sleuthkit.org/sleuthkit/) · [YARA](https://yara.readthedocs.io/)
- [Respuesta a incidentes](respuesta_incidentes.md) · [Monitoreo de seguridad](monitoreo_seguridad.md) · [Hardening Linux](hardening_linux.md)
- [Wazuh: logs y reglas](../monitoring/wazuh_logs.md) · [Seguridad SSH](../linux/ssh_security.md) · [Systemd](../linux/systemd.md)
- [Backup seguro](backup_seguro.md) · [Cumplimiento y auditoría](cumplimiento_auditoria.md)
- [QEMU: monitor](https://www.qemu.org/docs/master/system/monitor.html)
- [QEMU: comandos HMP (dump-guest-memory)](https://gitlab.com/qemu-project/qemu/-/blob/master/hmp-commands.hx)
