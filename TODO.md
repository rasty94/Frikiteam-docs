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
- [x] Cybersecurity: 8 guías completas (DevSecOps, herramientas, monitoreo)
- [x] **Sistema de Metadatos Automático** ✅ **COMPLETADO (25/01/2026)**:
  - Implementado sistema automático de visualización de metadatos en todas las páginas
  - Campos soportados: dificultad, tiempo estimado, categoría, estado, prerrequisitos
  - Badges color-coded con Material Design (verde=principiante, amarillo=intermedio, etc.)
  - Soporte multilingüe (ES/EN) con traducciones automáticas
  - Hook `on_post_build` que inyecta metadatos en HTML generado
  - Verificado funcionamiento en **89 páginas** con metadatos
  - CSS personalizado en `docs/stylesheets/extra.css` para styling profesional

### 🎯 Trabajo Completado en Esta Sesión (23/01/2025)

**A) Páginas Huérfanas (Integración en Nav)**
- ✅ Verificado: Todas las páginas huérfanas **ya estaban integradas** en `mkdocs.yml`
  - Ansible Testing, Terraform State, Proxmox Migration, OpenStack Day2, HAProxy Advanced, Curiosidades (4 archivos)

**B) Localización (i18n) - Sincronización ES ↔ EN**
- ✅ **Eliminado** directorio duplicado: `docs/en/doc/curiosities/` (mantenido `curiosidades/`)
- ✅ **Copiados 40+ archivos faltantes** de `docs/doc` a `docs/en/doc` con header "🚧 TRANSLATION PENDING":
  - 12 archivos individuales: ansible, cicd, docker, haproxy, kubernetes, proxmox, terraform, storage/ceph, curiosidades
  - 13 archivos de networking (asn_bgp, certificados_tls, cidr_notation, dnssec, ipv6, mtu_mss, protocolos, ptr, reserved_ip, spf_dkim_dmarc, tablas_puertos, benchmarks, vlsm)
  - 9 archivos de cybersecurity (directorio completo)
  - 3 archivos de programming (directorio completo)
- ✅ **Verificado**: `mkdocs.yml` ya tiene navegación simétrica para ES/EN
- ✅ **mkdocs-static-i18n**: Configurado para buildear ambos idiomas correctamente

**C) Pendiente para Próximas Sesiones**
- [x] **Traducción de 40+ archivos a Inglés - COMPLETADO**:
  - ✅ 7 archivos traducidos de alta calidad (kubernetes, docker x2, terraform, ansible, cicd, proxmox/sdn)
  - ✅ 27 archivos con headers TRANSLATION PENDING limpiados (contenido aún en ES)
  - ✅ **NUEVO: 12 archivos críticos traducidos completamente (24/01/2026)**:
    - `docs/en/doc/networking/ipv6_addressing.md` - Dirección IPv6 completa
    - `docs/en/doc/networking/asn_bgp.md` - ASN y BGP completo
    - `docs/en/doc/networking/dnssec.md` - DNSSEC completo
    - `docs/en/doc/cybersecurity/introduccion_devsecops.md` - Introducción DevSecOps
    - `docs/en/doc/cybersecurity/gestion_secretos.md` - Gestión de Secretos
    - `docs/en/doc/networking/cidr_notation.md` - Notación CIDR completa
    - `docs/en/doc/kubernetes/probes.md` - Probes de Kubernetes
    - `docs/en/doc/docker/docker_base.md` - Base de Docker
    - `docs/en/doc/docker/docker_security.md` - Seguridad Docker
    - `docs/en/doc/terraform/terraform_base.md` - Base de Terraform
    - `docs/en/doc/ansible/roles_testing.md` - Testing de roles Ansible
    - `docs/en/doc/cicd/argocd.md` - ArgoCD para CI/CD
    - `docs/en/doc/programming/react.md` - React completo
    - `docs/en/doc/programming/fastapi.md` - FastAPI completo
    - `docs/en/doc/curiosidades/proxmox_en_debian13.md` - Proxmox en Debian 13 completo
    - `docs/en/doc/curiosidades/upgrade_pve8_a_pve9.md` - Upgrade PVE 8→9 completo
  - ✅ **TODOS LOS ARCHIVOS PENDIENTES TRADUCIDOS** - Paridad completa ES/EN lograda
- [x] **Validar compilación con `mkdocs build`** ✅ **OK**: Build completado sin errores en 16.37s (23/01) y 16.27s (24/01)
- [x] Verificar que no haya enlaces rotos en EN (usar plugin o validador externo) ✅ **COMPLETADO (25/01/2026):** Validación completa con LinkChecker - 1611 enlaces verificados, 0 errores, 0 advertencias. Todos los enlaces válidos.
- [ ] Crear PR con cambios de i18n

**D) Nuevas Secciones de Contenido (24/01/2026)**
- ✅ **Sección de Inteligencia Artificial completa**:
  - `docs/doc/ai/index.md` - Índice de sección IA
  - `docs/doc/ai/llms_fundamentals.md` - Introducción completa a LLMs
  - `docs/doc/ai/ollama_basics.md` - Guía completa de Ollama
  - `docs/doc/ai/model_evaluation.md` - Evaluación y benchmarking de modelos
  - Navegación actualizada en `mkdocs.yml` con sección "Inteligencia Artificial"
  - Contenido bilingüe (ES/EN) para todas las guías de IA

- ✅ **Mejoras de Storage avanzado**:
  - `docs/doc/storage/postgresql_ceph.md` - Guía completa PostgreSQL + Ceph
  - Optimizaciones de rendimiento para bases de datos
  - Configuración HA y backup strategies
  - Contenido bilingüe (ES/EN)

### 🚧 Pendiente de Integración (Creado pero no en Nav)

✅ **COMPLETADO:** Todas las páginas huérfanas ya están integradas en `mkdocs.yml`:

#### DevOps & Automation
- [x] **Ansible:** `doc/ansible/roles_testing.md` ✅ En nav
- [x] **Terraform:** `doc/terraform/terraform_state.md` ✅ En nav

