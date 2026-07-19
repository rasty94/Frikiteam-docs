---
title: "Respuesta a Incidentes: playbook práctico con TheHive y MISP"
description: "Qué hacer cuando la alerta ya ha saltado. Ciclo NIST SP 800-61 aterrizado en infraestructura real: preservación de evidencia, contención en Kubernetes, gestión de casos con TheHive, threat intel con MISP y post-mortem sin culpa."
keywords: "incident response, thehive, misp, cortex, nist 800-61, forensics, memory dump, chain of custody, post-mortem, kubernetes, ioc"
date: 2026-07-19
tags: [cybersecurity, incident-response, thehive, misp, forensics, kubernetes, post-mortem]
draft: false
updated: 2026-07-19
difficulty: advanced
estimated_time: "18 min"
category: Ciberseguridad
status: published
last_reviewed: 2026-07-19
prerequisites:
  - "Monitoreo de seguridad desplegado (Falco/Wazuh)"
  - "Acceso administrativo a la infraestructura"
  - "Docker Compose y fundamentos de Kubernetes"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

## Ya tienes la alerta, ¿ahora qué?

Todo lo demás de esta sección construye defensas. [Hardening](hardening_linux.md) reduce la superficie, [Zero Trust](zero_trust.md) reduce el radio de explosión, [el modelo de amenazas](modelo_amenazas.md) te dice qué esperar y [el monitoreo](monitoreo_seguridad.md) te avisa. Este documento empieza justo después: son las 03:14, Falco ha disparado `Terminal shell in container` en un pod de producción y hay alguien mirando el móvil sin saber qué hacer primero. La respuesta a incidentes falla casi siempre por lo mismo, y no es falta de herramientas: la gente improvisa bajo presión, destruye la evidencia en los primeros cinco minutos y nadie sabe quién tiene autoridad para apagar producción.

!!! danger "El error número uno"
    Reiniciar la máquina comprometida. Es el reflejo natural ("a ver si así se arregla") y borra la memoria RAM, los procesos vivos, las conexiones abiertas y a menudo el propio malware si solo residía en memoria. Si te llevas una sola idea de esta guía, que sea: **no reinicies, no apagues, aísla**.

## El ciclo de vida según NIST SP 800-61

```mermaid
graph LR
    A[Preparación] --> B[Detección y Análisis]
    B --> C[Contención]
    C --> D[Erradicación]
    D --> E[Recuperación]
    E --> F[Lecciones Aprendidas]
    F --> A
    B -.falso positivo.-> F
    D -.reinfección.-> B
    style A fill:#2d6a4f,color:#fff
    style F fill:#7f5539,color:#fff
```

Las flechas punteadas son las importantes. Un incidente no es una tubería: si durante la erradicación descubres que el atacante tenía persistencia en otro sitio, vuelves a análisis. Y un falso positivo también genera lecciones aprendidas (normalmente: "ajustar esa regla").

El 80% del esfuerzo real está en la fase que nadie hace: **preparación**. Improvisar el resto sale caro.

## Preparación

### Matriz de severidad

Sin una matriz acordada *antes*, cada incidente empieza con una discusión sobre si es grave. Define esto y pégalo en el canal:

| Nivel | Criterio | Respuesta | Notificación |
| --- | --- | --- | --- |
| **SEV1** | Datos de clientes comprometidos, producción caída por atacante, ransomware activo | Inmediata, 24/7, todo el equipo | Dirección + legal < 1 h |
| **SEV2** | Compromiso confirmado sin exfiltración conocida, credencial de producción filtrada | < 30 min, guardia despierta | Responsable de seguridad |
| **SEV3** | Actividad sospechosa confirmada en entorno no productivo, minero de cripto | Horario laboral, siguiente día hábil | Canal de equipo |
| **SEV4** | Anomalía sin impacto confirmado, escaneo externo, alerta a validar | Backlog | Ninguna |

!!! warning "Escala hacia arriba, nunca hacia abajo"
    Cuando dudes entre SEV2 y SEV3, elige SEV2. Bajar la severidad cuando tienes más datos es barato; subirla tres horas tarde no.

### Roles

Tres roles, y una persona no puede tener dos a la vez en un SEV1:

- **Incident Commander (IC)**: decide, no ejecuta. Su trabajo es mantener la línea temporal, asignar tareas y decidir cuándo se contiene. Si el IC está con las manos en un `tcpdump`, nadie está coordinando.
- **Comms**: escribe hacia fuera. Actualizaciones cada 30 minutos aunque no haya novedad ("seguimos investigando" es una actualización válida). Aísla al equipo técnico de las preguntas de dirección.
- **Ops / Investigador**: manos en el teclado. Uno o varios. Reporta al IC, no toma decisiones destructivas por su cuenta.

