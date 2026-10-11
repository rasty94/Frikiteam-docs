---
title: "Networking: Comparativa de Rendimiento"
description: "Cómo medir el rendimiento de una red con iperf3, ping, mtr, ethtool y ss: metodología reproducible, MTU y offloads, e interpretación de resultados para comparar VPN y overlays."
keywords: "iperf3, ping, mtr, ethtool, ss, benchmark, throughput, latencia, jitter, mtu, offloads, wireguard, tailscale"
tags: ['networking']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 17 min
category: Redes
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Acceso SSH a dos nodos de prueba"
  - "Fundamentos de redes (TCP, MTU, latencia)"
  - "[MTU y MSS](mtu_mss_values.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Networking: Comparativa de Rendimiento

## El problema

Alguien afirma «WireGuard va a 9 Gbps y Tailscale a 7». Sin saber con qué MTU, cuántos flujos, en qué hardware y cuántas repeticiones, la cifra no vale nada: dos mediciones del mismo enlace pueden diferir más que dos tecnologías distintas. Un benchmark de red solo es útil si es **reproducible** y si sabes **qué limita** el resultado (el enlace, la CPU, la ventana TCP o el propio test).

Esta página reúne las herramientas clásicas, una metodología para que los números se puedan comparar y una guía para interpretarlos. **No publica cifras**: el rendimiento depende de tu hardware, tu kernel y tu red. Para comparar soluciones con tus propios datos usa la plantilla [vRouter Benchmark Template](vrouter_benchmark_template.md); para el análisis de VPN y mesh, [Tailscale vs NetBird: rendimiento](tailscale_netbird_performance.md).

!!! note "Qué cubre y qué no"
    Medición de rendimiento punto a punto entre dos hosts. El diagnóstico de fallos de conectividad (DNS, rutas, firewall) está en [Troubleshooting de red](troubleshooting.md).

## 📋 Tabla de Contenidos

