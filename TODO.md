# Roadmap de Documentación Frikiteam

Este documento rastrea las tareas pendientes y mejoras planificadas. El historial de tareas completadas y los logs de progreso de publicación viven en [`done.md`](done.md).

## 📅 Pendiente de Contenido

### Storage
- [ ] `doc/storage/protocols/protocols.md` (añadir más ejemplos reales)
- [ ] **Storage para Modelos:** optimización de almacenamiento de checkpoints (Ceph, Pure), versionado con DVC.

### Networking
- [ ] Networking zero-trust con Cilium en Kubernetes clusters.
- [ ] Optimización de MTU y MSS para redes de alto rendimiento (10G/40G).
- [ ] BGP avanzado para multi-homing y load balancing.
- [ ] Seguridad en redes overlay: encriptación, segmentación y monitoreo.
- [ ] **Networking para Inferencia:** optimización de bandwidth para descargas de modelos, caché distribuido con Redis.

### Inteligencia Artificial
- [ ] **Multi-agent Systems:** orquestación de múltiples LLMs, delegación de tareas, coordinación de flujos.
- [ ] **LLMs en Edge:** despliegue en dispositivos IoT, Raspberry Pi, optimización para consumo de energía.
- [ ] **Evaluación de Seguridad y Privacidad:** extracción de datos de entrenamiento, anonimización, GDPR compliance.
- [ ] **Monitoreo y Observabilidad:** tracking de costos (si usan APIs), latencias, calidad de respuestas.
- [ ] **CI/CD para Modelos:** validación automática de modelos, A/B testing de versiones, despliegue gradual.
- [ ] Fine-tuning avanzado para dominios específicos (DevOps, networking, storage).
- [ ] Evaluación de seguridad y privacidad.

### Ciberseguridad
- [ ] **Criptografía Aplicada:** TLS/SSL, certificados Let's Encrypt, VPNs (WireGuard, OpenVPN).
- [ ] **Cloud Security:** posturas de seguridad en AWS/Azure/GCP (CIS Benchmarks), IAM best practices.
- [ ] **Pentesting Básico:** herramientas open-source como Metasploit, Nmap, Burp Suite para ethical hacking.
- [ ] **Forensics Digital:** recolección de logs, chain of custody, herramientas como Volatility para memory forensics.
- [ ] **Ciberseguridad en Storage:** encriptación at-rest (LUKS, dm-crypt), secure erase, protección contra ransomware en Ceph/Pure/NetApp.
- [ ] **Networking Seguro:** VPNs overlay (Tailscale vs NetBird), zero-trust networking con Cilium.
- [ ] **Observabilidad con Seguridad:** dashboards de seguridad en Prometheus/Grafana, alertas en anomalías.
- [ ] Cross-references entre ciberseguridad y las secciones de storage/networking existentes.

## 🛠 Deuda pendiente (real)

- [ ] **Desplegar Plausible** en servidor o revisar logs existentes para analytics básico.
- [ ] **Sin ejecutar:** el `docker-compose` de TheHive/MISP y los comandos de `oscap` están escritos de conocimiento, no probados contra un despliegue real. Los tags de imagen (`strangebee/thehive:5.3`, `cassandra:4.1`, `elasticsearch:8.14.3`) y los paquetes SSG de Debian conviene contrastarlos antes de seguir la guía al pie de la letra.
- [ ] **Sin verificar al 100%:** 4 métricas de vLLM en `monitoreo_llms.md` (el sufijo `_total` de algunos counters y `num_requests_waiting`) son extrapolaciones coherentes pero no confirmadas carácter a carácter. El documento avisa de ello e incluye un `curl /metrics | grep` para comprobarlas en tu propio despliegue.
- [ ] **Huecos de roadmap sin empezar:** eBPF, Podman rootless, PostgreSQL HA, Chaos Engineering, optimización de costes en K8s.
- [ ] **11 borradores en WordPress esperando revisión humana** en `frikiteam.es/wp-admin`. El pipeline no los publica: el paso a `publish` es decisión manual.
- [ ] **4 `index.md` del árbol ES sin frontmatter.** Es deliberado, por convención del proyecto los índices quedan excluidos del campo `updated`.
- [ ] **Servidor de inferencia principal en `http://` sobre IP desnuda:** la clave de API y el contenido enviado viajan sin cifrar. Cambiar la URL en `.env` basta si el servidor admite https o está tras VPN.

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