### Quién decide apagar producción, y dónde se habla

Esto se decide en frío, hoy, no a las 03:14. La regla que funciona:

> El **Incident Commander** tiene autoridad unilateral para aislar (network policy, revocar credenciales, cortar tráfico). Para acciones con **pérdida de datos o caída total de servicio** necesita confirmación de una segunda persona de una lista corta y nominal, con un timeout: si nadie responde en 15 minutos, el IC procede solo y lo documenta.

El timeout es la parte crítica. Sin él, la gente espera indefinidamente a que alguien conteste al teléfono mientras el atacante trabaja.

El **canal de guerra** es uno dedicado por incidente (`#inc-2026-07-19-minero`), no el general. Todo lo relevante se escribe ahí aunque se haya hablado por voz — la transcripción **es** la línea temporal del post-mortem. Nada de hilos: se pierden. Y si el compromiso puede afectar a la propia plataforma de chat (se sospecha del SSO corporativo), se pasa a un canal fuera de banda acordado previamente.

## Detección y análisis: el triaje

La primera pregunta no es "¿qué hacemos?" sino "¿esto es real?". Un flujo de triaje de cinco preguntas:

1. **¿Qué disparó la alerta exactamente?** Lee la regla, no el título. `Terminal shell in container` es crítico en un pod de API y esperado en un pod de mantenimiento.
2. **¿Hay un cambio legítimo que lo explique?** Cruza el timestamp con el historial de despliegues, ventanas de mantenimiento y CI. La mayoría de los "incidentes" son un compañero depurando.
3. **¿Es reproducible o puntual?** Un evento único a las 04:00 pesa más que 400 eventos durante el horario laboral.
4. **¿El origen tiene sentido?** IP de origen, cuenta de servicio, user-agent. Un `kubectl exec` desde una IP residencial a las 4 de la mañana no necesita más análisis.
5. **¿Hay actividad correlacionada?** Una alerta sola es ruido; tres alertas distintas sobre el mismo host en diez minutos es un incidente.

```bash
# Triaje rápido en un host Linux sospechoso — SOLO LECTURA
# Ninguno de estos comandos modifica el sistema

# Procesos con conexiones de red activas
ss -tunap | grep ESTAB

# Procesos ejecutándose desde rutas temporales (patrón clásico de malware)
ls -la /proc/*/exe 2>/dev/null | grep -E '/tmp|/dev/shm|/var/tmp'

# Logins recientes y fallidos
last -20; lastb -20

# Tareas programadas de todos los usuarios
for u in $(cut -f1 -d: /etc/passwd); do crontab -l -u "$u" 2>/dev/null | sed "s/^/$u: /"; done

# Claves SSH autorizadas modificadas en los últimos 7 días y SUID recientes
find /home /root -name authorized_keys -mtime -7 -ls 2>/dev/null
find / -perm -4000 -mtime -30 -type f 2>/dev/null
```

!!! note "Documenta mientras triaces"
    Cada comando que ejecutas y su salida van al caso. Dentro de tres horas no recordarás si ese proceso ya estaba ahí antes de que tocaras nada.

## Preservación de evidencia: antes de tocar nada

Esta es la sección que más se hace mal y la que menos se puede arreglar después. La evidencia volátil desaparece por orden de fragilidad (RFC 3227): registros y caché, memoria RAM, estado de red, procesos, disco, backups.

La regla de oro: **aislar no es apagar**. Corta la red, deja la máquina encendida. Una máquina aislada con la memoria intacta es una mina de información; una máquina apagada es una imagen de disco y muchas preguntas sin responder.

### Snapshot de disco antes que nada

```bash
# --- Cloud (AWS): snapshot del volumen sin tocar la instancia ---
aws ec2 create-snapshot --volume-id vol-0a1b2c3d4e5f \
  --description "IR-2026-07-19 evidencia preservada por @rasty94" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=incident,Value=INC-2026-0042},{Key=legal-hold,Value=true}]'

# --- On-prem / KVM: snapshot en caliente ---
virsh snapshot-create-as --domain web-prod-01 \
  --name "INC-2026-0042" --atomic --disk-only --no-metadata

# --- Copia forense bit a bit de un disco desmontado ---
# dc3dd calcula el hash mientras copia: no hay ventana entre copia y verificación
dc3dd if=/dev/sdb of=/evidencia/INC-2026-0042-sdb.img \
  hash=sha256 log=/evidencia/INC-2026-0042-sdb.log

# Verificar la integridad de la copia
sha256sum /evidencia/INC-2026-0042-sdb.img
```

