# Curiosidades

Bienvenido a la sección de curiosidades técnicas. Aquí encontrarás comparaciones interesantes y datos curiosos sobre diferentes tecnologías:

- [Docker vs Kubernetes vs Máquinas Virtuales](docker_kubernetes_vm_comparison.md)
- [Proxmox vs VMware vs OpenStack: Migración hacia Soluciones Open Source](proxmox_vmware_openstack_migration.md)
- [Instalar Proxmox VE 9 sobre Debian 13 (Trixie)](proxmox_en_debian13.md)
- [Actualizar Proxmox VE 8 a 9 (Debian 13 Trixie)](upgrade_pve8_a_pve9.md)

Esta sección te ayudará a entender mejor las diferencias y similitudes entre estas tecnologías fundamentales en el mundo de la computación moderna.

## Mini-retos Técnicos

Pon a prueba tus conocimientos con estos desafíos prácticos:

### 🐳 Reto Docker
**Desafío:** Crea un contenedor que ejecute un servidor web simple mostrando "¡Hola desde Docker!" en el puerto 8080.

**Pistas:**
- Usa una imagen base de nginx o apache
- Copia un archivo HTML personalizado
- Expone el puerto correcto

**Solución aproximada:**
```bash
# Dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 8080
```

### ☸️ Reto Kubernetes
**Desafío:** Despliega una aplicación web simple con 3 réplicas usando un Deployment y expónla con un Service.

**Pistas:**
- Crea un Deployment con replicas: 3
- Usa un Service de tipo ClusterIP
- Verifica con kubectl get pods

### 🏗️ Reto Terraform
**Desafío:** Crea un plan Terraform que defina una instancia EC2 en AWS con una security group básica.

**Pistas:**
- Usa provider "aws"
- Define resource "aws_instance"
- Configura ami y instance_type

### 💡 Opiniones de la Comunidad

**Docker vs Podman:** La comunidad prefiere Docker por su simplicidad, pero Podman gana terreno por su enfoque rootless y compatibilidad con Kubernetes.

**Kubernetes vs Docker Swarm:** K8s es más poderoso pero complejo; Swarm es más simple para casos básicos.

**Proxmox vs ESXi:** Proxmox es gratuito y open-source, ESXi requiere licencia pero tiene mejor soporte enterprise.

¿Tienes una opinión o comparación que compartir? ¡Contribuye en nuestro [repositorio](https://github.com/rasty94/Frikiteam-docs)!
