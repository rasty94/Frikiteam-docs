# Changelog

Todos los cambios relevantes en el repositorio.

> Generado con `python scripts/generate_changelog.py`. No editar a mano.

## 2026-10-11

- `ce248b8` docs(todo): registrar que todo lo publicado cita fuente (2 archivos)
- `7e3276a` docs: fuente primaria para cada afirmación pendiente y referencias completas (ES/EN) (40 archivos)
- `8a8f3a9` docs: fuentes referenciadas en todas las páginas (ES/EN) (176 archivos)
- `4150e5f` feat(ci): validate_metadata exige una sección de referencias con fuentes externas (1 archivo)
- `0b55171` docs: regenerar CHANGELOG hasta el cierre del 2026-10-11 (1 archivo)
- `720844b` docs(todo): segunda pasada de verificación y diagnóstico de analisis_logs (2 archivos)
- `7af59e8` docs: Keystone audita con notificaciones CADF, no con una sección [audit]; aviso de ssh.socket en Ubuntu 24.04+ (4 archivos)
- `33a5648` docs(todo): registrar la verificación del 2026-10-11 y dejar solo lo que no tuvo fuente (2 archivos)
- `1a07e0a` docs: verificar 40 páginas contra la documentación oficial (ES/EN) (78 archivos)
- `108ac4d` chore(meta): recalcular estimated_time con la fórmula del proyecto en 72 parejas (143 archivos)
- `520894f` docs: quitar de ocho páginas de IA la cita que repetía a mano tiempo, dificultad y categoría (16 archivos)
- `1a28e7f` feat(ci): validate_metadata comprueba y recalcula estimated_time (2 archivos)
- `2ed4788` docs(todo): cerrar el roadmap del 2026-10-11 y anotar la deuda de verificación (2 archivos)
- `e90b543` chore(meta): igualar updated, last_reviewed y tags entre gemelas ES/EN (43 archivos)
- `e58e11a` docs: traducir 17 páginas EN que seguían en español y corregir errores en ambos idiomas (23 archivos)
- `6dcec76` docs: DNS propio, k3s con cert-manager, eBPF/Cilium, backup de Kubernetes y forense (ES/EN) (15 archivos)
- `c002296` feat(ci): detectar EN sin traducir y exigir paridad de tags y fechas (2 archivos)
- `5f3b969` docs(todo): cerrar ZFS y LVM y anotar sus puntos a verificar (2 archivos)
- `4d814f6` docs: ZFS y LVM en almacenamiento local (ES/EN) (5 archivos)
- `d18e726` docs(todo): roadmap de contenido revisado contra el repo el 2026-10-11 (1 archivo)
- `ad0340b` docs(todo): estado de graphify tras actualizar a 0.9.85 (1 archivo)

## 2026-10-10

- `f6bb657` docs(todo): cerrar páginas cortas y frontmatter EN; anotar la deuda de verificación (2 archivos)
- `1f231ef` chore(meta): completar description, keywords, prerequisites y last_reviewed en las gemelas EN (55 archivos)
- `f97c551` docs: ampliar dieciséis guías cortas a documentación completa (ES/EN) (34 archivos)
- `aa05e04` feat(ci): validate_metadata exige en EN los campos espejo de su ES (1 archivo)
- `34a55f2` docs(todo): recuento del 2026-10-10 y estado del grafo (2 archivos)
- `c31b584` fix: el test de enhance simula la ausencia de INFERENCE_SERVERS (1 archivo)

## 2026-09-03

- `f03756f` docs(todo): registrar el cierre de la asimetría y la limpieza de metadatos (2 archivos)
- `b14c3f9` feat(ci): la asimetría ES/EN pasa de aviso a fallo (2 archivos)
- `e781209` docs: igualar las cinco parejas ES/EN asimétricas (10 archivos)
- `bcf560a` chore(meta): retirar date y draft: false del frontmatter (103 archivos)
- `450fb23` docs: verificar las métricas de vLLM y las imágenes de TheHive (6 archivos)
- `7917e15` docs: actualizar .gitignore para incluir CLAUDE.md y añadir sección sobre graphify en CLAUDE.md (2 archivos)
- `870fea2` docs: añadir CLAUDE.md con las convenciones del repositorio (1 archivo)
- `e331f55` feat: hacer que draft: true excluya la página del sitio (10 archivos)
- `a7d868d` docs(todo): actualizar el roadmap al estado real del repositorio (1 archivo)
- `3de2fa4` docs: corregir la descripción del fallo de macros en Novedades y done.md (3 archivos)
- `6042a99` chore(meta): corregir estimated_time y detectar asimetría ES/EN (3 archivos)
- `1db26d4` docs: completar los tres stubs restantes (ES/EN) (34 archivos)
- `0c33244` docs: convertir diez stubs en documentación completa (ES/EN) (34 archivos)