### Volcado de memoria

La RAM contiene lo que el disco no tiene: claves en claro, procesos sin fichero en disco, conexiones establecidas, comandos descifrados.

```bash
# Linux: AVML produce un volcado compatible con Volatility sin compilar módulos
sudo ./avml /evidencia/INC-2026-0042-mem.lime
sha256sum /evidencia/INC-2026-0042-mem.lime | tee /evidencia/INC-2026-0042-mem.sha256

# Contenedores: el proceso vive en el namespace del host
crictl inspect <container-id> | grep -i '"pid"'   # PID real
sudo gcore -o /evidencia/INC-2026-0042-pid <PID>  # memoria de ese proceso

# Preservar el sistema de ficheros del contenedor sin ejecutarlo
docker export <container-id> > /evidencia/INC-2026-0042-fs.tar
```

!!! danger "El orden importa: memoria antes que disco"
    Cada segundo que pasa, la memoria cambia. El disco no se va a ningún lado si has cortado la red. Si solo te da tiempo a una cosa, volca la memoria.

### Chain of custody

Si el incidente puede acabar en un juzgado, en una aseguradora o en una notificación regulatoria, la evidencia sin cadena de custodia no vale nada. No necesitas un sistema complejo: un fichero versionado por incidente basta.

```yaml
# /evidencia/INC-2026-0042/custody.yaml
incidente: INC-2026-0042
apertura: 2026-07-19T03:14:22Z
responsable_evidencia: "@rasty94"

items:
  - id: EV-001
    tipo: volcado_memoria
    origen: web-prod-01 (10.20.3.14)
    fichero: INC-2026-0042-mem.lime
    sha256: "a3f2...c91d"
    recogido_por: "@rasty94"
    recogido_en: 2026-07-19T03:22:10Z
    metodo: "avml v0.14 ejecutado desde USB de solo lectura"
    almacenamiento: "S3 bucket-forense, object-lock COMPLIANCE 365d"
    transferencias:
      - {de: "@rasty94", a: "almacen-forense", cuando: 2026-07-19T03:41:00Z,
         hash_verificado_en_destino: true}

  - id: EV-002
    tipo: snapshot_disco
    origen: vol-0a1b2c3d4e5f
    identificador: snap-9f8e7d6c
    recogido_por: "@rasty94"
    recogido_en: 2026-07-19T03:19:45Z
    almacenamiento: "AWS, tag legal-hold=true"
```

Tres reglas que hacen que esto sirva de algo: **hashea inmediatamente** tras la recogida y verifica el hash en destino tras cada transferencia; usa **almacenamiento inmutable** (object-lock en S3, WORM, o como mínimo un bucket sin permisos de borrado para operaciones); y **trabaja siempre sobre copias** — el original no se monta, no se abre, no se toca, y si hay que montarlo, `mount -o ro,noexec,nodev,noload`.

## Contención

Contener es cortar la capacidad de actuar del atacante sin destruir la evidencia ni, si se puede evitar, el servicio.

### Aislar un pod en Kubernetes

La forma correcta no es borrar el pod (destruye la evidencia y el ReplicaSet lo recrea). Es sacarlo del servicio y encerrarlo:

```bash
# 1. Desengancharlo del Service cambiando su label — el ReplicaSet creará
#    un pod sano de reemplazo y el sospechoso queda vivo pero sin tráfico
kubectl label pod payments-7d9f-x2k4 -n prod app- quarantine=INC-2026-0042 --overwrite

# 2. Aplicar la network policy de cuarentena
kubectl apply -f quarantine-netpol.yaml

# 3. Verificar que ha quedado realmente aislado
kubectl exec -n prod payments-7d9f-x2k4 -- timeout 5 curl -s https://example.internal || echo "aislado OK"
```

```yaml
# quarantine-netpol.yaml — deny-all real: sin egress ni ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: quarantine
  namespace: prod
spec:
  podSelector:
    matchLabels:
      quarantine: INC-2026-0042
  policyTypes:
    - Ingress
    - Egress
  # Sin reglas ingress/egress = todo denegado. Para acceso forense desde un
  # jump host, añade solo: ingress con namespaceSelector {name: forensics}
```

!!! warning "El CNI debe soportar egress"
    Las NetworkPolicy solo las aplica el plugin de red. Calico y Cilium sí; algunos CNI antiguos ignoran las reglas de egress silenciosamente. **Verifica el aislamiento con el paso 3**, no des por hecho que el YAML funciona. Ver [Seguridad en Kubernetes](kubernetes_security.md).

### Aislar un nodo

