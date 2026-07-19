---
title: "🚀 Welcome to Frikiteam Docs 🚀"
tags: [inicio, documentacion, devops, infraestructura]
updated: 2026-07-19
---

# 🚀 Welcome to Frikiteam Docs 🚀

Welcome to Frikiteam's technical documentation! I am a professional passionate about technology who shares knowledge and experiences in the world of infrastructure, cloud, and automation.

## 🎯 My Idea

My idea is to provide practical, clear, and useful documentation about the technologies I use daily. I want to share not only theory but also real experiences, tricks, and best practices I've learned in the technological "trenches."

## 🆕 Latest Updates

### 📅 **July 19, 2026**

#### 🔒 **Cybersecurity: backup, incident response, compliance and offensive auditing (ES/EN)**

- **Secure backup**: [encryption, immutability and restore testing](doc/cybersecurity/backup_seguro.md) against ransomware, with a restore-verification script.
- **Incident response**: [a practical playbook with TheHive and MISP](doc/cybersecurity/respuesta_incidentes.md) following the NIST SP 800-61 lifecycle.
- **Compliance and auditing**: [GDPR, ISO 27001 and OpenSCAP](doc/cybersecurity/cumplimiento_auditoria.md) as technical controls with reproducible evidence.
- **Applied cryptography**: [primitives, password hashing and key management](doc/cybersecurity/criptografia_aplicada.md), the conceptual companion to [TLS](doc/networking/certificados_tls.md) and the existing VPN guides.
- **Basic pentesting**: [a methodology for auditing your own infrastructure](doc/cybersecurity/pentesting_basico.md) with Nmap, Burp Suite and Metasploit, framed around authorization and legal scope.

#### 🤖 **LLMs in production: Kubernetes, observability and cost (ES/EN)**

- **LLMs on Kubernetes**: [GitOps deployment with Helm and ArgoCD](doc/ai/llms_kubernetes.md), plus three reliability fixes to the [existing deployment guide](doc/ai/despliegue_kubernetes.md) (startupProbe, HPA on vLLM metrics, secrets management).
- **LLM monitoring**: [inference observability](doc/ai/monitoreo_llms.md) covering TTFT/TPOT, KV cache saturation and verified vLLM metrics.
- **Open-source vs cloud**: [cost, latency, privacy and control](doc/ai/opensource_vs_cloud.md), using this repo's own multi-server inference pipeline as a real case study.

#### 🐳 **Containers and databases (ES/EN)**

- **Rootless Podman**: [containers without a daemon or root](doc/docker/podman_rootless.md), threat model versus Docker and a practical migration path.
- **PostgreSQL High Availability**: [replication, Patroni and tested failover](doc/databases/postgresql_ha.md), expanding the HA section of the [base PostgreSQL guide](doc/databases/postgres.md).

### 📅 **July 18, 2026**

#### 🤖 **Complete local LLM ecosystem (ES/EN)**

- **Inference engines**: [LLaMA.cpp](doc/ai/llama_cpp.md) (build, GGUF quantization and benchmarking), [LM Studio](doc/ai/lm_studio.md) (graphical interface) and [vLLM](doc/ai/vllm.md) (serving at scale with high throughput).
- **Unified gateway**: [LiteLLM](doc/ai/litellm.md) as a single OpenAI-compatible layer in front of local models and cloud providers, with budget control and fallbacks.
- **Distributed inference**: [MeshLLM](doc/ai/meshllm.md), a P2P mesh that pools GPUs from several machines behind a single endpoint.
- **MCP protocol**: [MCP and FastMCP](doc/ai/mcp_fastmcp.md) integrated into the navigation.

#### 🔒 **Security: runtime, IaC and GitOps (ES/EN)**

- **Container isolation**: [Docker Runtime Security](doc/docker/docker_runtime_security.md) with gVisor and Kata Containers, complementing [image hardening](doc/docker/docker_security.md).
- **Infrastructure as Code**: [IaC Security](doc/cybersecurity/seguridad_iac.md) with Checkov and TFLint, integrated into pre-commit and CI/CD.
- **Versioned secrets**: [Secrets in GitOps](doc/cybersecurity/secrets_gitops.md) comparing SOPS, Sealed Secrets and External Secrets Operator.

#### ☸️ **Kubernetes and storage (ES/EN)**

- **Service Mesh**: [Istio vs Linkerd vs Cilium comparison](doc/kubernetes/service_mesh.md), including an honest section on when you *don't* need a service mesh.
- **Persistent storage**: [Kubernetes Storage](doc/storage/kubernetes_csi.md) comparing Ceph RBD, Longhorn and OpenEBS, with a reproducible benchmark methodology.

### 📅 **April 18, 2026**

#### 🌐 **New vRouters section (ES/EN)**

- **Overview**: new guide on [vRouters and virtual firewalls](doc/networking/vrouters.md) with selection criteria.
- **Platform guides**: specific documentation for [OPNsense](doc/networking/vrouter_opnsense.md), [pfSense](doc/networking/vrouter_pfsense.md), [MikroTik CHR](doc/networking/vrouter_mikrotik_chr.md) and [VyOS](doc/networking/vrouter_vyos.md).
- **Performance testing**: new [reusable template](doc/networking/vrouter_benchmark_template.md) with KPIs, per-environment profiles and acceptance criteria.
- **Language parity**: equivalent content also available in English under `en/doc/networking/`.