## 2026-09-02

- `5f56033` feat(ci): validar tags, categorías y sincronía ES/EN en CI (8 archivos)
- `6fe3b73` chore(meta): normalizar vocabulario de tags y categorías en ES/EN (263 archivos)

## 2026-08-03

- `24bbf0e` docs(wordpress): registrar los 19 posts sincronizados como borrador (1 archivo)
- `e2cc1cf` docs(linux): añadir nftables+fail2ban, Bash con APIs REST y monitorización en terminal (ES/EN) (9 archivos)
- `1119d93` docs(podman): añadir guía de Quadlet y ciclo de vida de contenedores (ES/EN) (7 archivos)
- `f32321c` docs(traefik): añadir guía base del proxy inverso (ES/EN) (5 archivos)

## 2026-07-31

- `7741959` fix(scripts): validar metadatos también en el árbol EN (1 archivo)
- `bebe663` fix(docs): rellenar metadatos del árbol EN desde el espejo ES (83 archivos)
- `5d8d497` fix(docs): reparar benchmarks.md del árbol EN (1 archivo)
- `8511d37` fix(docs): completar metadatos faltantes del árbol ES (13 archivos)

## 2026-07-25

- `f7d13ef` docs: separar historial completado (done.md) del roadmap pendiente (TODO.md) (5 archivos)
- `4e02791` chore: eliminar código muerto y sanear configuración del sitio (24 archivos)
- `1a38d92` fix: eliminar fallback de credenciales hardcodeadas en constants.py (2 archivos)

## 2026-07-20

- `86b6f62` chore: estudio.md es un documento de trabajo local (1 archivo)
- `dfd3bca` ci: unificar los dos workflows en docs-ci.yml (3 archivos)
- `4fe528c` feat: Cloudflare Web Analytics en todas las páginas (2 archivos)

## 2026-07-19

- `1296b21` feat: log de proceso en logs/ para cada ejecución de wordpress_sync (2 archivos)
- `c0dbb4b` fix: wordpress_sync excluye índices, glosario y páginas de navegación (1 archivo)
- `d19358f` fix: wordpress_sync solo sube contenido en español (1 archivo)
- `0338354` chore: registrar en TODO.md los 8 borradores creados por wordpress_sync (1 archivo)
- `7d17a88` docs: registrar novedades del 19/07 en la portada (ES/EN) (2 archivos)
- `aa9221e` fix: casar títulos texturizados de WordPress y evitar duplicados (1 archivo)
- `b1a014f` docs: Podman rootless, PostgreSQL HA, Criptografía Aplicada y Pentesting Básico (12 archivos)
- `43dc3b3` feat: sincronización incremental en wordpress_sync.py (2 archivos)
- `e0c69ad` fix(ai): corregir tres errores de despliegue_kubernetes.md (2 archivos)
- `21a01fd` docs: paquetes A y B — cierre de Ciberseguridad Fase 3 e IA en produccion (16 archivos)
- `814e436` docs: cerrar la deuda de i18n en TODO.md tras verificarla con los scripts (1 archivo)
- `b8bad36` fix: detectar la introducción cuando vive dentro de la primera sección (2 archivos)
- `934e154` fix: el mensaje de inicio mostraba una variable que ya no se usa (1 archivo)
- `5e737ef` feat: cadena de servidores de inferencia y reescritura de documento completo (3 archivos)
- `9f9d509` chore: configuración en .env, sin URLs de infraestructura en el código (3 archivos)
- `48ccb8c` fix: --enhance reescribe solo la introducción, no el documento entero (3 archivos)
- `314e8b1` feat: --file actualiza el post existente en vez de duplicarlo (2 archivos)
- `a6b0325` fix: completar 6 traducciones EN y evitar que la IA publique contenido perdido (8 archivos)
- `d64f7b2` fix: fechas 'updated' basadas en cambios reales de contenido (136 archivos)
- `8b35c74` fix: render de ceph_base, limpieza de duplicados y metadatos EN (53 archivos)
- `0099de7` chore: rellenar 'updated' en el árbol EN con fechas reales de git (66 archivos)

## 2026-07-18