`cordon` es seguro y siempre correcto. `drain` **no lo es** durante un incidente: mueve las cargas a otros nodos, y si el compromiso está en una imagen o en un DaemonSet, acabas de propagarlo.

```bash
# Siempre: dejar de programar cargas nuevas
kubectl cordon node-worker-07

# Marcarlo para que nadie lo toque por error
kubectl annotate node node-worker-07 incident=INC-2026-0042 do-not-touch=true

# Drain SOLO tras confirmar que el compromiso está confinado al nodo
# y NUNCA sobre pods que aún son evidencia viva
kubectl drain node-worker-07 --ignore-daemonsets --delete-emptydir-data \
  --pod-selector='quarantine!=INC-2026-0042'
```

### Revocar credenciales y rotar secretos

Orden importante: **primero revoca la sesión, luego rota el secreto**. Al revés, el atacante mantiene su sesión activa con el token viejo mientras tú celebras que has rotado la clave.

```bash
# --- AWS: cortar sesiones existentes antes de tocar las claves ---
# Denegación con condición temporal: invalida las credenciales temporales
# emitidas antes de este instante
aws iam put-user-policy --user-name deploy-bot \
  --policy-name IR-revoke-sessions \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*","Condition":{"DateLessThan":{"aws:TokenIssueTime":"2026-07-19T03:14:00Z"}}}]}'

aws iam update-access-key --user-name deploy-bot --access-key-id AKIA... --status Inactive

# --- Kubernetes: invalidar el token de una ServiceAccount ---
kubectl delete secret sa-token-payments -n prod
kubectl rollout restart deployment/payments -n prod

# --- SSH: revocar una clave concreta en toda la flota ---
ansible all -m lineinfile -a \
  "path=/root/.ssh/authorized_keys regexp='AAAAB3NzaC1yc2EAAAA...' state=absent"

# --- Sesiones vivas de un usuario en un host ---
pkill -KILL -u usuario_comprometido
```

Para la rotación de los secretos de aplicación, el flujo ya está descrito en [Gestión de Secretos](gestion_secretos.md) y [Secretos en GitOps](secrets_gitops.md). Lo específico de un incidente: **rota todo lo que la credencial comprometida pudiera leer**, no solo la credencial. Si el pod comprometido montaba tres secretos, son tres secretos rotados.

## TheHive: gestión de casos

Durante un incidente la información se dispersa: capturas en el chat, hashes en un `.txt` local, la línea temporal en la cabeza del IC. TheHive es una plataforma libre de gestión de casos de seguridad que centraliza eso — casos, tareas asignables, observables (IoCs) y línea temporal automática. Es la diferencia entre un post-mortem reconstruido de memoria y uno con marcas de tiempo reales.

```yaml
# docker-compose.yml — TheHive 5 con Cassandra y Elasticsearch
services:
  cassandra:
    image: cassandra:4.1
    environment: [CASSANDRA_CLUSTER_NAME=thehive]
    volumes: [cassandra-data:/var/lib/cassandra]
    restart: unless-stopped

  elasticsearch:
    image: elasticsearch:8.14.3
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ulimits:
      memlock: {soft: -1, hard: -1}
    volumes: [es-data:/usr/share/elasticsearch/data]
    restart: unless-stopped

  thehive:
    image: strangebee/thehive:5.3
    depends_on: [cassandra, elasticsearch]
    ports: ["9000:9000"]
    environment: [JVM_OPTS=-Xms2g -Xmx2g]
    command: [--secret, "CAMBIA_ESTO_POR_UN_SECRETO_LARGO_Y_ALEATORIO",
              --cql-hostnames, cassandra,
              --index-backend, elasticsearch, --es-hostnames, elasticsearch]
    volumes: [thehive-data:/opt/thp/thehive/data]
    restart: unless-stopped

volumes: {cassandra-data: , es-data: , thehive-data: }
```

!!! warning "Esto no es una configuración de producción"
    Sin TLS, sin autenticación en Elasticsearch y con un secreto en claro en el compose. Para producción: TLS terminado en un reverse proxy, secreto desde el gestor de secretos y **backups verificados** de Cassandra. Un TheHive que se pierde se lleva por delante el historial completo de incidentes.

### El modelo: casos, tareas, observables

