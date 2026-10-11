---
title: "WireGuard VPN"
description: "WireGuard en infraestructura propia: claves, servidor y clientes, enrutado y NAT, acceso remoto frente a site-to-site, operación con wg-quick y diagnóstico."
keywords: "wireguard, vpn, wg-quick, allowedips, persistentkeepalive, nat, site-to-site, homelab, mtu"
tags: ['linux', 'vpn', 'wireguard']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 17 min
category: Linux
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Linux con acceso root y systemd"
  - "Direccionamiento IP y rutas básicas"
  - "Un servidor con IP pública o un puerto UDP reenviado"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# WireGuard VPN

## El problema

Quieres llegar a tu Proxmox, a Grafana o al NAS de casa desde fuera sin exponer ningún panel a Internet. Las VPN clásicas (IPsec, OpenVPN) funcionan, pero arrastran configuraciones largas, negociaciones con muchos parámetros y un montón de código que auditar. Y cuando algo falla, no sabes si es la fase 1, la fase 2 o el certificado.

WireGuard reduce el problema a lo esencial: cada extremo tiene un par de claves, una lista de pares permitidos y una interfaz de red más. Vive en el kernel de Linux, el fichero de configuración cabe en una pantalla y no hay estado de sesión que depurar. A cambio, **no resuelve por ti** la distribución de claves, el direccionamiento ni el enrutado: eso lo decides tú, y de ahí salen casi todos los fallos.

!!! note "Qué cubre y qué no"
    Esta página trata WireGuard «a mano» con `wg` y `wg-quick`: el bloque de construcción. Si prefieres que un plano de control gestione claves y NAT traversal, mira [Tailscale](../networking/tailscale.md) o [NetBird](../networking/netbird.md); la comparativa está en [VPN overlay: comparativa](../networking/vpn_overlay_comparison.md).

## 📋 Tabla de Contenidos