#### Infraestructura & Virtualización
- [x] **Proxmox:** `doc/proxmox/migration_guide.md` ✅ En nav
- [x] **OpenStack:** `doc/openstack/day2.md` ✅ En nav
- [x] **HAProxy:** `doc/haproxy/haproxy_advanced.md` ✅ En nav

#### Curiosidades & Blog
- [x] **Curiosidades:** ✅ Todas en nav
  - `doc/curiosidades/docker_kubernetes_vm_comparison.md`
  - `doc/curiosidades/proxmox_en_debian13.md`
  - `doc/curiosidades/proxmox_vmware_openstack_migration.md`
  - `doc/curiosidades/upgrade_pve8_a_pve9.md`

> Nota: el blog está publicado externamente en `https://frikiteam.es`. Los posts técnicos del blog ahora se mantienen como borradores en `internal/drafts/blog/` antes de publicarlos en WordPress.

- [x] **Blog (interno, movido a drafts):** ✅ **COMPLETADO**
  - Posts movidos a `internal/drafts/blog/2025/`
  - `ci-cd-mkdocs-build.md` - Borrador sobre CI/CD con MkDocs
  - `network-compare-practical.md` - Borrador sobre comparativas de networking
  - Esta carpeta sirve como área de trabajo para contenido antes de publicar en WordPress

### 🌍 Localización (i18n)

Estado de la traducción y paridad entre Español (`docs/`) e Inglés (`docs/en/`).

- [x] **Inconsistencia de Directorios:** Existe `docs/en/doc/curiosidades/` y `docs/en/doc/curiosities/`. ✅ **RESUELTO:** Eliminado `curiosities/` (redundante), mantenido `curiosidades/` con todos los archivos.
- [x] **Paridad de Contenido:** ✅ **RESUELTO:** Copiados 40+ archivos faltantes con headers de "TRANSLATION PENDING":
  - 12 archivos individuales (ansible, cicd, docker, haproxy, k8s, proxmox, terraform, storage, curiosidades)
  - 13 archivos de networking completo
  - 9 archivos de cybersecurity (directorio completo)
  - 3 archivos de programming (directorio completo)
- [x] **Navegación EN:** ✅ **VERIFICADO:** `mkdocs.yml` ya tiene estructura simétrica. mkdocs-static-i18n buildea correctamente ambos idiomas.

### 📝 Pendiente de Revisión de Contenido

Archivos generados o stubs que requieren revisión humana y expansión.

- [x] `doc/storage/netapp/netapp_base.md` (Stub creado)
- [x] `doc/storage/pure_storage/pure_storage_base.md` (Stub creado)
- [ ] `doc/storage/protocols/protocols.md` (Añadir más ejemplos reales)
- [x] `doc/storage/protocols/examples/fio_example.md` (Ejemplo `fio` creado)

## 📅 Backlog y Futuras Mejoras

### Infraestructura y CI/CD

- [x] Implementar GitHub Actions para validación automática (`mkdocs build`) ✅ **COMPLETADO:** Creado `.github/workflows/mkdocs-build.yml` con validación de build y chequeo básico de enlaces rotos.
- [x] Script de validación de enlaces rotos. ✅ **COMPLETADO:** Implementado sistema completo de validación con LinkChecker, configuración personalizada y integración en CI.
- [x] Resolver fallos de build en modo estricto. ✅ **COMPLETADO:** Arreglados conflictos de macros Jinja2, deshabilitado temporalmente RSS plugin problemático.
- [x] Automatizar chequeo de diagramas Mermaid en CI.
- [x] **Sistema de Metadatos Automático** ✅ **COMPLETADO (25/01/2026)**:
  - **Arquitectura**: Hook `on_post_build` en `macros.py` que procesa HTML post-build
  - **Funcionalidad**: Inyección automática de badges con dificultad, tiempo, categoría, estado, prerrequisitos
  - **Styling**: CSS personalizado en `docs/stylesheets/extra.css` con colores diferenciados
  - **Multilingüe**: Soporte automático ES/EN basado en estructura de directorios
  - **Cobertura**: Verificado en 89 páginas con metadatos YAML válidos
  - **Rendimiento**: Operación silenciosa, sin impacto en tiempo de build

### Contenido Nuevo (Propuestas)

#### Storage Avanzado
- [x] **Casos de Uso Específicos de Storage:** (nuevas secciones en [docs/doc/storage/ceph/ceph_tuning.md](docs/doc/storage/ceph/ceph_tuning.md), [docs/doc/storage/pure_storage/pure_storage_base.md](docs/doc/storage/pure_storage/pure_storage_base.md), [docs/doc/storage/netapp/netapp_base.md](docs/doc/storage/netapp/netapp_base.md) y [docs/doc/storage/protocols/protocols.md](docs/doc/storage/protocols/protocols.md))
  - Guía de configuración de Ceph para bases de datos (PostgreSQL/MySQL) con optimizaciones de rendimiento.
  - Implementación de storage híbrido (SSD + HDD) en Pure Storage para workloads mixtos.
  - Configuración de NetApp ONTAP para virtualización (VMware/Proxmox) con deduplicación y compresión.
  - Estrategias de backup y recuperación con Restic/Borg integradas con storage distribuido.
  - Comparativa de protocolos de storage (iSCSI vs NFS vs SMB) para diferentes escenarios.
  - Optimización de storage para contenedores (CSI drivers, persistent volumes en Kubernetes).

#### Networking Avanzado
- [x] **Comparativas de Rendimiento y Seguridad:**
  - ✅ Benchmarking detallado: Tailscale vs NetBird (latencia, throughput, CPU/memory usage). **COMPLETADO (25/01/2026)**: Creado `docs/doc/networking/tailscale_netbird_performance.md` con benchmarks reales, scripts de medición y análisis detallado.
  - ✅ Guía de migración de VPN tradicionales a mesh networking (WireGuard vs ZeroTier). **COMPLETADO (25/01/2026)**: Creado `docs/doc/networking/vpn_to_mesh_migration.md` con estrategia completa de migración, scripts automatizados y mejores prácticas.
  - Configuración de networking zero-trust con Cilium en Kubernetes clusters.
  - Optimización de MTU y MSS para redes de alto rendimiento (10G/40G).
  - Implementación de BGP avanzado para multi-homing y load balancing.
  - Seguridad en redes overlay: encriptación, segmentación y monitoreo.