- **Caso**: un incidente. Tiene severidad, TLP (semáforo de compartición), estado y una plantilla.
- **Tarea**: unidad de trabajo asignable dentro del caso ("volcar memoria de web-prod-01"). Cada tarea lleva un log con marcas de tiempo — de aquí sale la línea temporal.
- **Observable**: un dato del incidente (IP, hash, dominio, ruta). Se marca como IoC si es indicador de compromiso, y TheHive te avisa si ya apareció en un caso anterior. Ese "ya lo hemos visto" es el mayor valor de la herramienta.
- **Plantillas de caso**: una por escenario recurrente (credencial, minero, acceso no autorizado) con las tareas ya definidas. A las 3 de la mañana nadie recuerda los 12 pasos; con plantilla, se abre el caso y ya están ahí.

### Integración con Falco y Wazuh

Las alertas de [monitoreo de seguridad](monitoreo_seguridad.md) deben crear alertas en TheHive automáticamente. Falco lo hace vía Falcosidekick sin escribir código:

```yaml
# values.yaml de Falco — envío directo a TheHive
falcosidekick:
  enabled: true
  config:
    customfields: "cluster:prod,env:production"
    webhook:
      address: "http://thehive:9000/api/v1/alert"
      customHeaders: "Authorization:Bearer ${THEHIVE_API_KEY}"
      minimumpriority: "warning"
```

Para Wazuh, un integrador que traduce la alerta al formato de TheHive:

```python
#!/usr/bin/env python3
# /var/ossec/integrations/custom-thehive.py
# Wazuh lo invoca como: script <alert_file> <api_key> <hook_url>
import json, sys, urllib.request

alert = json.load(open(sys.argv[1]))
api_key, url = sys.argv[2], sys.argv[3]
rule, level = alert["rule"], alert["rule"]["level"]
srcip = alert.get("data", {}).get("srcip")

payload = {
    "type": "wazuh",
    "source": alert.get("agent", {}).get("name", "unknown"),
    "sourceRef": alert.get("id"),
    "title": f"[Wazuh {level}] {rule['description']}",
    "description": json.dumps(alert, indent=2)[:4000],
    # Wazuh usa niveles 0-15; TheHive severidad 1-4
    "severity": 4 if level >= 12 else 3 if level >= 10 else 2 if level >= 7 else 1,
    "tlp": 2,
    "tags": ["wazuh"] + rule.get("groups", []),
    "observables": [{"dataType": "ip", "data": srcip, "ioc": False}] if srcip else [],
}

urllib.request.urlopen(urllib.request.Request(
    url, data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
), timeout=10)
```

```xml
<!-- /var/ossec/etc/ossec.conf -->
<integration>
  <name>custom-thehive</name>
  <hook_url>http://thehive:9000/api/v1/alert</hook_url>
  <api_key>TU_API_KEY</api_key>
  <level>7</level>
  <alert_format>json</alert_format>
</integration>
```

!!! note "Umbral, no todo"
    `<level>7</level>` no es arbitrario: por debajo de 7 Wazuh genera cientos de eventos diarios. Un TheHive con 400 alertas sin triar es exactamente igual de útil que no tener TheHive.

## MISP: inteligencia de amenazas

TheHive te dice qué está pasando en tu casa. MISP te dice si le ha pasado a alguien más. Es una plataforma libre de compartición de inteligencia de amenazas: eventos con atributos (IPs, hashes, dominios, reglas YARA), clasificados con taxonomías y sincronizables con otras organizaciones.

El uso práctico es doble: **enriquecimiento** (aparece una IP en tus logs → ¿MISP la conoce? Si está en un evento de una campaña de ransomware de hace dos semanas, tu SEV3 acaba de convertirse en SEV1) y **contribución** (los IoCs de tu incidente se publican para que otros los detecten antes).

### Taxonomías y niveles de compartición

Las taxonomías son vocabularios controlados para etiquetar. Las dos imprescindibles:

- **TLP** (Traffic Light Protocol): `tlp:red` no sale del equipo, `tlp:amber` circula dentro de la organización, `tlp:green` en la comunidad, `tlp:clear` es público. Etiqueta **todo**; un IoC sin TLP acaba compartido donde no debía.
- **PAP** (Permissible Actions Protocol): qué puedes hacer con el indicador sin avisar al atacante. `pap:red` significa que ni siquiera resuelvas ese dominio desde tu red — la consulta DNS le avisa de que le has detectado.

```mermaid
graph LR
    F[Falco] --> TH[TheHive: alerta]
    W[Wazuh] --> TH
    TH -->|triaje| C[Caso + observables]
    C --> CX[Cortex: analizadores]
    CX -->|consulta IoC| M[(MISP)]
    M -->|contexto: campaña, TTPs| C
    C -->|exportar IoCs confirmados| M
    M -->|sync| EXT[Comunidades externas]
    style TH fill:#1d3557,color:#fff
    style M fill:#6a040f,color:#fff
    style CX fill:#264653,color:#fff
```

