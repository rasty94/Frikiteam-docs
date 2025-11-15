# Recetas Rápidas

Bienvenido a la sección de **Recetas Rápidas**. Aquí encontrarás soluciones rápidas y comandos copy-paste para problemas comunes en las tecnologías que cubrimos.

## Ansible

### Ejecutar un playbook con inventario específico

```bash
ansible-playbook -i inventory.ini playbook.yml
```

### Verificar conectividad con hosts

```bash
ansible all -m ping
```

## Docker

### Limpiar contenedores e imágenes no utilizadas

```bash
docker system prune -a
```

### Ver logs de un contenedor

```bash
docker logs <container_name>
```

## Kubernetes

### Ver pods en todos los namespaces

```bash
kubectl get pods --all-namespaces
```

### Aplicar un manifiesto YAML

```bash
kubectl apply -f deployment.yaml
```

## HAProxy

### Recargar configuración sin downtime

```bash
sudo systemctl reload haproxy
```

### Ver estadísticas en tiempo real

```bash
echo "show stat" | socat stdio /var/run/haproxy.sock
```

## Networking

### Ver tabla de rutas

```bash
ip route show
```

### Ver interfaces de red

```bash
ip addr show
```

## Proxmox

### Actualizar el sistema

```bash
apt update && apt upgrade
```

### Crear una VM desde CLI

```bash
qm create 100 --name myvm --memory 2048 --net0 virtio,bridge=vmbr0
```

## OpenStack

### Listar instancias

```bash
openstack server list
```

### Crear una red

```bash
openstack network create mynetwork
```

## Terraform

### Inicializar un directorio

```bash
terraform init
```

### Planificar cambios

```bash
terraform plan
```

## Ceph

### Ver estado del cluster

```bash
ceph status
```

### Listar OSDs

```bash
ceph osd tree
```

!!! tip "Contribuye"
    Si tienes una receta rápida que crees que sería útil, ¡envía un PR o abre un issue en nuestro [repositorio](https://github.com/rasty94/Frikiteam-docs)!