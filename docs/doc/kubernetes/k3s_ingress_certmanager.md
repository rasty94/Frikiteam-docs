---
title: "Kubernetes en homelab: k3s, Ingress y cert-manager"
description: "De un clúster k3s vacío a un servicio publicado con HTTPS válido: instalación, LoadBalancer en bare metal (ServiceLB y MetalLB), Ingress con Traefik y certificados de Let's Encrypt con cert-manager."
keywords: "k3s, kubernetes, homelab, ingress, traefik, ingress-nginx, metallb, servicelb, cert-manager, let's encrypt, clusterissuer, http-01, dns-01, helm"
tags: ['kubernetes', 'networking', 'helm']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 28 min
category: Contenedores
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Conceptos básicos de Kubernetes (Pod, Deployment, Service)"
  - "Un servidor Linux (VM o bare metal) con IP fija"
  - "Un dominio propio con acceso a su DNS"
  - "Helm 3 instalado en tu máquina"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Kubernetes en homelab: k3s, Ingress y cert-manager

## El problema

Montas un clúster, despliegas tu primera aplicación y el `Service` de tipo `LoadBalancer` se queda eternamente en `<pending>`. Lo parcheas con un `NodePort`, accedes a `http://192.168.1.50:31874` y todo parece funcionar, hasta que quieres un nombre de dominio, un candado verde y más de un servicio escuchando en el puerto 443. Ahí descubres que en Kubernetes **nada de eso viene incluido**: el reparto de IPs, el enrutado HTTP y los certificados son tres piezas distintas que en la nube te da el proveedor y en tu rack tienes que montar tú.

Esta página recorre ese camino completo sobre k3s: un clúster vacío, una IP para los servicios, un Ingress que enruta por nombre y certificados de Let's Encrypt que se emiten y renuevan solos.

!!! note "Qué cubre y qué no"
    Aquí se trata la **exposición y el cifrado del tráfico de entrada**. Los conceptos básicos de Pods, Deployments y Services están en [Kubernetes](kubernetes_base.md); la salud de las aplicaciones en [Probes](probes.md); el tráfico este-oeste y mTLS en [Service Mesh](service_mesh.md). El almacenamiento persistente tiene su propia página: [Kubernetes CSI](../storage/kubernetes_csi.md).

## 📋 Tabla de Contenidos

