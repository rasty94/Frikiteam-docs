# Roadmap de Documentación Frikiteam

Este documento rastrea las tareas pendientes y mejoras planificadas. El historial de tareas completadas y los logs de progreso de publicación viven en [`done.md`](done.md).

## 🔍 Diagnóstico (actualizado 2026-09-03)

La estructura está sana y el problema es de mantenimiento, no de contenido nuevo.

**Lo que ya está bien (no tocar):**
- 150 páginas ES y 150 EN, todas en el `nav` y todas con frontmatter (salvo 4 `index.md`, excluidos a propósito).
- CI: `mkdocs build --strict`, `validate_metadata.py --strict`, `check_sync.py --strict` y `test_wordpress_format.py` en el job `build`; Mermaid y enlaces rotos en el job `quality`.
- `draft: true` excluye la página del sitio de verdad (`hooks/drafts.py`), y el validador exige que ambos idiomas coincidan.
- `check_sync.py --strict` falla si una gemela difiere más de un 40% en tamaño respecto a la otra.
- Vocabularios cerrados y validados: 76 tags y 15 categorías, estas últimas comprobando que la traducción EN coincide con la ES.
- Señal de frescura derivada de `git log`, ignorando los commits `chore(meta)`.
- Índice de tags navegable en `docs/tags.md` y `docs/en/tags.md`.

**Matiz:** «sincronizadas» empezó significando solo que las fechas coinciden. Desde el 2026-09-03 `check_sync.py --strict` compara también el tamaño y falla si difiere más de un 40%, así que una traducción a medias ya no pasa la CI.

## 🎯 Plan de mejora (por orden de retorno)

### 1. Cerrar la deuda "sin ejecutar"
TheHive/MISP y vLLM se verificaron el 2026-09-03 (ver `done.md`). Queda OpenSCAP y la hornada del 2026-10-10:
- [ ] **OpenSCAP:** los comandos `oscap` y los paquetes SSG de Debian no se han probado. Necesita una máquina Debian real; no se puede verificar desde el repositorio.
- [ ] **16 guías ampliadas el 2026-10-10 de conocimiento, sin ejecutar.** Los agentes que las escribieron dejaron su lista de dudas; todo lo dependiente de versión lleva `!!! warning`, pero esto hay que contrastar con la herramienta real:
    - `backups/pbs.md`: nombres de roles (`DatastoreBackup`, `DatastoreReader`, `DatastoreAdmin`) y sintaxis de `acl update`; flags de `verify-job`, `remote create` y `sync-job create`; existencia de `prune-job`; formato de `PBS_REPOSITORY` con token.
    - `backups/strategy_321.md` y `backups/restic_borg.md`: el agente que las escribió no entregó lista de dudas; revisar completas.
    - `storage/netapp/netapp_base.md`: parámetros de `volume create`, `export-policy rule create`, `cifs share create`; `-superuser sys` como equivalente de `no_root_squash`; `pvesm add nfs --content`; destino SnapMirror tipo DP; YAML de Trident (`csi.trident.netapp.io`, `ontap-nas`).
    - `storage/pure_storage/pure_storage_base.md`: sintaxis de `purevol create --size`, `purehost create --iqnlist`, `purevol snap --suffix`, `purevol copy`; nombre del provisioner CSI.
    - `storage/ceph/ceph_tuning.md`: `rbd_cache_writethrough_until_flush`, dependencias de `object-map`/`fast-diff` con `exclusive-lock`, `ceph balancer status`, `osd pool application enable`.
    - `linux/systemd.md`: `network-online.target` y wait-online; descripción de `systemd-analyze security`; versiones de `ProtectProc=` y `SystemCallFilter=`; `status=203/EXEC`; `StartLimitIntervalSec`/`StartLimitBurst` en `[Unit]`; `systemctl revert`.
    - `linux/ssh_security.md`: `KbdInteractiveAuthentication` frente a `ChallengeResponseAuthentication`; orden de lectura de `sshd_config.d/`; flujo de certificados (`ssh-keygen -s`, `TrustedUserCAKeys`, `@cert-authority`); requisitos de `ChrootDirectory`; backend systemd de fail2ban; unit `ssh` frente a `sshd`.
    - `linux/wireguard.md`: MTU por defecto de `wg-quick` (1420); afirmación sobre `PresharedKey`; alcance de `wg syncconf`.
    - `networking/vrouter_vyos.md`: sintaxis de firewall 1.4 (`firewall ipv4 input filter`, `inbound-interface name`); `bgp system-as-number`; política de rolling/estables; `commit-archive`; `show ip bgp summary`, `show ip ospf neighbor`, `show system cpu`.
    - `networking/benchmarks.md`: `iperf3 --bidir` (versión); `ping -M do -s 1472` (iputils); privilegios de `ping -i 0.2`; paquete `mtr-tiny`; nombres de features en `ethtool -K`.
    - `databases/redis.md`: relato de la licencia y Valkey; `HealthCmd`/`HealthInterval` en Quadlet; carga de AOF frente a RDB en la restauración.
    - `databases/postgres.md`: `POSTGRES_PASSWORD_FILE` y `/docker-entrypoint-initdb.d/`; `Secret=…,type=env,target=` en Quadlet; paso de `md5` a SCRAM; `pending_restart` en `pg_settings`.
    - `identity/keycloak.md`: `KC_BOOTSTRAP_ADMIN_*` frente a `KEYCLOAK_ADMIN`; `KC_HOSTNAME` con URL completa; `KC_PROXY_HEADERS=xforwarded`; puerto de gestión para health; alcance de `kc.sh export`.
    - `monitoring/uptime_kuma.md`: rama `:2` y BD externa; autenticación de `/metrics`; ruta `/api/push/<token>`; ajuste de proxy de confianza; `kuma.db`.
    - `programming/fastapi.md`: paquete `uvicorn-worker`; `Notify=healthy` en Quadlet; versiones `@vN` de las acciones; etiquetas de healthcheck de Traefik y `http-check` de HAProxy; `--proxy-headers`, `--forwarded-allow-ips`, `--root-path`.