- `2f6a036` docs: paridad ES/EN completa y normalización de categorías (32 archivos)
- `4622a1d` docs: paridad EN de los documentos enlazados desde la home (8 archivos)
- `709e039` docs: novedades en home EN, changelog regenerable y fix de registro draft (6 archivos)
- `98b4cf6` docs: actualizar Novedades con las guías del 18/07/2026 (2 archivos)
- `c2be8b0` docs: Service Mesh, Secretos en GitOps, vLLM e higiene i18n (11 archivos)
- `7df84e2` docs: Kubernetes CSI, LiteLLM y MeshLLM (8 archivos)
- `8aecad1` docs: guías de Docker runtime security, IaC security y modelos locales (10 archivos)
- `1e52364` feat: mermaid a imagen, admonitions inline y mejora "blog" con Ollama (4 archivos)
- `dae0989` feat: mejorar formato de posts WordPress y subir imágenes automáticamente (3 archivos)
- `c9afd5a` chore: cleanup from project review (6 archivos)

## 2026-04-18

- `e82b80f` Lint docs and update vRouters content in ES (9 archivos)
- `c47354b` Add vRouters docs, guides, and benchmark templates (ES/EN) (15 archivos)

## 2026-03-01

- `6ec0d79` feat: agregar documentación sobre Dex IdP en español e inglés (3 archivos)

## 2026-02-10

- `6dd5424` fix: actualizar configuración de WordPress y agregar funciones para sincronización de posts (5 archivos)

## 2026-01-25

- `2b17256` Implement feature X to enhance user experience and fix bug Y in module Z (1 archivo)
- `1d12823` fix: resolve Mermaid CLI Puppeteer sandbox issue (2 archivos)
- `530724a` fix: escape template variables in observability guide (2 archivos)
- `55e5c77` Add comprehensive observability stack guide: Prometheus, Grafana, Loki, Jaeger, OpenTelemetry, advanced alerting, storage/networking monitoring, and production configurations (2 archivos)
- `5742075` Fix MkDocs build issues: escape Jinja2 templates, exclude problematic files, disable git-revision plugin for strict builds (1 archivo)
- `58a9f92` Fix Jinja2 syntax errors and broken links in AI docs, update storage documentation (24 archivos)
- `76b07ee` Refactor Mermaid validation in validate_mermaid.sh (2 archivos)
- `2abfc05` Improve Mermaid validation logging (show mmdc stderr) (1 archivo)
- `1e3c271` Update Mermaid validation to render to temp file (no --validate) (1 archivo)
- `6be11e1` Fix Mermaid validation script quoting for backticks (1 archivo)
- `7510de3` Fix validate_mermaid.sh: Add graceful handling when mmdc is not installed (1 archivo)
- `0ccc811` Add VPN to Mesh Networking migration guide. Complete strategy for migrating from OpenVPN/IPsec to WireGuard/ZeroTier with testing scripts and best practices. (4 archivos)
- `f8692b3` Add performance benchmarks guide for Tailscale vs NetBird networking comparison. Update navigation and TODO status. (4 archivos)
- `790d28b` Add new cybersecurity guides: Supply Chain Security, CI Security Scanning, Zero Trust, and Trivy Operator. Update navigation in mkdocs.yml (5 archivos)
- `5273027` feat: Complete AI Phase 2 - Add Kubernetes deployment guide (5 archivos)
- `e88c121` Complete AI Phase 2: Add 4 comprehensive guides and English translations (7 archivos)
- `6b3b240` docs(ai): Add Content Generation, Log Analysis and Prompt Engineering guides (6 archivos)
- `d4f4154` feat: Añadir documentación de Optimización de Modelos y Chatbots Locales (6 archivos)
- `a4754cc` feat: Implementar sistema automático de metadatos para documentación (21 archivos)
- `54fe39f` Expand metadata fields across all documentation files (89 archivos)
- `506aa18` Complete 'updated' field implementation for all documentation files (71 archivos)
- `e0e05fd` Add 'updated' field to critical documentation files (15 archivos)
- `6c7a0f0` Add "Últimas Novedades" section to homepage (1 archivo)
- `5891e7f` Add comprehensive OpenStack and Ceph production documentation (6 archivos)
- `a1f3a42` Add privacy-focused analytics: Plausible self-hosted + log analyzer (4 archivos)
- `d0725a5` Add freshness tracking script and simplify contribution guidelines (12 archivos)
- `3c223cd` Update TODO.md and move blog posts to internal drafts (4 archivos)
- `81ee8f0` feat: completar guías de IA y ciberseguridad, actualizar navegación y estado de fases (1 archivo)
- `2dbfcf3` Make git revision plugin optional via env (1 archivo)
- `07c89d6` Add RAG, vector DB, and security guides (14 archivos)

