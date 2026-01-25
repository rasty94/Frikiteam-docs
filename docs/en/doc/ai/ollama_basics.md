# Ollama: Installation and Getting Started

🚧 **TRANSLATION PENDING** - Last updated in Spanish: 2026-01-25


Ollama is a tool that simplifies running Large Language Models (LLMs) locally. This guide will help you install and start using Ollama in your DevOps environment.

## 📦 Installation

### macOS
```bash
# Using Homebrew (recommended)
brew install ollama

# Or using the official script
curl -fsSL https://ollama.ai/install.sh | sh
```

### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://ollama.ai/install.sh | sh

# Or using the package
sudo apt update
sudo apt install ollama
```

### Windows
```powershell
# Using Winget
winget install Ollama.Ollama

# Or download from the official website
```

### Installation verification
```bash
ollama --version
# Output: ollama version is 0.1.x
```

## 🚀 Getting Started

### Start Ollama
```bash
# Start the service (runs in background)
ollama serve

# Or on macOS/Linux with launchd/systemd
brew services start ollama  # macOS
sudo systemctl start ollama # Linux
```

### Download your first model
```bash
# List available models
ollama list

# Download a small model to start
ollama pull llama2:7b

# Popular models
ollama pull llama2          # 7B parameters, good balance
ollama pull codellama       # Specialized in code
ollama pull mistral         # Efficient model
ollama pull phi             # Very small, fast
```

### Run a model
```bash
# Interactive mode
ollama run llama2

# Once inside, you can ask questions:
# >>> What is Kubernetes?
# >>> Create a bash script for backup
# >>> Explain container concept
```

## 🛠️ Advanced Usage

### Run specific models
```bash
# Models with different sizes
ollama run llama2:13b      # Smarter, slower
ollama run llama2:7b       # Balance speed/intelligence
ollama run llama2:3.2b     # Very fast, less intelligent

# Specialized models
ollama run codellama       # For code generation
ollama run mathstral       # For mathematics
ollama run llama2-uncensored # Without content restrictions
```

### REST API
```bash
# Start API server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

```python
# Python usage example
import requests

response = requests.post('http://localhost:11434/api/generate',
    json={
        'model': 'llama2',
        'prompt': 'Explain Docker in 3 lines',
        'stream': False
    })

print(response.json()['response'])
```

### Model Management
```bash
# List installed models
ollama list

# View detailed information
ollama show llama2

# Remove a model
ollama rm llama2:7b

# Copy a model with new name
ollama cp llama2 my-custom-model

# Create custom model
echo 'FROM llama2
PARAMETER temperature 0.8
PARAMETER top_p 0.9' > Modelfile

ollama create my-model -f Modelfile
```

## ⚙️ Configuration and Optimization

### Environment Variables
```bash
# Models directory
export OLLAMA_MODELS=/opt/ollama/models

# Custom port
export OLLAMA_HOST=0.0.0.0:8080

# GPU (if available)
export OLLAMA_GPU_LAYERS=35  # For large models
```

### System Configuration
```yaml
# ~/.ollama/config.yaml (if exists)
models:
  - name: llama2
    parameters:
      temperature: 0.7
      top_p: 0.9
      max_tokens: 2048
```

## 🔧 DevOps Integration

### In Docker
```dockerfile
FROM ollama/ollama:latest

# Pre-download models
RUN ollama serve & sleep 5 && \
    ollama pull llama2:7b && \
    ollama pull codellama:7b

EXPOSE 11434
CMD ["ollama", "serve"]
```

### In Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        volumeMounts:
        - name: models
          mountPath: /root/.ollama/models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ollama-models-pvc
```

### Automation Scripts
```bash
#!/bin/bash
# setup_ollama.sh

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start service
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for ready
sleep 10

# Download essential models
ollama pull llama2:7b
ollama pull codellama:7b
ollama pull mistral:7b

echo "Ollama configured with basic models"
```

## 📊 Monitoring and Troubleshooting

### View logs
```bash
# Service logs
journalctl -u ollama -f

# Ollama logs
tail -f ~/.ollama/logs/server.log
```

### Common issues
```bash
# If it doesn't start
sudo systemctl status ollama
ps aux | grep ollama

# If it doesn't respond
curl http://localhost:11434/api/tags

# Free GPU memory
ollama stop all-models
```

### Performance metrics
```bash
# View GPU usage
nvidia-smi

# View processes
ps aux --sort=-%mem | head

# Continuous monitoring
watch -n 1 nvidia-smi
```

## 🎯 DevOps Use Cases

### 1. Log analysis
```bash
# Analyze application logs
cat app.log | ollama run llama2 "Analyze these logs and find errors:"

# Kubernetes troubleshooting
kubectl logs pod-name | ollama run llama2 "Explain these K8s errors:"
```

### 2. Code generation
```bash
# Automation scripts
ollama run codellama "Create a bash script for PostgreSQL backup"

# IaC configurations
ollama run llama2 "Generate Terraform configuration for an EKS cluster"
```

### 3. Documentation
```bash
# Create README
ollama run llama2 "Create a README.md for a user REST API"

# Document code
ollama run codellama "Document this Python function:"
```

## 🔗 Additional Resources

- [Official Documentation](https://github.com/ollama/ollama)
- [Available Models](https://ollama.ai/library)
- [API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Discord Community](https://discord.gg/ollama)