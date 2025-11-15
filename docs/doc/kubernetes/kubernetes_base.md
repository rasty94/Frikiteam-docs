# Kubernetes - Orquestación de Contenedores

## Introducción a Kubernetes

Kubernetes (K8s) es una plataforma de orquestación de contenedores de código abierto que automatiza el despliegue, escalado y gestión de aplicaciones contenerizadas.

## 🚀 :material-kubernetes: Iniciar con Kubernetes en 20 minutos

¿Nuevo en Kubernetes? Comienza aquí:

- **[Tutorial oficial: Primeros pasos](https://kubernetes.io/docs/tutorials/kubernetes-basics/)** - Crea tu primer cluster y despliega una app
- **[Play with Kubernetes](https://labs.play-with-k8s.com/)** - Entorno interactivo online gratuito
- **[Katacoda Kubernetes scenarios](https://www.katacoda.com/courses/kubernetes)** - Tutoriales interactivos paso a paso

## Arquitectura de Kubernetes

### Componentes del plano de control
- **API Server**: Punto de entrada para todas las operaciones
- **etcd**: Base de datos distribuida que almacena la configuración
- **Scheduler**: Asigna pods a nodos
- **Controller Manager**: Mantiene el estado del cluster

### Componentes del nodo
- **kubelet**: Agente que ejecuta en cada nodo
- **kube-proxy**: Gestiona las reglas de red
- **Container Runtime**: Software que ejecuta los contenedores

## Conceptos fundamentales

### Pods
Los pods son la unidad más pequeña de Kubernetes. Contienen uno o más contenedores.

```yaml
# pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: mi-pod
spec:
  containers:
  - name: nginx
    image: nginx:latest
    ports:
    - containerPort: 80
```

### Deployments
Los deployments gestionan el estado deseado de los pods.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mi-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mi-app
  template:
    metadata:
      labels:
        app: mi-app
    spec:
      containers:
      - name: nginx
        image: nginx:latest
```

### Services
Los services exponen aplicaciones que se ejecutan en pods.

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mi-service
spec:
  selector:
    app: mi-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

## Comandos básicos

```bash
# Aplicar un manifiesto
kubectl apply -f archivo.yaml

# Listar pods
kubectl get pods

# Ver logs de un pod
kubectl logs <pod-name>

# Ejecutar comando en un pod
kubectl exec -it <pod-name> -- /bin/bash

# Escalar un deployment
kubectl scale deployment mi-deployment --replicas=5
```

## Casos de uso

- Microservicios
- Aplicaciones nativas en la nube
- CI/CD pipelines
- Aplicaciones de alta disponibilidad

## Próximos pasos

En las siguientes secciones exploraremos:
- Configuración avanzada de clusters
- Gestión de almacenamiento
- Redes y políticas de seguridad
- Monitoreo y logging
- Helm y gestión de paquetes

## Recursos adicionales

### Videos tutoriales

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;">
  <iframe src="https://www.youtube.com/embed/X48VuDVv0do" frameborder="0" allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe>
</div>

*Video: Kubernetes en 5 minutos - Introducción rápida y completa*

### Documentación oficial
- **Sitio web oficial:** [kubernetes.io](https://kubernetes.io/)
- **Documentación:** [kubernetes.io/docs](https://kubernetes.io/docs/)
- **GitHub:** [github.com/kubernetes/kubernetes](https://github.com/kubernetes/kubernetes)
- **Blog oficial:** [kubernetes.io/blog](https://kubernetes.io/blog/)

### Comunidad
- **Reddit:** [r/kubernetes](https://www.reddit.com/r/kubernetes/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/kubernetes](https://stackoverflow.com/questions/tagged/kubernetes)
- **Slack:** [slack.k8s.io](https://slack.k8s.io/)
- **Discord:** [discord.gg/kubernetes](https://discord.gg/kubernetes)
