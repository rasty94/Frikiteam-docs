---
title: "Deploying LLMs at Scale with Kubernetes"
date: 2026-01-25
tags: [ai, kubernetes, vllm, helm, scaling, production]
draft: false
difficulty: advanced
time: 45 minutes
category: Artificial Intelligence
prerequisites: [ollama_basics, model_evaluation, fine_tuning_basico]
updated: 2026-07-18
---

# Deploying LLMs at Scale with Kubernetes

A complete guide to deploying and scaling large language models (LLMs) in production using Kubernetes, vLLM and advanced optimization strategies.

## 🎯 Learning Objectives

By the end of this guide you will be able to:

- Deploy LLMs with vLLM on Kubernetes
- Set up auto-scaling driven by GPU metrics
- Apply caching and optimization strategies
- Run several models side by side in production
- Track inference performance and cost

## 📋 Prerequisites

- Working knowledge of Kubernetes
- Hands-on experience with Docker and Helm
- Familiarity with LLMs and vLLM
- A Kubernetes cluster with GPUs (optional, but recommended)

## 🏗️ Deployment Architecture

### Core Components

```mermaid
graph TB
    A[Ingress/Load Balancer] --> B[API Gateway]
    B --> C[vLLM Service 1]
    B --> D[vLLM Service 2]
    B --> E[vLLM Service N]

    C --> F[GPU Node Pool]
    D --> F
    E --> F

    G[Prometheus] --> H[Metrics Server]
    H --> I[HPA Controller]
    I --> C
    I --> D
    I --> E

    J[Model Registry] --> K[Init Container]
    K --> C
```

### Deployment Strategies

1. **Single Model per Pod**: full isolation
2. **Multi-Model per Pod**: better resource utilization
3. **Model Sharding**: splitting large models across nodes
4. **Dynamic Loading**: load models on demand

## 🚀 Basic Deployment with vLLM

### 1. Preparing the Cluster

```bash
# Check which GPUs are available
kubectl get nodes -o json | jq '.items[].status.capacity."nvidia.com/gpu"'

# Install the NVIDIA GPU Operator (if it isn't already installed)
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update
helm install gpu-operator nvidia/gpu-operator \
  --create-namespace \
  --namespace gpu-operator
```

### 2. Creating the Namespace and ConfigMaps

```yaml
# vllm-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: vllm-system
  labels:
    name: vllm-system
```

```yaml
# vllm-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-config
  namespace: vllm-system
data:
  MODEL_NAME: "microsoft/DialoGPT-medium"
  MODEL_REVISION: "main"
  DTYPE: "float16"
  MAX_MODEL_LEN: "2048"
  GPU_MEMORY_UTILIZATION: "0.9"
  MAX_NUM_SEQS: "256"
  TENSOR_PARALLEL_SIZE: "1"
```

### 3. Deploying with Helm

```yaml
# vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-deployment
  namespace: vllm-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: vllm-config
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            nvidia.com/gpu: 1
        # startupProbe: covers model loading. Until it succeeds,
        # liveness and readiness are not even evaluated.
        # 60 failures x 10s = 10 minutes of headroom to load the weights.
        startupProbe:
          httpGet:
            path: /health
            port: 8000
          failureThreshold: 60
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          periodSeconds: 5
```

!!! danger "Without `startupProbe` the pod ends up in CrashLoopBackOff"
    A `livenessProbe` with `initialDelaySeconds: 30` declares the container dead after 30 seconds. Loading the weights of a 13B model from disk into the GPU takes **several minutes**, so Kubernetes kills it right before it finishes starting, restarts it, and kills it again: an infinite loop that also burns GPU time on every attempt.

    The `startupProbe` exists precisely for this: while it has not succeeded, the other two probes stay suspended. Tune `failureThreshold` to your model's real load time with room to spare — overshooting is safer than falling short.

### 4. Service and Ingress

```yaml
# vllm-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
  namespace: vllm-system
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

```yaml
# vllm-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vllm-ingress
  namespace: vllm-system
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: vllm.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vllm-service
            port:
              number: 80
```

## 📊 Auto-Scaling with HPA

### Metrics Configuration

```yaml
# metrics-server.yaml (if it isn't already installed)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: metrics-server
  namespace: kube-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-server
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - name: metrics-server
        image: k8s.gcr.io/metrics-server/metrics-server:v0.6.3
        args:
        - --kubelet-insecure-tls
        - --kubelet-preferred-address-types=InternalIP