### 2. Otra deuda operativa
- [ ] **Desplegar Plausible** en servidor o revisar logs existentes para analytics básico.
- [ ] **19 borradores en WordPress esperando revisión humana** en `frikiteam.es/wp-admin`. El pipeline no los publica: el paso a `publish` es decisión manual.
- [ ] **18 páginas sin tocar en más de 90 días** (recontado el 2026-10-10 con `scripts/check_freshness.py`, tras ampliar `ceph_tuning` y `vrouter_vyos`). Concentradas en vRouters, Cybersecurity, AI, OpenStack y Ceph. Revisar versiones y comandos.
- [ ] **4 `index.md` del árbol ES sin frontmatter.** Es deliberado, por convención del proyecto los índices quedan excluidos del campo `updated`.
- [ ] **Grafo de graphify incompleto para los Markdown.** Comprobado el 2026-10-10: `secrets_gitops.md` (ES y EN) no tiene nodos, y el `manifest.json` solo conserva `semantic_hash` en 11 de 310 páginas, así que `/graphify --update` querría reextraer las 310 con LLM. El paquete en `.venv` es 0.9.19 y el skill 0.9.69. Pasos: `pip install -U graphifyy`, y decidir si se paga una reextracción semántica completa o se indexan solo las 2 páginas que faltan. `graphify update .` (solo código, sin LLM) sí está al día.

## 🔮 Futurible (no ahora)

- [ ] **Servidor de inferencia en `http://` sobre IP desnuda** (`INFERENCE_SERVERS` en `.env`, usado por `wordpress_sync.py`). La clave de API y el contenido reescrito viajan sin cifrar. Hoy el valor por defecto es `http://localhost:11434`, que no sale de la máquina; solo importa si se apunta a un servidor remoto. Cambiar la URL a https o meterlo tras VPN cuando eso ocurra.

## 📅 Contenido nuevo (solo cuando lo anterior esté cerrado)

Huecos reales, comprobados contra el repo el 2026-09-02. Los 13 stubs ya están cerrados, así que esta sección es la siguiente en la cola:

### Cybersecurity / Networking
- [ ] **Zero-trust con Cilium** en Kubernetes (solo 2 menciones de paso en el repo).
- [ ] **Forense digital:** recolección de logs, chain of custody, Volatility para memory forensics (1 mención).
- [ ] **Cifrado at-rest en storage:** LUKS/dm-crypt, secure erase, protección contra ransomware en Ceph/Pure/NetApp (LUKS aparece en 2 docs).
- [ ] **eBPF** como tema propio (hoy solo aparece dentro de service mesh y monitoreo).
- [ ] **Cloud Security:** CIS Benchmarks en AWS/Azure/GCP, IAM best practices.
- [ ] Optimización de MTU y MSS para 10G/40G.
- [ ] BGP avanzado para multi-homing y load balancing.
- [ ] Cross-references entre ciberseguridad y storage/networking.

### Plataforma
- [ ] Chaos Engineering.
- [ ] Optimización de costes en Kubernetes.

### Storage
- [ ] `doc/storage/protocols/protocols.md`: añadir más ejemplos reales.
- [ ] Storage para modelos: checkpoints en Ceph/Pure, versionado con DVC.

### Ya cubierto, retirado del roadmap
Podman rootless (`doc/docker/podman_rootless.md`), PostgreSQL HA (`doc/databases/postgresql_ha.md`), WireGuard (15 docs), Let's Encrypt/certbot (9), Tailscale/NetBird, Nmap/Metasploit/Burp (pentesting básico), TLS.

### Aparcado: Inteligencia Artificial
AI ya es la segunda sección más grande (25 docs). Los 13 stubs que bloqueaban esta sección se cerraron el 2026-09-03, así que queda desbloqueada; se mantiene aparcada por prioridad, no por impedimento:
- Multi-agent systems, LLMs en edge, seguridad y privacidad (GDPR), observabilidad de costes/latencias, CI/CD para modelos, fine-tuning por dominio, networking para inferencia.

---

### Gobernanza del contenido (owners por área)

