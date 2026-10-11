---
title: "LLM Model Optimization"
description: "Optimization techniques for running LLMs on limited hardware: quantization, pruning, distillation and deployment strategies"
tags: ['ai', 'llm', 'performance', 'quantization']
difficulty: intermediate
estimated_time: 13 min
category: Artificial Intelligence
status: published
prerequisites: ["llms_fundamentals", "ollama_basics"]
updated: 2026-10-11
---

# LLM Model Optimization

## Overview

Optimizing LLM models is crucial for running large models on limited hardware. This guide covers techniques such as quantization, pruning, distillation and deployment strategies that reduce memory usage and improve performance without significantly sacrificing quality.

## 🎯 Why Optimize LLM Models

### Common Problems Without Optimization

- **Insufficient memory:** Models with 7B-70B parameters require 14-140GB+ of RAM/VRAM
- **Slow speed:** Inference can take seconds per token
- **High costs:** Expensive GPU hardware for deployment
- **Limited scalability:** Difficulty serving multiple users

### Benefits of Optimization

- ✅ **70-90% less memory** with 4-bit quantization
- ✅ **2-5x faster** inference
- ✅ **More accessible hardware:** Mid-range GPUs or CPUs
- ✅ **Higher throughput:** More simultaneous users
- ✅ **Lower costs:** Less hardware required

## 🔢 Quantization

### What Is Quantization?

Quantization reduces the precision of the model's weights from float32 (4 bytes) to smaller formats such as float16, int8 or int4, while keeping the model functional.

### Types of Quantization

#### 1. **Post-Training Quantization (PTQ)**
- Applied after training
- Does not require retraining
- Quick and easy to implement

```bash
# Example with Ollama (GGUF quantization)
ollama pull llama2:7b
ollama pull llama2:7b-q4_0  # 4-bit quantized version
```

#### 2. **Quantization-Aware Training (QAT)**
- Training takes quantization into account
- Better accuracy but more complex
- Used in critical production systems

### Quantization Levels

| Precision | Memory | Speed | Quality | Use |
|-----------|---------|-----------|---------|-----|
| FP32 | 100% | 100% | 100% | Training |
| FP16 | 50% | ~2x | 99.9% | Modern GPUs |
| INT8 | 25% | ~4x | 98-99% | GPUs, CPUs |
| INT4 | 12.5% | ~8x | 95-97% | CPUs, edge |

### Practical Implementation

#### With Ollama (GGUF)

```bash
# Download base model
ollama pull llama2:7b

# Create custom quantized model
cat > Modelfile << EOF
FROM llama2:7b
PARAMETER temperature 0.8
PARAMETER top_p 0.9
QUANTIZE q4_0
EOF

ollama create llama2-custom:q4_0 -f Modelfile
```

#### With llama.cpp

```bash
# Convert and quantize model
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Convert PyTorch to GGML
python convert.py --model /path/to/model.bin --type f16

# Quantize to different formats
./quantize /path/to/model-f16.bin /path/to/model-q4_0.bin q4_0
```

## 🌿 Pruning

### Basic Concept

Pruning removes neural connections that contribute little, reducing the model size without significantly affecting performance.

### Pruning Techniques

#### 1. **Weight Pruning**
- Removes individual weights below a threshold
- Effective but requires subsequent fine-tuning

#### 2. **Structured Pruning**
- Removes entire neurons, layers or attention heads
- More efficient for hardware
- Examples: removing 20-30% of attention heads

#### 3. **Dynamic Pruning**
- Adjusts the structure during inference
- Trade-off between quality and speed

### Practical Example

```python
import torch
from transformers import AutoModelForCausalLM

# Load model
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")

# Apply pruning (simplified)
def prune_weights(model, threshold=0.1):
    for name, param in model.named_parameters():
        if 'weight' in name:
            mask = torch.abs(param) > threshold
            param.data *= mask.float()

prune_weights(model)
```

## 🧪 Distillation (Knowledge Distillation)

### What Is Distillation?

Distillation transfers knowledge from a large model ("teacher") to a smaller one ("student"), retaining most of the performance.

### Distillation Process

1. **Teacher Model:** Large, accurate model
2. **Student Model:** Small model to be trained
3. **Soft Targets:** The student learns from the teacher's probability distributions
4. **Fine-tuning:** Final adjustment on real data

### Advantages

- ✅ **Better quality/size ratio** than quantization alone
- ✅ **Smaller model** that is still capable
- ✅ **Effective transfer learning**

### Example with Hugging Face

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Teacher model (large)
teacher = AutoModelForCausalLM.from_pretrained("gpt2-large")

# Student model (small)
student = AutoModelForCausalLM.from_pretrained("gpt2")

# Distillation loss function
def distillation_loss(student_logits, teacher_logits, temperature=2.0):
    soft_targets = torch.softmax(teacher_logits / temperature, dim=-1)
    student_soft = torch.log_softmax(student_logits / temperature, dim=-1)
    return torch.nn.functional.kl_div(student_soft, soft_targets, reduction='batchmean')
