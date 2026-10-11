---
title: "Monitorización con Uptime Kuma"
description: "Desplegar y operar Uptime Kuma auto-hospedado: contenedor, reverse proxy, tipos de monitor, notificaciones, status pages, integración con Prometheus y copias de seguridad."
keywords: "uptime kuma, monitoring, status pages, notifications, self-hosted, docker, reverse proxy, push monitor, backup"
tags: ['monitoring']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 14 min
category: Monitoreo
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Docker o Podman con Compose"
  - "Un reverse proxy con TLS ([Traefik](../traefik/traefik_base.md) o [HAProxy](../haproxy/haproxy_base.md))"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Monitorización con Uptime Kuma

## El problema

Te enteras de que el servicio está caído cuando alguien te escribe. Montar un stack completo de métricas para saber si una web responde es desproporcionado, y un `curl` en un cron no avisa a nadie ni deja histórico.

Uptime Kuma cubre ese hueco: una sola aplicación con interfaz web que comprueba periódicamente si las cosas responden, te avisa por el canal que prefieras y publica una página de estado. No sustituye a las métricas internas (CPU, latencias, trazas), que se tratan en el [stack de observabilidad](observability_stack.md); responde a una sola pregunta: ¿está funcionando, visto desde fuera?

!!! note "Punto de vista"
    Si Uptime Kuma corre en el mismo host que lo que vigila, un corte del host se lleva ambos y nadie avisa. Colócalo en otra máquina, otra red o incluso otro proveedor.

## 📋 Tabla de Contenidos