```

### HPA for vLLM

```yaml
# vllm-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
  namespace: vllm-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-deployment
  minReplicas: 1
  maxReplicas: 10
  metrics:
  # Primary metric: requests waiting in the scheduler queue.
  # This is what actually reflects the service falling behind.
  - type: Pods
    pods:
      metric:
        name: vllm:num_requests_waiting
      target:
        type: AverageValue
        averageValue: "5"
  # Secondary: KV cache occupancy. Close to 100% means no more
  # concurrent requests fit, however much GPU headroom is left.
  - type: Pods
    pods:
      metric:
        name: vllm:kv_cache_usage_perc
      target:
        type: AverageValue
        averageValue: "900m"   # 0.9 = 90%
  behavior:
    scaleUp:
      # A new pod takes minutes to load the model: scaling aggressively
      # buys nothing and just doubles GPU consumption.
      stabilizationWindowSeconds: 120
    scaleDown:
      stabilizationWindowSeconds: 600
```

!!! warning "Do not scale an inference service by CPU"
    This is the most common mistake when reusing a web application's HPA. During token generation the process is **waiting on the GPU**, not computing: CPU stays low even while the service is saturated and the queue is growing. An HPA on CPU at 70% simply never fires, or fires when it no longer matters.

    The two metrics that do correlate with real saturation are queue length (`vllm:num_requests_waiting`) and KV cache occupancy, which is what actually caps concurrency. Both need [prometheus-adapter](https://github.com/kubernetes-sigs/prometheus-adapter) to be exposed to the HPA. Details on both in [LLM Monitoring](monitoreo_llms.md).

## 🔧 Advanced Optimizations

### 1. Model Caching and Warm-up

```yaml
# vllm-deployment-optimized.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-deployment-optimized
  namespace: vllm-system
spec:
  template:
    spec:
      initContainers:
      - name: model-cache
        image: vllm/vllm-openai:latest
        command: ["/bin/sh", "-c"]
        args:
        - |
          python -c "
          from vllm import LLM
          llm = LLM(model='microsoft/DialoGPT-medium', download_dir='/tmp/models')
          print('Model cached successfully')
          "
        volumeMounts:
        - name: model-cache
          mountPath: /tmp/models
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        env:
        - name: VLLM_CACHE_DIR
          value: /tmp/models
        volumeMounts:
        - name: model-cache
          mountPath: /tmp/models
      volumes:
      - name: model-cache
        emptyDir: {}
```

### 2. Multi-Model Deployment

```yaml
# multi-model-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: multi-model-config
  namespace: vllm-system
data:
  models.json: |
    [
      {
        "name": "gpt2-medium",
        "model": "microsoft/DialoGPT-medium",
        "max_model_len": 1024
      },
      {
        "name": "gpt2-large",
        "model": "microsoft/DialoGPT-large",
        "max_model_len": 1024
      }
    ]
```

### 3. GPU Memory Optimization

```yaml
# vllm-gpu-optimized.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-gpu-optimized
  namespace: vllm-system
spec:
  template:
    spec:
      containers:
      - name: vllm
        env:
        - name: VLLM_GPU_MEMORY_UTILIZATION
          value: "0.95"
        - name: VLLM_MAX_NUM_SEQS
          value: "128"
        - name: VLLM_MAX_NUM_BATCHED_TOKENS
          value: "4096"
        - name: VLLM_ENABLE_CHUNKED_PREFILL
          value: "true"
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 32Gi
          requests:
            nvidia.com/gpu: 1
            memory: 16Gi
