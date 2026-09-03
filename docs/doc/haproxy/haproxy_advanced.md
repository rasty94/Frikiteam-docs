---
title: "HAProxy Avanzado — Balanceo, TLS y Alta Disponibilidad"
description: "Algoritmos de balanceo, health checks activos y pasivos, persistencia con cookies y stick tables, ACLs, terminación TLS, rate limiting, maxconn y colas, recarga sin cortes y HA con keepalived."
keywords: "haproxy, balanceo de carga, leastconn, stick table, httpchk, tls, rate limiting, maxconn, seamless reload, keepalived, vrrp"
tags: ['networking', 'high-availability', 'performance']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 25 min
category: Redes
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "[HAProxy — guía base](haproxy_base.md)"
  - "HTTP y TLS a nivel de conceptos"
  - "Acceso root al balanceador"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# HAProxy Avanzado — Balanceo, TLS y Alta Disponibilidad

## El problema

La configuración de tres líneas funciona. `balance roundrobin`, dos servidores, `check`, y el tráfico se reparte. Hasta que un backend deja de responder correctamente pero sigue aceptando conexiones TCP, y HAProxy le manda la mitad de los usuarios durante horas. O hasta que despliegas y todo el mundo pierde la sesión. O hasta que un bot descubre `/login` y tumba la base de datos mientras el balanceador reparte el ataque con toda diligencia. Ninguno de esos fallos se arregla cambiando de balanceador: se arreglan configurando el que ya tienes.

!!! note "Qué cubre y qué no"
    La instalación y el `haproxy.cfg` mínimo están en [HAProxy — guía base](haproxy_base.md). Aquí ya tienes tráfico pasando y hablamos de **por qué** elegir cada opción. La comparativa con otros proxies vive en [Comparativa de balanceadores](../networking/load_balancer_comparison.md).

## 📋 Tabla de Contenidos

