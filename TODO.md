# Roadmap de Documentación Frikiteam

Este documento rastrea el estado de la documentación, tareas pendientes y mejoras planificadas.

## 🚀 Estado Actual (Q4 2025)

### ✅ Completado / En Producción

- [x] Quickstart (`docs/quickstart.md`)
- [x] Guía de Contribución (`CONTRIBUTING.md`)
- [x] Troubleshooting (`docs/troubleshooting.md`)
- [x] Mermaid Tools (`docs/dev/mermaid.md`)
- [x] Docker: Optimización y Seguridad
- [x] Kubernetes: Probes
- [x] Storage: Estructura base (Ceph, Pure, NetApp, Protocolos)
- [x] Networking: 12 guías completas (Fundamentos, Seguridad/DNS, Operaciones)

### 🚧 Pendiente de Integración (Creado pero no en Nav)

Estos archivos existen en el repositorio pero no están visibles en el menú de navegación (`mkdocs.yml`).

#### DevOps & Automation

- [ ] **Ansible:** `doc/ansible/roles_testing.md`
- [ ] **Terraform:** `doc/terraform/terraform_state.md`

#### Infraestructura & Virtualización

- [ ] **Proxmox:** `doc/proxmox/migration_guide.md`
- [ ] **OpenStack:** `doc/openstack/day2.md`
- [ ] **HAProxy:** `doc/haproxy/haproxy_advanced.md`

#### Ciberseguridad

- [ ] **Cybersecurity:** `docs/doc/cybersecurity/introduccion_devsecops.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/modelo_amenazas.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/principios_seguridad.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/escaneo_vulnerabilidades.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/gestion_secretos.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/firewall_red.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/autenticacion_autorizacion.md`
- [ ] **Cybersecurity:** `docs/doc/cybersecurity/monitoreo_seguridad.md`

#### Curiosidades & Blog

- [ ] **Curiosidades:**
  - `doc/curiosidades/docker_kubernetes_vm_comparison.md`
  - `doc/curiosidades/proxmox_en_debian13.md`
  - `doc/curiosidades/proxmox_vmware_openstack_migration.md`
  - `doc/curiosidades/upgrade_pve8_a_pve9.md`

> Nota: el blog está publicado externamente en `https://frikiteam.es` y por ahora **no** queremos incluir las entradas del blog interno en la navegación del sitio de documentación.

- [ ] **Blog (interno, excluido del nav):**
  - `blog/posts/2025/ci-cd-mkdocs-build.md`
  - `blog/posts/2025/network-compare-practical.md`

Opciones para manejar los archivos del blog interno:

1. Mantenerlos en `blog/` en el repositorio y no incluirlos en `nav` (estado actual).
2. Moverlos a `docs/internal_blog/` para dejarlos disponibles pero fuera del nav principal.
3. Añadir frontmatter `draft: true` o marcarlos con `exclude: true` si se desea que herramientas CI los ignoren (requiere soporte en CI).

Indica si quieres que aplique la opción 2 (mover a `docs/internal_blog/`) o que los deje tal cual.

### 🌍 Localización (i18n)

Estado de la traducción y paridad entre Español (`docs/`) e Inglés (`docs/en/`).

- [ ] **Inconsistencia de Directorios:** Existe `docs/en/doc/curiosidades/` y `docs/en/doc/curiosities/`. Unificar en `curiosities`.
- [ ] **Paridad de Contenido:** Verificar que los artículos nuevos en `docs/doc/storage/` tengan su contraparte en `docs/en/doc/storage/`.
- [ ] **Navegación EN:** Asegurar que `mkdocs.yml` tenga la estructura de navegación correcta para la versión en inglés. *Nota: mkdocs-static-i18n suele requerir configuración cuidadosa del nav si los archivos no son simétricos.*

### 📝 Pendiente de Revisión de Contenido

Archivos generados o stubs que requieren revisión humana y expansión.

- [x] `doc/storage/netapp/netapp_base.md` (Stub creado)
- [x] `doc/storage/pure_storage/pure_storage_base.md` (Stub creado)
- [ ] `doc/storage/protocols/protocols.md` (Añadir más ejemplos reales)
- [x] `doc/storage/protocols/examples/fio_example.md` (Ejemplo `fio` creado)

## 📅 Backlog y Futuras Mejoras

### Infraestructura y CI/CD

- [ ] Implementar GitHub Actions para validación automática (`mkdocs build`).
- [ ] Script de validación de enlaces rotos.
- [ ] Automatizar chequeo de diagramas Mermaid en CI.

### Contenido Nuevo (Propuestas)

- [ ] **Series de Storage:** Profundizar en casos de uso específicos.
- [ ] **Networking:** Comparativas de rendimiento (Tailscale vs NetBird).
- [ ] **Observabilidad:** Guías sobre Prometheus/Grafana en este stack.

## 🛠 Mantenimiento

- [ ] Revisar advertencias de linter (MD0xx) en archivos existentes.
- [ ] Unificar estilo de encabezados (Setext vs ATX).

---

## 🔒 Ciberseguridad

Esta sección propone contenido nuevo sobre ciberseguridad, enfocado en prácticas, herramientas y casos reales aplicables a infraestructuras DevOps y cloud.

### Fundamentos y Conceptos Básicos

