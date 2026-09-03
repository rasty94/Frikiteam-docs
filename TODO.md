# Roadmap de Documentación Frikiteam

Este documento rastrea las tareas pendientes y mejoras planificadas. El historial de tareas completadas y los logs de progreso de publicación viven en [`done.md`](done.md).

## 🔍 Diagnóstico (actualizado 2026-09-03)

La estructura está sana y el problema es de mantenimiento, no de contenido nuevo.

**Lo que ya está bien (no tocar):**
- 150 páginas ES y 150 EN, todas en el `nav` y todas con frontmatter (salvo 4 `index.md`, excluidos a propósito).
- CI: `mkdocs build --strict`, `validate_metadata.py --strict`, `check_sync.py --strict` y `test_wordpress_format.py` en el job `build`; Mermaid y enlaces rotos en el job `quality`.
- `draft: true` excluye la página del sitio de verdad (`hooks/drafts.py`), y el validador exige que ambos idiomas coincidan.
- Vocabularios cerrados y validados: 76 tags y 15 categorías, estas últimas comprobando que la traducción EN coincide con la ES.
- Señal de frescura derivada de `git log`, ignorando los commits `chore(meta)`.
- Índice de tags navegable en `docs/tags.md` y `docs/en/tags.md`.

**Matiz importante:** «sincronizadas» significa que las fechas coinciden, no que el contenido sea equivalente. Quedan 5 parejas con asimetría real (ver punto 2).

## 🎯 Plan de mejora (por orden de retorno)

### 1. Cerrar la deuda "sin ejecutar"
TheHive/MISP y vLLM se verificaron el 2026-09-03 (ver `done.md`). Queda uno:
- [ ] **OpenSCAP:** los comandos `oscap` y los paquetes SSG de Debian no se han probado. Necesita una máquina Debian real; no se puede verificar desde el repositorio.

### 2. Otra deuda operativa
- [ ] **Desplegar Plausible** en servidor o revisar logs existentes para analytics básico.
- [ ] **19 borradores en WordPress esperando revisión humana** en `frikiteam.es/wp-admin`. El pipeline no los publica: el paso a `publish` es decisión manual.
- [ ] **22 páginas sin tocar en más de 90 días**, según `scripts/check_freshness.py` (ahora fiable). Concentradas en OpenStack, vRouters, Ceph/NetApp/Pure y Cybersecurity. Revisar versiones y comandos.
- [ ] **Cerrar la asimetría de contenido ES/EN.** `check_sync.py` la detecta y la reporta como aviso (umbral del 40%, constante `UMBRAL_ASIMETRIA`). No bloquea la CI todavía porque hay backlog previo. Pendientes a 2026-09-03:

    | Página | ES | EN | Diferencia |
    |---|---|---|---|
    | `cicd/argocd.md` | 40 | 232 | 82% |
    | `docker/docker_optimizations.md` | 50 | 117 | 57% |
    | `quickstart.md` | 153 | 67 | 56% |
    | `storage/protocols/protocols.md` | 162 | 81 | 50% |
    | `kubernetes/probes.md` | 57 | 99 | 42% |

    En ArgoCD, `docker_optimizations` y `probes` el árbol inglés está más completo que el español, al revés de lo habitual. Cuando la lista quede vacía, subir el aviso a fallo en `--strict`.

    Nota: el chequeo salta los `index.md` por diseño heredado, así que no ve `networking/index.md` (115 ES / 21 EN). Y `ai/contenido_tecnico.md` (886/1256) y `ai/analisis_logs.md` (937/1261) quedan por debajo del umbral pese a diferir en más de 300 líneas; si molestan, bajar el umbral a 0.25.

- [ ] **Limpiar metadatos muertos del frontmatter.** Quedan 47 páginas con `date:`, que no consume nadie (la fecha buena es `updated`). `draft: false` sigue en 50 páginas: ahora es semánticamente válido, pero redundante con no ponerlo. Ninguna de las dos cosas rompe nada; es limpieza.
- [ ] **4 `index.md` del árbol ES sin frontmatter.** Es deliberado, por convención del proyecto los índices quedan excluidos del campo `updated`.

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
- [ ] `python scripts/check_sync.py --strict`: sin desincronizados. Revisa también el aviso de asimetría por si la traducción se ha quedado corta.
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