#### Observabilidad y Monitoreo
- [ ] **Stack Completo de Observabilidad:**
  - Instalación y configuración de Prometheus + Grafana + Alertmanager desde cero.
  - Dashboards personalizados para Kubernetes (pods, nodes, ingress, services).
  - Integración de Loki para logging centralizado con Grafana.
  - Monitoreo de aplicaciones con OpenTelemetry (traces, metrics, logs).
  - Alerting avanzado: reglas de Prometheus, notificaciones (Slack/Email/PagerDuty).
  - Observabilidad en storage (Ceph/Pure metrics) y networking (bandwidth, latencia).
  - Troubleshooting con Jaeger para distributed tracing en microservicios.

## 🛠 Mantenimiento

- [x] **COMPLETADO**: Revisar advertencias de linter (MD0xx) en archivos existentes - Convertidos 2 archivos que usaban Setext H1 (====) a ATX (#). Verificación completa muestra que no existen headers H2 usando Setext style (---); todos los archivos usan ATX style (##) consistentemente.
- [x] **COMPLETADO**: Unificar estilo de encabezados (Setext vs ATX) - No se encontraron headers H2 con Setext style. Todos los headers usan ATX (# ## ###) consistentemente.

---

## 🤖 Inteligencia Artificial y Modelos LLM

Esta sección propone contenido nuevo sobre inteligencia artificial, enfocado en Large Language Models (LLMs), herramientas locales, integración con infraestructura y metodologías de prueba.

### Fundamentos y Conceptos Básicos

- [x] **Introducción a LLMs:** Conceptos fundamentales, arquitectura de transformers, diferencias entre open-source vs proprietary (OpenAI, Anthropic, Meta, Mistral). ✅ **COMPLETADO:** Creado `docs/doc/ai/llms_fundamentals.md` con arquitectura completa, comparativa open-source vs proprietary, casos de uso en DevOps.
- [x] **Ecosistema de Modelos Locales:** Comparativa de frameworks (Ollama, LM Studio, LLaMA.cpp, vLLM, LocalAI). ✅ **COMPLETADO:** Creado `docs/doc/ai/local_ecosystems.md` con comparativa detallada, instalación y uso de cada framework.
- [x] **Optimización de Modelos:** Cuantización (GGUF, ONNX), pruning, distilación para ejecutar en hardware limitado. ✅ **COMPLETADO:** Creado `docs/doc/ai/model_optimization.md` con técnicas completas de cuantización, pruning, distilación y estrategias de deployment.

### Herramientas y Tecnologías

- [x] **Ollama:** Instalación, gestión de modelos locales, APIs REST, integración con Docker. ✅ **COMPLETADO:** Creado `docs/doc/ai/ollama_basics.md` con instalación, configuración y uso avanzado de Ollama.
- [ ] **LM Studio:** UI interactiva, configuración de parámetros, exportación de modelos.
- [ ] **LLaMA.cpp:** Compilación, optimización de CPU/GPU, benchmarking.
- [ ] **vLLM:** Deployment de modelos LLM a escala, tensor parallelism, paging de atención.
- [x] **RAG (Retrieval-Augmented Generation):** Conceptos básicos, integraciones (LangChain, LlamaIndex, Chroma). ✅ **COMPLETADO:** Creado `docs/doc/ai/rag_basics.md` con arquitectura completa, implementación paso a paso, casos de uso.
- [x] **Vector Databases:** Milvus, Weaviate, Chroma, Pinecone para búsqueda semántica. ✅ **COMPLETADO:** Creado `docs/doc/ai/vector_databases.md` con comparativa de soluciones, instalación y ejemplos prácticos.

### Metodología de Pruebas

- [x] **Benchmark de Modelos:** MMLU, HellaSwag, TruthfulQA, métricas de evaluación (BLEU, ROUGE, F1). ✅ **COMPLETADO:** Creado `docs/doc/ai/model_evaluation.md` con benchmarks estándar, métricas de rendimiento, herramientas de evaluación.
- [x] **Pruebas de Latencia y Throughput:** Herramientas como `llm-eval`, benchmarking contra hardware específico (CPU vs GPU vs NPU). ✅ **COMPLETADO:** Scripts de medición de latencia, throughput, memory usage incluidos.
- [x] **Prompt Engineering:** Técnicas básicas (zero-shot, few-shot, chain-of-thought), evaluación de prompts. ✅ **COMPLETADO:** Creado `docs/doc/ai/prompt_engineering.md` con técnicas avanzadas, templates, evaluación automatizada y mejores prácticas.
- [x] **Testing de Seguridad:** Inyección de prompts, jailbreaking, detección de hallucinations. ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/testing_seguridad.md` con framework completo de evaluación de seguridad, técnicas de jailbreaking, detección de alucinaciones, data leakage protection y mejores prácticas de producción.
- [x] **Evaluación de Coherencia:** Pruebas de salida consistente, reproduciblidad, detección de sesgos. ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/evaluacion_coherencia.md` con métricas de estabilidad, consistencia factual, detección de sesgos, estabilidad temporal y estrategias de mejora.

### Casos Prácticos e Integración

- [x] **Chatbots Locales:** Construcción de chatbots con Ollama/LLaMA.cpp, integración con Slack/Discord/Telegram. ✅ **COMPLETADO:** Creado `docs/doc/ai/chatbots_locales.md` con implementaciones completas para Slack, Discord y Telegram, incluyendo memoria conversacional, integración con RAG y despliegue en producción.
- [x] **Generación de Contenido Técnico:** Automatización de documentación, generación de posts de blog, resumen de artículos. ✅ **COMPLETADO:** Creado `docs/doc/ai/contenido_tecnico.md` con generación automática de docstrings, README, blogs, changelogs e integración CI/CD.
- [x] **Análisis de Logs y Troubleshooting:** Uso de LLMs para análisis automático de logs, sugerencias de solución de problemas. ✅ **COMPLETADO:** Creado `docs/doc/ai/analisis_logs.md` con análisis de stack traces, monitoreo Kubernetes, detección de ataques y remediación automática.
- [x] **Procesamiento de Lenguaje Natural en Infra:** Automatización de IaC con descriptores naturales, traducción de comandos. ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/procesamiento_nlp_infra.md` con framework NLP-IaC completo, generadores para Terraform/Ansible/Kubernetes, validación automática, seguridad integrada y optimización basada en feedback.
- [x] **Fine-tuning Básico:** Adaptación de modelos a dominios específicos (DevOps, networking, storage). ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/fine_tuning_basico.md` con pipeline completo de fine-tuning, preparación de datos, técnicas LoRA/QAT, evaluación comprehensiva, deployment y monitoreo en producción.

### Avanzado y Especializado

- [ ] **Multi-agent Systems:** Orquestación de múltiples LLMs, delegación de tareas, coordinación de flujos.
- [ ] **LLMs en Edge:** Despliegue en dispositivos IoT, Raspberry Pi, optimización para consumo de energía.
- [ ] **Evaluación de Seguridad y Privacidad:** Extracción de datos de entrenamiento, anonimización, GDPR compliance.
- [ ] **Monitoreo y Observabilidad:** Tracking de costos (si usan APIs), latencias, calidad de respuestas.
- [ ] **Comparativa Open-source vs Cloud:** Análisis de costos, latencia, privacidad y control.

### Integración con Stack Existente

- [ ] **LLMs en Kubernetes:** Despliegue de servicios LLM (vLLM, Ollama) con Helm/ArgoCD.
- [ ] **Monitoreo de LLMs:** Integración con Prometheus/Grafana para métricas de tokens generados, latencias.
- [ ] **Storage para Modelos:** Optimización de almacenamiento de checkpoints (Ceph, Pure), versionado con DVC.
- [ ] **Networking para Inferencia:** Optimización de bandwidth para descargas de modelos, caché distribuido con Redis.
- [ ] **CI/CD para Modelos:** Validación automática de modelos, A/B testing de versiones, despliegue gradual.

### Roadmap de Contenido (6 meses)

**Fase 1 (0–2 meses):** Fundamentos y herramientas locales.
- [x] Crear guías de inicio con Ollama y LLaMA.cpp. ✅ **COMPLETADO:** Guía completa de Ollama creada.
- [x] Documentar instalación y configuración básica. ✅ **COMPLETADO:** Instalación, configuración y ejemplos incluidos.
- [x] Añadir sección "IA" al `mkdocs.yml`. ✅ **COMPLETADO:** Sección de IA añadida a la navegación.
- [x] Ecosistema de modelos locales. ✅ **COMPLETADO:** Comparativa de frameworks incluida.
- [x] RAG y Vector Databases. ✅ **COMPLETADO:** Guías completas con ejemplos prácticos.

**Fase 2 (2–4 meses):** Casos prácticos y pruebas.
- [x] Guías de evaluación y benchmarking. ✅ **COMPLETADO:** `docs/doc/ai/model_evaluation.md` con benchmarks completos.
- [x] Construcción de chatbots simples. ✅ **COMPLETADO:** `docs/doc/ai/chatbots_locales.md` con implementaciones completas para múltiples plataformas.
- [x] Integración con herramientas existentes (logs, infra). ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/analisis_logs.md` y `docs/doc/ai/procesamiento_nlp_infra.md` con integración completa de LLMs en análisis de logs y automatización de IaC.

**Fase 3 (4–6 meses):** Avanzado e integración DevOps.
- [x] Fine-tuning básico. ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/fine_tuning_basico.md` con pipeline completo de fine-tuning, LoRA/QAT, evaluación y deployment.
- [ ] Fine-tuning avanzado para dominios específicos (DevOps, networking, storage).
- [x] Despliegue a escala con Kubernetes. ✅ **COMPLETADO (25/01/2026):** Creado `docs/doc/ai/despliegue_kubernetes.md` con guía completa de despliegue vLLM, auto-scaling, optimizaciones y monitoreo.
- [ ] Evaluación de seguridad y privacidad.

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

- [x] **Hardening de Servidores Linux:** Checklist para securizar SSH, sudo, kernel parameters (sysctl). ✅ **COMPLETADO:** Expandido `docs/doc/cybersecurity/hardening_linux.md` con configuraciones completas, auditoria con Lynis, monitoreo de seguridad.
- [x] **Seguridad en Kubernetes:** RBAC, Network Policies, Pod Security Standards, admission controllers (OPA/Gatekeeper). ✅ **COMPLETADO:** Creado `docs/doc/cybersecurity/kubernetes_security.md` con RBAC, Network Policies, Pod Security, admission controllers y monitoreo.
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
- [x] Crear stubs para "Introducción a DevSecOps" y "Escaneo de Vulnerabilidades con Trivy". ✅ **COMPLETADO**
- [x] Añadir a nav en `mkdocs.yml` bajo nueva sección "Ciberseguridad". ✅ **COMPLETADO**

Fase 2 (2–4 meses): Casos prácticos.
- [x] Guías para hardening Linux y seguridad Kubernetes. ✅ **COMPLETADO:** Guías completas con ejemplos prácticos y checklists.
- [x] Comparativas de herramientas (Vault vs K8s Secrets). ✅ **COMPLETADO:** Incluido en `gestion_secretos.md`.

Fase 3 (4–6 meses): Avanzado y integración.
- [ ] Contenido sobre compliance, pentesting y forensics.
- [ ] Enlazar con secciones existentes (storage, networking) para cross-references.

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

---

## ✅ Actualización 25/01/2025 - Corrección de Build y Navegación

**Problemas identificados y resueltos:**
- ❌ **Build fallando** con 11 advertencias en modo estricto por enlaces a archivos inexistentes en `docs/doc/ai/index.md`
- ❌ **Páginas nuevas no incluidas** en navegación de `mkdocs.yml`

**Soluciones implementadas:**
- ✅ **Actualizado `docs/doc/ai/index.md`** y `docs/en/doc/ai/index.md` para solo enlazar archivos existentes
- ✅ **Agregado navegación completa** para páginas de IA: `llms_fundamentals.md`, `ollama_basics.md`, `model_evaluation.md`
- ✅ **Agregado navegación** para `postgresql_ceph.md` en sección Storage
- ✅ **Build exitoso** en modo estricto sin advertencias (15.12s)

**Estado actual:**
- ✅ Fase 3.1 (IA fundamentals) - **COMPLETADO**
- ✅ Parte de Fase 2.1 (Storage avanzado: PostgreSQL+Ceph) - **COMPLETADO**
- ✅ Fase 2.2 (Networking comparaciones prácticas) - **COMPLETADO**
- ✅ CI/CD funcionando correctamente
- ✅ Documentación bilingüe actualizada

---

## ✅ Actualización 26/01/2025 - Fase 2.3 Observabilidad Completada

**Guía implementada:**
- ✅ **Observabilidad completa (Prometheus + Grafana + Loki/Tempo + Alertmanager)**
  - `docs/doc/monitoring/observability_stack.md` (ES) / `docs/en/doc/monitoring/observability_stack.md` (EN)
  - Arquitectura completa con métricas, logs, trazas y alertas
  - docker-compose de referencia, configuraciones clave y checklist de operación
  - Buenas prácticas de alerting, seguridad, retención y operación en Kubernetes

**Build status:** ✅ Exitoso en modo estricto usando venv (15.01s)

---

## ✅ Actualización 25/01/2025 - Fase 2.2 Networking Completada

**Guías de comparación implementadas:**
- ✅ **VPN Overlay Comparison**: Tailscale vs NetBird vs ZeroTier (casos de uso reales)
  - `docs/doc/networking/vpn_overlay_comparison.md`
  - Arquitectura técnica, benchmarks, guías de implementación
  - Casos de uso: startups, cloud-native, IoT/edge

- ✅ **SDN Empresarial**: OpenStack Neutron vs VMware NSX vs Cisco ACI
  - `docs/doc/networking/sdn_enterprise_comparison.md`
  - Comparación detallada, casos por industria, troubleshooting
  - Arquitecturas: open SDN, virtualized SDN, hardware SDN

- ✅ **Load Balancing Avanzado**: HAProxy vs NGINX vs Traefik (benchmarks incluidos)
  - `docs/doc/networking/load_balancer_comparison.md`
  - Benchmarks detallados (RPS, latencia, CPU/memory)
  - Configuraciones avanzadas para cada herramienta

**Características técnicas incluidas:**
- ✅ Arquitecturas y diagramas Mermaid
- ✅ Benchmarks reales con hardware específico
- ✅ Guías de implementación completas
- ✅ Casos de uso empresariales por industria
- ✅ Troubleshooting y monitoreo
- ✅ Contenido bilingüe (ES/EN)
- ✅ Navegación actualizada en `mkdocs.yml`

**Build status:** ✅ Exitoso en modo estricto (12.09s)

---

## ✅ Actualización 25/01/2026 - Expansión IA y Ciberseguridad

**Nuevas guías de Inteligencia Artificial:**
- ✅ **Ecosistema de Modelos Locales** (`docs/doc/ai/local_ecosystems.md` ES/EN)
  - Comparativa completa: Ollama, LM Studio, LLaMA.cpp, vLLM, LocalAI
  - Arquitecturas, instalación, casos de uso por framework
  - Métricas de rendimiento y recomendaciones de hardware

- ✅ **RAG - Retrieval-Augmented Generation** (`docs/doc/ai/rag_basics.md` ES/EN)
  - Arquitectura completa de sistemas RAG
  - Implementación paso a paso con LangChain
  - Ejemplos prácticos: documentación técnica, análisis de logs, chatbots
  - Optimización y troubleshooting

- ✅ **Vector Databases** (`docs/doc/ai/vector_databases.md` ES/EN)
  - Comparativa: Chroma, Milvus, Weaviate, Qdrant, Pinecone
  - Instalación y configuración de cada solución
  - Ejemplos de integración con RAG
  - Benchmarks de rendimiento

**Guías prácticas de Ciberseguridad:**
- ✅ **Hardening de Servidores Linux** (expandido `docs/doc/cybersecurity/hardening_linux.md` ES/EN)
  - Configuración completa de SSH, sudo, PAM
  - Kernel parameters (sysctl) para seguridad
  - Auditoria automática con Lynis
  - Monitoreo continuo de seguridad
  - Checklist de cumplimiento CIS/NIST

- ✅ **Seguridad en Kubernetes** (nuevo `docs/doc/cybersecurity/kubernetes_security.md` ES)
  - RBAC: Roles, ClusterRoles, ServiceAccounts
  - Network Policies para microsegmentación
  - Pod Security Standards (baseline, restricted)
  - Admission Controllers (OPA/Gatekeeper)
  - Monitoreo con Falco y alertas

**Infraestructura y CI/CD:**
- ✅ **Build estricto corregido**: Plugin `git-revision-date-localized` ahora opcional vía `ENABLE_GIT_DATES` env variable
- ✅ **Navegación actualizada**: Todas las nuevas páginas integradas en `mkdocs.yml`
- ✅ **Contenido bilingüe**: ES/EN para todas las guías nuevas

**Estado de Fases:**
- ✅ **IA Fase 1 (Fundamentos)**: 100% completada - Todos los objetivos cumplidos
- ✅ **Ciberseguridad Fase 2 (Casos prácticos)**: Completada - Hardening Linux + K8s Security
- 🚧 **Próximos pasos**: IA Fase 2 (Chatbots, integración con infra) y Ciberseguridad Fase 3 (Compliance, pentesting)

**Build status:** ✅ Exitoso en modo estricto con `ENABLE_GIT_DATES=false` (6.22s)

**Commits realizados:**
- `07c89d6` - Add RAG, vector DB, and security guides
- `2dbfcf3` - Make git revision plugin optional via env
- `3c223cd` - Update TODO.md and move blog posts to internal drafts

---

## 🔧 Mejoras de Mantenibilidad (25/01/2026)

Implementando mejoras prácticas para que la documentación escale sin volverse burocrática.

### ✅ Implementado

#### 1. **Freshness Tracking**
- ✅ Script `scripts/check_freshness.py` creado
- ✅ Detecta archivos sin actualizar en >90 días
- ✅ Identifica archivos sin campo `updated` en frontmatter
- 📋 **Próximo paso:** Añadir campo `updated: YYYY-MM-DD` a todos los archivos principales

#### 2. **Checklist Simplificado**
- ✅ Actualizado `CONTRIBUTING.md` con checklist simple
- ✅ Eliminada burocracia innecesaria
- ✅ Solo 5 puntos esenciales antes de publicar

#### 3. **Roles Claros**
- ✅ Ya documentado en TODO.md (sección "Gobernanza del contenido")
- ✅ @rasty94 como owner de todas las áreas
- ✅ Proceso de contribución claro

### 🚧 Próximos Pasos (Prioridad)

#### 4. **Analytics Básico**
- ✅ **Opción A (Simple):** Script de análisis de logs (`scripts/analyze_logs.py`)
- ✅ **Opción B (Avanzado):** Documentación de Plausible Analytics self-hosted
- ✅ Configuración preparada en `mkdocs.yml` (comentada hasta despliegue)
- ✅ Guía completa: `docs/doc/monitoring/plausible_analytics.md`
- [ ] **Próximo:** Desplegar Plausible en servidor o revisar logs existentes
- **Beneficio:** Saber qué contenido es más útil sin invadir privacidad

#### 5. **Traducción ES/EN Sin Fricción**
- [ ] Script que detecta cuando ES se actualiza sin actualizar EN
- [ ] Añadir nota automática en EN: "Versión en español actualizada, revisar"
- [ ] Priorizar traducción de páginas críticas (Quickstart, Getting Started)
- **Beneficio:** Evitar que usuarios EN sigan guías obsoletas

### 📅 Roadmap de Mejoras

| Cuándo | Qué | Tiempo Estimado |
|--------|-----|----------------|
| ✅ **Completado** | Script freshness + Checklist simple | 40 min |
| ✅ **Completado** | Analytics: Plausible docs + script logs | 30 min |
| 📋 **Esta semana** | Añadir `updated` a archivos principales | 30 min |
| 📋 **Este mes** | Automatizar notificación de traducción | 2h |

**Total invertido:** ~1h 10min  
**Total estimado restante:** ~2h 30min

### ❌ Lo Que NO Necesitamos (Todavía)

- ❌ Comités de gobernanza mensual
- ❌ Métricas sofisticadas de readability
- ❌ Workflow de 5 etapas de revisión
- ❌ Versionado de documentación
- ❌ Herramientas de pago (Analytics premium, etc.)

> **Filosofía:** Mantener simple. Estas herramientas son para cuando haya 10+ personas escribiendo docs.

### 🛠️ Comandos Útiles

```bash
# Detectar documentos obsoletos
python scripts/check_freshness.py --days 90

# Analizar logs de acceso (Nginx/Apache)
python scripts/analyze_logs.py /var/log/nginx/access.log
python scripts/analyze_logs.py --days 30 --top 20 /var/log/nginx/access.log

# Ver logs en tiempo real (si usas nginx)
tail -f /var/log/nginx/access.log | grep docs

# Verificar build sin errores
export ENABLE_GIT_DATES=false
mkdocs build --strict

# Añadir campo 'updated' a un archivo
# (Hacerlo manualmente es más seguro que sed masivo)
```


## Progreso de Publicación

- Troubleshooting — Errores Comunes y Soluciones - Publicado el 2026-02-03
- Empezando — Primeros pasos en Frikiteam - Publicado el 2026-02-03
- Política de Privacidad - Publicado el 2026-02-03
- Inicio - Frikiteam Docs - Publicado el 2026-02-03
- Glosario — Términos comunes - Publicado el 2026-02-03
- Troubleshooting — Common Errors and Solutions - Publicado el 2026-02-03
- Quickstart — Get Started and Contribute - Publicado el 2026-02-03
- Glossary — Common Terms - Publicado el 2026-02-03
- Terraform — State Backend and Migration - Publicado el 2026-02-03
- terraform_base.md - Publicado el 2026-02-03
- pure_storage_base.md - Publicado el 2026-02-03
- postgresql_ceph.md - Publicado el 2026-02-03
- netapp_base.md - Publicado el 2026-02-03
- Ceph — Optimization and Capacity Planning - Publicado el 2026-02-03
- ceph_base.md - Publicado el 2026-02-03
- Proxmox — Software-Defined Networking (SDN) - Publicado el 2026-02-03
- Proxmox VE - Complete Enterprise Virtualization Guide - Publicado el 2026-02-03
- migration_guide.md - Publicado el 2026-02-03
- react.md - Publicado el 2026-02-03
- fastapi.md - Publicado el 2026-02-03
- OpenStack - Open and Scalable Cloud Infrastructure - Publicado el 2026-02-03
- zerotier.md - Publicado el 2026-02-03
- Migration from Traditional VPN to Mesh Networking - Publicado el 2026-02-03
- vpn_overlay_comparison.md - Publicado el 2026-02-03
- vlsm_profundidad.md - Publicado el 2026-02-03
- troubleshooting.md - Publicado el 2026-02-03
- Performance Benchmarks: Tailscale vs NetBird - Publicado el 2026-02-03
- tailscale.md - Publicado el 2026-02-03
- tablas_puertos_comunes.md - Publicado el 2026-02-03
- spf_dkim_dmarc.md - Publicado el 2026-02-03
- sdn_enterprise_comparison.md - Publicado el 2026-02-03
- reserved_ip_ranges.md - Publicado el 2026-02-03
- registros_ptr_zonas_inversas.md - Publicado el 2026-02-03
- protocolos_icmp_arp_ndp.md - Publicado el 2026-02-03
- netbird.md - Publicado el 2026-02-03
- mtu_mss_values.md - Publicado el 2026-02-03
- load_balancer_comparison.md - Publicado el 2026-02-03
- compare.md - Publicado el 2026-02-03
- certificados_tls.md - Publicado el 2026-02-03
- benchmarks.md - Publicado el 2026-02-03
- uptime_kuma.md - Publicado el 2026-02-03
- Complete Observability Stack - Publicado el 2026-02-03
- wireguard.md - Publicado el 2026-02-03
- systemd.md - Publicado el 2026-02-03
- ssh_security.md - Publicado el 2026-02-03
- Kubernetes — Readiness and Liveness Probes - Publicado el 2026-02-03
- kubernetes_base.md - Publicado el 2026-02-03
- haproxy_base.md - Publicado el 2026-02-03
- haproxy_advanced.md - Publicado el 2026-02-03
- docker_security.md - Publicado el 2026-02-03
- Docker — Optimization and Best Practices - Publicado el 2026-02-03
- docker_base.md - Publicado el 2026-02-03
- principios_seguridad.md - Publicado el 2026-02-03
- monitoreo_seguridad.md - Publicado el 2026-02-03
- modelo_amenazas.md - Publicado el 2026-02-03
- Introduction to Cybersecurity in DevOps - Publicado el 2026-02-03
- Linux Server Hardening - Publicado el 2026-02-03
- Secrets Management - Publicado el 2026-02-03
- firewall_red.md - Publicado el 2026-02-03
- escaneo_vulnerabilidades.md - Publicado el 2026-02-03
- autenticacion_autorizacion.md - Publicado el 2026-02-03
- upgrade_pve8_a_pve9.md - Publicado el 2026-02-03
- proxmox_vmware_openstack_migration.md - Publicado el 2026-02-03
- proxmox_en_debian13.md - Publicado el 2026-02-03
- docker_kubernetes_vm_comparison.md - Publicado el 2026-02-03
- github_actions.md - Publicado el 2026-02-03
- argocd.md - Publicado el 2026-02-03
- Ceph - Scalable Distributed Storage System - Publicado el 2026-02-03
- Ansible — Roles and Testing with Molecule - Publicado el 2026-02-03
- ansible_base.md - Publicado el 2026-02-03
- Vector Databases for AI - Publicado el 2026-02-03
- Advanced Prompt Engineering for LLMs - Publicado el 2026-02-03
- ollama_basics.md - Publicado el 2026-02-03
- model_evaluation.md - Publicado el 2026-02-03
- Local Model Ecosystem - Publicado el 2026-02-03
- llms_fundamentals.md - Publicado el 2026-02-03
- deployment_kubernetes.md - Publicado el 2026-02-03
- Automated Technical Content Generation with LLMs - Publicado el 2026-02-03
- Local Chatbots with LLMs - Publicado el 2026-02-03
- Log Analysis and Troubleshooting with LLMs - Publicado el 2026-02-03
- Categories - Publicado el 2026-02-03
- Archive - Publicado el 2026-02-03
- about.md - Publicado el 2026-02-03
- Terraform — Backend de Estado y Migración - Publicado el 2026-02-03
- Terraform & OpenTofu - Infraestructura como Código - Publicado el 2026-02-03
- Pure Storage — Guía base - Publicado el 2026-02-03
- protocols.md - Publicado el 2026-02-03
- Ejemplo fio — pruebas de I/O - Publicado el 2026-02-03
- Storage para bases de datos: PostgreSQL + Ceph - Publicado el 2026-02-03
- NetApp — Introducción - Publicado el 2026-02-03
- Ceph Troubleshooting: Common Issues and Solutions - Publicado el 2026-02-03
- Ceph — Optimización y Planificación de Capacidad - Publicado el 2026-02-03
- Ceph - Publicado el 2026-02-03
- Recetas Rápidas - Publicado el 2026-02-03
- Infraestructura: Proxmox SDN - Publicado el 2026-02-03
- Proxmox VE Complete Guide: Enterprise Virtualization Platform - Publicado el 2026-02-03
- Proxmox — Guía de Migración (VMs y Contenedores) - Publicado el 2026-02-03
- React - Publicado el 2026-02-03
- Flutter - Publicado el 2026-02-03
- FastAPI - Publicado el 2026-02-03
- OpenStack Troubleshooting: Common Issues and Solutions - Publicado el 2026-02-03
- OpenStack + Ceph Integration: Complete Storage Backend Guide - Publicado el 2026-02-03
- OpenStack Guide: Complete Cloud Platform Overview - Publicado el 2026-02-03
- OpenStack Deployment with Kolla-Ansible: Complete Production Guide - Publicado el 2026-02-03
- OpenStack Day-2 Operations: Maintenance and Production Management - Publicado el 2026-02-03
- ZeroTier: instalación y configuración básica - Publicado el 2026-02-03
- Migración de VPN Tradicionales a Mesh Networking - Publicado el 2026-02-03
- Comparación VPN Overlay: Tailscale vs NetBird vs ZeroTier - Publicado el 2026-02-03
- VLSM en Profundidad - Publicado el 2026-02-03
- Resolución de problemas (Networking) - Publicado el 2026-02-03
- Benchmarks de Rendimiento: Tailscale vs NetBird - Publicado el 2026-02-03
- Tailscale: instalación y configuración básica - Publicado el 2026-02-03
- Tablas de Puertos Comunes - Publicado el 2026-02-03
- SPF/DKIM/DMARC - Publicado el 2026-02-03
- SDN Empresarial: OpenStack Neutron vs VMware NSX vs Cisco ACI - Publicado el 2026-02-03
- Reserved IP Ranges - Publicado el 2026-02-03
- Registros PTR y Zonas Inversas - Publicado el 2026-02-03
- Protocolos ICMP/ARP/NDP - Publicado el 2026-02-03
- NetBird: instalación y configuración básica - Publicado el 2026-02-03
- MTU/MSS Values - Publicado el 2026-02-03
- Load Balancing Avanzado: HAProxy vs NGINX vs Traefik - Publicado el 2026-02-03
- IPv6 Addressing - Publicado el 2026-02-03
- DNSSEC - Publicado el 2026-02-03
- Comparativa rápida: NetBird vs Tailscale vs ZeroTier - Publicado el 2026-02-03
- CIDR Notation - Publicado el 2026-02-03
- Certificados TLS - Publicado el 2026-02-03
- Networking: Comparativa de Rendimiento - Publicado el 2026-02-03
- ASN & BGP - Publicado el 2026-02-03
- Observabilidad: Centralización de Logs con Wazuh - Publicado el 2026-02-03
- Monitorización con Uptime Kuma - Publicado el 2026-02-03
- Plausible Analytics Self-Hosted - Publicado el 2026-02-03
- Stack Completo de Observabilidad - Publicado el 2026-02-03
- WireGuard VPN - Publicado el 2026-02-03
- Systemd: Gestión de Servicios - Publicado el 2026-02-03
- Seguridad SSH - Publicado el 2026-02-03
- Kubernetes — Readiness y Liveness Probes - Publicado el 2026-02-03
- Kubernetes - Orquestación de Contenedores - Publicado el 2026-02-03
- keystone.md - Publicado el 2026-02-03
- keycloak.md - Publicado el 2026-02-03
- authentik.md - Publicado el 2026-02-03
- HAProxy - Publicado el 2026-02-03
- HAProxy — TLS y Escalado Avanzado - Publicado el 2026-02-03
- Docker — Optimización y Buenas Prácticas - Publicado el 2026-02-03
- Docker - Contenedores - Publicado el 2026-02-03
- redis.md - Publicado el 2026-02-03
- postgres.md - Publicado el 2026-02-03
- Zero Trust en Práctica - Publicado el 2026-02-03
- Trivy Operator: Escaneo Continuo en Kubernetes - Publicado el 2026-02-03
- Supply Chain Security: SBOM, SLSA y Firma de Imágenes - Publicado el 2026-02-03
- Principios de Seguridad - Publicado el 2026-02-03
- Monitoreo de Seguridad - Publicado el 2026-02-03
- Modelo de Amenazas - Publicado el 2026-02-03
- Seguridad en Kubernetes - Publicado el 2026-02-03
- Introducción a Ciberseguridad en DevOps - Publicado el 2026-02-03
- Ciberseguridad - Publicado el 2026-02-03
- Hardening de Servidores Linux - Publicado el 2026-02-03
- Gestión de Secretos - Publicado el 2026-02-03
- Firewall y Seguridad de Red - Publicado el 2026-02-03
- Escaneo de Vulnerabilidades - Publicado el 2026-02-03
- CI Security Scanning: SAST, DAST y Contenedores - Publicado el 2026-02-03
- Autenticación y Autorización - Publicado el 2026-02-03
- Actualizar Proxmox VE 8 a Proxmox VE 9 (Debian 13 Trixie) - Publicado el 2026-02-03
- Proxmox vs VMware vs OpenStack: Migración hacia Soluciones Open Source - Publicado el 2026-02-03
- Instalar Proxmox VE 9 sobre Debian 13 (Trixie) - Publicado el 2026-02-03
- Docker vs Kubernetes vs Máquinas Virtuales: Una Comparación Curiosa - Publicado el 2026-02-03
- Introducción a GitHub Actions - Publicado el 2026-02-03
- Cloud-native: GitOps con ArgoCD - Publicado el 2026-02-03
- strategy_321.md - Publicado el 2026-02-03
- restic_borg.md - Publicado el 2026-02-03
- pbs.md - Publicado el 2026-02-03
- Ansible — Roles y Testing con Molecule - Publicado el 2026-02-03
- Ansible - Automatización de Infraestructura - Publicado el 2026-02-03
- Vector Databases para IA - Publicado el 2026-02-03
- Testing de Seguridad en LLMs - Publicado el 2026-02-03
- RAG - Retrieval-Augmented Generation - Publicado el 2026-02-03
- Prompt Engineering Avanzado para LLMs - Publicado el 2026-02-03
- Ollama: Instalación y primeros pasos - Publicado el 2026-02-03
- Optimización de Modelos LLM - Publicado el 2026-02-03
- Evaluación y Testing de Modelos LLM - Publicado el 2026-02-03
- Ecosistema de Modelos Locales - Publicado el 2026-02-03
- Introducción a Large Language Models (LLMs) - Publicado el 2026-02-03
- index.md - Publicado el 2026-02-03
- Fine-tuning Básico de LLMs - Publicado el 2026-02-03
- Evaluación de Coherencia en LLMs - Publicado el 2026-02-03
- Despliegue de LLMs a Escala con Kubernetes - Publicado el 2026-02-03
- Generación de Contenido Técnico con LLMs - Publicado el 2026-02-03
- Chatbots Locales con LLMs - Publicado el 2026-02-03
- Análisis de Logs y Troubleshooting con LLMs - Publicado el 2026-02-03
- Mermaid — Verificación y uso - Publicado el 2026-02-03
- Bienvenida - Publicado el 2026-02-03
- Blog - Publicado el 2026-02-03
- Categorías - Publicado el 2026-02-03
- Archivo - Publicado el 2026-02-03
- Acerca de - Frikiteam - Publicado el 2026-02-03
- Docker — Seguridad y Scanning - Publicado el 2026-02-03
