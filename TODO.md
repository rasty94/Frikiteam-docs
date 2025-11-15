# TODO — Posts y Temas Prioritarios

Este documento recoge propuestas de posts y artículos para ampliar la documentación de FrikiTeam. Está basada en la revisión del contenido actual en `docs/` y `docs/doc/`, los scripts internos (`scripts/new_post.sh`) y herramientas (Mermaid, macros).

Instrucciones:
- Si quieres que cree stubs de los posts automáticamente, responde "si crear stubs".
- Podemos priorizar y dividir temas en series si lo prefieres.

---

## Must-have (Prioridad Alta)

1. Quickstart: "Arranca y contribuye" — docs/quickstart.md (CREADO)
   - Descripción: Instrucciones para instalar dependencias (venv, pip), ejecutar `mkdocs serve`, generar la build, y un ejemplo mínimo con Docker y un contenedor `nginx` para ver contenido.
   - Audiencia: Nuevos contribuidores
   - Estimado: 1h
   - Ruta sugerida: `docs/quickstart.md`

2. Contribuir: "CONTRIBUTING.md" — root (CREADO)
   - Descripción: Cómo usar `scripts/new_post.sh`, normas de formato de posts, cómo probar localmente, PR checklist y estilo.
   - Audiencia: Contribuidores/Authors
   - Estimado: 1h
   - Ruta sugerida: `CONTRIBUTING.md`

3. Troubleshooting MkDocs y plugins — docs/troubleshooting.md (CREADO)
   - Descripción: Lista de errores comunes (plugins faltantes, rutas de recursos, minify plugin), comandos y soluciones. Ejemplos: error `minify` plugin.
   - Audiencia: Admins / Maintainers
   - Estimado: 2h
   - Ruta sugerida: `docs/troubleshooting.md`

4. Mermaid: verificación y automatización — docs/dev/mermaid.md (CREADO)
   - Descripción: Documentar el script de verificación (`internal/mermaid/tools/check_diagrams.py`), añadir cómo integrarlo en CI, y ejemplos de diagramas y mejores prácticas.
   - Audiencia: Redactores técnicos
   - Estimado: 2h
   - Ruta sugerida: `docs/dev/mermaid.md`

5. Docker: Dockerfile optimizado (multi-stage) y buenas prácticas — docs/doc/docker/docker_optimizations.md (CREADO)
   - Descripción: Multi-stage build, imagen mínima (slim/alpine), manejo de cache, usuarios no root, recomendación de scanning (trivy), ejemplos.
   - Audiencia: Desarrolladores/DevOps
   - Estimado: 3h
   - Ruta sugerida: `docs/doc/docker/docker_optimizations.md`

6. Kubernetes: readiness/liveness/health-checks y patterns — docs/doc/kubernetes/probes.md (CREADO)
   - Descripción: Explicar readiness vs liveness, ejemplos con `kubectl` y YAML, casos prácticos y debugging.
   - Audiencia: DevOps/Administradores K8s
   - Estimado: 3h
   - Ruta sugerida: `docs/doc/kubernetes/probes.md`

---

## Recommended (Prioridad Media)

7. CI/CD: GitHub Actions para MkDocs + build de contenedores — docs/blog/posts/2025/ci-cd-mkdocs-build.md (CREADO)
   - Descripción: Ejemplo de workflow que instala deps, valida con `mkdocs build`, ejecuta verificación de mermaid y despliega al sitio (o PR preview).
   - Audiencia: Maintainers
   - Estimado: 3h
   - Ruta sugerida: `docs/blog/posts/2025/ci-cd-mkdocs-build.md`

8. Docker: Seguridad (hardening, secrets y scanning) — docs/doc/docker/docker_security.md (CREADO)
   - Descripción: Manejo de secretos, no almacenar credenciales en images, scanning con `trivy`, autenticación a registries y hardening.
   - Audiencia: DevOps
   - Estimado: 3h
   - Ruta sugerida: `docs/doc/docker/docker_security.md`

9. Terraform: Backend de estado, locking y migración — docs/doc/terraform/terraform_state.md (CREADO)
   - Descripción: Ejemplos con S3/Dynamo/consul, migrar state, mantenimiento, `terraform fmt` y `terraform validate`.
   - Audiencia: Infra/DevOps
   - Estimado: 3h
   - Ruta sugerida: `docs/doc/terraform/terraform_state.md`

10. Ansible: buenas prácticas y testing con Molecule — docs/doc/ansible/roles_testing.md (CREADO)
    - Descripción: Organización de roles, pruebas unitarias con `molecule`, y CI de roles.
    - Audiencia: Infra/DevOps
    - Estimado: 3h
    - Ruta sugerida: `docs/doc/ansible/roles_testing.md`

11. HAProxy: TLS y escalado — docs/doc/haproxy/haproxy_advanced.md (CREADO)
    - Descripción: TLS termination, certificados y balanceo formado por niveles, configuración para alta disponibilidad.
    - Audiencia: Admins de red
    - Estimado: 3h
    - Ruta sugerida: `docs/doc/haproxy/haproxy_advanced.md`

---

## Nice-to-have (Prioridad Baja)

12. Ceph: optimización y planificación de capacidad — docs/doc/ceph/ceph_tuning.md (CREADO)
   - Estimado: 4h

13. Proxmox: migraciones (VMs y contenedores) — docs/doc/proxmox/migration_guide.md (CREADO)
   - Estimado: 3h

14. Networking práctico: casos de uso y comparativa con ejemplos (Tailscale/NetBird/ZeroTier) — docs/blog/posts/2025/network-compare-practical.md (CREADO)
   - Estimado: 2h

15. OpenStack: Day-2 operations y backup — docs/doc/openstack/day2.md (CREADO)
   - Estimado: 4h

16. Glosario: conceptos comunes — docs/glossary.md (CREADO)
   - Beneficio: ayuda a nuevos usuarios.

---

## Propuestas técnicas y meta-requisitos
- Añadir `CONTRIBUTING.md` al root (importante para mantener consistencia en nuevas entradas).
- Asegurar `requirements.txt` en la raíz y crear un script `dev_setup.sh` para preparar venv, deps y comandos básicos.
- Crear un workflow de GitHub Actions para:
  - Instalar deps y ejecutar `mkdocs build`.
  - Ejecutar `scripts/check_diagrams.py` (si existe) o una verificación equivalente.
  - Validar enlaces con un comprobador de enlaces (mkdocs plugin o `html-proofer` en GH Actions).

---

## Acciones siguientes sugeridas
1. Priorizar 3 posts Must-have y crear stubs Markdown (usar `scripts/new_post.sh` para posts del blog) — ¿quieres que los cree ahora?
2. Añadir PR template y CONTRIBUTING.md — ¿confirmas el texto base?
3. Añadir workflow GH Actions para validar `mkdocs build` — ¿prefieres que lo añada en `.github/workflows/mkdocs.yml`?

---

Si estás de acuerdo con esta lista te genero los stubs (post y doc) y puedo crear PR o aplicar cambios directos al repo. Si quieres cambiar prioridades o añadir otros temas, dímelo y adapto el TODO.