## 2026-01-24

- `ddc936e` feat: add observability stack guide (Fase 2.3) (4 archivos)
- `6facc9b` feat: complete Fase 2.2 - Networking comparisons (8 archivos)
- `94f1520` fix: resolve build warnings and update navigation (4 archivos)
- `02b23cf` docs: update TODO with completed AI and storage implementations (1 archivo)
- `07cd624` feat: implement AI section and storage improvements (11 archivos)
- `752038a` docs: update TODO with CI/CD fixes completion (2 archivos)
- `b3e95f1` fix: resolve strict mode build failures (5 archivos)
- `ac0acfc` docs: update TODO and gitignore for link validation (2 archivos)
- `18a6e53` feat: implement comprehensive link validation system (4 archivos)
- `c86eb57` feat: Complete i18n translations - Programming and Curiosities sections (5 archivos)
- `c8b1778` cleanup: Remove temporary backup files from header unification (3 archivos)
- `99a7eae` feat: Completar unificación de estilo de encabezados (5 archivos)
- `eb10b31` feat: Unificar estilo de encabezados - Convertir Setext H1 a ATX (3 archivos)
- `7855eab` feat: Add GitHub Actions workflow for MkDocs build validation (3 archivos)
- `5399ba9` docs: Update TODO.md with completion of 5 critical EN translations (1 archivo)
- `bd65e58` i18n: Translate 5 critical files to English (IPv6, ASN/BGP, DNSSEC, DevSecOps, Secrets Management) (5 archivos)

## 2026-01-23

- `e0c0da0` i18n: Traducir CIDR Notation a inglés completo (1 archivo)
- `2fbcae9` TODO: Actualizar estado de traducción i18n (1 archivo)
- `cdd55d6` i18n: Traducciones completadas y headers limpiados (29 archivos)
- `ed3a533` i18n: Traducción de 6 archivos críticos a inglés (7 archivos)
- `6ee250b` i18n: Sincronización ES↔EN - 40+ archivos copiados, curiosities eliminado (40 archivos)

## 2026-01-09

- `76df316` docs: update TODO.md to reflect cybersecurity guides completion (1 archivo)
- `31eb5e8` feat: integrate cybersecurity guides into MkDocs navigation (1 archivo)
- `7b41830` feat: add comprehensive cybersecurity documentation (9 archivos)
- `056909a` docs: update TODO.md to reflect networking guides completion (1 archivo)
- `2d56564` feat: integrate networking guides into MkDocs navigation (1 archivo)
- `e5e7673` feat: add comprehensive networking documentation (12 archivos)

## 2026-01-04

- `ff7c5af` docs: add programming technologies section (flutter, react, fastapi) (5 archivos)

## 2025-12-25

- `d52213c` feat: Add new documentation for Proxmox SDN, ArgoCD, Wazuh logs, and networking benchmarks, and enable new MkDocs features. (6 archivos)

## 2025-12-08

- `d0d092c` feat(docs): add improvements (giscus, tags, mermaid diagrams) (17 archivos)

## 2025-12-07

- `3766760` refactor(nav): restructure docs into Infra, DevOps, Services, and Misc tabs (1 archivo)
- `8063e1b` feat(content): add guides for databases, backups, and identity (27 archivos)
- `7f91841` fix(mkdocs): restore explicit nav, remove awesome-pages plugin (6 archivos)
- `cd1af62` feat(mkdocs): modernize config with awesome-pages, RSS, and localized dates (6 archivos)
- `e59ec27` chore: add CHANGELOG entry for recent docs updates (1 archivo)
- `3b9daa6` docs: add fio example to nav; fix markdown whitespace; update TODO.md; add scripts/fix_md_whitespace.py (45 archivos)

## 2025-11-23

- `fdfb29f` Add storage protocols section (ES/EN), update nav and indices (5 archivos)
- `d4fcf19` Move Ceph images to docs/doc/storage/ceph and update references; remove legacy Ceph MD (17 archivos)

## 2025-11-15