### Cortex: el pegamento

TheHive no consulta MISP directamente: lo hace a través de **Cortex**, un motor de analizadores. Seleccionas un observable en el caso, ejecutas el analizador `MISP_2_1` y recibes en segundos si ese indicador ya es conocido y en qué contexto.

```json
{
  "name": "MISP_2_1",
  "configuration": {
    "url": ["http://misp"], "key": ["TU_API_KEY_MISP"],
    "cert_check": [true], "name": ["MISP-interno"]
  },
  "rateLimit": { "count": 200, "duration": 3600 }
}
```

```bash
# Enriquecimiento manual vía API de MISP: ¿conocemos esta IP?
curl -s -X POST http://misp/attributes/restSearch \
  -H "Authorization: TU_API_KEY_MISP" \
  -H "Content-Type: application/json" \
  -d '{"value":"203.0.113.44","type":"ip-dst","includeEventTags":true}' \
  | jq '.response.Attribute[] | {event_id, category, comment, tags: [.Tag[].name]}'
```

### Exportar los IoCs de tu incidente

Cuando el caso se cierra, los observables marcados como IoC se exportan a MISP como un evento nuevo. En TheHive: *Case → Export → MISP*. Antes de pulsar, dos comprobaciones: **que no exportas datos internos** (rutas con nombres de proyecto, hostnames internos e IPs privadas no aportan nada a nadie y te describen a ti) y **que el TLP es el correcto** — por defecto, `tlp:amber` para cualquier cosa que salga de un incidente propio.

## Erradicación y recuperación

Erradicar es eliminar la presencia del atacante; recuperar es volver a estar operativo. Se confunden constantemente y por eso hay reinfecciones.

**Erradicación** — no está terminada hasta que puedas responder cómo entró. Identifica el vector inicial (sin esto, reconstruyes el sistema y te vuelven a entrar por la misma puerta), busca persistencia en **todos** los sitios y no solo donde saltó la alerta (cron, systemd units, `authorized_keys`, webshells, imágenes de contenedor modificadas, ServiceAccounts creadas, reglas de webhook) y reconstruye desde imagen limpia: un host comprometido no se "limpia", se destruye y se despliega de nuevo.

**Recuperación** — con condiciones:

- Restaura desde un backup **anterior al compromiso**, y ese "anterior" lo dice la línea temporal, no la intuición. Si el atacante entró hace tres semanas, el backup de ayer también está comprometido.
- Monitoriza el sistema restaurado con más detalle durante al menos dos semanas: las reinfecciones ocurren en los primeros días.
- Restaura por fases: primero un servicio no crítico, verifica, luego el resto.

!!! danger "No cierres el incidente al restaurar el servicio"
    Servicio arriba no es incidente cerrado. El incidente se cierra cuando conoces el vector, has erradicado la persistencia y has hecho el post-mortem. Cerrar en cuanto la web responde es cómo un incidente se convierte en dos.

## Post-mortem sin culpa

Sin culpa no significa sin responsabilidad: significa que se asume que cada persona actuó razonablemente con la información que tenía en ese momento. Si alguien pudo borrar producción con un comando, el fallo es que ese comando fuera posible, no la persona que lo escribió.

