---
title: "eBPF y Cilium: red, seguridad y observabilidad en Kubernetes"
description: "Qué es eBPF y cómo lo aprovecha Cilium como CNI: instalación, sustitución de kube-proxy, políticas L3/L4/L7 y por FQDN, Hubble para depurar tráfico bloqueado, Tetragon y herramientas eBPF en el host."
keywords: "ebpf, cilium, hubble, tetragon, cni, kube-proxy, networkpolicy, ciliumnetworkpolicy, toFQDNs, bpftrace, bcc, kubernetes"
tags: ['ebpf', 'kubernetes', 'networking', 'observability']
updated: 2026-10-11
difficulty: advanced
estimated_time: 24 min
category: Contenedores
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Clúster Kubernetes funcional y kubectl (ver Kubernetes base)"
  - "Conceptos de CNI, Services y NetworkPolicy"
  - "Acceso a los nodos para comprobar la versión del kernel"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# eBPF y Cilium: red, seguridad y observabilidad en Kubernetes

## El problema

Tu clúster funciona, hasta que deja de hacerlo sin explicación. Un pod no llega a otro y no sabes si es DNS, una `NetworkPolicy`, el `Service` o la tabla de `iptables` del nodo. Con kube-proxy en modo iptables esa tabla crece con cada Service y cada endpoint; leerla con `iptables-save` es arqueología, y las `NetworkPolicy` que bloquean tráfico no dejan ningún rastro que puedas consultar.

eBPF cambia el sitio donde se decide y se observa el tráfico: en el kernel, con datos estructurados por conexión. Cilium es la implementación de CNI que lo aprovecha: red, balanceo de Services, políticas y observabilidad (Hubble) con un único agente por nodo.

!!! note "Qué cubre y qué no"
    Esta página trata Cilium como **CNI y plano de datos**: instalación, políticas, Hubble y herramientas eBPF. La comparativa de Cilium frente a Istio y Linkerd como malla de servicios (mTLS, canary, overhead) vive en [Service Mesh](service_mesh.md) y no se repite aquí.

## 📋 Tabla de Contenidos