- `2d04477` docs: actualizar TODO.md con estado final de mejoras (1 archivo)
- `974c40a` feat: completar mejoras de UX y navegación (10 archivos)
- `adecfc2` docs: actualizar TODO.md con mejoras de UX implementadas (1 archivo)
- `734c71e` fix: corregir rutas de enlaces en guías Docker y Kubernetes (2 archivos)
- `054d9b5` feat: mejoras de navegación, contenido y privacidad (7 archivos)
- `d2ba991` fix: corregir anchors de enlaces en documentación inglesa (1 archivo)
- `1aa89e5` feat: sincronizar documentación en inglés con español (6 archivos)
- `8224692` remove: quitar todas las referencias :material de los tutoriales (1 archivo)
- `c0c2674` fix: corregir iconos de Material Design - mostrar solo en índice (6 archivos)
- `ab73df5` feat: añadir iconos de Material Design a tutoriales rápidos (6 archivos)
- `b7592a3` feat: añadir enlaces directos a tutoriales rápidos para cada tecnología (6 archivos)
- `2606517` fix: Desactivar temporalmente sección de notebooks interactivos (1 archivo)
- `7d02149` fix: Reparar notebook interactivo de DevOps, (1 archivo)
- `3135cce` fix: Mejorar visibilidad del texto en nodo inicial del diagrama (1 archivo)
- `58c6f44` fix: Mejorar contraste de colores en diagramas de comparación networking (1 archivo)
- `f8f23a2` fix: Corregir diagrama de modelos de seguridad en comparación networking (1 archivo)
- `b780414` fix: Limpiar sección de comparación de networking (1 archivo)
- `fa001ec` feat: Reorganizar navegación de networking en barra lateral (1 archivo)
- `c497ae5` feat: Actualizar video comparativo de VPN modernas en sección networking (1 archivo)
- `2a66ab9` feat: Agregar diagramas visuales completos a la sección de networking (5 archivos)
- `57ae93b` feat: Agregar videos tutoriales a todas las documentaciones principales (7 archivos)
- `072efa8` feat: Agregar contenido multimedia - videos tutoriales y capturas de referencia (3 archivos)
- `ac5be0f` fix: Commitear cambios pendientes en notebook de Python DevOps (1 archivo)
- `79fbe34` feat: Expandir sección 'Empezando' con roadmap visual y ejemplos prácticos (4 archivos)
- `e5f9f8e` feat: Mejorar visibilidad de notebooks Jupyter en sección Dev (1 archivo)
- `7de319d` fix: Remover mkdocs-tags-plugin innecesario, usar soporte built-in de Material (2 archivos)
- `4aa94b9` feat: Implementar mejoras sugeridas para la documentación (5 archivos)
- `54fe5a3` feat: Implementar SEO avanzado y sincronización bilingüe (5 archivos)
- `b23ed08` feat: Add SEO metadata to key documents (3 archivos)
- `734f698` fix: Correct git-revision-date plugin configuration (1 archivo)
- `c8afda4` feat: Add last update dates and change history links (2 archivos)
- `24dd407` feat: Synchronize English content with Spanish version (4 archivos)
- `f1a3945` chore: Update CI to use Python 3.13 (1 archivo)
- `6cf7d7a` fix: Add libfreetype6-dev to CI system dependencies (1 archivo)
- `cd72d05` fix: Add system dependencies installation to CI workflow (1 archivo)
- `0bfbf4b` feat: Add PVETUI tool to Proxmox docs and create initial stubs (20 archivos)

## 2025-09-10

- `cf40dc7` add networking to index (4 archivos)
- `d8a24ac` add networking section (13 archivos)

## 2025-09-07

- `8e16301` more curiosities (3 archivos)

## 2025-09-03

- `ad92593` improve section , fix links and new section (15 archivos)

## 2025-08-29

- `07907b0` proxmox reference (2 archivos)
- `3db757d` fix proxmox name (1 archivo)
- `09f8848` Add proxmox and improve haproxy (6 archivos)
- `f4330be` improve doc with diagrams and more examples (12 archivos)

## 2025-08-28

- `1288159` improve documentation adding haproxy (4 archivos)

## 2025-08-25

- `c992628` fix pipeline dependency installation (1 archivo)
- `1d2c4ca` Clean base (9 archivos)
- `5f2df05` base improvements (3 archivos)
- `c04ba18` base improvements (25 archivos)
- `4d790ff` clean and fix some links (53 archivos)

## 2025-08-24

- `09241a9` Change Home and Doc reference (1 archivo)
- `c21716b` improve welcome page and favicon (4 archivos)
- `dbd7ee6` test blog and improvements on terraform doc to refer opentofu (3 archivos)
- `c27eaf5` Disable twitter Improve doc references Improve admin reference (15 archivos)
- `26436ce` Feature: More sections and improve author sign (13 archivos)

## 2025-08-23

- `711ca10` temporaly disable analytics (1 archivo)
- `863aa54` update logo (1 archivo)
- `bcbeba5` base (73 archivos)
- `b1d2f4b` Create CNAME (1 archivo)
- `e3fd5ec` Initial commit (1 archivo)