```

## 📈 Monitoring and Observability

### vLLM Metrics

```yaml
# prometheus-service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
  namespace: vllm-system
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "vLLM Performance Dashboard",
    "panels": [
      {
        "title": "GPU Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "nvidia_gpu_utilization{namespace=\"vllm-system\"}",
            "legendFormat": "{{pod}}"
          }
        ]
      },
      {
        "title": "Request Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(vllm_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

## 🔄 Update Strategies

### Rolling Updates

```yaml
# vllm-deployment-rolling.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-deployment
  namespace: vllm-system
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    # ... rest of the configuration
```

### Blue-Green Deployment

```yaml
# blue-green-deployment.sh
#!/bin/bash

# Create the new version (green)
kubectl apply -f vllm-deployment-green.yaml

# Wait until it is ready
kubectl wait --for=condition=available --timeout=300s deployment/vllm-deployment-green -n vllm-system

# Point the service at green
kubectl patch service vllm-service -n vllm-system -p '{"spec":{"selector":{"version":"green"}}}'

# Confirm everything works
# ... tests ...

# Remove blue
kubectl delete deployment vllm-deployment-blue -n vllm-system
```

## 🛡️ Security and Compliance

### Network Policies

```yaml
# vllm-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
  namespace: vllm-system
spec:
  podSelector:
    matchLabels:
      app: vllm
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### Secret Management

!!! danger "base64 is not encryption"
    A Kubernetes `Secret` stores the value in base64, which is **encoding, not encryption**: anyone who can read the YAML decodes it with a single command. A manifest like that is **never** committed to Git.

    For GitOps use SOPS, Sealed Secrets or External Secrets Operator. A comparison of all three is in [Secrets in GitOps](../cybersecurity/secrets_gitops.md).

Object reference (to create it from the command line, not to commit it):

```bash
# Create the Secret without the token ever touching a file in the repo
kubectl create secret generic vllm-secrets \
  --namespace vllm-system \
  --from-literal=huggingface-token="$HF_TOKEN" \
  --from-literal=api-key="$VLLM_API_KEY"
```

```yaml
# How the Deployment consumes it: by reference, without exposing the value
env:
  - name: HUGGING_FACE_HUB_TOKEN
    valueFrom:
      secretKeyRef:
        name: vllm-secrets
        key: huggingface-token
```

## 📊 Cost Optimization

### Spot and Preemptible Instances

```yaml
# spot-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-spot
  namespace: vllm-system
spec:
  template:
    spec:
      tolerations:
      - key: "cloud.google.com/gke-spot"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      nodeSelector:
        cloud.google.com/gke-spot: "true"
      # ... rest of the configuration
```

### Cost-Driven Auto-scaling

```yaml
# cost-based-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-cost-hpa
  namespace: vllm-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-deployment
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: External
    external:
      metric:
        name: cloud_provider_cost_per_hour
      target:
        type: AverageValue
        averageValue: 2.0
```

## 🔍 Troubleshooting

### Common Problems

1. **Out of Memory (OOM)**:
   ```bash
   # Check the logs
   kubectl logs -f deployment/vllm-deployment -n vllm-system

   # Tune the configuration
   kubectl edit configmap vllm-config -n vllm-system
   ```

2. **GPU Not Available**:
   ```bash
   # Check GPU allocation
   kubectl describe node <node-name>

   # Check GPU operator
   kubectl get pods -n gpu-operator
   ```

3. **Slow Inference**:
   ```bash
   # Check the metrics
   kubectl exec -it deployment/vllm-deployment -n vllm-system -- curl http://localhost:8000/metrics

   # Tune the batch size
   kubectl edit configmap vllm-config -n vllm-system
   ```

## 🎯 Best Practices

### Performance
- Use A100/H100 GPUs for the best throughput
- Set `tensor_parallel_size` when running on multiple GPUs
- Cache models ahead of time
- Keep an eye on metrics continuously

### Reliability
- Define meaningful health checks
- Use rolling updates for zero-downtime releases
- Set resource limits and requests
- Add circuit breakers

### Security
- Store API tokens in secrets
- Enforce network policies
- Audit access logs
- Keep models up to date

### Cost Management
- Use spot instances wherever it makes sense
- Implement smart auto-scaling
- Track costs in real time
- Squeeze the most out of every GPU

## 📚 Further Reading

- [vLLM Documentation](https://vllm.readthedocs.io/)
- [Kubernetes GPU Guide](https://kubernetes.io/docs/tasks/manage-gpus/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/)
- [Prometheus Metrics](https://prometheus.io/docs/)

## 🤝 Contributing

This guide is part of the Frikiteam Docs project. If you spot an error or want to contribute improvements:

1. Fork the repository
2. Create a branch for your feature
3. Open a Pull Request

Thanks for helping grow shared knowledge!