### 📅 **January 25, 2026**

#### 🚀 **Complete OpenStack + Ceph documentation**

- **New deployment guide**: [Deployment with Kolla-Ansible](doc/openstack/kolla_deployment.md) - Full OpenStack installation in production
- **Storage integration**: [OpenStack + Ceph](doc/openstack/openstack_ceph_integration.md) - Ceph backend for Glance, Cinder and Nova
- **Advanced troubleshooting**: [OpenStack issues](doc/openstack/troubleshooting_openstack.md) and [Ceph issues](doc/storage/ceph/troubleshooting_ceph.md)
- **Production operations**: [Day-2 Operations](doc/openstack/day2.md) expanded with upgrades, backups, monitoring and DR

#### 📊 **Privacy-friendly analytics**

- **Plausible Analytics**: complete [self-hosting guide](doc/monitoring/plausible_analytics.md) (GDPR-compliant, cookie-free)
- **Log script**: access analysis to monitor without invasive tracking
- **Ready-made configuration**: MkDocs prepared to integrate analytics when deployed

#### 🔧 **Maintainability improvements**

- **Freshness tracking**: script that detects stale documentation (>90 days)
- **Simplified checklist**: contribution guide updated with 5 essential points
- **Improvement roadmap**: TODO.md with a practical maintainability plan

#### 🤖 **Artificial Intelligence section**

- **LLM fundamentals**: [complete introduction](doc/ai/llms_fundamentals.md) to language models
- **Ollama**: [practical guide](doc/ai/ollama_basics.md) to local AI
- **Models and evaluation**: [benchmarking](doc/ai/model_evaluation.md) and model comparison

### 📅 **January 24, 2026**

- **Full ES/EN parity**: translation of 40+ critical files (Kubernetes, Docker, networking, cybersecurity)
- **New AI documentation**: local ecosystems, RAG, vector databases
- **Storage improvements**: PostgreSQL + Ceph, Pure Storage, NetApp

### 📅 **January 23, 2026**

- **Blog reorganization**: technical posts moved to drafts for publication on WordPress
- **i18n link fixes**: symmetric Spanish/English navigation
- **Build validation**: clean MkDocs build with no errors

---

*[See all updates →](https://github.com/rasty94/Frikiteam-docs/commits/main)*

## 📚 Available Technical Documentation

### 🔧 **Automation & Infrastructure**
- **[Ansible](doc/ansible/ansible_base.md)** - Agentless infrastructure automation
- **[Terraform & OpenTofu](doc/terraform/terraform_base.md)** - Infrastructure as Code

### ☁️ **Cloud Platforms**
- **[OpenStack](doc/openstack/openstack_base.md)** - Private and public cloud platform
- **[Kubernetes](doc/kubernetes/kubernetes_base.md)** - Container orchestration

### 🐳 **Containers & Storage**
- **[Docker](doc/docker/docker_base.md)** - Containers and virtualization
- **[Kubernetes](doc/kubernetes/kubernetes_base.md)** - Container orchestration
- **[Ceph](doc/storage/ceph/ceph_base.md)** - Scalable distributed storage
- **[Pure Storage](doc/storage/pure_storage/pure_storage_base.md)** - Enterprise all-flash storage
- **[NetApp](doc/storage/netapp/netapp_base.md)** - Enterprise storage solutions
- **[Protocols & Metrics](doc/storage/protocols/protocols.md)** - Protocols (iSCSI/NFS/SMB/S3) and metrics (IOPS, latency, throughput)

### 🌐 **Networking & Connectivity**
- **[Networking](doc/networking/index.md)** - VPN and networking solutions (NetBird, Tailscale, ZeroTier)

### 🎯 **Curiosities and Comparisons**
- **[Curiosities](doc/curiosidades/index.md)** - Interesting comparisons between technologies

## 🚀 Getting Started

Don't know where to start? We recommend:

1. **If you're new to automation**: Start with [Ansible](doc/ansible/ansible_base.md)
2. **If you want to work with containers**: Explore [Docker](doc/docker/docker_base.md)
3. **If you're interested in cloud**: Discover [OpenStack](doc/openstack/openstack_base.md)
4. **If you want to orchestrate applications**: Learn [Kubernetes](doc/kubernetes/kubernetes_base.md)
5. **If you want to deploy a complete HomeLab**: Learn [Proxmox](doc/proxmox/proxmox_base.md)
6. **If you need to connect devices securely**: Explore [Networking](doc/networking/index.md)

## 📖 Blog and Articles

Stay up to date with the latest news and tutorials on my [blog](https://frikiteam.es). I share experiences, best practices, and real use cases.

## 🤝 Contributing

Your contribution is welcome! If you find errors, want to add content, or have suggestions:

- **GitHub**: [rasty94/Frikiteam-docs](https://github.com/rasty94/Frikiteam-docs)
- **Issues**: Report problems or request new features
- **Pull Requests**: Contribute with improvements or new content

## 📞 Contact

- **GitHub**: [@rasty94](https://github.com/rasty94) 🐙
- **Repository**: [Frikiteam-docs](https://github.com/rasty94/Frikiteam-docs) 📚

---

*Thank you for being part of our community. We hope this documentation is useful in your technological journey! ✨*

**Antonio Rodríguez** 🚀