Para asegurar calidad y consistencia, asignamos responsables (owners) por sección principal:

- **Storage**: @rasty94 - Responsable de Ceph, Pure, NetApp, protocolos
- **Networking**: @rasty94 - Responsable de fundamentos, seguridad, operaciones, comparaciones
- **Docker/Kubernetes**: @rasty94 - Responsable de contenedores y orquestación
- **DevOps (Ansible/Terraform/CI/CD)**: @rasty94 - Responsable de automatización e IaC
- **Cybersecurity**: @rasty94 - Responsable de seguridad, hardening, monitoreo
- **Monitoring/Observability**: @rasty94 - Responsable de Prometheus, Grafana, logs
- **AI/LLMs**: @rasty94 - Responsable de modelos, herramientas locales, evaluación
- **Programming**: @rasty94 - Responsable de guías de desarrollo
- **Linux/Identity/Backups**: @rasty94 - Responsable de sistema operativo y servicios

**Proceso de contribución:**
1. PRs requieren revisión del owner del área
2. Owners revisan contenido técnico y consistencia
3. Ciclo mínimo de revisión: semanal para áreas activas

Etiquetas de PR: `docs`, `docs-review`, `docs-ready`

### Convenciones para nuevas páginas

- Frontmatter, tal como lo validan `validate_metadata.py` y `check_sync.py`:

    ```yaml
    title: "Título claro"
    description: "Una frase que explique qué resuelve la página"
    keywords: "palabras, clave, separadas, por, comas"
    tags: ['storage', 'ceph']      # solo valores de TAG_VOCABULARY (76)
    updated: 2026-09-03            # debe coincidir con la gemela EN
    last_reviewed: 2026-09-03
    difficulty: intermediate       # beginner | intermediate | advanced | expert
    estimated_time: 20 min
    category: Almacenamiento       # solo valores de CATEGORY_VOCABULARY (15)
    status: published              # draft | review | published | archived
    prerequisites:
      - "Lo que hay que saber antes"
    reviewers: ["@rasty94"]
    contributors: ["@rasty94"]
    ```

    Los campos `date:` y `draft:` aparecen en páginas antiguas pero **no los lee nadie**;
    no los añadas en páginas nuevas. El estado se controla con `status`.
    En el árbol EN, `category` va traducido según `CATEGORY_VOCABULARY`; `updated` y
    `last_reviewed` deben ser idénticos a los de la página ES.

- Estructura recomendada del MD:
    1. Resumen (1–2 líneas)
    2. Prerrequisitos / audiencias
    3. Pasos o explicación técnica
    4. Ejemplos reproducibles (si aplica)
    5. Links relacionados y referencias

### Checklist de publicación (PR)

- [ ] `mkdocs build --strict`: sin avisos ni errores.
- [ ] `python scripts/validate_metadata.py --strict`: tags y categorías dentro del vocabulario, y categoría EN emparejada con la ES.
- [ ] `python scripts/check_sync.py --strict`: sin desincronizados y sin asimetría de tamaño mayor del 40%.
- [ ] `./validate_mermaid.sh` si has tocado diagramas.
- [ ] Página gemela en el otro idioma, con la misma estructura y las mismas fechas.
- [ ] Llaves de Jinja en bloques de código envueltas en `raw`. Ver [Troubleshooting](docs/troubleshooting.md).
- [ ] Imágenes con `alt`.
- [ ] Entrada en Novedades de `docs/index.md` y `docs/en/index.md` si es contenido nuevo.
- [ ] Revisado por el owner del área.

**Prefijo de commit:** si el cambio solo toca frontmatter o metadatos, usa `chore(meta):`.
`check_freshness.py` ignora esos commits; sin el prefijo, un cambio masivo de metadatos
marca como recién revisadas páginas que nadie ha leído y se pierde la señal de obsolescencia.

---

## Integración al `nav` (propuesta de proceso)

1. Añadir los archivos que se consideran estables a `mkdocs.yml` en una rama de trabajo.
2. Ejecutar `mkdocs build` en CI y revisar advertencias.
3. Abrir PR con la modificación de `mkdocs.yml` y asignar al owner del área.

---

## Comandos útiles para editores

```bash
# crear/activar entorno (el del repo es .venv)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# servir sitio localmente
mkdocs serve -a 0.0.0.0:8000

# lo mismo que ejecuta la CI, antes de abrir el PR
mkdocs build --strict
python scripts/validate_metadata.py --strict
python scripts/check_sync.py --strict
python test_wordpress_format.py

# informativos, no bloquean
python scripts/check_freshness.py     # páginas sin tocar en 90+ días
./validate_mermaid.sh                 # renderiza todos los diagramas (lento)
```

---

## ❌ Lo Que NO Necesitamos (Todavía)

- ❌ Comités de gobernanza mensual
- ❌ Métricas sofisticadas de readability
- ❌ Workflow de 5 etapas de revisión
- ❌ Versionado de documentación
- ❌ Herramientas de pago (Analytics premium, etc.)

> **Filosofía:** Mantener simple. Estas herramientas son para cuando haya 10+ personas escribiendo docs.