- [Qué medir](#que-medir)
- [Preparar el laboratorio](#preparar-el-laboratorio)
- [iperf3: ancho de banda](#iperf3-ancho-de-banda)
- [ping y mtr: latencia y ruta](#ping-y-mtr-latencia-y-ruta)
- [ethtool y ss: interfaz y sockets](#ethtool-y-ss-interfaz-y-sockets)
- [MTU y offloads](#mtu-y-offloads)
- [Metodología](#metodologia)
- [Interpretar los resultados](#interpretar-los-resultados)
- [Comparar VPN y overlays](#comparar-vpn-y-overlays)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué medir

| Métrica | Qué responde | Herramienta |
|---|---|---|
| **Throughput** | Cuántos bits por segundo caben | `iperf3` |
| **Latencia (RTT)** | Cuánto tarda ir y volver | `ping`, `mtr` |
| **Jitter** | Cuánto varía la latencia | `iperf3 -u`, `ping` (desviación) |
| **Pérdida** | Qué fracción de paquetes no llega | `ping`, `mtr`, `iperf3 -u` |
| **Uso de CPU** | Qué coste tiene el cifrado o el reenvío | `top`, `mpstat` durante el test |
| **Estado TCP** | Retransmisiones, ventana, RTT visto por el kernel | `ss -ti` |

Una sola métrica engaña: un enlace puede tener mucho throughput y mala latencia bajo carga (bufferbloat), o buena latencia y poco ancho de banda.

## Preparar el laboratorio

- Dos nodos que controles, con el mismo hardware si es posible, y **sin otro tráfico** relevante.
- Herramientas instaladas: `iperf3`, `mtr`, `ping` y `ethtool`. En Debian/Ubuntu: `sudo apt install iperf3 mtr-tiny ethtool`.
- Anota versión de kernel (`uname -r`), de las herramientas (`iperf3 --version`), MTU de cada interfaz y modelo de NIC. Sin ese contexto el resultado no es comparable.
- Fija el firewall: un conjunto de reglas distinto entre dos pruebas es una variable más.

```bash
# Contexto mínimo que conviene guardar junto a cada resultado
uname -r
ip -br link
ip -br addr
ethtool eth0 | grep -E 'Speed|Duplex'
```

## iperf3: ancho de banda

Un extremo hace de servidor y el otro de cliente:

```bash
# Nodo B (servidor)
iperf3 -s

# Nodo A (cliente): 30 segundos, un flujo TCP
iperf3 -c 192.0.2.10 -t 30
```

Opciones habituales:

| Opción | Efecto |
|---|---|
| `-t N` | Duración en segundos |
| `-P N` | N flujos TCP en paralelo |
| `-R` | Modo inverso: el servidor envía y el cliente recibe |
| `-u -b 100M` | UDP a una tasa objetivo; informa de pérdida y jitter |
| `-i 1` | Informe cada segundo |
| `-J` | Salida JSON, útil para guardar y procesar |
| `-p PUERTO` | Puerto distinto del 5201 por defecto |

```bash
# Mide los dos sentidos por separado: los enlaces pueden ser asimétricos
iperf3 -c 192.0.2.10 -t 30
iperf3 -c 192.0.2.10 -t 30 -R

# Varios flujos: ¿un solo flujo agota la CPU o la ventana?
iperf3 -c 192.0.2.10 -t 30 -P 4

# UDP con tasa fija para ver pérdida y jitter
iperf3 -c 192.0.2.10 -u -b 200M -t 30

# Resultado en JSON para comparar después
iperf3 -c 192.0.2.10 -t 30 -J > resultado.json
```

!!! warning "Dependiente de la versión"
    Algunas opciones (por ejemplo la prueba bidireccional simultánea con `--bidir`) existen solo en versiones recientes de iperf3. Comprueba `iperf3 --help` en ambos extremos, y usa la misma versión en cliente y servidor.

Con UDP, `-b` fija cuánto intenta enviar el cliente; si lo pones por encima de lo que el enlace soporta, la «pérdida» que ves es la tuya, no la del enlace. Sube la tasa de forma escalonada hasta que aparezca pérdida.

## ping y mtr: latencia y ruta

```bash
# 100 paquetes, un resumen al final (min/avg/max/mdev)
ping -c 100 192.0.2.10

# Intervalo más corto (los intervalos muy bajos pueden requerir privilegios)
ping -c 100 -i 0.2 192.0.2.10

# Informe de mtr: 100 ciclos, sin DNS, formato legible
mtr -rwn -c 100 192.0.2.10
```

Qué mirar en `mtr`:

- **Loss%** en un salto intermedio pero 0 % en el destino casi siempre es limitación de ICMP en ese router, no pérdida real.
- Si la pérdida o la latencia **empieza en un salto y continúa hasta el final**, ahí está el problema.
- `StDev` alta indica jitter, aunque la media sea buena.

`ping` y `mtr` usan ICMP, que muchos equipos priorizan a la baja o filtran. Si el servicio real es TCP o UDP, contrasta con una medición del propio protocolo (por ejemplo `iperf3` o un `curl` temporizado).

## ethtool y ss: interfaz y sockets

`ethtool` dice qué negoció la NIC; `ss` dice qué ve el kernel dentro de las conexiones TCP.

```bash
# Velocidad y dúplex negociados
ethtool eth0

# Contadores de la NIC: busca errores, drops, descartes
ethtool -S eth0

# Estadísticas por interfaz del kernel
ip -s link show eth0

# Resumen de sockets
ss -s

# Detalle TCP de las conexiones al puerto de iperf3 durante el test
ss -ti dst 192.0.2.10
```

Del detalle de `ss -ti` interesa el RTT que mide el kernel, el tamaño de la ventana de congestión (`cwnd`) y las retransmisiones. Muchas retransmisiones con un enlace sano apuntan a pérdida o a un buffer desbordado en algún punto; una `cwnd` que no crece, a pérdida o a una ventana de recepción pequeña.

Una velocidad negociada inferior a la esperada (100 Mb/s en un puerto de 1 Gb/s) suele ser cable o puerto defectuoso, y hace inútil cualquier medición posterior.

## MTU y offloads

**MTU.** Un MTU mal ajustado fragmenta o descarta paquetes y hunde el rendimiento sin que los pings pequeños lo delaten. Los túneles (WireGuard, VXLAN, overlays) añaden cabeceras y reducen el MTU útil. Descubre el máximo sin fragmentar con `ping` y la bandera de no fragmentar (en Linux, `-M do`; el tamaño es la carga útil, sin las cabeceras de IP e ICMP):

```bash
# Si responde, el camino admite ese tamaño de carga sin fragmentar
ping -M do -s 1472 -c 3 192.0.2.10
```

Cómo se relaciona la carga con el MTU y cómo calcular el MSS está en [MTU y MSS](mtu_mss_values.md).

**Offloads.** Las NIC y el kernel agrupan y segmentan paquetes por hardware (TSO, GSO, GRO). Mejoran el throughput y reducen CPU, pero alteran lo que ven `tcpdump` y los contadores (verás «paquetes» mayores que el MTU).

```bash
# Ver qué offloads están activos
ethtool -k eth0

# Desactivar uno para una prueba concreta (se pierde al reiniciar)
sudo ethtool -K eth0 gro off
```

Desactivar offloads no es una optimización, es una herramienta de diagnóstico: úsala para aislar si un problema depende de ellos y vuelve a activarlos. Los nombres de las características varían según el controlador.

## Metodología

1. **Una variable cada vez.** Cambia MTU, o cifrado, o número de flujos; nunca varias a la vez.
2. **Repite.** Al menos varias ejecuciones por configuración; guarda cada una, no solo la mejor.
3. **Aisla.** Sin otro tráfico en el enlace, sin copias de seguridad ni actualizaciones en segundo plano. Si hay máquinas virtuales, fija en qué host corre cada extremo.
4. **Calienta.** La primera ejecución puede incluir arranque lento de TCP, cachés ARP o establecimiento del túnel; descártala o ignora los primeros segundos.
5. **Mide los dos sentidos** (`-R`), UDP y TCP, uno y varios flujos.
6. **Registra el contexto**: versiones, MTU, offloads, CPU, hora. Un resultado sin contexto no se puede reproducir.
7. **Mide también la CPU.** Un túnel que satura un núcleo está limitado por CPU, no por red.
8. **Baseline primero.** Mide el enlace sin VPN antes de medir con ella; el coste de la VPN es la diferencia.

## Interpretar los resultados

| Observación | Lectura probable |
|---|---|
| Un flujo rinde poco y `-P 4` mucho más | Limitado por un solo flujo (ventana TCP, RTT alto o un solo núcleo), no por el enlace |
| Throughput bajo y CPU al 100 % en un núcleo | Cuello de botella de CPU (cifrado, softirq), no de ancho de banda |
| Muchas retransmisiones en `ss -ti` | Pérdida, buffer desbordado o MTU incorrecto en el camino |
| Sentido normal y `-R` muy distintos | Enlace asimétrico, o configuración distinta en cada extremo |
| UDP con pérdida desde tasas bajas | Problema del enlace o de la cola; baja la tasa para localizar el umbral |
| Latencia buena en reposo y mala bajo carga | Bufferbloat: colas largas en algún dispositivo |
| Resultados que varían mucho entre repeticiones | Interferencia externa o falta de aislamiento; el dato no es fiable |
| Mejora al desactivar un offload | Interacción con el controlador o el túnel; investiga antes de dejarlo así |

El teórico de una línea de 10 Gb/s no es lo que verás con TCP: las cabeceras y la sobrecarga de cifrado reducen el valor útil. Compara siempre con tu baseline, no con el número del fabricante.

## Comparar VPN y overlays

Para comparar WireGuard, Tailscale, NetBird o ZeroTier con rigor:

- Mismo par de hosts, misma red subyacente y el mismo juego de pruebas para todos.
- Con cifrado activado en todos los casos y sin saltos por relays si lo que mides es el camino directo: en las soluciones mesh comprueba si la conexión es directa o va por relay, porque cambia por completo el resultado.
- Ajusta el MTU del túnel de forma explícita (ver [MTU y MSS](mtu_mss_values.md)) y repite.
- Registra latencia, throughput en ambos sentidos y CPU, y guárdalo en el formato de [vRouter Benchmark Template](vrouter_benchmark_template.md).

El análisis comparativo de Tailscale y NetBird está en [Tailscale vs NetBird: rendimiento](tailscale_netbird_performance.md). Las cifras aproximadas que figuraban en versiones anteriores de esta página se han retirado: no tenían hardware ni método asociados y no eran reproducibles.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `iperf3: error - unable to connect to server` | Servidor parado, puerto 5201 filtrado o IP errónea | Arrancar `iperf3 -s`, abrir el puerto, revisar la IP |
| Throughput muy inferior a la velocidad del enlace | Un solo flujo, CPU saturada o MTU incorrecto | Probar `-P`, mirar la CPU, revisar MTU |
| Ping pequeño funciona, transferencias grandes se cuelgan | MTU/PMTUD roto en el camino | `ping -M do -s` para localizar el MTU y ajustar |
| Pérdida en un salto de `mtr` pero no en el destino | Limitación de ICMP en ese router | Ignorar si el destino no pierde |
| Resultados distintos cada vez | Tráfico concurrente o falta de calentamiento | Aislar, descartar la primera ejecución, repetir |
| `ethtool` muestra menos velocidad de la esperada | Cable, puerto o negociación defectuosos | Cambiar cable o puerto y volver a medir |
| La captura muestra paquetes mayores que el MTU | Offloads (GRO/TSO) en la captura | Es normal; desactivarlos solo para diagnosticar |
| UDP con pérdida alta al subir `-b` | La tasa pedida excede el enlace | Reducir la tasa hasta que desaparezca la pérdida |

## Buenas prácticas

- Guarda el resultado bruto (`-J`) junto con la fecha, las versiones y la configuración.
- Una prueba es reproducible si otra persona puede repetirla con tu nota y obtener números parecidos.
- Mide antes de optimizar y vuelve a medir después; un cambio sin medida no es una mejora.
- No dejes el servidor `iperf3` expuesto: ábrelo solo durante la prueba y desde la IP del cliente.
- No ejecutes pruebas de saturación en redes de producción sin avisar.
- Desactiva offloads solo para diagnosticar y reactívalos.
- Documenta la topología (qué hay entre los dos nodos) tanto como los resultados.

## Referencias

- [Documentación de iperf3](https://iperf.fr/iperf-doc.php)
- [Documentación de WireGuard](https://www.wireguard.com/)
- [Páginas de manual de ethtool, ss y mtr](https://man7.org/linux/man-pages/)
- Páginas relacionadas: [MTU y MSS](mtu_mss_values.md), [Tailscale vs NetBird: rendimiento](tailscale_netbird_performance.md), [vRouter Benchmark Template](vrouter_benchmark_template.md), [Troubleshooting de red](troubleshooting.md)