1. [Cómo funciona](#como-funciona)
2. [Instalación](#instalacion)
3. [Generación de claves](#generacion-de-claves)
4. [Servidor](#servidor-etcwireguardwg0conf)
5. [Cliente](#cliente)
6. [Enrutado y NAT](#enrutado-y-nat)
7. [Firewall](#firewall)
8. [Arranque y operación](#arranque-y-operacion)
9. [Site-to-site](#site-to-site)
10. [Troubleshooting](#troubleshooting)
11. [Buenas prácticas](#buenas-practicas)
12. [Referencias](#referencias)

## Cómo funciona

WireGuard no distingue entre «servidor» y «cliente»: todos son pares (*peers*). Lo que llamamos servidor es el par con IP o puerto alcanzable, y por eso el que recibe la conexión inicial.

- **Claves**: cada par tiene una clave privada (que nunca sale de la máquina) y una pública (que se reparte a los demás). No hay CA ni certificados.
- **Cryptokey routing**: `AllowedIPs` hace dos cosas a la vez. Al enviar, decide a qué par va un paquete según su destino. Al recibir, descarta cualquier paquete descifrado cuyo origen no esté en la lista de ese par.
- **UDP y silencioso**: usa un solo puerto UDP y no responde a paquetes de quien no conoce, así que un escaneo no ve nada.
- **Roaming**: el `Endpoint` de un par se actualiza solo con el último paquete autenticado que llega, de modo que un portátil que cambia de wifi a 4G sigue conectado.

!!! warning "AllowedIPs no es solo un filtro"
    Es también la tabla de rutas del túnel. Poner `0.0.0.0/0` en un cliente manda todo su tráfico por la VPN; ponerlo en dos pares del mismo extremo hace que solo uno lo reciba.

## Instalación

En Debian y Ubuntu actuales, el soporte está en el kernel y el paquete aporta las herramientas:

```bash
sudo apt install wireguard
```

El paquete instala `wg` (inspección y ajuste en caliente) y `wg-quick` (levanta la interfaz leyendo un fichero). Si usas un kernel muy antiguo, el módulo puede no estar disponible; consulta la documentación oficial de tu distribución.

## Generación de claves

Genera cada par de claves en la máquina que lo va a usar, con permisos restrictivos:

```bash
umask 077
wg genkey | tee privatekey | wg pubkey > publickey
```

`umask 077` evita que la clave privada quede legible para otros usuarios. Para añadir una capa simétrica extra (resistencia a ataques con ordenadores cuánticos futuros, según la documentación del proyecto) puedes generar una clave precompartida por cada pareja de pares:

```bash
wg genpsk > preshared_srv_laptop
```

Esa clave se declara con `PresharedKey` en ambos extremos y es opcional.

## Servidor (`/etc/wireguard/wg0.conf`)

```ini
[Interface]
Address = 10.100.0.1/24
ListenPort = 51820
PrivateKey = <CONTENIDO_DE_PRIVATEKEY_SERVIDOR>

# Peer: portátil
[Peer]
PublicKey = <PUBLICKEY_DEL_CLIENTE>
AllowedIPs = 10.100.0.2/32

# Peer: móvil
[Peer]
PublicKey = <PUBLICKEY_DEL_MOVIL>
AllowedIPs = 10.100.0.3/32
```

Cada cliente recibe una `/32` dentro de la red del túnel (`10.100.0.0/24`). Esa red debe ser distinta de cualquier LAN en la que vayan a estar tus clientes: si el portátil está en una wifi `192.168.1.0/24` y tu casa también, las rutas chocan.

!!! warning "SaveConfig = true reescribe el fichero"
    La versión anterior de esta página usaba `SaveConfig = true`. Con él, `wg-quick` vuelca la configuración en memoria al fichero cuando baja la interfaz, y **descarta tus comentarios y cualquier edición manual hecha mientras estaba arriba**. Para un fichero que mantienes a mano o en Git, déjalo desactivado.

El fichero contiene la clave privada: permisos `600` y propietario root.

```bash
sudo chmod 600 /etc/wireguard/wg0.conf
```

## Cliente

```ini
[Interface]
Address = 10.100.0.2/24
PrivateKey = <CONTENIDO_DE_PRIVATEKEY_CLIENTE>
DNS = 10.100.0.1

[Peer]
PublicKey = <PUBLICKEY_DEL_SERVIDOR>
Endpoint = vpn.example.com:51820
AllowedIPs = 10.100.0.0/24, 192.168.10.0/24
PersistentKeepalive = 25
```

- **Split tunnel** (el de arriba): solo el tráfico hacia la red del túnel y la LAN doméstica `192.168.10.0/24` va por la VPN; el resto sale directo. Es lo recomendable para acceso a servicios internos.
- **Full tunnel**: cambia `AllowedIPs` por `0.0.0.0/0, ::/0` y todo el tráfico pasa por el servidor. Exige NAT en el servidor (siguiente sección) y una decisión sobre el DNS.
- `DNS` solo lo interpreta `wg-quick`, y usa `resolvconf` o `systemd-resolved` para aplicarlo. Si tu sistema no tiene ninguno de los dos, la línea puede hacer fallar el arranque.
- `PersistentKeepalive = 25` manda un paquete cada 25 segundos. Es necesario si el cliente está detrás de NAT y el servidor tiene que poder hablarle sin que el cliente haya enviado nada antes. Sin él, la entrada del NAT caduca y el túnel parece caído en un sentido.

## Enrutado y NAT

Para que los clientes alcancen la LAN detrás del servidor, el servidor debe reenviar paquetes. Actívalo de forma persistente:

```bash
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl --system
```

Si la LAN no tiene la ruta de vuelta hacia `10.100.0.0/24` (porque el servidor WireGuard no es su pasarela), añade NAT para que los dispositivos de la LAN vean las conexiones como originadas en el servidor. Con `iptables`, en la sección `[Interface]` del servidor:

```ini
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

`%i` lo sustituye `wg-quick` por el nombre de la interfaz (`wg0`) y `eth0` debe ser tu interfaz de salida real. Si ya tienes una política de reenvío en nftables, escribe ahí las reglas equivalentes en lugar de mezclar ambos mundos.

!!! tip "La mejor ruta es la de vuelta"
    El NAT funciona, pero oculta el origen real en los registros de la LAN. Si puedes añadir en tu router una ruta estática `10.100.0.0/24` hacia el servidor WireGuard, no necesitas MASQUERADE y conservas trazabilidad.

## Firewall

El servidor solo necesita abrir un puerto: `51820/udp` en el cortafuegos del host y, si hay router por delante, un reenvío del mismo puerto hacia él. Las reglas de ejemplo con nftables están en [nftables y fail2ban](../cybersecurity/nftables_fail2ban.md). Conviene:

- Aceptar `udp dport 51820` desde cualquier origen en la interfaz pública.
- Permitir en la interfaz `wg0` solo lo que quieras exponer a los clientes; que estén autenticados no significa que deban alcanzarlo todo.
- Si el servidor es un router virtual, la comparativa de [vRouters](../networking/vrouters.md) ayuda a decidir dónde colocar el extremo.

## Arranque y operación

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

`wg-quick@wg0` es la unit que lee `/etc/wireguard/wg0.conf` al arrancar. Para parar o reiniciar:

```bash
sudo wg-quick down wg0
sudo systemctl restart wg-quick@wg0
```

Para ver el estado en vivo:

```bash
sudo wg show
```

La salida lista la interfaz con su clave pública y puerto, y debajo cada par con su `endpoint`, los `allowed ips`, el tiempo desde el último *handshake* y los bytes transferidos. Un par que nunca ha hecho handshake no aparece con esa línea: es la señal más directa de que el tráfico no está llegando o las claves no coinciden.

### Cambios sin cortar el túnel

Para añadir un par en caliente, sin reiniciar la interfaz:

```bash
sudo wg set wg0 peer <PUBLICKEY_NUEVO> allowed-ips 10.100.0.4/32
```

Eso no se guarda en el fichero (salvo con `SaveConfig`), así que añádelo también a `wg0.conf`. Si editas el fichero y quieres aplicarlo sin tumbar las conexiones existentes, `wg-quick strip` produce la configuración sin las directivas propias de `wg-quick` y `wg syncconf` la aplica:

```bash
sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'
```

`syncconf` solo aplica lo que entiende `wg` (clave privada, puerto, pares y sus `AllowedIPs`, `Endpoint`, etc.); no toca `Address`, rutas ni `PostUp`. Si cambias esos, hay que bajar y subir la interfaz.

### Revocar un acceso

Eliminar el bloque `[Peer]` y aplicar el cambio basta: sin su clave pública en la lista, el par no puede hablar con el servidor. No hay listas de revocación porque no hay certificados. Rota las claves de un dispositivo perdido generando un par nuevo y sustituyéndolo.

## Site-to-site

Para unir dos sedes (casa y un VPS, o dos laboratorios), ambos lados son servidor y cliente a la vez. Cada lado declara en `AllowedIPs` la LAN remota:

```ini
# Sede A (LAN 192.168.10.0/24, túnel 10.100.0.1)
[Interface]
Address = 10.100.0.1/30
ListenPort = 51820
PrivateKey = <CLAVE_PRIVADA_A>

[Peer]
PublicKey = <CLAVE_PUBLICA_B>
Endpoint = sedeb.example.com:51820
AllowedIPs = 10.100.0.2/32, 192.168.20.0/24
PersistentKeepalive = 25
```

La sede B es el espejo, con `192.168.10.0/24` en su `AllowedIPs`. Los dispositivos de cada LAN necesitan que su pasarela sepa que la red remota está detrás del extremo WireGuard (ruta estática o que el extremo sea la pasarela). Para topologías con más de dos sedes, malla completa a mano escala mal; valora un plano de control como los de [Tailscale](../networking/tailscale.md) o [NetBird](../networking/netbird.md).

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `wg show` no muestra línea de *latest handshake* | El UDP no llega (puerto cerrado, NAT sin reenvío) o las claves no coinciden | Comprueba el reenvío de `51820/udp`; verifica que la clave pública declarada en cada lado es la del otro |
| Handshake correcto pero no hay tráfico | `AllowedIPs` no incluye la IP origen o destino | Revisa `AllowedIPs` en ambos extremos; recuerda que filtra al recibir |
| El cliente llega al servidor pero no a la LAN | Falta `ip_forward` o la LAN no conoce la ruta de vuelta | Activa el reenvío; añade ruta estática o NAT |
| El túnel funciona de cliente a servidor pero no al revés | Cliente tras NAT sin keepalive | Añade `PersistentKeepalive = 25` en el cliente |
| Conexiones colgadas con páginas grandes o SSH que se congela | MTU: el encapsulado reduce el tamaño útil | Baja `MTU` en `[Interface]`; si no lo fijas, `wg-quick` lo calcula a partir de la interfaz de la ruta hacia el `Endpoint` (o de la ruta por defecto) |
| `wg-quick up` falla con error de DNS o resolvconf | Línea `DNS` sin `resolvconf` ni `systemd-resolved` | Instala uno de los dos o quita `DNS` y configura el resolvedor a mano |
| Tras `down`, los cambios y comentarios de `wg0.conf` se pierden | `SaveConfig = true` | Desactívalo y gestiona el fichero a mano o con Git |
| Dos clientes con el mismo `AllowedIPs` y solo uno funciona | Cada IP solo puede pertenecer a un par | Asigna una `/32` única por cliente |
| Funciona en casa pero no en una red corporativa | La red bloquea UDP saliente no estándar | Prueba un puerto más común como `443/udp` |

Para ver por qué un paquete no entra, `tcpdump -ni eth0 udp port 51820` en el servidor confirma si llegan datagramas; el contenido va cifrado, pero basta para saber si el problema es de red o de claves.

## Buenas prácticas

- Un par de claves por dispositivo, nunca compartidas; así revocas uno sin tocar el resto.
- `AllowedIPs` mínimos: la `/32` del cliente en el servidor y solo las redes necesarias en el cliente.
- Claves privadas con permisos `600`, fuera de repositorios y copias sin cifrar. Si versionas `wg0.conf`, usa un gestor de secretos y plantillas, no la clave en claro.
- Reserva un rango de túnel propio (`10.100.0.0/24` aquí) que no solape con ninguna LAN conocida.
- Documenta la tabla de IPs asignadas a cada par; es la única «base de usuarios» que existe.
- Expón solo el puerto UDP y controla qué alcanza el tráfico entrante desde `wg0` con el cortafuegos.
- Monitoriza el último handshake de cada par (`wg show wg0 latest-handshakes`) para detectar pares caídos.
- Para flotas grandes o NAT traversal complejo, valora una capa de control encima antes de multiplicar ficheros a mano.

## Referencias

- [WireGuard: documentación oficial](https://www.wireguard.com/)
- [wg(8) y wg-quick(8)](https://man7.org/linux/man-pages/man8/wg.8.html)
- [Tailscale](../networking/tailscale.md)
- [NetBird](../networking/netbird.md)
- [VPN overlay: comparativa](../networking/vpn_overlay_comparison.md)
- [nftables y fail2ban](../cybersecurity/nftables_fail2ban.md)
- [vRouters: comparativa](../networking/vrouters.md)
