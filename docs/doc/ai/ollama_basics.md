---
title: "Ollama: Instalación y primeros pasos"
description: "Guía completa de Ollama: instalación, gestión de modelos locales, APIs REST, integración con Docker y casos de uso en DevOps"
keywords: "ollama, llm, local models, docker, api, devops"
tags: [ai, ollama, llm, docker, api]
updated: 2026-01-25
difficulty: intermediate
estimated_time: 4 min
category: Inteligencia Artificial
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Python básico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ollama: Instalación y primeros pasos

Ollama es una herramienta que simplifica la ejecución de Large Language Models (LLMs) localmente. Esta guía te ayudará a instalar y comenzar a usar Ollama en tu entorno DevOps.

## 📦 Instalación

### macOS
```bash
# Usando Homebrew (recomendado)
brew install ollama

# O usando el script oficial
curl -fsSL https://ollama.ai/install.sh | sh
```

### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://ollama.ai/install.sh | sh

# O usando el paquete
sudo apt update
sudo apt install ollama
```

### Windows
```powershell
# Usando Winget
winget install Ollama.Ollama

# O descarga desde el sitio web oficial
```

### Verificación de instalación
```bash
ollama --version
# Output: ollama version is 0.1.x
```

## 🚀 Primeros pasos

### Iniciar Ollama
```bash
# Inicia el servicio (se ejecuta en background)
ollama serve

# O en macOS/Linux con launchd/systemd
brew services start ollama  # macOS
sudo systemctl start ollama # Linux
```

### Descargar tu primer modelo
```bash
# Lista modelos disponibles
ollama list

# Descarga un modelo pequeño para empezar
ollama pull llama2:7b

# Modelos populares
ollama pull llama2          # 7B parámetros, buen balance
ollama pull codellama       # Especializado en código
ollama pull mistral         # Modelo eficiente
ollama pull phi             # Muy pequeño, rápido
```

### Ejecutar un modelo
```bash
# Modo interactivo
ollama run llama2

# Una vez dentro, puedes hacer preguntas:
# >>> ¿Qué es Kubernetes?
# >>> Crea un script bash para backup
# >>> Explica el concepto de containers
```

## 🛠️ Uso avanzado

### Ejecutar modelos específicos
```bash
# Modelos con diferentes tamaños
ollama run llama2:13b      # Más inteligente, más lento
ollama run llama2:7b       # Balance velocidad/inteligencia
ollama run llama2:3.2b     # Muy rápido, menos inteligente

# Modelos especializados
ollama run codellama       # Para generación de código
ollama run mathstral       # Para matemáticas
ollama run llama2-uncensored # Sin restricciones de contenido
```

### API REST
```bash
# Inicia el servidor API
ollama serve

# Verifica que esté corriendo
curl http://localhost:11434/api/tags
```

```python
# Ejemplo de uso con Python
import requests

response = requests.post('http://localhost:11434/api/generate',
    json={
        'model': 'llama2',
        'prompt': 'Explica Docker en 3 líneas',
        'stream': False
    })

print(response.json()['response'])
```

### Gestión de modelos
```bash
# Listar modelos instalados
ollama list

# Ver información detallada
ollama show llama2

# Eliminar un modelo
ollama rm llama2:7b

# Copiar un modelo con nuevo nombre
ollama cp llama2 my-custom-model

# Crear modelo personalizado
echo 'FROM llama2
PARAMETER temperature 0.8
PARAMETER top_p 0.9' > Modelfile

ollama create my-model -f Modelfile
```

## ⚙️ Configuración y optimización

### Variables de entorno
```bash
# Directorio de modelos
export OLLAMA_MODELS=/opt/ollama/models

# Puerto personalizado
export OLLAMA_HOST=0.0.0.0:8080

# GPU (si disponible)
export OLLAMA_GPU_LAYERS=35  # Para modelos grandes
```

### Configuración del sistema
```yaml
# ~/.ollama/config.yaml (si existe)
models:
  - name: llama2
    parameters:
      temperature: 0.7
      top_p: 0.9
      max_tokens: 2048
```

## 🔧 Integración con DevOps

### En Docker
```dockerfile
FROM ollama/ollama:latest

# Pre-descarga modelos
RUN ollama serve & sleep 5 && \
    ollama pull llama2:7b && \
    ollama pull codellama:7b

EXPOSE 11434
CMD ["ollama", "serve"]
```

### En Kubernetes
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

### Scripts de automatización
```bash
#!/bin/bash
# setup_ollama.sh

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar servicio
sudo systemctl enable ollama
sudo systemctl start ollama

# Esperar a que esté listo
sleep 10

# Descargar modelos esenciales
ollama pull llama2:7b
ollama pull codellama:7b
ollama pull mistral:7b

echo "Ollama configurado con modelos básicos"
```

## 📊 Monitoreo y troubleshooting

### Ver logs
```bash
# Logs del servicio
journalctl -u ollama -f

# Logs de Ollama
tail -f ~/.ollama/logs/server.log
```

### Problemas comunes
```bash
# Si no inicia
sudo systemctl status ollama
ps aux | grep ollama

# Si no responde
curl http://localhost:11434/api/tags

# Liberar memoria GPU
ollama stop all-models
```

### Métricas de rendimiento
```bash
# Ver uso de GPU
nvidia-smi

# Ver procesos
ps aux --sort=-%mem | head

# Monitoreo continuo
watch -n 1 nvidia-smi
```

## 🎯 Casos de uso en DevOps

### 1. Análisis de logs
```bash
# Analizar logs de aplicación
cat app.log | ollama run llama2 "Analiza estos logs y encuentra errores:"

# Troubleshooting Kubernetes
kubectl logs pod-name | ollama run llama2 "Explica estos errores de K8s:"
```

### 2. Generación de código
```bash
# Scripts de automatización
ollama run codellama "Crea un script bash para backup de PostgreSQL"

# Configuraciones IaC
ollama run llama2 "Genera configuración Terraform para un cluster EKS"
```

### 3. Documentación
```bash
# Crear README
ollama run llama2 "Crea un README.md para una API REST de usuarios"

# Documentar código
ollama run codellama "Documenta esta función Python:"
```

## 🔗 Recursos adicionales

- [Documentación oficial](https://github.com/ollama/ollama)
- [Modelos disponibles](https://ollama.ai/library)
- [API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Comunidad Discord](https://discord.gg/ollama)