```markdown
# Post-mortem INC-2026-0042 — Minero de cripto en cluster de producción

**Severidad:** SEV2 · **Duración:** 6 h 12 min · **Impacto:** degradación en 3
servicios, sin exfiltración confirmada
**IC:** @rasty94 · **Fecha del post-mortem:** 2026-07-22 (< 5 días hábiles)

## Resumen ejecutivo
Tres párrafos máximo, legibles por alguien no técnico: qué pasó, qué impacto
tuvo, qué se ha hecho para que no vuelva a pasar.

## Línea temporal
Horas en UTC. Se exporta de los logs de tareas de TheHive.

| Hora  | Evento | Fuente |
|-------|--------|--------|
| 01:47 | Primer pod comprometido (deducido a posteriori) | logs kube-apiserver |
| 03:14 | Falco dispara `Outbound connection to C2` | alerta Falco |
| 03:19 | IC asignado, canal #inc-2026-0042 abierto | Slack |
| 03:22 | Snapshot de disco y volcado de memoria completados | custody.yaml |
| 03:41 | Pod aislado con network policy de cuarentena | kubectl audit |
| 05:30 | Vector identificado: imagen base con RCE sin parchear | análisis |
| 07:59 | Servicio restaurado desde imagen reconstruida | ArgoCD |

## ¿Qué pasó?
Narrativa técnica. Sin nombres propios asociados a errores: "el despliegue
incluyó una imagen sin escanear", no "X desplegó una imagen sin escanear".

## Análisis de causa raíz
No pares en la primera causa. Cinco porqués o similar:
- ¿Por qué había un minero? Un pod ejecutaba código arbitrario.
- ¿Por qué? La imagen tenía una vulnerabilidad RCE conocida.
- ¿Por qué llegó a producción? El escaneo no bloqueaba el despliegue.
- ¿Por qué no bloqueaba? Se puso en modo aviso para no frenar releases.
- ¿Por qué se quedó así? Nadie revisó esa decisión temporal de hace 8 meses.

## Lo que funcionó / lo que no
La detección tardó 4 minutos: eso es una regla que alguien escribió y hay que
mantener. En contra: 25 minutos hasta asignar IC (sin escalado automático) y
nadie sabía dónde estaba el runbook de aislamiento de pods.

## Acciones
Con responsable y fecha. Sin dueño, no es una acción, es un deseo.

| # | Acción | Responsable | Fecha | Estado |
|---|--------|-------------|-------|--------|
| 1 | Trivy bloqueante en el admission controller | @rasty94 | 2026-08-01 | En curso |
| 2 | Escalado automático de guardia tras 10 min sin ACK | @rasty94 | 2026-07-30 | Pendiente |
| 3 | Runbook de cuarentena enlazado desde la alerta de Falco | @rasty94 | 2026-07-25 | Hecho |

## Preguntas abiertas
Ser honesto vale más que inventar certezas: "no se pudo confirmar si hubo
acceso a la BD entre 01:47 y 03:14 porque el audit log solo retiene 24 h".
```

Reglas que hacen que el post-mortem sirva: **máximo 5 días hábiles** tras el cierre (después nadie recuerda los detalles), **acciones con dueño y fecha** revisadas en la retro siguiente, y **publicación interna abierta** — un post-mortem que solo lee el equipo de seguridad no enseña nada a nadie más.

## Playbook 1: credencial filtrada en Git

**Detección típica**: escáner de secretos en CI, aviso de GitHub, o un tercero que te escribe.

```bash
# 1. REVOCAR PRIMERO. La credencial se considera comprometida desde el
#    momento del commit, no desde el momento en que te has enterado.
aws iam update-access-key --user-name $USER --access-key-id $KEY --status Inactive

# 2. Determinar la ventana de exposición: cuándo entró y si sigue en HEAD
git log --all --oneline -S 'AKIAIOSFODNN7EXAMPLE' -- .
git log -1 --format='%aI %an %H' -S 'AKIAIOSFODNN7EXAMPLE'

# 3. ¿Se ha usado? Esta es la pregunta que decide la severidad.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAIOSFODNN7EXAMPLE \
  --start-time 2026-06-01 --query 'Events[].{t:EventTime,e:EventName,ip:CloudTrailEvent}'

# 4. Limpiar el historial (solo si el repo es privado y controlas todos los clones)
git filter-repo --replace-text <(echo 'AKIAIOSFODNN7EXAMPLE==>REDACTED')
```

!!! danger "Repo público: el historial ya no importa"
    Si el repositorio fue público en algún momento, la credencial está en manos de terceros: hay bots que escanean commits públicos en segundos. Reescribir el historial es cosmético. **Lo único que cuenta es revocar y auditar el uso.**

**Severidad**: SEV2 por defecto; SEV1 si CloudTrail muestra uso desde una IP desconocida.
**Prevención**: escaneo de secretos como pre-commit hook y en CI (bloqueante), credenciales de vida corta con OIDC en lugar de claves estáticas.

## Playbook 2: contenedor con minero de cripto

**Detección típica**: CPU al 100% sostenido, Falco detectando conexiones a pools de minería, factura cloud disparada.

```bash
# 1. Identificar el pod y NO borrarlo
kubectl top pods -A --sort-by=cpu | head -5

# 2. Preservar antes de contener
kubectl logs payments-7d9f-x2k4 -n prod --timestamps > /evidencia/INC-0042-pod.log
kubectl get pod payments-7d9f-x2k4 -n prod -o yaml > /evidencia/INC-0042-pod.yaml
crictl inspect $(crictl ps -q --name payments) > /evidencia/INC-0042-runtime.json

# 3. Aislar (ver sección de contención) — no borrar, no reiniciar
kubectl label pod payments-7d9f-x2k4 -n prod app- quarantine=INC-2026-0042 --overwrite

# 4. Vector de entrada: ¿la imagen ya venía comprometida o entraron después?
kubectl get pod payments-7d9f-x2k4 -n prod -o jsonpath='{.spec.containers[*].image}'
trivy image --severity CRITICAL,HIGH <esa-imagen>

# 5. Buscar propagación: el mismo patrón en otros pods
kubectl get pods -A -o json | jq -r '.items[] | select(.spec.containers[].image
  | contains("imagen-sospechosa")) | "\(.metadata.namespace)/\(.metadata.name)"'
```