- [k3s: qué trae y cómo instalarlo](#k3s-que-trae-y-como-instalarlo)
- [Kubeconfig y nodos adicionales](#kubeconfig-y-nodos-adicionales)
- [Exponer servicios en bare metal](#exponer-servicios-en-bare-metal)
- [Ingress: enrutar por nombre](#ingress-enrutar-por-nombre)
- [cert-manager: certificados automáticos](#cert-manager-certificados-automaticos)
- [Publicar un servicio con HTTPS](#publicar-un-servicio-con-https)
- [Depurar la emisión de certificados](#depurar-la-emision-de-certificados)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## k3s: qué trae y cómo instalarlo

k3s es una distribución de Kubernetes certificada, empaquetada en un único binario y pensada para recursos modestos. En instalaciones de un solo servidor usa SQLite en lugar de etcd (etcd embebido si montas alta disponibilidad) y trae de serie lo que un clúster vacío necesita para ser útil:

| Componente | Función | Se desactiva con |
|---|---|---|
| containerd | Runtime de contenedores | (no se desactiva) |
| Flannel | Red de pods (CNI) | `--flannel-backend=none` |
| CoreDNS | DNS interno del clúster | `--disable coredns` |
| Traefik | Ingress controller | `--disable traefik` |
| ServiceLB | Implementación de `LoadBalancer` | `--disable servicelb` |
| local-path-provisioner | StorageClass con directorios del nodo | `--disable local-storage` |
| metrics-server | Métricas para `kubectl top` y HPA | `--disable metrics-server` |

!!! warning "Depende de la versión"
    La lista de componentes incluidos, sus versiones y los nombres exactos de los flags cambian entre versiones de k3s. Contrasta la tabla con la documentación de la versión que instales (`k3s server --help` lista los flags de la tuya) antes de automatizar nada.

### Instalación

El script oficial instala el binario, crea la unit de systemd `k3s` y arranca el servidor:

```bash
curl -sfL https://get.k3s.io | sh -
```

Descarga y ejecuta un script como root: revísalo antes, y **fija la versión** con `INSTALL_K3S_VERSION="<versión>"` (delante de `sh -`) en cuanto salgas del laboratorio, para que la misma receta dé el mismo clúster.

Comprueba que el servicio está arriba y que el nodo se registra:

```bash
sudo systemctl status k3s
sudo k3s kubectl get nodes
```

El nodo pasa a `Ready` en uno o dos minutos; k3s incluye su propio `kubectl`.

### Desactivar componentes

Se puede hacer con flags en la instalación (`sh -s - --disable traefik --disable servicelb`) o, mejor, con un fichero versionable, `/etc/rancher/k3s/config.yaml`, antes de arrancar (o reiniciando `k3s` después):

```yaml
# /etc/rancher/k3s/config.yaml
disable:
  - traefik
  - servicelb
write-kubeconfig-mode: "0644"
```

Las claves reflejan los nombres de los flags sin los guiones iniciales. `write-kubeconfig-mode` abre el kubeconfig a otros usuarios: cómodo en un homelab de un solo administrador, un riesgo en un servidor compartido.

## Kubeconfig y nodos adicionales

### Acceder desde tu portátil

k3s escribe las credenciales de administrador en `/etc/rancher/k3s/k3s.yaml`, por defecto solo legible por root. Cópialo a tu máquina y sustituye la dirección del servidor, que viene como `127.0.0.1`:

```bash
scp usuario@192.168.1.50:/etc/rancher/k3s/k3s.yaml ~/.kube/k3s-homelab.yaml
sed -i 's/127.0.0.1/192.168.1.50/' ~/.kube/k3s-homelab.yaml   # en macOS: sed -i ''
export KUBECONFIG=~/.kube/k3s-homelab.yaml
kubectl get nodes
```

Si `scp` no puede leerlo siendo root-only, activa `write-kubeconfig-mode` (ver arriba) o cópialo con `sudo cat`. Ese kubeconfig es de administrador total: trátalo como una contraseña. Si accedes al API por un nombre de dominio, añádelo con `tls-san` en `config.yaml` para que figure en el certificado del API.

### Añadir nodos

Un agente necesita la URL del servidor (el API escucha en el 6443) y el token, que está en el servidor:

```bash
# En el servidor
sudo cat /var/lib/rancher/k3s/server/node-token

# En el nodo nuevo
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.50:6443 K3S_TOKEN="<token>" sh -
```

El script detecta `K3S_URL` e instala el servicio `k3s-agent`. El agente debe llegar al 6443 del servidor y los nodos entre sí por el puerto UDP de la red de pods (Flannel con VXLAN usa el 8472): si hay firewall o VLANs entre nodos, ábrelos. El token da acceso al clúster: no lo pegues en repositorios ni tickets.

## Exponer servicios en bare metal

Un `Service` de tipo `LoadBalancer` no crea nada por sí mismo: pide a un controlador que lo haga. En AWS o GCP, ese controlador es el del proveedor y devuelve una IP pública. En un clúster propio **nadie atiende la petición** y el campo `EXTERNAL-IP` se queda en `<pending>` para siempre. Hay que instalar quien lo atienda.

| | ServiceLB (k3s) | MetalLB |
|---|---|---|
| Instalación | Viene incluido | Helm o manifiestos |
| IP asignada | La de los nodos del clúster | Una de un pool que tú defines |
| Varios servicios en el 443 | No: el puerto es del nodo, se pisan | Sí: cada servicio tiene su propia IP |

### ServiceLB: lo que ya tienes

Por cada `Service` `LoadBalancer`, ServiceLB lanza un pod en cada nodo que reserva el puerto en el propio host y reenvía el tráfico al servicio. La `EXTERNAL-IP` que ves es la IP del nodo (o las de todos). Para un clúster de un nodo con Traefik escuchando en el 80 y el 443 es suficiente y no hay nada que configurar. Su límite es estructural: dos servicios no pueden usar el mismo puerto, porque el puerto es del nodo, no del servicio.

### MetalLB en modo L2

En cuanto quieras varias IPs de servicio o un failover real, MetalLB asigna IPs de un rango tuyo. En modo L2, un nodo responde a las peticiones ARP (NDP en IPv6) de esa IP y, si cae, otro la toma. Es el modo adecuado para una red doméstica porque no exige router con BGP. Su coste: todo el tráfico de una IP entra por un solo nodo, así que es alta disponibilidad, no reparto de carga. Para comparar con otras opciones, mira [comparativa de balanceadores](../networking/load_balancer_comparison.md).

Primero desactiva ServiceLB en k3s (clave `servicelb` en `disable`, como arriba), o ambos se disputarán los `LoadBalancer`. Después instala MetalLB:

```bash
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm install metallb metallb/metallb --namespace metallb-system --create-namespace
```

Espera a que los pods de `metallb-system` estén `Running` y declara el rango con dos recursos: el pool de direcciones y el anuncio L2 que lo publica.

```yaml
# metallb-pool.yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: homelab-pool
  namespace: metallb-system
spec:
  addresses:
    - 192.168.1.240-192.168.1.250
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: homelab-l2
  namespace: metallb-system
spec:
  ipAddressPools:
    - homelab-pool
```

```bash
kubectl apply -f metallb-pool.yaml
```

El rango tiene que ser de tu LAN, **fuera del reparto DHCP** del router y sin IPs ya en uso. Sin un `L2Advertisement`, MetalLB asigna la IP pero no la anuncia: el servicio tendrá `EXTERNAL-IP` y seguirá inalcanzable.

!!! warning "Depende de la versión"
    El grupo de API `metallb.io/v1beta1` y los nombres de los chart values han cambiado entre versiones de MetalLB. Si `kubectl apply` rechaza los recursos, revisa la documentación de la versión instalada. Las versiones antiguas configuraban todo con un ConfigMap, que las actuales ya no leen.

## Ingress: enrutar por nombre

Con una sola IP (o unas pocas) y muchos servicios web, no quieres una IP por servicio: quieres un único punto de entrada que mire el nombre de host y la ruta y reparta. Eso es un **Ingress controller** (el proceso que recibe el tráfico) más recursos `Ingress` (las reglas). El Ingress controller se expone él mismo con un `Service` `LoadBalancer`, y todo lo demás cuelga de ahí.

Un recurso `Ingress` estándar (el ejemplo completo está en [Publicar un servicio con HTTPS](#publicar-un-servicio-con-https)) funciona igual con cualquier controlador. Declara `ingressClassName`, uno o varios `host`, rutas con su `pathType` y el `Service` de destino.

`ingressClassName` indica qué controlador atiende la regla; las clases disponibles se ven con `kubectl get ingressclass`.

### Traefik (el de k3s) frente a ingress-nginx

Traefik viene incluido en k3s, se configura con CRDs (`IngressRoute`, `Middleware`) además de anotaciones y recarga su configuración de forma dinámica. ingress-nginx no viene incluido, se configura con anotaciones `nginx.ingress.kubernetes.io/*` y tiene muchos más ejemplos en la red.

Para un homelab, **quédate con Traefik**: ya está instalado, entiende `Ingress` estándar y, si más adelante necesitas middlewares (redirecciones, autenticación básica, limitación de tasa), los tienes sin cambiar de controlador. Su configuración y su dashboard se tratan en [Traefik](../traefik/traefik_base.md). Para personalizar el Traefik que trae k3s (puertos, logs, plugins) no edites sus manifiestos, que k3s regenera: crea un recurso `HelmChartConfig` llamado `traefik` en el namespace `kube-system` con tus `valuesContent`.

!!! warning "Depende de la versión"
    El proyecto ingress-nginx de la comunidad de Kubernetes anunció en noviembre de 2025 su retirada: mantenimiento de mejor esfuerzo hasta marzo de 2026 y, después, sin nuevas versiones ni correcciones de seguridad. No lo elijas para algo nuevo. Si necesitas un sustituto, mira los demás controladores y, sobre todo, Gateway API.

### Gateway API: hacia dónde va esto

`Ingress` solo cubre host y ruta; todo lo demás (cabeceras, pesos, TCP) acaba en anotaciones propias de cada controlador, no portables. Gateway API es su sucesor (`GatewayClass`, `Gateway`, `HTTPRoute`): separa roles y es portable entre implementaciones. Traefik la soporta y cert-manager puede trabajar con ella. Hoy, para un homelab, `Ingress` sigue siendo lo más simple y documentado; conviene saber que es hacia donde se mueve el ecosistema.

## cert-manager: certificados automáticos

cert-manager es un controlador que **pide, guarda y renueva certificados** como recursos de Kubernetes. Tú declaras qué certificado quieres y de dónde; él habla con la autoridad (aquí, Let's Encrypt), supera el desafío de validación y guarda el resultado en un `Secret` que el Ingress consume. Los conceptos de TLS y de ACME en general están en [Certificados TLS](../networking/certificados_tls.md).

### Instalación con Helm

El chart oficial instala los pods (controlador, webhook, cainjector) y los CRDs, que son los tipos nuevos (`ClusterIssuer`, `Certificate`...). **Sin los CRDs nada de lo siguiente funciona**:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

!!! warning "Depende de la versión"
    El valor que activa los CRDs se llamaba `installCRDs=true` en versiones antiguas del chart y `crds.enabled=true` en las actuales. Fija también la versión del chart con `--version`. Si `helm install` ignora el valor sin error, `kubectl get crd | grep cert-manager` te dice si los CRDs existen.

Comprueba que los tres pods están `Running` antes de seguir:

```bash
kubectl get pods -n cert-manager
```

El webhook tarda unos segundos más en estar listo; si el siguiente `kubectl apply` falla con un error de webhook, espera y reintenta.

### ClusterIssuer: staging y producción

Un `ClusterIssuer` es la definición, válida en todo el clúster, de *quién emite* los certificados. Crea **dos**: uno contra el entorno de pruebas de Let's Encrypt (el que se muestra) y otro contra el real.

```yaml
# clusterissuers.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: tu-correo@ejemplo.com
    privateKeySecretRef:
      name: letsencrypt-staging-account-key
    solvers:
      - http01:
          ingress:
            ingressClassName: traefik
```

El de producción es idéntico cambiando `name` a `letsencrypt-prod`, `server` a `https://acme-v02.api.letsencrypt.org/directory` y el Secret de cuenta a `letsencrypt-prod-account-key`. Aplica ambos:

```bash
kubectl apply -f clusterissuers.yaml
kubectl get clusterissuer
```

Ambos deben aparecer con `READY` en `True`: significa que la cuenta ACME se ha registrado. `privateKeySecretRef` es el Secret donde cert-manager guarda la clave de esa cuenta (lo crea él, no lo creas tú); el correo recibe los avisos de caducidad.

**Siempre staging primero.** Sus certificados los firma una CA que ningún navegador reconoce, pero el flujo es idéntico y sus límites son mucho más holgados. Los de producción se aplican por dominio registrado, por certificados duplicados y por validaciones fallidas: un bucle de reintentos con una configuración errónea puede bloquearte unos días. Consulta la página de límites de Let's Encrypt para los valores vigentes.

### HTTP-01 frente a DNS-01

El *solver* es el método con el que demuestras que controlas el dominio.

| | HTTP-01 | DNS-01 |
|---|---|---|
| Cómo valida | Let's Encrypt pide un fichero por HTTP en el puerto 80 | Busca un registro TXT en `_acme-challenge.<dominio>` |
| Requisitos | El clúster accesible desde Internet en el 80, DNS apuntando a él | Acceso por API a tu proveedor DNS |
| Wildcard (`*.ejemplo.com`) | No | Sí |
| Clúster sin exponer a Internet | No | Sí |

**Usa HTTP-01 si el clúster es alcanzable desde fuera** (puerto 80 redirigido a tu IP de MetalLB o al nodo). Necesitas **DNS-01** en dos casos: certificados wildcard, o servicios internos con nombre público que nunca quieres abrir a Internet. Un ejemplo con Cloudflare, uno de los proveedores con solver integrado (cert-manager soporta otros; ver su documentación):

```yaml
# Dentro de spec.acme.solvers del ClusterIssuer
solvers:
  - dns01:
      cloudflare:
        apiTokenSecretRef:
          name: cloudflare-api-token
          key: api-token
```

El Secret `cloudflare-api-token` debe estar en el namespace `cert-manager` (el de los pods del controlador, para un `ClusterIssuer`) y el token debe poder editar solo la zona DNS necesaria, nunca la cuenta entera.

## Publicar un servicio con HTTPS

Prueba con `traefik/whoami`, que devuelve datos de la petición. Usa un dominio tuyo cuyo DNS apunte a la IP de entrada de tu clúster.

```bash
kubectl create deployment whoami --image=traefik/whoami --port=80
kubectl expose deployment whoami --port=80
```

Y el Ingress, que une Traefik, el Service y cert-manager:

```yaml
# whoami-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whoami
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - whoami.ejemplo.com
      secretName: whoami-tls
  rules:
    - host: whoami.ejemplo.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: whoami
                port:
                  number: 80
```

```bash
kubectl apply -f whoami-ingress.yaml
kubectl get certificate
```

La anotación `cert-manager.io/cluster-issuer` es lo único que conecta las dos mitades: cert-manager ve el Ingress, lee el bloque `tls` y **crea por ti un recurso `Certificate`** que produce el Secret `whoami-tls`. Cuando el `Certificate` pasa a `READY: True`, Traefik empieza a servir ese Secret en el host indicado.

Para pasar a un certificado de verdad, cambia la anotación a `letsencrypt-prod` y vuelve a aplicar. Como el Secret ya existe con el certificado de staging, bórralo para forzar la reemisión:

```bash
kubectl delete secret whoami-tls
```

Desde dentro de tu LAN, el dominio público resuelve a tu IP pública y muchos routers no devuelven el tráfico al interior (*hairpin NAT*). La solución es un DNS interno que resuelva ese nombre a la IP del balanceador (split-horizon).

## Depurar la emisión de certificados

Una emisión ACME es una cadena de recursos, cada uno creado por el anterior. Cuando algo falla, el error está en el eslabón en que se rompe la cadena:

| Recurso | Qué representa |
|---|---|
| `Certificate` | Lo que quieres: nombres, emisor, Secret de destino |
| `CertificateRequest` | La petición de firma concreta enviada al emisor |
| `Order` | El pedido ACME a Let's Encrypt, uno por petición |
| `Challenge` | Cada desafío de validación (uno por nombre) |

Se recorre de arriba abajo, deteniéndose donde aparezca el error:

```bash
kubectl get certificate,certificaterequest,order,challenge -A
kubectl describe certificate whoami-tls
kubectl describe challenge -A
```

El `describe` de cada recurso trae el motivo en la sección `Events` y en `Status`. El `Challenge` es el más informativo: su `Reason` suele ser el error literal (conexión rechazada, tiempo agotado, respuesta incorrecta). Si ningún recurso hijo existe, el problema está más arriba: en el `ClusterIssuer` (`kubectl describe clusterissuer letsencrypt-staging`) o en el propio controlador:

```bash
kubectl logs -n cert-manager deploy/cert-manager --tail=100
```

Existe además `cmctl`, una herramienta aparte del proyecto que resume el estado de un `Certificate` y su cadena (`cmctl status certificate <nombre>`).

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `Certificate` en `READY: False` mucho tiempo | La cadena `Order` / `Challenge` está atascada | `kubectl describe challenge`: leer `Reason` |
| `Challenge` en `pending` con error de conexión o 404 | Let's Encrypt no llega al puerto 80 del clúster, o el Ingress de resolución no es atendido | Comprobar DNS, reenvío del 80 en el router y que `ingressClassName` del solver coincide con tu controlador |
| `EXTERNAL-IP` en `<pending>` | No hay controlador de LoadBalancer (ServiceLB desactivado y sin MetalLB) | Instalar MetalLB o reactivar ServiceLB |
| MetalLB asigna IP pero no responde a ping ni HTTP | Falta el `L2Advertisement`, o el rango se solapa con DHCP | `kubectl get l2advertisement,ipaddresspool -n metallb-system` |
| Navegador avisa de certificado no confiable | Es un certificado de `letsencrypt-staging` | Cambiar la anotación a `letsencrypt-prod` y borrar el Secret |
| El `Order` falla por límite de tasa (*rate limit*) | Se ha alcanzado un límite de Let's Encrypt | Esperar; usar staging para probar; no repetir emisiones de producción |
| HTTP-01 falla con el clúster tras CGNAT | El 80 de tu IP pública no llega a casa | Usar DNS-01 |

El flujo para un certificado atascado, de menor a mayor esfuerzo: leer el `Challenge`, confirmar desde **fuera de tu red** (por ejemplo desde datos móviles) que `http://<dominio>/.well-known/acme-challenge/` llega al clúster, y solo entonces borrar el `Certificate` y su Secret para empezar de cero. Si el problema es de red, repetir la emisión no lo arregla y puede gastar tu cupo.

## Buenas prácticas

- **Staging para todo lo nuevo.** Cambia a producción solo cuando el flujo completo haya funcionado en staging. Es la única defensa contra los límites de tasa.
- **Versiones fijadas**: k3s (`INSTALL_K3S_VERSION`), charts de MetalLB y cert-manager (`--version`). Un `helm upgrade` sin fijar versión es una actualización sorpresa de CRDs.
- **Todo en Git.** `config.yaml`, el pool de MetalLB, los `ClusterIssuer` y los Ingress son YAML declarativo: son infraestructura como código sin herramienta adicional.
- **Tokens DNS con el mínimo alcance** (una zona, solo editar TXT) y rotados. El token del DNS es la llave de tu dominio.
- **Un [service mesh](service_mesh.md) si necesitas mTLS interno**: el TLS de esta página solo protege la entrada.
- **Define [probes](probes.md)** en todo lo que publiques: un Ingress que enruta a un pod no listo devuelve errores 502/503 a tus usuarios.

## Referencias

- [Documentación de k3s](https://docs.k3s.io/)
- [Servicios, LoadBalancer y ServiceLB en k3s](https://docs.k3s.io/networking/networking-services)
- [Documentación de MetalLB](https://metallb.io/)
- [Ingress en Kubernetes](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [Documentación de cert-manager](https://cert-manager.io/docs/)
- [Límites de tasa de Let's Encrypt](https://letsencrypt.org/docs/rate-limits/)
- [Kubernetes](kubernetes_base.md) · [Probes](probes.md) · [Service Mesh](service_mesh.md)
- [Certificados TLS](../networking/certificados_tls.md) · [Traefik](../traefik/traefik_base.md) · [Kubernetes CSI](../storage/kubernetes_csi.md)
- [Comparativa de balanceadores](../networking/load_balancer_comparison.md)
- [k3s: requisitos de red](https://docs.k3s.io/installation/requirements)
- [cert-manager: cmctl](https://cert-manager.io/docs/reference/cmctl/)
- [k3s: Helm y HelmChartConfig](https://docs.k3s.io/add-ons/helm)