```

## 🚀 Deployment Strategies

### 1. **CPU vs GPU Optimization**

#### CPU Optimizations
```bash
# Use llama.cpp with CPU optimizations
./main -m model.bin --threads 8 --ctx-size 2048 -p "Prompt"
```

#### GPU Optimizations
```python
# With vLLM
from vllm import LLM

llm = LLM(
    model="microsoft/DialoGPT-large",
    tensor_parallel_size=2,  # Multi-GPU
    gpu_memory_utilization=0.9,
    max_model_len=4096
)
```

### 2. **Batch Processing**

```python
# Batch processing for higher throughput
prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]

# Batch inference
outputs = llm.generate(prompts, max_tokens=100)
```

### 3. **Model Caching and Prefilling**

```python
# KV cache for common prompts
from transformers import Cache

cache = Cache()
model = AutoModelForCausalLM.from_pretrained("gpt2", use_cache=True)

# First inference creates the cache
output1 = model.generate("Common prefix", use_cache=True)

# Subsequent inferences reuse the cache
output2 = model.generate("Common prefix + continuation", past_key_values=output1.past_key_values)
```

## 📊 Benchmarks and Comparisons

### Typical Optimization Results

| Technique | Model | Original Size | Optimized Size | Degradation | Speed |
|---------|--------|-----------------|-------------------|-------------|-----------|
| FP16 | LLaMA-7B | 13GB | 6.5GB | ~0% | 2x |
| INT8 | LLaMA-7B | 13GB | 3.5GB | 1-2% | 4x |
| INT4 | LLaMA-7B | 13GB | 1.8GB | 3-5% | 8x |
| Pruning 20% | GPT-2 | 1.5GB | 1.2GB | 2-3% | 1.5x |
| Distillation | BERT Large→Base | 340M→110M params | 67% fewer | 3-5% | 2x |

### Hardware Recommendations

| Hardware | Maximum Model | Recommended Technique |
|----------|----------------|---------------------|
| CPU (16GB RAM) | 7B Q4 | GGUF + llama.cpp |
| GPU RTX 3060 (12GB) | 13B FP16 | vLLM + tensor parallel |
| GPU RTX 4080 (16GB) | 30B Q4 | Ollama + quantization |
| CPU Server (128GB) | 70B Q4 | llama.cpp + threads |

## 🛠️ Tools and Frameworks

### Optimization Frameworks

#### 1. **GGUF (llama.cpp model format, successor to GGML)**
- llama.cpp quantization format
- Compatible with multiple platforms
- Optimized for CPU and GPU

```bash
# Convert model to GGUF
python convert-hf-to-gguf.py --model /path/to/model --outdir /output/dir
```

#### 2. **AWQ (Activation-aware Weight Quantization)**
- Quantization that takes activations into account
- Better accuracy than standard PTQ
- Especially good for GPUs

#### 3. **GPTQ (GPT Quantization)**
- Post-training quantization
- Maintains high quality
- Compatible with AutoGPTQ

### Practical Tools

```bash
# Benchmark with llama.cpp
./llama-bench -m model.gguf -p 512 -n 128 -t 8

# Memory profiling
python -c "
import torch
from transformers import AutoModel
model = AutoModel.from_pretrained('model')
print(f'Model size: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M parameters')
print(f'Memory: {torch.cuda.memory_allocated()/1e9:.2f}GB')
"
```

## ⚠️ Considerations and Limitations

### Important Trade-offs

- **Accuracy vs Speed:** More quantization = more speed but less accuracy
- **Quality vs Size:** Smaller models may lose specific capabilities
- **Hardware vs Software:** Optimizations depend on the target hardware

### Common Mistakes

1. **Excessive quantization:** INT2/INT3 can make models unusable
2. **Aggressive pruning:** Removing >50% can cause performance collapse
3. **Ignoring fine-tuning:** Optimized models need subsequent adjustment

### Best Practices

- ✅ **Test thoroughly** after optimizing
- ✅ **Monitor quality** with automated metrics
- ✅ **A/B testing** between optimized versions
- ✅ **Document trade-offs** for stakeholders

## References

- [llama.cpp Documentation](https://github.com/ggerganov/llama.cpp)
- [Hugging Face Optimum](https://huggingface.co/docs/optimum/index)
- [vLLM Performance Guide](https://docs.vllm.ai/en/latest/)
- [GPTQ Paper](https://arxiv.org/abs/2210.17323)

## 📚 Next Steps

After optimizing models, consider:

1. **[Local Chatbots](chatbots_locales.md)** - Building conversational interfaces
2. **[Prompt Engineering](prompt_engineering.md)** - Techniques for better results
3. **[Production Deployment](despliegue_kubernetes.md)** - Serving optimized models at scale

---

*Have you optimized any LLM model? Share your experiences and best practices in the comments.*