**Severidad**: SEV3 si está confinado a un pod sin datos sensibles; **SEV1 si el minero es la carga visible de un compromiso mayor** — un minero es a menudo lo que dejan cuando ya han hecho lo demás. Nunca lo trates como "solo un minero" hasta haber descartado acceso a datos.
**Prevención**: `limits` de CPU en todos los pods, egress restringido por defecto, imágenes distroless y escaneo bloqueante en el admission controller.

## Playbook 3: acceso SSH no autorizado

**Detección típica**: Wazuh alerta de login desde geografía inusual, clave nueva en `authorized_keys`, login fuera de horario.

```bash
# 1. NO cerrar la sesión aún: primero mira qué está haciendo
who; ps -u <usuario> -f; ss -tunap | grep <ip_sospechosa>

# 2. Capturar tráfico de esa sesión en paralelo (a fichero, para el caso)
timeout 120 tcpdump -i any -w /evidencia/INC-0042.pcap host <ip_sospechosa> &

# 3. Volcar memoria ANTES de cortar (ver sección de evidencia)
sudo ./avml /evidencia/INC-0042-mem.lime

# 4. Ahora sí: cortar acceso y matar sesiones
iptables -I INPUT 1 -s <ip_sospechosa> -j DROP
pkill -KILL -u <usuario>

# 5. Buscar persistencia — el atacante casi siempre deja algo
grep -rn 'ssh-' /home/*/.ssh/authorized_keys /root/.ssh/authorized_keys
systemctl list-units --type=service --state=running --no-pager | grep -vf /etc/servicios-conocidos.txt
find /etc/cron* /var/spool/cron -mtime -7 -ls
last -F | head -40

# 6. Alcance: ¿desde este host llegaron a otros?
grep -h 'Accepted' /var/log/auth.log* | awk '{print $9, $11}' | sort -u
```

**Severidad**: SEV2 mínimo. SEV1 si el acceso fue con privilegios de root o si hay evidencia de movimiento lateral.
**Prevención**: SSH solo con clave y a través de bastión, MFA, `AllowUsers` explícito, y las medidas de [Hardening Linux](hardening_linux.md).

## Los primeros 60 minutos

Imprime esto. Pégalo donde la guardia lo vea.

**0-5 min — Confirmar y declarar**

- [ ] ¿La alerta es real? Aplica las cinco preguntas de triaje
- [ ] Asigna severidad (ante la duda, **sube**)
- [ ] Declara el incidente y abre el canal `#inc-AAAA-MM-DD-nombre`
- [ ] Nombra al Incident Commander en voz alta. Sin IC no hay incidente gestionado

**5-20 min — Preservar**

- [ ] **NO reinicies. NO apagues. NO borres el pod.**
- [ ] Snapshot de disco de todo sistema afectado
- [ ] Volcado de memoria de los hosts comprometidos
- [ ] Hashea y registra todo en `custody.yaml`
- [ ] Exporta logs con riesgo de rotación (auth.log, audit log del apiserver)

**20-35 min — Contener**

- [ ] Aísla en red sin apagar: network policy, security group, `iptables DROP`
- [ ] Revoca sesiones activas, **luego** rota credenciales
- [ ] Verifica que el aislamiento funciona de verdad (prueba de salida)
- [ ] Comprueba si el compromiso se ha propagado a otros hosts o pods

**35-50 min — Documentar y evaluar**

- [ ] Abre el caso en TheHive con la plantilla del escenario
- [ ] Carga los observables (IPs, hashes, dominios) y márcalos como IoC
- [ ] Enriquece con MISP vía Cortex: ¿campaña conocida?
- [ ] Determina si hay obligación de notificación (RGPD: 72 h desde el conocimiento)

**50-60 min — Comunicar y planificar**

- [ ] Primera actualización de Comms a dirección
- [ ] Decide: ¿seguimos observando o erradicamos ya?
- [ ] Si va para largo, organiza turnos **ahora**. Nadie investiga bien en la hora 9
- [ ] Fija la hora de la siguiente actualización y anúnciala

!!! note "La regla de las 4 horas"
    Si un incidente pasa de 4 horas, releva al IC. El agotamiento produce decisiones destructivas e irreversibles, y el relevo obliga a un traspaso que a menudo destapa lo que el primer IC había pasado por alto.
