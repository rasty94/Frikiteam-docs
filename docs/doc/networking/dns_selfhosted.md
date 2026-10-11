---
title: "DNS propio: resolutor y servidor autoritativo"
description: "Montar el DNS de una red propia: resolutor Unbound, zona interna autoritativa con BIND o PowerDNS, split-horizon, integración con DHCP, Proxmox y Kubernetes, alta disponibilidad y diagnóstico."
keywords: "dns, unbound, bind, bind9, powerdns, resolutor, autoritativo, split-horizon, home.arpa, tsig, axfr, dig"
tags: ['networking', 'linux']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 37 min
category: Redes
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Fundamentos de redes (IP, puertos, UDP/TCP)"
  - "Administración básica de Linux (systemd, journalctl)"
  - "Un dominio propio o disposición a usar home.arpa"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# DNS propio: resolutor y servidor autoritativo

## El problema

Tu red crece: tres nodos Proxmox, un clúster de Kubernetes, un par de NAS. Empiezas con un `/etc/hosts` copiado a mano, luego con el DNS del router, y un día un servicio se mueve de IP y la mitad de los clientes sigue apuntando a la vieja. O peor: el DNS del operador deja de responder y, de repente, "no hay internet" aunque el enlace funcione perfectamente.

La solución es tener **tu propio DNS**, pero el error habitual es montar un único servicio que lo hace todo. DNS son dos trabajos distintos con requisitos distintos, y esta página explica cómo montarlos por separado: un resolutor que responde a tus clientes y un servidor autoritativo que es la fuente de verdad de tu zona interna.

!!! note "Qué cubre y qué no"
    Aquí está la base: resolutor, zona interna, split-horizon, integración y alta disponibilidad. La firma de zonas está en [DNSSEC](dnssec.md) y las zonas inversas en [Registros PTR y zonas inversas](registros_ptr_zonas_inversas.md); no se repiten aquí.

## 📋 Tabla de Contenidos

