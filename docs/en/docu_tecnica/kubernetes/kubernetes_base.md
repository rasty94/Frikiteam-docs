# Kubernetes - Container Orchestration

## Introduction to Kubernetes

Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications.

## Kubernetes Architecture

### Control Plane Components
- **API Server**: Entry point for all operations
- **etcd**: Distributed database that stores configuration
- **Scheduler**: Assigns pods to nodes
- **Controller Manager**: Maintains cluster state

### Node Components
- **kubelet**: Agent that runs on each node
- **kube-proxy**: Manages network rules
- **Container Runtime**: Software that runs containers

## Fundamental concepts

### Pods
Pods are the smallest unit in Kubernetes. They contain one or more containers.

```yaml
# pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: nginx
    image: nginx:latest
    ports:
    - containerPort: 80
```

### Deployments
Deployments manage the desired state of pods.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: nginx
        image: nginx:latest
```

### Services
Services expose applications running on pods.

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

## Basic commands

```bash
# Apply a manifest
kubectl apply -f file.yaml

# List pods
kubectl get pods

# View pod logs
kubectl logs <pod-name>

# Execute command in a pod
kubectl exec -it <pod-name> -- /bin/bash

# Scale a deployment
kubectl scale deployment my-deployment --replicas=5
```

## Use cases

- Microservices
- Cloud-native applications
- CI/CD pipelines
- High-availability applications

## Next steps

In the following sections we will explore:
- Advanced cluster configuration
- Storage management
- Networking and security policies
- Monitoring and logging
- Helm and package management

## Additional resources

### Official documentation
- **Official website:** [kubernetes.io](https://kubernetes.io/)
- **Documentation:** [kubernetes.io/docs](https://kubernetes.io/docs/)
- **GitHub:** [github.com/kubernetes/kubernetes](https://github.com/kubernetes/kubernetes)
- **Official blog:** [kubernetes.io/blog](https://kubernetes.io/blog/)

### Community
- **Reddit:** [r/kubernetes](https://www.reddit.com/r/kubernetes/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/kubernetes](https://stackoverflow.com/questions/tagged/kubernetes)
- **Slack:** [slack.k8s.io](https://slack.k8s.io/)
- **Discord:** [discord.gg/kubernetes](https://discord.gg/kubernetes)
