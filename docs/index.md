---
title: Inicio - Frikiteam Docs
description: Documentación técnica completa sobre DevOps, infraestructura, contenedores y nube. Guías prácticas de Ansible, Docker, Kubernetes, OpenStack y más.
keywords: devops, infraestructura, docker, kubernetes, ansible, terraform, openstack, proxmox, haproxy, ceph, networking
tags: [inicio, documentacion, devops, infraestructura]
---

# 🚀 Bienvenido a Frikiteam Docs 🚀

¡Bienvenido a la documentación técnica de Frikiteam! Soy un profesional apasionado por la tecnología que comparte conocimiento y experiencias en el mundo de la infraestructura, la nube y la automatización.

## 🎯 Mi Idea

Mi idea es proporcionar documentación práctica, clara y útil sobre las tecnologías que utilizo día a día. Quiero compartir no solo la teoría, sino también las experiencias reales, los trucos y las mejores prácticas que he aprendido en la "trinchera" tecnológica.

## 🆕 Últimas Novedades

### 📅 **25 de enero de 2026**

#### 🚀 **Documentación Completa OpenStack + Ceph**
- **Nueva guía de despliegue**: [Despliegue con Kolla-Ansible](doc/openstack/kolla_deployment.md) - Instalación completa de OpenStack en producción
- **Integración storage**: [OpenStack + Ceph](doc/openstack/openstack_ceph_integration.md) - Backend Ceph para Glance, Cinder y Nova
- **Troubleshooting avanzado**: [Problemas OpenStack](doc/openstack/troubleshooting_openstack.md) y [Problemas Ceph](doc/storage/ceph/troubleshooting_ceph.md)
- **Operaciones producción**: [Day-2 Operations](doc/openstack/day2.md) expandido con upgrades, backups, monitorización y DR

#### 📊 **Analytics Respetuoso con Privacidad**
- **Plausible Analytics**: Guía completa de [auto-hosting](doc/monitoring/plausible_analytics.md) (GDPR-compliant, sin cookies)
- **Script de logs**: Análisis de acceso para monitorizar sin tracking invasivo
- **Configuración preparada**: MkDocs listo para integrar analytics cuando se despliegue

#### 🔧 **Mejoras de Mantenibilidad**
- **Freshness tracking**: Script que detecta documentación obsoleta (>90 días)
- **Checklist simplificado**: Guía de contribución actualizada con 5 puntos esenciales
- **Roadmap de mejoras**: TODO.md con plan de mantenibilidad práctica

#### 🤖 **Sección de Inteligencia Artificial**
- **Fundamentos LLMs**: [Introducción completa](doc/ai/llms_fundamentals.md) a modelos de lenguaje
- **Ollama**: [Guía práctica](doc/ai/ollama_basics.md) de IA local
- **Modelos y evaluación**: [Benchmarking](doc/ai/model_evaluation.md) y comparación de modelos

### 📅 **24 de enero de 2026**
- **Paridad ES/EN completa**: Traducción de 40+ archivos críticos (Kubernetes, Docker, networking, cybersecurity)
- **Nueva documentación IA**: Ecosistemas locales, RAG, vector databases
- **Mejoras de storage**: PostgreSQL + Ceph, Pure Storage, NetApp

### 📅 **23 de enero de 2026**
- **Reorganización blog**: Posts técnicos movidos a drafts para publicación en WordPress
- **Corrección enlaces i18n**: Navegación simétrica español/inglés
- **Validación build**: MkDocs build limpio sin errores

---

*[Ver todas las actualizaciones →](https://github.com/rasty94/Frikiteam-docs/commits/main)*

## 📚 Documentación Técnica Disponible

### 🔧 **Automatización e Infraestructura**
- **[Ansible](doc/ansible/ansible_base.md)** - Automatización de infraestructura sin agentes
- **[Terraform & OpenTofu](doc/terraform/terraform_base.md)** - Infraestructura como Código
- **[Haproxy](doc/haproxy/haproxy_base.md)** - Balanceo de carga TCP/HTTP

### ☁️ **Plataformas de Nube**
- **[OpenStack](doc/openstack/openstack_base.md)** - Plataforma de nube privada y pública Open-Source
- **[Proxmox](doc/proxmox/proxmox_base.md)** - Plataforma de virtualización Open-Source

### 🐳 **Contenedores y Almacenamiento**
- **[Docker](doc/docker/docker_base.md)** - Contenedores y virtualización
- **[Kubernetes](doc/kubernetes/kubernetes_base.md)** - Orquestación de contenedores
- **[Ceph](doc/storage/ceph/ceph_base.md)** - Almacenamiento distribuido escalable
- **[Pure Storage](doc/storage/pure_storage/pure_storage_base.md)** - Almacenamiento All‑Flash empresarial
- **[NetApp](doc/storage/netapp/netapp_base.md)** - Soluciones de almacenamiento empresarial
- **[Protocols & Metrics](doc/storage/protocols/protocols.md)** - Protocolos (iSCSI/NFS/SMB/S3) y métricas (IOPS, latencia, throughput)

### 🌐 **Redes y Conectividad**
- **[Networking](doc/networking/index.md)** - VPN y soluciones de red (NetBird, Tailscale, ZeroTier)

### 🎯 **Curiosidades y Comparativas**
- **[Curiosidades](doc/curiosidades/index.md)** - Comparativas interesantes entre tecnologías

## 🚀 Empezando

¿No sabes por dónde empezar? Te recomendamos:

1. **Si eres nuevo en automatización**: Comienza con [Ansible](doc/ansible/ansible_base.md)
2. **Si quieres trabajar con contenedores**: Explora [Docker](doc/docker/docker_base.md)
3. **Si te interesa la nube**: Descubre [OpenStack](doc/openstack/openstack_base.md)
4. **Si quieres orquestar aplicaciones**: Aprende [Kubernetes](doc/kubernetes/kubernetes_base.md)
5. **Si te interesa montar un HomeLab completo y flexible**: Aprende [Proxmox](doc/proxmox/proxmox_base.md)
6. **Si necesitas conectar dispositivos de forma segura**: Explora [Networking](doc/networking/index.md)

## 📖 Blog y Artículos

Mantente al día con las últimas novedades y tutoriales en mi [blog](https://frikiteam.es). Comparto experiencias, mejores prácticas y casos de uso reales.

## 🤝 Contribuir

¡Tu contribución es bienvenida! Si encuentras errores, quieres añadir contenido o tienes sugerencias:

- **GitHub**: [rasty94/Frikiteam-docs](https://github.com/rasty94/Frikiteam-docs)
- **Issues**: Reporta problemas o solicita nuevas funcionalidades
- **Pull Requests**: Contribuye con mejoras o nuevo contenido

## 📞 Contacto

- **GitHub**: [@rasty94](https://github.com/rasty94) 🐙
- **Repositorio**: [Frikiteam-docs](https://github.com/rasty94/Frikiteam-docs) 📚

---

*Gracias por ser parte de nuestra comunidad. ¡Esperamos que esta documentación te sea útil en tu viaje tecnológico! ✨*

**Antonio Rodríguez** 🚀