- [Características](#caracteristicas)
- [Despliegue con Docker](#despliegue-con-docker)
- [Detrás de un reverse proxy](#detras-de-un-reverse-proxy)
- [Primeros pasos](#primeros-pasos)
- [Tipos de monitor](#tipos-de-monitor)
- [Notificaciones](#notificaciones)
- [Status pages](#status-pages)
- [Integración con Prometheus](#integracion-con-prometheus)
- [Backup y recuperación](#backup-y-recuperacion)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Características

- Monitorización de servicios HTTP(s), TCP, Ping, DNS, Push y más.
- Notificaciones (Telegram, Discord, Slack, Email, etc.).
- Páginas de estado (Status Pages) públicas.
- Aviso de caducidad de certificados TLS en los monitores HTTPS.
- Ventanas de mantenimiento para silenciar avisos planificados.
- Soporte para Docker: se despliega como contenedor único.

Es una aplicación Node.js con interfaz que se comunica por WebSocket. Guarda todo su estado (monitores, histórico, ajustes) en un directorio de datos, lo que hace trivial moverla y respaldarla.

## Despliegue con Docker

La forma más sencilla de desplegar Uptime Kuma es mediante Docker. La imagen es `louislam/uptime-kuma`, el puerto es el 3001 y el estado vive en `/app/data`.

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    restart: unless-stopped
    volumes:
      - ./uptime-kuma-data:/app/data
    ports:
      - "127.0.0.1:3001:3001"
```

El puerto solo escucha en `127.0.0.1`: lo publica el reverse proxy. Si no tienes proxy y lo usas solo en tu red local, cambia a `"3001:3001"`.

!!! warning "Dependiente de la versión"
    La etiqueta `:1` sigue la rama 1.x; la guía de instalación actual del proyecto usa `:2`. La rama 2.x tiene cambios de almacenamiento (entre ellos, soporte de bases de datos externas además del fichero local) y una migración propia. No cambies de rama a ciegas: haz copia del directorio de datos y lee las notas de la versión antes de subir.

Para monitorizar contenedores Docker del host, el contenedor necesita acceso al socket (`/var/run/docker.sock`) y eso equivale a darle control sobre el demonio. Úsalo solo si lo necesitas, en modo lectura cuando sea posible, o prefiere monitores HTTP/TCP que no requieren el socket. Para ejecutarlo como servicio de systemd, ver [Quadlets](../docker/quadlets.md).

## Detrás de un reverse proxy

La interfaz depende de WebSocket. Un proxy que no lo reenvíe produce el síntoma clásico: la página de login carga y después se queda en «conectando».

- **Traefik:** reenvía WebSocket sin configuración adicional. Ver [Traefik](../traefik/traefik_base.md).
- **HAProxy:** el modo `http` lo gestiona, pero revisa los `timeout tunnel` si las conexiones se cortan. Ver [HAProxy](../haproxy/haproxy_base.md).

```yaml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kuma.rule=Host(`status.ejemplo.com`)"
      - "traefik.http.routers.kuma.tls=true"
      - "traefik.http.services.kuma.loadbalancer.server.port=3001"
```

En los ajustes de la aplicación hay una opción de proxy de confianza (*Settings → Reverse Proxy → HTTP Headers → Trust Proxy*) para que Uptime Kuma lea la IP real del cliente desde las cabeceras `X-Forwarded-*`. Actívala solo cuando el proxy las sobrescriba.

## Primeros pasos

1. Accede a `http://tuserver:3001` (o a la URL pública del proxy).
2. Crea el usuario administrador en el primer acceso. Hasta que lo hagas, cualquiera que llegue a la URL puede crearlo: no expongas la instancia nueva a Internet antes.
3. En *Settings → Security* activa el segundo factor (2FA) para el administrador.
4. Añade tu primer monitor en «Add New Monitor».
5. Configura al menos un canal de notificación antes de crear más monitores; un monitor sin aviso solo sirve para mirarlo.

Los parámetros principales de cada monitor son el intervalo de comprobación (cada cuántos segundos), el número de reintentos antes de marcarlo caído y el intervalo de reintento. Un solo fallo puntual no debería despertar a nadie: con uno o dos reintentos se filtra la mayoría del ruido de red.

Para trabajos planificados (actualizaciones, reinicios) usa una ventana de mantenimiento en lugar de pausar monitores a mano: así no olvidas reactivarlos y el histórico no cuenta esa parada como caída.

## Tipos de monitor

| Tipo | Qué comprueba | Cuándo usarlo |
|---|---|---|
| HTTP(s) | Código de estado de una URL, con validez del certificado | Webs y APIs |
| HTTP(s) con palabra clave | Que la respuesta contenga (o no) un texto | Páginas que devuelven 200 con un error dentro |
| TCP Port | Que un puerto acepte conexiones | Bases de datos, SSH, servicios sin HTTP |
| Ping | Respuesta ICMP de un host | Alcanzabilidad de red y equipos |
| DNS | Que un nombre resuelva al registro esperado | Detectar fallos o cambios de DNS |
| Push | La aplicación llama a Uptime Kuma; si deja de hacerlo, salta la alarma | Cron, backups, tareas sin puerto |
| Docker Container | Estado de un contenedor, vía el socket de Docker | Contenedores del propio host |

El monitor *Push* invierte la dirección y es el más útil para tareas programadas: el monitor genera una URL con un token; el trabajo la invoca cuando termina bien, y si pasa el intervalo sin recibirla el monitor se marca caído. Así detectas un backup que dejó de ejecutarse, algo que una comprobación activa nunca vería.

```bash
# Al final del script de backup, solo si todo salió bien
curl -fsS "https://status.ejemplo.com/api/push/<token>?status=up&msg=OK" > /dev/null
```

El nombre exacto de los tipos y las opciones disponibles varía entre versiones; los de la tabla existen en la rama 1.x, pero comprueba el desplegable de tu instalación.

## Notificaciones

En *Settings → Notifications* se definen los canales y después se asocian a cada monitor. Hay integraciones para Telegram, Discord, Slack, correo SMTP, webhooks genéricos y muchos más.

- Crea un canal por destino y márcalo como *Default enabled* si quieres que todo monitor nuevo lo use.
- Usa el botón de prueba al crear el canal: confirma que el aviso llega antes de depender de él.
- Se avisa al cambiar de estado (caída y recuperación), no en cada comprobación fallida. Existe un reenvío periódico configurable para incidentes largos.
- Combina dos canales independientes para lo crítico (por ejemplo, correo y Telegram): si el servidor de correo es lo que se cae, el aviso por correo no llega.

Las credenciales de los canales (tokens de bots, contraseñas SMTP) se guardan en los datos de la aplicación. Trata el volumen y sus copias como material sensible.

## Status pages

Una *status page* es una vista pública de un subconjunto de monitores, sin necesidad de login.

1. En «Status Pages» crea una página con un título y un *slug*; quedará accesible bajo la ruta `/status/<slug>`.
2. Añade grupos de monitores y ordénalos; muestra solo lo que le interesa a quien consulta, no tu infraestructura interna.
3. Opcionalmente, asigna un dominio propio a la página y publica incidentes con mensajes manuales.

Que una página sea pública no significa que deba mostrar nombres de host, IPs ni rutas internas: usa nombres descriptivos («Correo», «Web») en lugar de los nombres técnicos del monitor.

## Integración con Prometheus

Uptime Kuma expone un endpoint `/metrics` en formato Prometheus con el estado y la latencia de cada monitor. Está protegido: se accede con autenticación básica usando un usuario y contraseña de la aplicación o una clave de API creada en los ajustes. Al crear la primera clave de API, la autenticación básica con usuario y contraseña deja de aceptarse de forma permanente.

```yaml
scrape_configs:
  - job_name: uptime-kuma
    scheme: https
    metrics_path: /metrics
    basic_auth:
      username: ""
      password_file: /etc/prometheus/kuma_api_key
    static_configs:
      - targets: ["status.ejemplo.com"]
```

!!! warning "Dependiente de la versión"
    Las métricas y el formato de autenticación (clave de API como contraseña con usuario vacío, o credenciales de usuario) dependen de la versión. Comprueba en tu instancia qué acepta `/metrics` antes de configurar Prometheus. Guarda la clave en un fichero aparte (`password_file`) en lugar de ponerla en claro en la configuración.

Con esto puedes graficar la disponibilidad en Grafana y alertar desde Alertmanager, reutilizando lo descrito en el [stack de observabilidad](observability_stack.md). Si no necesitas ese nivel, las notificaciones propias de Uptime Kuma bastan.

## Backup y recuperación

Todo el estado está en el directorio `/app/data`. En la rama 1.x la base de datos es un fichero SQLite (`kuma.db`) dentro de ese directorio, junto con ficheros auxiliares.

- **Copia en frío:** para el contenedor, copia el directorio y arráncalo. Es la opción más segura porque SQLite no está escribiendo.
- **Copia en caliente:** copiar `kuma.db` mientras la aplicación escribe puede dar un fichero inconsistente. Usa la API de copia de SQLite o una instantánea del volumen o del sistema de ficheros.

```bash
docker compose stop uptime-kuma
tar -czf uptime-kuma-$(date +%F).tar.gz uptime-kuma-data
docker compose start uptime-kuma
```

Envía el archivo fuera del host con la herramienta de copias habitual (ver [Restic y Borg](../backups/restic_borg.md)). Para restaurar, para el contenedor, vacía el directorio de datos, extrae el archivo y arranca de nuevo.

El único cambio de máquina que necesitas hacer es mover ese directorio y levantar el mismo compose. Si usas la rama 2.x con una base externa, respalda también esa base.

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| La página carga pero se queda en «conectando» | El proxy no reenvía WebSocket | Revisar la configuración de WebSocket y los timeouts del proxy |
| Todos los monitores aparecen caídos a la vez | Fallo de red o DNS del propio host de Uptime Kuma | Probar la salida y la resolución DNS desde el contenedor; colocar la instancia en otra red |
| Monitor HTTPS caído por certificado | Certificado caducado, autofirmado o cadena incompleta | Renovar el certificado; solo para uso interno, usar la opción de ignorar errores TLS en ese monitor |
| El monitor responde 200 pero la web está rota | Comprobación solo por código de estado | Pasar a monitor con palabra clave que valide el contenido |
| Notificaciones que no llegan | Canal no asociado al monitor o credenciales incorrectas | Usar el botón de prueba; comprobar que el canal está activado en el monitor |
| Se pierden monitores y ajustes al recrear el contenedor | No hay volumen montado en `/app/data` | Montar el volumen y restaurar desde la última copia |
| Falsos positivos frecuentes | Intervalo corto y sin reintentos | Aumentar reintentos y el intervalo de comprobación |
| Error al leer contenedores Docker | El socket no está montado o falta de permisos | Montar `/var/run/docker.sock` y valorar el riesgo antes de hacerlo |

## Buenas prácticas

- Ejecuta Uptime Kuma fuera de lo que monitoriza, o al menos de un dominio de fallo distinto.
- Fija la etiqueta de la imagen y actualiza de forma deliberada, con copia previa del volumen.
- Usa reintentos para filtrar ruido y dos canales de aviso para lo crítico.
- Monitoriza tareas programadas con monitores *Push*, no solo servicios con puerto.
- Activa 2FA, no expongas la interfaz de administración a Internet y publica solo la status page si hace falta.
- No montes el socket de Docker salvo que lo necesites.
- Prueba la restauración de la copia al menos una vez; una copia sin probar no es una copia.
- Añade el propio Uptime Kuma a un monitor externo (otro Kuma o un servicio gratuito) para saber si el vigilante cae.

## Referencias

- [Repositorio de Uptime Kuma](https://github.com/louislam/uptime-kuma)
- [Wiki de Uptime Kuma](https://github.com/louislam/uptime-kuma/wiki)
- [Stack completo de observabilidad](observability_stack.md)
- [Podman Quadlet](../docker/quadlets.md)
- [Keycloak](../identity/keycloak.md), un servicio crítico para vigilar
