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
- [ ] **Desplegar Plausible** en servidor o revisar logs existentes para analytics básico.
- [ ] **19 borradores en WordPress esperando revisión humana** en `frikiteam.es/wp-admin`. El pipeline no los publica: el paso a `publish` es decisión manual.
- [ ] **4 `index.md` del árbol ES sin frontmatter.** Es deliberado, por convención del proyecto los índices quedan excluidos del campo `updated`.
- [ ] **Reextracción semántica de graphify pendiente.** Comprobado el 2026-10-11 con graphifyy 0.9.85 (actualizado desde 0.9.19): `graphify update .` deja el grafo al día en código y estructura de los Markdown, y `secrets_gitops.md` ya tiene nodos. Pero el `manifest.json` solo conserva `semantic_hash` en 3 de 313 páginas (71 en julio, 11 el 2026-10-10: la 0.9.19 los iba perdiendo en cada reconstrucción de los hooks), así que `/graphify --update` reextraería 314 documentos con LLM. Decidir si se paga esa pasada completa. `graphify-out/` acumula además una copia fechada por reconstrucción; las anteriores a septiembre se pueden borrar.

## 🔮 Futurible (no ahora)

- [ ] **Servidor de inferencia en `http://` sobre IP desnuda** (`INFERENCE_SERVERS` en `.env`, usado por `wordpress_sync.py`). La clave de API y el contenido reescrito viajan sin cifrar. Hoy el valor por defecto es `http://localhost:11434`, que no sale de la máquina; solo importa si se apunta a un servidor remoto. Cambiar la URL a https o meterlo tras VPN cuando eso ocurra.

## 📅 Contenido nuevo

Revisado contra el repo el 2026-10-11. Los seis primeros huecos (ZFS/LVM, DNS propio, Kubernetes en homelab, backup de Kubernetes, eBPF con Cilium y forense) se escribieron ese mismo día; ver `done.md`. No queda ningún hueco grande verificado: el siguiente paso es contrastar la deuda de verificación de arriba antes de abrir temas.


### Reducido a una sección de una página existente
- [ ] **Cifrado en reposo en cabinas** (Ceph/Pure/NetApp): LUKS ya está a fondo en `cybersecurity/criptografia_aplicada.md` (14 menciones); falta solo el ángulo de cabina.
- [ ] `doc/storage/protocols/protocols.md`: más ejemplos reales.

### Retirado del roadmap el 2026-10-11
- **CIS Benchmarks en nube y optimización de costes en Kubernetes**: no encajan en un sitio de infraestructura propia (costes: 0 menciones).
- **Chaos engineering, DVC, BGP multihoming**: 0-1 menciones y ninguna página vecina que los pida. Aparcados sin fecha.
- **Falsos huecos**, ya cubiertos con otro título: Prometheus, Grafana, Alertmanager y Helm (`monitoring/observability_stack.md`), Vault (`cybersecurity/gestion_secretos.md`, `secrets_gitops.md`), Falco y Kyverno (`monitoreo_seguridad.md`, `kubernetes_security.md`), Keepalived (`haproxy/haproxy_advanced.md`).
- Ya cubierto antes: Podman rootless, PostgreSQL HA, WireGuard, Let's Encrypt/certbot, Tailscale/NetBird, Nmap/Metasploit/Burp, TLS.

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