- [x] **Introducción a Ciberseguridad en DevOps:** Guía básica sobre DevSecOps, integración de seguridad en pipelines CI/CD. (Creado: `docs/doc/cybersecurity/introduccion_devsecops.md`)
- [x] **Modelo de Amenazas:** Identificación de amenazas comunes en entornos cloud/infra (OWASP Top 10 para infra, MITRE ATT&CK). (Creado: `docs/doc/cybersecurity/modelo_amenazas.md`)
- [x] **Principios de Seguridad:** Defense in Depth, Zero Trust, Least Privilege aplicados a Kubernetes/Docker. (Creado: `docs/doc/cybersecurity/principios_seguridad.md`)

### Herramientas y Tecnologías

- [x] **Escaneo de Vulnerabilidades:** Guías para Trivy, Clair, Snyk en contenedores e imágenes. (Creado: `docs/doc/cybersecurity/escaneo_vulnerabilidades.md`)
- [x] **Gestión de Secretos:** Comparativa HashiCorp Vault vs AWS Secrets Manager vs Kubernetes Secrets. (Creado: `docs/doc/cybersecurity/gestion_secretos.md`)
- [x] **Firewall y Red:** Configuración de firewalls en Linux (iptables/nftables), UFW, y herramientas como Suricata/Zeek para IDS. (Creado: `docs/doc/cybersecurity/firewall_red.md`)
- [x] **Autenticación y Autorización:** LDAP, OAuth2, SAML en entornos empresariales; integración con Keycloak/FreeIPA. (Creado: `docs/doc/cybersecurity/autenticacion_autorizacion.md`)
- [x] **Monitoreo de Seguridad:** Integración de Falco para detección de anomalías en Kubernetes, Wazuh para SIEM básico. (Creado: `docs/doc/cybersecurity/monitoreo_seguridad.md`)

### Casos Prácticos y Guías

- [ ] **Hardening de Servidores Linux:** Checklist para securizar SSH, sudo, kernel parameters (sysctl).
- [ ] **Seguridad en Kubernetes:** RBAC, Network Policies, Pod Security Standards, admission controllers (OPA/Gatekeeper).
- [ ] **Seguridad en Docker:** Imágenes seguras, multi-stage builds, scanning, runtime security con gVisor/Kata Containers.
- [ ] **Backup Seguro:** Encriptación de backups (restic, borg), offsite storage, testing de restauración.
- [ ] **Respuesta a Incidentes:** Playbook básico para IR en infra cloud, herramientas como TheHive/MISP.
- [ ] **Cumplimiento y Auditoría:** Guías para GDPR, ISO 27001 en entornos DevOps; herramientas como OpenSCAP para compliance.

### Avanzado y Especializado

- [ ] **Criptografía Aplicada:** TLS/SSL, certificados Let's Encrypt, VPNs (WireGuard, OpenVPN).
- [ ] **Seguridad en IaC:** Escaneo de Terraform/Ansible con Checkov/TFLint para detectar misconfigurations.
- [ ] **Cloud Security:** Posturas de seguridad en AWS/Azure/GCP (CIS Benchmarks), IAM best practices.
- [ ] **Pentesting Básico:** Herramientas open-source como Metasploit, Nmap, Burp Suite para ethical hacking.
- [ ] **Forensics Digital:** Recolección de logs, chain of custody, herramientas como Volatility para memory forensics.

### Integración con Stack Existente

- [ ] **Ciberseguridad en Storage:** Encriptación at-rest (LUKS, dm-crypt), secure erase, protección contra ransomware en Ceph/Pure/NetApp.
- [ ] **Networking Seguro:** VPNs overlay (Tailscale vs NetBird), zero-trust networking con Cilium.
- [ ] **Observabilidad con Seguridad:** Usar Prometheus/Grafana para dashboards de seguridad, alertas en anomalías.

### Roadmap de Contenido (6 meses)

Fase 1 (0–2 meses): Fundamentos y herramientas básicas.
- [ ] Crear stubs para "Introducción a DevSecOps" y "Escaneo de Vulnerabilidades con Trivy".
- [ ] Añadir a nav en `mkdocs.yml` bajo nueva sección "Ciberseguridad".

Fase 2 (2–4 meses): Casos prácticos.
- [ ] Guías para hardening Linux y seguridad Kubernetes.
- [ ] Comparativas de herramientas (Vault vs K8s Secrets).

Fase 3 (4–6 meses): Avanzado y integración.
- [ ] Contenido sobre compliance, pentesting y forensics.
- [ ] Enlazar con secciones existentes (storage, networking) para cross-references.

---

## Gobernanza del contenido (propuesta)

- **Owner por área:** asignar un responsable breve por sección (ej. `storage`, `docker`, `kubernetes`) para revisión y merge.
- **Cadencia:** ciclo mínimo de revisión mensual para áreas activas.
- **Etiquetas de PR:** usar `docs`, `docs-review` y `docs-ready` para filtrar PRs.

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

Si quieres, puedo generar un parche propuesto para `mkdocs.yml` que incluya las páginas hoy listadas como "exist but not in nav".

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

## Próximos pasos sugeridos (elige una)

1. Aplico los cambios propuestos en `mkdocs.yml` (incluir páginas huérfanas).
2. Creo stubs para X items prioritarios y abro PR(s) de ejemplo.
3. Implemento un workflow de GitHub Actions `docs-ci.yml` que ejecuta `mkdocs build` y la comprobación de diagramas.

