# Roadmap de Documentación Frikiteam

Este documento rastrea las tareas pendientes y mejoras planificadas. El historial de tareas completadas y los logs de progreso de publicación viven en [`done.md`](done.md).

## 🔍 Diagnóstico (2026-09-02)

La estructura está sana y el problema real es de mantenimiento, no de contenido nuevo.

**Lo que ya está bien (no tocar):**
- 149 páginas ES y 149 EN, sincronizadas al 100%, todas en el `nav` y todas con frontmatter.
- CI con `mkdocs build --strict`, validación de Mermaid, enlaces rotos, vocabulario de tags y sincronía ES/EN. El checklist de publicación lo cumple la CI sola.
- Vocabularios cerrados y validados en CI: 76 tags y 15 categorías, estas últimas con comprobación de que la traducción EN coincide. Señal de frescura derivada de `git log`.

## 🎯 Plan de mejora (por orden de retorno)

### 1. Terminar los stubs pendientes
Diez de los trece se completaron el 2026-09-03 (ver `done.md`). Quedan tres:
- [ ] `doc/programming/flutter.md` (35 líneas). Mismo enfoque que React: construir, empaquetar y desplegar, no enseñar el framework.
- [ ] `troubleshooting.md` (37). Página raíz orientada a quien trabaja con este repositorio: errores de `mkdocs build --strict`, el fallo por llaves de Jinja, enlaces rotos, vocabularios cerrados y entorno de Python.
- [ ] `doc/proxmox/sdn.md`. Caso inverso: el árbol EN tiene 175 líneas y el ES 38. Traducir el inglés al español y ampliar ambos.

### 2. Cerrar la deuda "sin ejecutar"
Vale más verificar estos tres puntos en un despliegue real que escribir un doc nuevo.
- [ ] **TheHive/MISP:** el `docker-compose` está escrito de conocimiento. Contrastar al menos los tags de imagen (`strangebee/thehive:5.3`, `cassandra:4.1`, `elasticsearch:8.14.3`) contra los registries.
- [ ] **OpenSCAP:** los comandos `oscap` y los paquetes SSG de Debian no se han probado.
- [ ] **vLLM:** 4 métricas en `monitoreo_llms.md` (sufijo `_total` de algunos counters y `num_requests_waiting`) son extrapolaciones. El doc incluye un `curl /metrics | grep` para comprobarlas.

### 3. Otra deuda operativa
- [ ] **Desplegar Plausible** en servidor o revisar logs existentes para analytics básico.
- [ ] **19 borradores en WordPress esperando revisión humana** en `frikiteam.es/wp-admin`. El pipeline no los publica: el paso a `publish` es decisión manual.
- [ ] **25 páginas sin tocar en más de 90 días**, según `scripts/check_freshness.py` (ahora fiable). Concentradas en OpenStack (4), vRouters (6), Ceph/NetApp/Pure (4) y Cybersecurity (6). Revisar versiones y comandos.
- [ ] **Cerrar la asimetría de contenido ES/EN.** `check_sync.py` ya la detecta y la reporta como aviso (umbral del 40%, constante `UMBRAL_ASIMETRIA`). No bloquea la CI todavía porque hay backlog previo. Pendientes a 2026-09-03:

    | Página | ES | EN | Diferencia |
    |---|---|---|---|
    | `cicd/argocd.md` | 40 | 232 | 82% |
    | `docker/docker_optimizations.md` | 50 | 117 | 57% |
    | `quickstart.md` | 153 | 67 | 56% |
    | `storage/protocols/protocols.md` | 162 | 81 | 50% |
    | `kubernetes/probes.md` | 57 | 99 | 42% |

    En ArgoCD, `docker_optimizations` y `probes` el árbol inglés está más completo que el español, al revés de lo habitual. Cuando la lista quede vacía, subir el aviso a fallo en `--strict`.

    Nota: el chequeo salta los `index.md` por diseño heredado, así que no ve `networking/index.md` (115 ES / 21 EN). Y `ai/contenido_tecnico.md` (886/1256) y `ai/analisis_logs.md` (937/1261) quedan por debajo del umbral pese a diferir en más de 300 líneas; si molestan, bajar el umbral a 0.25.

- [ ] **4 `index.md` del árbol ES sin frontmatter.** Es deliberado, por convención del proyecto los índices quedan excluidos del campo `updated`.

## 🔮 Futurible (no ahora)

- [ ] **Servidor de inferencia en `http://` sobre IP desnuda** (`INFERENCE_SERVERS` en `.env`, usado por `wordpress_sync.py`). La clave de API y el contenido reescrito viajan sin cifrar. Hoy el valor por defecto es `http://localhost:11434`, que no sale de la máquina; solo importa si se apunta a un servidor remoto. Cambiar la URL a https o meterlo tras VPN cuando eso ocurra.

## 📅 Contenido nuevo (solo cuando lo anterior esté cerrado)

Huecos reales, comprobados contra el repo el 2026-09-02:

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
AI ya es la segunda sección más grande (25 docs) y el resto del repo tiene stubs sin rellenar. No abrir hasta cerrar el punto 1 (stubs):
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

- Frontmatter mínimo:

    ```yaml
    title: "Título claro"
    date: 2025-11-23
    tags: [storage, ceph]
    draft: true # o false si listo para publicar
    ```

- Estructura recomendada del MD:
    1. Resumen (1–2 líneas)
    2. Prerrequisitos / audiencias
    3. Pasos o explicación técnica
    4. Ejemplos reproducibles (si aplica)
    5. Links relacionados y referencias

### Checklist de publicación (PR)

- [ ] `mkdocs build` local: no errores.
- [ ] No enlaces rotos (usar plugin o comprobador externo).
- [ ] Imágenes con `alt`.
- [ ] Metadatos (description/keywords) añadidos cuando aplique.
- [ ] Revisado por el owner del área.

---

## Integración al `nav` (propuesta de proceso)

1. Añadir los archivos que se consideran estables a `mkdocs.yml` en una rama de trabajo.
2. Ejecutar `mkdocs build` en CI y revisar advertencias.
3. Abrir PR con la modificación de `mkdocs.yml` y asignar al owner del área.

---

## Comandos útiles para editores

```bash
# crear/activar venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# servir sitio localmente
mkdocs serve -a 0.0.0.0:8000

# generar build para ver advertencias
mkdocs build
```

---

## ❌ Lo Que NO Necesitamos (Todavía)

- ❌ Comités de gobernanza mensual
- ❌ Métricas sofisticadas de readability
- ❌ Workflow de 5 etapas de revisión
- ❌ Versionado de documentación
- ❌ Herramientas de pago (Analytics premium, etc.)

> **Filosofía:** Mantener simple. Estas herramientas son para cuando haya 10+ personas escribiendo docs.