- [eBPF en dos párrafos](#ebpf-en-dos-parrafos)
- [Requisitos](#requisitos)
- [Instalar Cilium](#instalar-cilium)
- [Sustituir kube-proxy](#sustituir-kube-proxy)
- [Políticas de red](#politicas-de-red)
- [Observabilidad con Hubble](#observabilidad-con-hubble)
- [Seguridad en runtime con Tetragon](#seguridad-en-runtime-con-tetragon)
- [eBPF fuera de Kubernetes](#ebpf-fuera-de-kubernetes)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## eBPF en dos párrafos

eBPF permite cargar pequeños programas en el kernel de Linux sin recompilarlo ni escribir un módulo. Antes de ejecutarse, el **verificador** del kernel los analiza y rechaza los que podrían colgar la máquina (bucles sin límite, accesos a memoria fuera de rango), y después un compilador JIT los traduce a código nativo. Los programas no tienen estado propio: comparten datos entre sí y con el espacio de usuario mediante **mapas** (tablas hash, arrays, colas), que es donde un agente como Cilium guarda, por ejemplo, la tabla de endpoints o las reglas de política.

Cada programa se engancha a un **hook**, un punto del kernel donde se ejecuta cuando ocurre algo. Los que más aparecen en red y observabilidad son:

| Hook | Dónde actúa | Uso típico |
|---|---|---|
| **XDP** | En el driver de la tarjeta, antes de que exista el paquete en el stack | Descartar o redirigir tráfico a máxima velocidad (anti-DDoS, balanceo) |
| **tc** (traffic control) | En la entrada o salida de una interfaz, con el paquete ya construido | Enrutado de pods, políticas, NAT de Services |
| **kprobes** | Entrada o salida de casi cualquier función del kernel | Diagnóstico puntual; depende de la versión del kernel |
| **tracepoints** | Puntos estables que el kernel declara explícitamente | Trazar llamadas al sistema y eventos de forma portable |

La razón por la que sustituye a iptables en el datapath es de coste, no de moda. Una cadena de iptables se evalúa **regla a regla**, de modo que el tiempo por paquete y el de actualización crecen con el número de Services y de reglas. Con eBPF la decisión es una búsqueda en un mapa hash, con coste prácticamente independiente del tamaño del clúster, y el tráfico entre pods puede saltarse capas del stack que iptables obliga a recorrer.

## Requisitos

!!! warning "Depende del kernel"
    Cilium necesita un kernel con soporte eBPF suficiente, y cada funcionalidad (reemplazo de kube-proxy, cifrado WireGuard, enrutado con `bpf host routing`, Egress Gateway) exige una versión mínima distinta. No hay una cifra única válida para todo: consulta la tabla de requisitos de la versión de Cilium que vayas a instalar y compárala con `uname -r` en **cada nodo**. Las distribuciones de servidor actuales suelen cumplir lo básico; los kernels antiguos de algunas imágenes cloud o de NAS no.

Comprueba la versión con `uname -r` en cada nodo y que `CONFIG_BPF`, `CONFIG_BPF_SYSCALL` y `CONFIG_BPF_JIT` estén activas en la configuración del kernel (`/boot/config-$(uname -r)` o `/proc/config.gz`, según la distribución).

Además, Cilium es el **único CNI** del clúster: no se instala encima de Flannel o Calico, hay que desactivar el anterior antes. En k3s, por ejemplo, el servidor se arranca con `--flannel-backend=none --disable-network-policy`.

## Instalar Cilium

El CLI `cilium` es lo más corto para un homelab; Helm es mejor con GitOps, porque los valores quedan en un fichero versionado.

### Con el CLI

```bash
cilium install
cilium status --wait
```

`cilium status --wait` espera a que el agente (DaemonSet), el operador y los demás componentes estén listos, y resume su estado por componente. Para validar de verdad la red, la suite de pruebas despliega pods temporales en un namespace propio y prueba conectividad entre nodos, hacia Services y hacia el exterior:

```bash
cilium connectivity test
```

Tarda varios minutos; si falla solo alguna prueba de acceso externo, comprueba antes si el clúster tiene salida a internet.

### Con Helm

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update

helm install cilium cilium/cilium \
  --namespace kube-system \
  --values cilium-values.yaml
```

Un `cilium-values.yaml` mínimo, con Hubble activado:

```yaml
# cilium-values.yaml
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

!!! warning "Depende de la versión"
    Los nombres de los valores de Helm y los flags del CLI cambian entre versiones menores (ver el siguiente apartado). Fija la versión con `--version` en Helm, y antes de actualizar lee las *upgrade notes* de la versión de destino, no las de la última estable.

## Sustituir kube-proxy

Cilium puede encargarse del balanceo de Services (ClusterIP, NodePort, LoadBalancer) con eBPF y dejar kube-proxy sin trabajo. Es lo que da el mayor beneficio de rendimiento, pero tiene una trampa: sin kube-proxy, el agente de Cilium no puede usar el Service `kubernetes` para llegar al API server, porque ese Service lo implementaría él mismo. Hay que indicarle **la dirección real del API server**.

```bash
cilium install \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=192.168.1.10 \
  --set k8sServicePort=6443
```

El equivalente en Helm es el mismo trío de valores bajo `kubeProxyReplacement`, `k8sServiceHost` y `k8sServicePort`. Usa la IP o el nombre DNS de un endpoint estable del API server (la VIP del balanceador si tienes varios control planes), no la de un único nodo.

!!! warning "Depende de la versión"
    El valor de `kubeProxyReplacement` ha cambiado: versiones antiguas aceptaban cadenas como `strict`, `partial` o `disabled`, y las actuales usan booleanos (`true` / `false`). Con el valor equivocado el agente falla al arrancar o ignora tu intención en silencio. Comprueba la referencia de Helm de **tu** versión.

Para que kube-proxy no compita con Cilium, hay que retirarlo del clúster: con kubeadm se omite en `init` (o se borra su DaemonSet y su ConfigMap) y en k3s se arranca el servidor con `--disable-kube-proxy`. Verifica el resultado desde el agente:

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep KubeProxyReplacement
```

El binario de diagnóstico dentro del pod del agente se llama `cilium-dbg` en versiones recientes y `cilium` en las anteriores; no lo confundas con el CLI `cilium` de tu máquina.

## Políticas de red

Cilium aplica las `NetworkPolicy` estándar de Kubernetes (L3/L4: pods, namespaces, CIDR y puertos) y añade su propio CRD, `CiliumNetworkPolicy`, para lo que el estándar no puede expresar: reglas L7 y destinos por nombre DNS. La teoría general de políticas y RBAC está en [Seguridad en Kubernetes](../cybersecurity/kubernetes_security.md); aquí solo lo específico de Cilium.

| Capacidad | `NetworkPolicy` | `CiliumNetworkPolicy` |
|---|---|---|
| Selección por pod, namespace y CIDR | Sí | Sí |
| Puertos y protocolos L4 | Sí | Sí |
| Reglas HTTP (método, ruta) | No | Sí (proxy Envoy en el nodo) |
| Salida a un dominio (`toFQDNs`) | No | Sí |

### Default-deny y salida a un dominio

Un namespace sin políticas permite todo. El patrón correcto es denegar todo y abrir lo necesario. Primero el *default-deny* con la `NetworkPolicy` estándar, que funciona en cualquier CNI:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: apps
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

Con eso ni siquiera resuelve DNS. La política de Cilium siguiente deja a los pods con la etiqueta `app: backend` consultar `kube-dns` y salir a un único dominio por HTTPS:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-egress
  namespace: apps
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
    # 1) Permitir DNS y que Cilium observe las respuestas
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s:k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: ANY
          rules:
            dns:
              - matchPattern: "*"
    # 2) Salida solo a este dominio
    - toFQDNs:
        - matchName: "api.example.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

La regla DNS no es opcional: Cilium aprende a qué IPs resuelve `api.example.com` interceptando las respuestas DNS, y solo entonces abre esas IPs. Sin el bloque `rules.dns`, `toFQDNs` no tiene de dónde sacar direcciones y el tráfico se descarta. Dos matices: `toFQDNs` filtra por lo que resolvió el DNS, no inspecciona el contenido TLS, y si la aplicación cachea IPs más tiempo que el TTL puede dejar de funcionar cuando el dominio cambia de dirección.

### Reglas L7 (HTTP)

Para limitar qué puede hacer un cliente sobre un servicio, no solo a qué puerto llega:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-solo-lectura
  namespace: apps
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          rules:
            http:
              - method: "GET"
                path: "/v1/.*"
```

El frontend solo puede hacer `GET` bajo `/v1/`; el resto lo rechaza el proxy. `path` es una **expresión regular**, no un prefijo. Las reglas HTTP desvían ese puerto por Envoy, con su coste de latencia: resérvalas para lo que lo justifique.

## Observabilidad con Hubble

Hubble es la capa de observabilidad de Cilium: cada agente registra los flujos que ve (origen, destino, protocolo, veredicto de política) y Hubble Relay los agrega para todo el clúster. Se activa con el CLI o con los valores de Helm vistos antes:

```bash
cilium hubble enable --ui
```

Para usar el CLI `hubble` desde tu máquina, abre un túnel al Relay y comprueba que responde:

```bash
cilium hubble port-forward &
hubble status
```

### Consultar flujos

```bash
# Tráfico en vivo de un namespace
hubble observe --namespace apps --follow

# Solo lo que se descarta por política
hubble observe --verdict DROPPED

# Descartes de un pod concreto
hubble observe --pod apps/backend-7d9f --verdict DROPPED --follow
```

Cada línea indica origen, destino, puerto, protocolo y veredicto (`FORWARDED` o `DROPPED`). Los flujos L7 (HTTP, DNS) solo aparecen si hay una política L7 o la visibilidad L7 activada para esos pods.

### Hubble UI

```bash
cilium hubble ui
```

Abre un mapa de servicios por namespace con el tráfico entre ellos, y los flujos descartados marcados aparte. Es la forma más rápida de ver de un vistazo que un servicio al que nadie llama (o que llama a algo inesperado) existe. Si la expones de forma permanente, hazlo con autenticación (SSO o VPN), como el resto de paneles de [observabilidad](../monitoring/observability_stack.md).

### Depurar una política que bloquea

El flujo de trabajo que más se repite:

1. **Reproduce el fallo** y, en paralelo, lanza `hubble observe --namespace apps --verdict DROPPED --follow`.
2. **Lee el descarte**: el origen, el destino y el puerto de la línea son exactamente lo que falta en una regla. Si el destino es `kube-dns`, falta la regla DNS; si es una IP externa, falta una regla de salida o un `toFQDNs`.
3. **Comprueba qué política afecta al pod**: `kubectl get cnp,netpol -n apps` y los labels del pod (`kubectl get pod --show-labels`). Un `endpointSelector` con una etiqueta mal escrita no selecciona nada y no falla.
4. **Ajusta la regla, reaplica y repite el paso 1**: el descarte debe desaparecer y aparecer un `FORWARDED`.

## Seguridad en runtime con Tetragon

Las políticas de red controlan quién habla con quién; no ven qué hace un proceso dentro del contenedor. **Tetragon** (proyecto hermano de Cilium, mismo ecosistema eBPF) cubre ese hueco: observa ejecuciones de procesos, accesos a ficheros y conexiones de red a nivel de kernel, sin modificar las aplicaciones, y con políticas `TracingPolicy` puede además **imponer** reglas (por ejemplo, terminar un proceso que abre un fichero sensible). Se instala por separado de Cilium y se puede usar con otro CNI.

Empieza en modo observación: una política que mata procesos puede tumbar una carga legítima. El modelo de amenazas, el endurecimiento y la respuesta a incidentes están en otras páginas del sitio y no se duplican aquí:

- [Zero Trust](../cybersecurity/zero_trust.md): por qué la segmentación por identidad es la base de las políticas anteriores.
- [Seguridad en Kubernetes](../cybersecurity/kubernetes_security.md): RBAC, Pod Security y NetworkPolicies estándar.
- [Monitoreo de seguridad](../cybersecurity/monitoreo_seguridad.md): a dónde enviar los eventos de Tetragon y Hubble para alertar.

## eBPF fuera de Kubernetes

No hace falta un clúster para sacar partido de eBPF. En un host Linux (un nodo con un problema, una VM de Proxmox) hay dos familias de herramientas de diagnóstico.

**bpftrace** es un lenguaje de una línea para trazar el kernel, parecido a `awk`:

```bash
# Qué proceso abre qué fichero, en vivo
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Llamadas al sistema por proceso, resumen al pulsar Ctrl-C
sudo bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'
```

**bcc-tools** es una colección de utilidades ya hechas, una por pregunta típica:

| Herramienta | Responde a |
|---|---|
| `execsnoop` | ¿Qué procesos nuevos se están lanzando? |
| `opensnoop` | ¿Qué ficheros abre cada proceso? |
| `tcpconnect` / `tcplife` | ¿Quién abre conexiones TCP y cuánto duran? |
| `biolatency` | ¿Cómo es la latencia de disco? |

!!! note "Nombres según la distribución"
    En Debian y Ubuntu los binarios de bcc llevan el sufijo `-bpfcc` (`execsnoop-bpfcc`) y se instalan con el paquete `bpfcc-tools`. En otras distribuciones se instalan en `/usr/share/bcc/tools/`. Ambas herramientas necesitan root y cabeceras o BTF del kernel que estés ejecutando.

Para inspeccionar lo que tiene cargado el propio nodo (incluido Cilium), `bpftool prog list` y `bpftool map list` enumeran programas y mapas. Si lo que buscas es una vista general de recursos del host sin eBPF, mira [monitorización en terminal](../linux/tui_monitoring.md).

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Los pods quedan en `ContainerCreating` tras instalar | Quedó otro CNI o su configuración en `/etc/cni/net.d/` | Retirar el CNI anterior, borrar sus ficheros en cada nodo y reiniciar los pods |
| El agente de Cilium falla al arrancar con kube-proxy sustituido | Falta `k8sServiceHost` / `k8sServicePort`, o el valor de `kubeProxyReplacement` no es el de tu versión | Fijar la dirección real del API server y revisar el valor en la referencia de tu versión |
| Tras activar `toFQDNs` todo el tráfico del pod se descarta | Falta la regla de salida a `kube-dns` con `rules.dns` | Añadir el bloque DNS de la política de ejemplo |
| `hubble observe` no devuelve nada | No hay port-forward al Relay, o Relay desactivado | `cilium hubble port-forward` y `hubble status` |
| No veo flujos HTTP, solo L3/L4 | La visibilidad L7 solo existe con una política L7 o anotación de visibilidad | Aplicar una `CiliumNetworkPolicy` con `rules.http` a ese puerto |
| Una política de Cilium "no hace nada" | El `endpointSelector` no coincide con ninguna etiqueta | Cotejar con `kubectl get pod --show-labels` y mirar el descarte en Hubble |

## Buenas prácticas

- **Un solo CNI y una versión fijada.** Lee las *upgrade notes* antes de actualizar.
- **Activa Hubble desde el primer día**, antes de escribir políticas. Escribir reglas a partir de flujos observados es más seguro que a partir de memoria.
- **Default-deny por namespace, con DNS explícito.** Y guarda las políticas en Git junto al resto de manifiestos.
- **Reserva L7 para donde aporte.** El filtrado HTTP pasa por Envoy; para el resto, L3/L4 con identidades es más barato y suficiente.
- **Si solo quieres mTLS y canary**, mira primero [Service Mesh](service_mesh.md): puede que no necesites todo lo de esta página.

## Referencias

- [Kubernetes - Orquestación de contenedores](kubernetes_base.md)
- [Service Mesh en Kubernetes: Istio vs Linkerd vs Cilium](service_mesh.md)
- [Zero Trust](../cybersecurity/zero_trust.md)
- [Seguridad en Kubernetes](../cybersecurity/kubernetes_security.md)
- [Monitoreo de seguridad](../cybersecurity/monitoreo_seguridad.md)
- [Stack de observabilidad](../monitoring/observability_stack.md)
- [Monitorización en terminal](../linux/tui_monitoring.md)

### Documentación oficial

- [Cilium Docs](https://docs.cilium.io/en/stable/)
- [Cilium: requisitos del sistema](https://docs.cilium.io/en/stable/operations/system_requirements/)
- [Hubble](https://docs.cilium.io/en/stable/observability/hubble/)
- [Tetragon](https://tetragon.io/docs/)
- [bpftrace](https://github.com/bpftrace/bpftrace)
- [BCC tools](https://github.com/iovisor/bcc)
- [ebpf.io](https://ebpf.io/what-is-ebpf/)