- [Elegir algoritmo de balanceo](#elegir-algoritmo-de-balanceo)
- [Health checks: activos y pasivos](#health-checks-activos-y-pasivos)
- [Persistencia: cookies frente a stick tables](#persistencia-cookies-frente-a-stick-tables)
- [ACLs y enrutado](#acls-y-enrutado)
- [Terminación TLS](#terminacion-tls)
- [Rate limiting con stick tables](#rate-limiting-con-stick-tables)
- [maxconn y colas](#maxconn-y-colas)
- [Recarga sin cortar conexiones](#recarga-sin-cortar-conexiones)
- [Estadísticas y logs](#estadisticas-y-logs)
- [Alta disponibilidad del propio HAProxy](#alta-disponibilidad-del-propio-haproxy)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Elegir algoritmo de balanceo

El criterio real no es "cuál es mejor", sino **cuánto dura una petición**.

| Algoritmo | Reparte según | Elígelo cuando |
|---|---|---|
| `roundrobin` | Turno rotatorio ponderado | Peticiones cortas y homogéneas (HTTP típico), servidores de capacidad similar |
| `leastconn` | Menos conexiones activas | Sesiones largas o de duración muy variable: WebSocket, LDAP, SQL, descargas |
| `source` | Hash de la IP origen | Necesitas afinidad sin poder usar cookies (modo TCP, clientes que no las gestionan) |
| `uri` | Hash de la parte izquierda de la URI | Granjas de caché: el mismo objeto cae siempre en el mismo nodo |

El error frecuente es usar `leastconn` "porque suena más inteligente". Con peticiones de 20 ms el número de conexiones activas es ruido estadístico y `roundrobin` reparte igual con menos trabajo. `leastconn` gana justo donde `roundrobin` falla: cuando una petición puede durar 200 ms o 20 minutos y el turno rotatorio amontona las largas en un mismo servidor.

```haproxy
backend app
  balance roundrobin
  server app1 10.0.0.11:8080 check weight 100
  server app2 10.0.0.12:8080 check weight 50     # la mitad de tráfico

backend ws
  balance leastconn                              # WebSocket: conexiones largas
  server ws1 10.0.0.21:8080 check
  server ws2 10.0.0.22:8080 check
```

`source` y `uri` reparten un hash entre los servidores **vivos**. Con el modo por defecto (`map-based`) cae un nodo y se recalcula todo: *todos* los clientes cambian de servidor. Añadir `hash-type consistent` al backend limita la redistribución a la fracción del nodo caído; con más de dos servidores casi siempre es lo que quieres. Y `source` reparte por IP, no por usuario: detrás de un CGNAT o de la NAT de una oficina, miles de clientes son una sola IP y el balanceo se desequilibra solo.

## Health checks: activos y pasivos

`server app1 10.0.0.11:8080 check` hace una comprobación de **capa 4**: abre una conexión TCP y la cierra. Eso responde a una única pregunta —¿hay algo escuchando?— y a ninguna de las que importan. Un servidor con el pool de conexiones agotado acepta TCP y devuelve 500. Un Tomcat con el WAR mal desplegado acepta TCP y devuelve 404 en todo. Un proceso vivo pero bloqueado acepta TCP y no responde nunca. En los tres casos el check pasa y HAProxy sigue enviando usuarios a un servidor roto.

```haproxy
backend app
  option httpchk GET /healthz
  http-check expect status 200
  server app1 10.0.0.11:8080 check inter 3s fall 3 rise 2 observe layer7 error-limit 10 on-error mark-down
  server app2 10.0.0.12:8080 check inter 3s fall 3 rise 2 observe layer7 error-limit 10 on-error mark-down
```

| Parámetro | Qué controla | Criterio |
|---|---|---|
| `inter` | Intervalo entre sondeos | 2–5 s; bajarlo mucho añade carga al backend |
| `fall` | Fallos consecutivos para marcarlo caído | 3, para no expulsar un servidor por un pico puntual |
| `rise` | Aciertos para readmitirlo | 2 o más: readmitir rápido produce oscilación |
| `observe layer7` | Vigila el **tráfico real**, no los sondeos | Detecta la caída sin esperar al siguiente `inter` |
| `on-error mark-down` | Qué hacer al superar `error-limit` | Sacar el servidor de rotación de inmediato |

Los dos mecanismos se complementan: el pasivo (`observe`) detecta rápido porque ve todas las peticiones; el activo (`check`) decide cuándo readmitir. Y un buen `/healthz` comprueba las dependencias críticas: un endpoint que devuelve 200 siempre es un check de capa 4 con pasos extra.

!!! warning "La sintaxis de `option httpchk` depende de la rama"
    `option httpchk GET /healthz` funciona en todas las ramas mantenidas. Lo que cambió es cómo se añaden cabeceras: meter `Host` dentro de la propia línea de `option httpchk` está desaconsejado desde HAProxy 2.2, que introdujo `http-check send` para hacer lo mismo de forma legible. Mira la documentación de **tu** versión (`haproxy -v`) antes de copiar un ejemplo de un blog: es donde más divergen los ejemplos que circulan.

## Persistencia: cookies frente a stick tables

Si la aplicación guarda estado en memoria del servidor, el usuario tiene que volver al mismo nodo. Hay dos formas y no son equivalentes.

```haproxy
# Opción A: cookie insertada por HAProxy (solo modo HTTP)
backend app
  balance roundrobin
  cookie SRVID insert indirect nocache httponly secure
  server app1 10.0.0.11:8080 check cookie a1
  server app2 10.0.0.12:8080 check cookie a2

# Opción B: stick table, invisible para el cliente, también en modo TCP
backend tcpapp
  balance roundrobin
  stick-table type ip size 200k expire 30m
  stick on src
  server t1 10.0.0.21:5432 check
  server t2 10.0.0.22:5432 check
```

`insert` crea la cookie, `indirect` la quita antes de pasar la petición al backend, `nocache` evita que un proxy intermedio cachee la respuesta con ella. El valor (`a1`) es opaco: no pongas ahí la IP del servidor.

| | Cookie | Stick table |
|---|---|---|
| Funciona en modo TCP | No | Sí |
| Depende del cliente | Sí: si la borra, pierde afinidad | No |
| Sobrevive al reinicio del proxy | Sí | No (tabla en memoria) |
| Coste de memoria en el proxy | Nulo | Proporcional al número de entradas |

Regla práctica: **HTTP con clientes normales, cookie; TCP o clientes sin cookies, stick table**. En un par de balanceadores, la tabla solo se comparte si declaras una sección `peers` y la referencias con `stick-table ... peers nombre`; si no, cada nodo tiene su propia memoria y el failover pierde todas las sesiones. En cualquier caso la persistencia es una tirita: convierte cualquier caída de servidor en pérdida de sesión para sus usuarios. La solución real es sacar el estado a Redis o a la base de datos y no necesitar afinidad.

## ACLs y enrutado

Una ACL es una condición con nombre; `use_backend` la usa para decidir destino. Se evalúan de arriba abajo y gana la primera que casa.

```haproxy
frontend web
  bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1

  acl host_api    hdr(host) -i api.ejemplo.com      # por host
  acl host_admin  hdr_beg(host) -i admin.
  acl path_static path_beg /static/ /assets/        # por path

  use_backend api    if host_api
  use_backend admin  if host_admin
  use_backend static if path_static
  default_backend app
```

`hdr(host) -i` compara la cabecera completa ignorando mayúsculas; `hdr_beg(host) -i admin.` casa cualquier subdominio que empiece así. `path_beg` acepta varios valores y casa si coincide **alguno**. Se combinan: `if host_api path_static` es un AND, `if host_api || host_admin` un OR, `if !host_api` niega. Y siempre debe haber un `default_backend`: sin él, lo que no casa recibe un 503 y el log solo dice `NOSRV`.

## Terminación TLS

```haproxy
global
  ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

frontend web
  bind *:80
  bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1
  http-request redirect scheme https code 301 unless { ssl_fc }

  http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains"
  http-response set-header X-Content-Type-Options nosniff
  http-response set-header Referrer-Policy strict-origin-when-cross-origin
  http-request set-header X-Forwarded-Proto https if { ssl_fc }
  default_backend app
```

- **`crt` acepta un fichero o un directorio.** Con directorio, HAProxy carga todos los `.pem` y selecciona por SNI. Cada `.pem` debe contener la cadena completa **y** la clave privada concatenadas.
- **`alpn h2,http/1.1`** es lo que habilita HTTP/2 hacia el cliente. Sin ese parámetro no hay HTTP/2 por mucho que el navegador lo soporte.
- **La redirección va la primera** en el frontend, con `unless { ssl_fc }` para no redirigir en bucle lo que ya llega cifrado. Y **HSTS solo cuando estés seguro**: un año de `max-age` con un certificado caducado es un sitio inaccesible que el usuario no puede saltarse; añade `preload` solo si vas a inscribir el dominio en la lista de precarga.
- **Re-cifrado hacia el backend** si la red interna no es de confianza: `server app1 10.0.0.11:8443 ssl verify required ca-file /etc/ssl/certs/ca.pem check check-ssl`. `verify required` es lo que hace que esto sirva de algo; `verify none` cifra sin autenticar nada.

La gestión de los certificados (ACME, renovación, cadenas) está en [Certificados TLS](../networking/certificados_tls.md).

## Rate limiting con stick tables

Una stick table es un mapa clave → contadores con expiración: la misma estructura de la persistencia, usada aquí para contar.

```haproxy
frontend web
  bind *:443 ssl crt /etc/haproxy/certs/

  # Clave = IP, hasta 100k entradas, se olvida a los 10 min de inactividad.
  stick-table type ip size 100k expire 10m store http_req_rate(10s),http_err_rate(60s)
  http-request track-sc0 src                        # esto es lo que cuenta

  acl exceso_peticiones sc_http_req_rate(0) gt 100
  acl exceso_errores    sc_http_err_rate(0) gt 20
  http-request deny deny_status 429 if exceso_peticiones
  http-request deny deny_status 403 if exceso_errores
  default_backend app
```

1. `store http_req_rate(10s)` es una **tasa deslizante**: peticiones en los últimos 10 segundos, no un contador absoluto que haya que reiniciar.
2. `http-request track-sc0 src` es lo que incrementa el contador. Sin esta línea la tabla existe pero está vacía y las ACLs nunca disparan. Es el olvido número uno.
3. `sc_http_req_rate(0)` lee la ranura 0, la misma que declaró `track-sc0`; hay varias (`sc0`, `sc1`, `sc2`) para rastrear claves distintas a la vez. Y `deny_status 429` devuelve *Too Many Requests*: un cliente legítimo puede reintentar con backoff y en el log se distingue el abuso del bloqueo por política.

`http_err_rate` cuenta respuestas 4xx y detecta fuerza bruta mejor que la tasa total: un escáner de contraseñas genera pocos accesos y muchos 401.

!!! tip "Contar antes de bloquear"
    Despliega la tabla y el `track-sc0` sin los `deny`, deja pasar un día y mira los valores reales con `echo "show table web" | socat stdio /run/haproxy/admin.sock`. Un umbral elegido a ojo bloquea a tu propio monitor de uptime o a una oficina entera saliendo por NAT. Si estás detrás de un CDN, rastrea la IP real de `X-Forwarded-For` y no `src`, que será siempre la del CDN.

A nivel de red esto se complementa con [nftables y fail2ban](../cybersecurity/nftables_fail2ban.md): HAProxy filtra en capa 7, el firewall descarta antes de gastar CPU en TLS.

## maxconn y colas

`maxconn` aparece en tres sitios y significa algo distinto en cada uno:

```haproxy
global
  maxconn 20000              # tope del proceso
frontend web
  maxconn 15000              # tope de este frontend
backend app
  timeout queue 10s
  server app1 10.0.0.11:8080 check maxconn 200
  server app2 10.0.0.12:8080 check maxconn 200
```

El de servidor es el interesante: al alcanzarlo, HAProxy **no rechaza**, encola hasta que se libera una ranura. Eso protege al backend de recibir más concurrencia de la que aguanta, pero tiene límite temporal (`timeout queue`); al agotarse el cliente recibe un 503.

El número correcto no se adivina: es la concurrencia con la que el backend responde en tiempo aceptable. Un PHP-FPM con `pm.max_children = 50` tiene un `maxconn` natural de 50; mandarle 500 conexiones no lo hace más rápido, solo mueve la cola del proxy —donde es visible y medible— al servidor, donde se convierte en timeouts. Y si subes el `maxconn` global, sube también el límite de ficheros abiertos del servicio: cada conexión consume descriptores.

## Recarga sin cortar conexiones

`systemctl reload haproxy` no mata el proceso: arranca trabajadores nuevos con la configuración nueva y deja que los antiguos terminen las conexiones que ya tenían.

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg    # validar SIEMPRE antes
systemctl reload haproxy
```

Qué la rompe: **no validar antes** (una configuración inválida hace fallar la recarga, y quedarte sin servicio por una coma es evitable con un comando); **`hard-stop-after` demasiado corto**, que pone tope a la vida de los trabajadores antiguos y es necesaria —sin ella una conexión eterna deja un proceso viejo para siempre— pero corta las peticiones largas si es menor que su duración real; **conexiones muy largas**, porque WebSocket y streaming mantienen procesos antiguos vivos hasta que el cliente se va y recargar cada pocos minutos acumula procesos y memoria; y **ficheros externos** como listas de certificados o mapas, que si están mal en el momento de la recarga la hacen fallar igual.

!!! warning "El detalle que depende de la versión"
    Que sobrevivan las conexiones **existentes** es comportamiento estándar. Que no se pierda ninguna conexión **nueva** durante la ventana de recarga depende de que el proceso nuevo herede los sockets de escucha del antiguo, algo que HAProxy soporta desde la rama 1.8 mediante el socket de administración (`expose-fd listeners` y la opción `-x`) y que en las ramas 2.x con master-worker gestiona el unit de systemd de la distribución. Si necesitas garantía de cero pérdidas, comprueba cómo está montado **tu** unit: los paquetes no lo configuran todos igual.

Para sacar un servidor de rotación antes de un despliegue no hace falta recargar. `drain` deja de mandar conexiones nuevas pero respeta las existentes; `maint` corta en seco.

```bash
echo "set server app/app1 state drain" | socat stdio /run/haproxy/admin.sock
echo "set server app/app1 state ready" | socat stdio /run/haproxy/admin.sock
```

## Estadísticas y logs

```haproxy
listen stats
  bind 127.0.0.1:8404
  stats enable
  stats uri /
  stats refresh 10s
  stats hide-version
  stats auth admin:una-contrasena-larga
  stats admin if LOCALHOST
```

La página expone nombres de servidores, IPs internas, tasas de error y —con `stats admin`— **botones para tumbar backends desde el navegador**. Nunca debe estar en Internet. Tres capas, y conviene tener las tres: `bind` a una interfaz interna o a `127.0.0.1` con túnel SSH; autenticación o restricción por IP (`http-request deny unless { src 10.0.0.0/8 }`); y `stats hide-version` para no regalarle la versión exacta a un escáner. Para Prometheus, HAProxy trae un exportador nativo **si el binario se compiló con `USE_PROMEX`** — compruébalo con `haproxy -vv | grep -i prometheus` antes de configurar `http-request use-service prometheus-exporter`; si no aparece, necesitas un exporter externo. Integración en [Observabilidad](../monitoring/observability_stack.md).

Con `option httplog` cada petición produce una línea; estos son los campos que se leen primero cuando algo va mal:

| Campo | Qué te dice |
|---|---|
| Temporizadores (5 valores con `/`) | Dónde se fue el tiempo: espera del cliente, cola, conexión, respuesta del servidor, total |
| Código de estado | Si es `-1`, no hubo respuesta: el problema es de conexión, no de aplicación |
| Estado de terminación | **El campo más informativo**: quién cortó y en qué fase |
| `srv_conn` / `srv_queue` / `backend_queue` | Si hay cola, tu `maxconn` por servidor es el cuello de botella |
| `retries` | Reintentos de conexión; un valor alto sostenido señala red o backend inestable |
| Backend/servidor | `NOSRV` significa que ningún servidor estaba disponible |

| Estado | Lectura |
|---|---|
| `----` | Petición completada con normalidad |
| `sH--` | Timeout esperando cabeceras de respuesta: el backend tarda más que `timeout server` |
| `sQ--` | Expiró en cola: se alcanzó el `maxconn` del servidor y venció `timeout queue` |
| `SC--` | HAProxy no pudo conectar con el servidor (rechazo o red) |
| `SD--` | El servidor cortó a mitad de la transferencia |
| `cD--` | El cliente dejó de leer: red lenta o cliente que abandona |
| `PR--` | Denegada por una regla del propio proxy |

Distinguir `sH` de `SD` ahorra horas: el primero es tu aplicación tardando demasiado, el segundo es tu aplicación muriéndose a mitad de respuesta. Son problemas distintos y el navegador muestra lo mismo. Y si un monitor de salud genera miles de líneas al día, enmascara lo interesante: `option dontlognull` descarta conexiones sin datos y `monitor-uri` permite aislar el sondeo en un frontend aparte.

## Alta disponibilidad del propio HAProxy

Un balanceador único es un punto único de fallo bien disfrazado: has dado alta disponibilidad a la aplicación y se la has quitado a la entrada. El patrón habitual es un par de nodos con **keepalived** e IP virtual (VIP) por VRRP.

1. Los dos nodos anuncian su prioridad por VRRP en la red local. El de prioridad más alta se queda la VIP y responde al ARP por ella.
2. Si el BACKUP deja de recibir anuncios, asume que el MASTER murió, toma la VIP y envía un ARP gratuito para que los switches actualicen sus tablas.
3. Un `vrrp_script` comprueba que HAProxy sigue vivo y **resta prioridad** cuando falla. Es la pieza que hace que el failover ocurra al morir HAProxy y no solo al morir la máquina: sin ella, un nodo con keepalived vivo y HAProxy muerto se queda la VIP y agujerea el servicio.

Los tres puntos donde esto se rompe en la práctica: **`virtual_router_id` duplicado** en el mismo segmento, donde dos parejas con el mismo ID se pisan y fallan de forma intermitente; **VRRP filtrado por el firewall o el switch**, con lo que cada nodo cree muerto al otro, ambos toman la VIP y tienes split brain con IP duplicada; y **HAProxy que no arranca en el BACKUP** porque hace `bind` sobre una IP que ese nodo todavía no tiene — se resuelve con `net.ipv4.ip_nonlocal_bind=1` o haciendo `bind` a `0.0.0.0`, y es el fallo clásico al montar el par por primera vez.

Este esquema es activo/pasivo: el BACKUP no atiende tráfico. Para activo/activo hay que repartir por DNS o por ECMP en el router, y entonces la persistencia por stick table exige la sección `peers` para que ambos nodos vean las mismas asociaciones.

## Troubleshooting

| Síntoma | Causa probable | Comprobación / arreglo |
|---|---|---|
| 503 inmediato, log con `NOSRV` | Ningún servidor pasa el health check | `echo "show stat" \| socat stdio /run/haproxy/admin.sock`; probar `/healthz` con `curl` |
| 503 tras unos segundos, `sQ--` | Cola llena y `timeout queue` vencido | Subir el `maxconn` del servidor si el backend aguanta; si no, es capacidad real |
| 504 o estado `sH--` | El backend tarda más que `timeout server` | Medir el tiempo real antes de subir el timeout: puede ser una consulta sin índice |
| Sesiones perdidas al azar | Persistencia incompleta o backend inestable | Comprobar que hay `cookie` en **cada** línea `server`; buscar flaps en `show stat` |
| Todos los usuarios en un servidor | `balance source` con clientes tras NAT | Pasar a `roundrobin` con cookie, o al menos `hash-type consistent` |
| El rate limiting nunca dispara | Falta `http-request track-sc0 src` | `show table <nombre>`: si está vacía, no se rastrea nada |
| `bind` falla en el nodo BACKUP | La VIP no está en ese nodo | `sysctl -w net.ipv4.ip_nonlocal_bind=1` |
| La recarga corta conexiones largas | `hard-stop-after` menor que la vida de la conexión | Ajustarlo a la duración real de WebSocket o descargas |
| TLS falla solo en algunos dominios | Un `.pem` sin cadena completa o sin clave | Verificar cada fichero: cadena y clave privada concatenadas |

Los cuatro comandos que resuelven la mayoría de los casos:

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg               # sintaxis
haproxy -vv                                          # versión y opciones compiladas
echo "show stat" | socat stdio /run/haproxy/admin.sock
journalctl -u haproxy -f
```

## Buenas prácticas

- **`haproxy -c` antes de cada recarga**, sin excepciones. Es la diferencia entre un cambio y una caída.
- **Health check de capa 7 en todo lo que sirva HTTP**, contra un endpoint que compruebe dependencias reales.
- **`maxconn` por servidor ajustado a la capacidad medida.** Encolar en el proxy, nunca ahogar el backend.
- **Persistencia solo si la aplicación la necesita.** Si puedes sacar el estado a Redis, hazlo y borra la afinidad.
- **La página de estadísticas nunca en Internet**, con `stats hide-version`, y rate limiting medido antes de activarse: primero contar, luego bloquear.
- **HAProxy nunca solo.** Un par con keepalived y un `vrrp_script` que compruebe el proceso, no solo la máquina, con timeouts explícitos en `defaults` y la configuración en Git desplegada con [Ansible](../ansible/ansible_base.md).

## Referencias

- [Documentación de configuración de HAProxy](https://docs.haproxy.org/) — elige tu rama antes de copiar nada
- [HAProxy Management Guide](https://docs.haproxy.org/2.8/management.html) · [Documentación de keepalived](https://keepalived.readthedocs.io/)
- [HAProxy — guía base](haproxy_base.md) · [Comparativa de balanceadores](../networking/load_balancer_comparison.md) · [Certificados TLS](../networking/certificados_tls.md) · [Traefik](../traefik/traefik_base.md) · [Observabilidad](../monitoring/observability_stack.md)