- [Resolutor frente a autoritativo](#resolutor-frente-a-autoritativo)
- [Resolutor con Unbound](#resolutor-con-unbound)
- [Zona interna autoritativa con BIND](#zona-interna-autoritativa-con-bind)
- [PowerDNS como alternativa con API](#powerdns-como-alternativa-con-api)
- [Dominio interno y split-horizon](#dominio-interno-y-split-horizon)
- [Integración con la red](#integracion-con-la-red)
- [Alta disponibilidad](#alta-disponibilidad)
- [Diagnóstico](#diagnostico)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Resolutor frente a autoritativo

| | Resolutor recursivo | Servidor autoritativo |
|---|---|---|
| Pregunta que contesta | "¿Cuál es la IP de `ejemplo.org`?" (para cualquier nombre) | "¿Cuál es la IP de `nas.lab.ejemplo.org`?" (solo de sus zonas) |
| Quién lo consulta | Tus clientes (portátiles, VMs, pods) | Resolutores, nunca el cliente final |
| Qué hace | Pregunta a la raíz, a los TLD y a los autoritativos hasta obtener la respuesta, y la **cachea** | Sirve datos de un fichero de zona o una base de datos |
| Estado | Caché (se puede perder sin pérdida de datos) | Datos de la zona (hay que respaldarlos) |
| Ejemplos | Unbound, BIND con `recursion yes`, Knot Resolver | BIND, PowerDNS Authoritative, NSD, Knot DNS |
| Exposición | Solo a tu red | Puede ser pública si la zona lo es |

Mezclarlos en un mismo proceso funciona en una casa, pero tiene costes reales:

- **Seguridad.** Un resolutor abierto a internet es un amplificador de ataques DDoS; un autoritativo no debe recursar para nadie. Con `recursion no` en el autoritativo y `access-control` en el resolutor, cada uno falla cerrado.
- **Ciclo de vida.** El autoritativo se toca cuando cambias registros; el resolutor, casi nunca. Reiniciar uno no debería tumbar al otro.
- **Alta disponibilidad.** Dos resolutores idénticos son triviales. Un autoritativo replicado necesita transferencias de zona. Son problemas distintos.

El esquema que usa el resto de la página: los clientes preguntan al resolutor; el resolutor reenvía las consultas de la zona interna al autoritativo y resuelve todo lo demás por su cuenta o a través de un upstream cifrado.

```text
cliente --> resolutor (192.168.10.2)
               |-- lab.ejemplo.org --> autoritativo (192.168.10.3)
               '-- resto del mundo --> raíz/TLD, o upstream DoT
```

## Resolutor con Unbound

Unbound es un resolutor recursivo con validación DNSSEC, pequeño y sin zonas autoritativas propias más allá de datos locales. En Debian/Ubuntu el paquete es `unbound` y los ficheros extra se leen de `/etc/unbound/unbound.conf.d/*.conf`.

### Configuración mínima

```yaml
# /etc/unbound/unbound.conf.d/resolutor.conf
server:
    interface: 127.0.0.1
    interface: 192.168.10.2
    port: 53

    # Quién puede preguntar. Lo que no case se rechaza.
    access-control: 127.0.0.0/8 allow
    access-control: 192.168.10.0/24 allow
    access-control: 0.0.0.0/0 refuse

    do-ip6: no
    hide-identity: yes
    hide-version: yes

    # Protección contra DNS rebinding: bloquea respuestas públicas
    # que apunten a IPs privadas, salvo para los dominios internos.
    private-address: 192.168.0.0/16
    private-address: 10.0.0.0/8
    private-domain: "lab.ejemplo.org"
```

Parece YAML pero **no lo es**: es el formato propio de Unbound (`clave: valor` bajo secciones como `server:`). Tres detalles que muerden:

- `interface` se repite una vez por dirección. Si pones `0.0.0.0` en un host con `systemd-resolved`, chocarás con su stub en `127.0.0.53:53`; enlaza a IPs concretas.
- `access-control` evalúa la regla más específica. Por defecto Unbound solo permite localhost, así que sin estas líneas tus clientes reciben `REFUSED`.
- `do-ip6: no` solo desactiva las consultas salientes por IPv6. Si tu red tiene conectividad IPv6 real, déjalo en `yes`.

### Caché

La caché es la razón de ser del resolutor. Los parámetros que importan:

```yaml
server:
    num-threads: 2
    msg-cache-size: 64m
    rrset-cache-size: 128m   # regla práctica: el doble que msg-cache
    prefetch: yes            # renueva entradas populares antes de que caduquen
    cache-min-ttl: 60        # modesto: subirlo viola los TTL del propietario
    serve-expired: yes       # sirve caducadas si el upstream no responde
```

!!! warning "Depende de la versión"
    `serve-expired` no está en las versiones más antiguas de Unbound, y sus opciones asociadas (`serve-expired-ttl`, `serve-expired-client-timeout`) han cambiado con las versiones. Comprueba `unbound -V` y la página de manual de tu versión antes de afinarlas.

`cache-min-ttl` es tentador, pero un TTL de cinco minutos suele estar puesto por un motivo (un failover, un balanceador). Úsalo con valores bajos o no lo uses.

### Forward-zone: zona interna y upstream cifrado

Dos usos de `forward-zone`. El primero envía la zona interna al autoritativo; el segundo, opcional, manda **todo lo demás** a un upstream mediante DNS over TLS en lugar de recursar desde la raíz:

```yaml
forward-zone:
    name: "lab.ejemplo.org."
    forward-addr: 192.168.10.3

# Opcional: delegar el resto en un upstream por DoT (puerto 853)
server:
    tls-cert-bundle: /etc/ssl/certs/ca-certificates.crt

forward-zone:
    name: "."
    forward-tls-upstream: yes
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 9.9.9.9@853#dns.quad9.net
```

El formato `IP@puerto#nombre` es lo que permite a Unbound validar el certificado del upstream; sin el `#nombre` el cifrado funciona pero no se autentica al servidor. Antes de decidir si usar upstream, piensa qué ganas y qué pierdes:

- **Recursar tú mismo** (sin `forward-zone: "."`): no dependes de nadie ni le cuentas a nadie lo que consultas, pero los autoritativos del mundo ven tu IP y el tráfico sale en claro.
- **DoT hacia un upstream**: el operador de tu red no ve las consultas, pero se las cuentas a un tercero y dependes de él.

Si la zona interna cuelga de un dominio público firmado con DNSSEC y el autoritativo interno no firma, Unbound puede devolver `SERVFAIL` al validar; hay `domain-insecure: "lab.ejemplo.org"` para ese caso. Detalle de la validación en [DNSSEC](dnssec.md).

### Validar y operar

```bash
unbound-checkconf                      # sintaxis y ficheros incluidos
sudo systemctl restart unbound
dig @192.168.10.2 debian.org +short
```

`unbound-checkconf` debe ejecutarse **siempre** antes de reiniciar: un fichero roto deja el resolutor caído y toda la red sin DNS. Para operar en caliente, activa el canal de control:

```yaml
remote-control:
    control-enable: yes
    control-interface: 127.0.0.1
```

Genera los certificados con `unbound-control-setup` si tu paquete no lo hizo. Después:

```bash
unbound-control status                  # versión, uptime, hilos
unbound-control stats_noreset           # contadores sin ponerlos a cero
unbound-control flush nombre.ejemplo.org   # borra un nombre de la caché
unbound-control flush_zone ejemplo.org     # borra toda una zona
unbound-control list_forwards           # forward-zones activas
unbound-control reload                  # relee la configuración
```

`flush` es lo primero que haces tras corregir un registro: el resolutor seguirá sirviendo el dato viejo hasta que caduque el TTL.

## Zona interna autoritativa con BIND

BIND (`bind9` en Debian, `bind` en RHEL; el servicio se llama `named`) es el autoritativo de referencia. Lo configuramos solo como autoritativo: **sin recursión**.

!!! warning "Depende de la versión"
    `type primary` y `type secondary` (y `primaries` en lugar de `masters`) llegaron con BIND 9.16. En versiones anteriores se escribe `type master` / `type slave`, que las nuevas siguen aceptando como alias. Comprueba `named -v`.

### named.conf

```text
// /etc/bind/named.conf.options
options {
    directory "/var/cache/bind";
    listen-on { 192.168.10.3; };
    recursion no;
    allow-query { 192.168.10.0/24; };
    allow-transfer { none; };
    notify yes;
};
```

```text
// /etc/bind/named.conf.local
zone "lab.ejemplo.org" {
    type primary;
    file "/etc/bind/zones/db.lab.ejemplo.org";
};
```

`recursion no` es la línea importante: sin ella tu autoritativo contesta a cualquiera consultas de cualquier dominio. `allow-transfer { none; }` por defecto cierra las transferencias; se abren después para el secundario (ver [Alta disponibilidad](#alta-disponibilidad)).

### Fichero de zona

```text
; /etc/bind/zones/db.lab.ejemplo.org
$TTL 1h
@   IN  SOA ns1.lab.ejemplo.org. hostmaster.lab.ejemplo.org. (
            2026101101  ; serial (AAAAMMDDNN)
            1h          ; refresh
            15m         ; retry
            1w          ; expire
            5m )        ; TTL negativo

    IN  NS  ns1.lab.ejemplo.org.

ns1     IN  A     192.168.10.3
pve1    IN  A     192.168.10.11
pve2    IN  A     192.168.10.12
nas     IN  A     192.168.10.20
k8s-api IN  A     192.168.10.30
grafana IN  CNAME nas
```

Reglas del SOA que más se rompen:

- **El serial debe subir en cada cambio.** Los secundarios solo transfieren la zona si el serial del primario es mayor. Editar un registro sin subirlo es el fallo número uno: el primario sirve el dato nuevo y el secundario, el viejo. El formato `AAAAMMDDNN` permite hasta 100 cambios al día.
- **El nombre debe terminar en punto** cuando es absoluto. `ns1.lab.ejemplo.org` sin punto final se interpreta como `ns1.lab.ejemplo.org.lab.ejemplo.org.`.
- **El segundo campo del SOA** (`hostmaster.lab.ejemplo.org.`) es el correo del responsable con el primer punto en lugar de la `@`.
- **Un CNAME no puede convivir con otros registros del mismo nombre**, y no puede estar en el ápice de la zona.

### Comprobar y recargar

```bash
named-checkconf                                           # sintaxis de named.conf
named-checkconf -z                                        # además, carga cada zona
named-checkzone lab.ejemplo.org /etc/bind/zones/db.lab.ejemplo.org

sudo rndc reload                      # recarga todo
sudo rndc reload lab.ejemplo.org      # solo esa zona
sudo rndc zonestatus lab.ejemplo.org  # serial cargado, tipo, última recarga
```

`named-checkzone` responde `OK` y el serial cargado si la zona es válida; los errores indican línea y causa (nombre sin punto, registro duplicado, CNAME con otros datos). `rndc` se comunica por el puerto 953 en localhost con una clave que la instalación del paquete suele generar sola (`rndc-confgen` si hay que crearla a mano).

Para las zonas inversas de `192.168.10.0/24` y los registros PTR, ver [Registros PTR y zonas inversas](registros_ptr_zonas_inversas.md).

## PowerDNS como alternativa con API

[PowerDNS Authoritative Server](https://doc.powerdns.com/authoritative/) guarda las zonas en una **base de datos** (SQLite, MySQL/MariaDB o PostgreSQL) en lugar de ficheros, y expone una **API HTTP** para crear zonas y registros. Es la opción cuando los registros los gestiona una herramienta (Terraform, scripts, un panel como PowerDNS-Admin) y no una persona editando ficheros.

```ini
# /etc/powerdns/pdns.conf (fragmento)
launch=gsqlite3
gsqlite3-database=/var/lib/powerdns/pdns.sqlite3
local-address=192.168.10.3
api=yes
api-key=CAMBIA-ESTE-VALOR
webserver=yes
webserver-address=127.0.0.1
webserver-port=8081
```

```bash
pdnsutil create-zone lab.ejemplo.org ns1.lab.ejemplo.org
pdnsutil add-record lab.ejemplo.org nas A 3600 192.168.10.20
pdnsutil check-all-zones

curl -s -H 'X-API-Key: CAMBIA-ESTE-VALOR' \
  http://127.0.0.1:8081/api/v1/servers/localhost/zones
```

!!! warning "Depende de la versión"
    Los nombres de las opciones del backend y la sintaxis de `pdnsutil` han cambiado entre PowerDNS 3.x, 4.x y 5.x. El ejemplo sigue la línea 4.x; confirma con `pdnsutil --help` y la documentación de tu versión antes de copiarlo. El esquema SQL inicial lo da el propio paquete.

Diferencias con BIND que importan en la práctica:

- **El serial lo puede gestionar el servidor** (opción `SOA-EDIT` por zona) en lugar de editarlo tú a mano.
- **La replicación** puede ser la de siempre (AXFR/NOTIFY) o la nativa de la base de datos (réplicas MySQL/PostgreSQL), sin transferencias de zona.
- **No recursa**: PowerDNS Recursor es otro producto. Con Unbound delante ya tienes resolutor.
- La clave de la API da control total sobre las zonas: mantenla en `127.0.0.1` o detrás de un proxy con TLS y no la publiques.

## Dominio interno y split-horizon

### Qué dominio usar

| Opción | Veredicto |
|---|---|
| `lab.tudominio.org` (subdominio de un dominio que posees) | **Recomendada.** Nadie más puede registrarlo, permite certificados reales por reto DNS-01 y evita colisiones |
| `home.arpa` | **Buena** si no tienes dominio. Reservado por el RFC 8375 precisamente para redes domésticas; no se delegará nunca |
| `.local` | **Evítala.** Está reservada para mDNS (RFC 6762) |
| `.lan`, `.home`, `.corp` | Evítalas. No están reservadas y pueden terminar delegadas públicamente |
| `.internal` | Reservada por ICANN para uso privado en 2024; válida si tu software la acepta |

El problema de `.local`: los sistemas con Avahi, Bonjour (macOS) o `systemd-resolved` envían esos nombres por multicast (mDNS) **en lugar de preguntar a tu DNS**. El síntoma es el más desconcertante posible: `dig nas.local` funciona y `ping nas.local` tarda cinco segundos o falla, porque cada herramienta usa una ruta de resolución distinta. Los certificados válidos para nombres internos (reto DNS-01) se tratan en [Certificados TLS](certificados_tls.md).

### Split-horizon

*Split-horizon* es responder de forma distinta a una misma pregunta según quién la haga: desde dentro `app.ejemplo.org` es `192.168.10.20`; desde fuera, la IP pública. Hay dos formas de hacerlo sin complicarte:

**1. En el resolutor (la más simple).** Unbound sirve datos locales que prevalecen sobre el DNS público:

```yaml
server:
    local-zone: "app.ejemplo.org." transparent
    local-data: "app.ejemplo.org. 300 IN A 192.168.10.20"
```

`transparent` significa que los nombres de esa zona **sin** `local-data` se resuelven con normalidad por el camino habitual; con otros tipos (`static`) un nombre no definido daría `NXDOMAIN`.

**2. En el autoritativo con `view` de BIND.** Dos versiones de la misma zona según el cliente:

```text
acl interna { 192.168.10.0/24; 127.0.0.1; };

view "interna" {
    match-clients { interna; };
    zone "ejemplo.org" { type primary; file "/etc/bind/zones/db.ejemplo.org.int"; };
};

view "externa" {
    match-clients { any; };
    zone "ejemplo.org" { type primary; file "/etc/bind/zones/db.ejemplo.org.ext"; };
};
```

Con vistas, **todas las zonas deben estar dentro de alguna vista**. Las dos versiones de la zona son ficheros independientes y hay que mantenerlos sincronizados, lo que a la larga cuesta más que la opción 1. Reserva las vistas para cuando el mismo servidor atiende a redes distintas. Los registros de correo de la zona pública están en [SPF, DKIM y DMARC](spf_dkim_dmarc.md).

## Integración con la red

### DHCP reparte el resolutor

Los clientes usan el DNS que les da el DHCP. Con dnsmasq:

```ini
# /etc/dnsmasq.d/dhcp.conf
dhcp-range=192.168.10.100,192.168.10.200,12h
dhcp-option=option:dns-server,192.168.10.2,192.168.10.5
dhcp-option=option:domain-search,lab.ejemplo.org
domain=lab.ejemplo.org
```

En Kea la opción equivalente es `domain-name-servers` y en ISC DHCP, `option domain-name-servers`. Reparte **dos resolutores** (ver [Alta disponibilidad](#alta-disponibilidad)) y un `domain-search` para que `ping nas` complete a `nas.lab.ejemplo.org`. Con dnsmasq haciendo de DHCP **y** de DNS a la vez, recuerda que dnsmasq también escucha en el puerto 53 y chocará con Unbound si comparten IP.

### Pi-hole o AdGuard Home como filtro

Si quieres bloqueo de publicidad o rastreadores, Pi-hole o AdGuard Home se ponen **delante** como filtro y usan Unbound como upstream. Los clientes preguntan al filtro; el filtro, a Unbound; Unbound, al autoritativo o a internet. Dos consecuencias a tener en cuenta:

- Unbound ve todas las consultas con la IP del filtro, no la del cliente. Añade esa IP a `access-control` y busca los logs por cliente en el filtro, no en Unbound.
- El filtro pasa a ser un punto único de fallo para toda la red: o lo duplicas, o el DHCP reparte también un resolutor "sin filtro" de respaldo.

No se despliegan aquí; solo se describe cómo encajan con el resolutor.

### Proxmox

En cada nodo, `Nodo → Sistema → DNS` fija servidores y dominio de búsqueda, y se refleja en `/etc/resolv.conf`. Los contenedores LXC heredan el DNS del host salvo que lo fijes por contenedor, y las VM con cloud-init lo reciben por configuración:

```bash
pct set 201 --nameserver 192.168.10.2 --searchdomain lab.ejemplo.org
qm set 301 --nameserver 192.168.10.2 --searchdomain lab.ejemplo.org
```

El nombre de cada nodo debe resolverse a su IP **real** (no a `127.0.1.1`) y, para la comunicación del clúster, conviene no depender solo del DNS: mantén los nodos también en `/etc/hosts`. Un clúster que no arranca porque el DNS está en una VM del propio clúster es un clásico. Detalles en [Proxmox base](../proxmox/proxmox_base.md).

### Kubernetes

CoreDNS resuelve los nombres del clúster y reenvía el resto al `resolv.conf` del nodo. Para que los pods vean tu zona interna, añade un bloque al `Corefile` del ConfigMap `coredns` de `kube-system`:

```text
lab.ejemplo.org:53 {
    errors
    cache 30
    forward . 192.168.10.2
}
```

Después reinicia los pods de CoreDNS (`kubectl -n kube-system rollout restart deployment coredns`). Si el `resolv.conf` del nodo apunta al stub `127.0.0.53` de systemd-resolved, apunta el kubelet al fichero real (`/run/systemd/resolve/resolv.conf`) o CoreDNS acabará reenviándose a sí mismo en bucle. Contexto del clúster en [Kubernetes base](../kubernetes/kubernetes_base.md).

### Firewall y puertos

DNS usa **53/UDP y 53/TCP** (TCP para respuestas grandes y transferencias de zona; bloquearlo causa fallos intermitentes difíciles de ver). DoT usa **853/TCP** hacia el upstream, y `rndc` el 953 solo por localhost. Ver [Tablas de puertos comunes](tablas_puertos_comunes.md).

## Alta disponibilidad

### Resolutores

Dos resolutores Unbound **idénticos** en hosts distintos, ambos entregados por DHCP. Es todo. La caché es independiente en cada uno y no necesita replicarse.

Sé consciente de cómo se comportan los clientes: la biblioteca de Linux prueba los servidores **en orden** y, si el primero está caído, espera el timeout (5 s por defecto) antes de pasar al segundo, así que cada consulta se vuelve lenta, no solo la primera. En `/etc/resolv.conf` puedes acortarlo:

```text
options timeout:1 attempts:2
```

Si necesitas una única IP que siga viva, una IP virtual con keepalived entre los dos resolutores lo resuelve sin tocar a los clientes.

### Autoritativo: primario y secundario

El secundario obtiene la zona por **transferencia** (AXFR/IXFR) y el primario le avisa de los cambios con NOTIFY. Genera una clave TSIG para autenticar la transferencia en lugar de confiar en la IP origen:

```bash
tsig-keygen -a hmac-sha256 xfer-key
```

Imprime un bloque `key "xfer-key" { ... };` con el secreto. Pégalo en **ambos** servidores y configura:

```text
// Primario (192.168.10.3)
zone "lab.ejemplo.org" {
    type primary;
    file "/etc/bind/zones/db.lab.ejemplo.org";
    allow-transfer { key xfer-key; };
    also-notify { 192.168.10.4; };
};
```

```text
// Secundario (192.168.10.4)
server 192.168.10.3 { keys { xfer-key; }; };

zone "lab.ejemplo.org" {
    type secondary;
    file "/var/cache/bind/db.lab.ejemplo.org";
    primaries { 192.168.10.3; };
};
```

El secundario guarda la zona en `/var/cache/bind` porque `named` suele poder escribir ahí y no en `/etc/bind`. Añade el segundo servidor como `NS` en la zona (y su registro `A`) para que los resolutores sepan que existe. Después de recargar:

```bash
dig @192.168.10.3 lab.ejemplo.org SOA +short   # el serial del primario
dig @192.168.10.4 lab.ejemplo.org SOA +short   # debe coincidir
sudo rndc retransfer lab.ejemplo.org           # en el secundario: forzar
```

`also-notify` es necesario cuando el secundario no figura como `NS` de la zona (o no quieres depender de ello); si ya está en los `NS`, BIND le avisa solo. Si el primario cae, el secundario sigue sirviendo la zona hasta que venza el valor `expire` del SOA.

## Diagnóstico

`dig` (paquete `dnsutils` o `bind-utils`) es la herramienta principal. Los cuatro patrones que resuelven casi todo:

```bash
dig nas.lab.ejemplo.org                      # consulta con el resolutor del sistema
dig @192.168.10.2 nas.lab.ejemplo.org        # a un servidor concreto
dig @192.168.10.3 nas.lab.ejemplo.org +norecurse +short   # al autoritativo, solo la IP
dig +trace nas.lab.ejemplo.org               # sigue la delegación desde la raíz
```

Qué mirar en la respuesta:

- **`status:`** `NOERROR` (existe), `NXDOMAIN` (el nombre no existe), `SERVFAIL` (el servidor falló: validación DNSSEC, upstream caído, zona rota), `REFUSED` (el servidor no quiere hablar contigo: `access-control` o `allow-query`).
- **Flag `aa`** (authoritative answer): presente solo si respondió el autoritativo. Si preguntas al autoritativo y no sale, no está sirviendo esa zona.
- **Flag `ra`** (recursion available): indica que ese servidor recursa. Un autoritativo bien configurado **no** lo trae.
- **`+trace`** ignora tu resolutor y camina desde la raíz; sirve para ver si el problema es la delegación pública o tu configuración local.

Más opciones útiles: `+tcp` fuerza TCP (comprueba que el 53/TCP está abierto), `-x 192.168.10.20` hace la consulta inversa, `+dnssec` pide los registros de firma, y `+short` deja solo el dato.

`drill` (paquete `ldnsutils`) acepta la misma idea con otra sintaxis y es muy cómodo para DNSSEC:

```bash
drill @192.168.10.2 nas.lab.ejemplo.org
drill -T nas.lab.ejemplo.org       # traza desde la raíz
drill -S ejemplo.org               # persigue las firmas DNSSEC
```

En un host con systemd-resolved, `resolvectl status` y `resolvectl query nombre` enseñan qué servidor y qué ruta usa **realmente** el sistema, que no siempre es el de `/etc/resolv.conf`.

### Logs

```bash
journalctl -u unbound -f
journalctl -u named -f        # en Debian el servicio también se llama bind9

sudo rndc querylog on         # BIND: registra cada consulta (y se apaga con off)
```

Para Unbound, `verbosity: 2` en `server:` da detalle de resolución, y `log-queries: yes` registra cada consulta; ambos generan mucho volumen, actívalos solo mientras depuras. Más metodología general en [Troubleshooting de red](troubleshooting.md).

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `REFUSED` desde un cliente | La IP del cliente no está en `access-control` (Unbound) o `allow-query` (BIND) | Añadir la subred y recargar; probar con `dig @servidor` |
| Unbound o BIND no arrancan: "address already in use" | Otro servicio ocupa el 53 (systemd-resolved, dnsmasq) | `ss -lntup \| grep ':53'`; enlazar a IPs concretas o desactivar el stub |
| El secundario sirve datos viejos | El serial no subió, o falta NOTIFY/transferencia | Subir el serial; comparar `SOA +short`; `rndc retransfer` en el secundario |
| Transferencia rechazada | Falta TSIG o `allow-transfer` no incluye la clave | Revisar la clave idéntica en ambos y los logs de `named` |
| `nombre.local` falla en unas herramientas y no en otras | `.local` se resuelve por mDNS, no por el DNS | Migrar a `home.arpa` o a un subdominio propio |
| `SERVFAIL` solo en la zona interna | Unbound valida DNSSEC y la zona interna cuelga de un dominio firmado | `domain-insecure` para esa zona, o firmarla ([DNSSEC](dnssec.md)) |
| Resolución con retardos de ~5 s | El primer servidor del `resolv.conf` está caído | Reparar o reducir `timeout`; revisar el orden |
| Cambias un registro y los clientes ven el viejo | Caché del resolutor | `unbound-control flush nombre`; esperar el TTL |
| Falla con respuestas grandes | 53/TCP bloqueado en el firewall | Abrir TCP además de UDP; probar `dig +tcp` |
| Los pods no resuelven la zona interna | Falta el bloque en el `Corefile` de CoreDNS | Añadir el `forward` y reiniciar CoreDNS |

## Buenas prácticas

- **Resolutor y autoritativo en servicios separados**, aunque compartan máquina al principio. Recursión desactivada en el autoritativo, `access-control` cerrado en el resolutor.
- **Valida antes de recargar**: `unbound-checkconf`, `named-checkconf -z` y `named-checkzone` en cada cambio. Un script o un hook de Git que los ejecute evita la mayoría de los incidentes.
- **Un solo sitio donde editar y el serial siempre sube.** Las zonas son texto: versiónalas en Git y despliega con [Ansible](../ansible/ansible_base.md).
- **Dos resolutores desde el primer día**, repartidos por DHCP, en hosts físicos distintos. El DNS no debe vivir solo dentro del clúster que depende de él.
- **TSIG para las transferencias**, no confianza en la IP origen.
- **Un dominio que posees (o `home.arpa`)**, nunca `.local`.
- **Respalda las zonas** y guarda los ficheros fuera de la máquina que las sirve; una caché se reconstruye, una zona no.
- **No expongas el resolutor a internet**; si hay que dar DNS fuera de la LAN, hazlo por VPN.

## Referencias

- [Documentación de Unbound](https://unbound.docs.nlnetlabs.nl/en/latest/)
- [BIND 9 Administrator Reference Manual](https://bind9.readthedocs.io/)
- [PowerDNS Authoritative Server](https://doc.powerdns.com/authoritative/)
- [RFC 8375: home.arpa](https://www.rfc-editor.org/rfc/rfc8375)
- [RFC 6762: Multicast DNS](https://www.rfc-editor.org/rfc/rfc6762)
- [DNSSEC](dnssec.md) · [Registros PTR y zonas inversas](registros_ptr_zonas_inversas.md)
- [Troubleshooting de red](troubleshooting.md) · [Tablas de puertos comunes](tablas_puertos_comunes.md) · [SPF, DKIM y DMARC](spf_dkim_dmarc.md)
- [Proxmox base](../proxmox/proxmox_base.md) · [Kubernetes base](../kubernetes/kubernetes_base.md)
