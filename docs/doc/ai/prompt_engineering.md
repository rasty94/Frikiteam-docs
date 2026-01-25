---
title: "Prompt Engineering Avanzado para LLMs"
description: "Técnicas profesionales de prompt engineering: zero-shot, few-shot, chain-of-thought, y evaluación de prompts para modelos locales"
date: 2026-01-25
tags: [ai, llm, prompt-engineering, best-practices, optimization]
difficulty: intermediate
estimated_time: "40 min"
category: ai
status: published
prerequisites: ["llms_fundamentals", "ollama_basics"]
---

# Prompt Engineering Avanzado para LLMs

> **Tiempo de lectura:** 40 minutos | **Dificultad:** Intermedia | **Categoría:** Inteligencia Artificial

## Resumen

El prompt engineering es el arte y ciencia de diseñar instrucciones efectivas para LLMs. Esta guía cubre técnicas profesionales desde zero-shot hasta chain-of-thought, con ejemplos prácticos y frameworks de evaluación para modelos locales.

## 🎯 Por Qué Import

a el Prompt Engineering

### Impacto del Prompt en Resultados

```python
# Prompt mal diseñado
prompt_malo = "dame info sobre kubernetes"
# Resultado: vago, poco útil, sin estructura

# Prompt bien diseñado
prompt_bueno = """
Actúa como un experto en Kubernetes. Explica los conceptos de Pods, Deployments y Services en el contexto de una aplicación web de 3 capas (frontend, backend, database).

Requisitos:
- Audiencia: Desarrolladores con conocimiento básico de Docker
- Longitud: 300-400 palabras
- Incluir: 1 ejemplo de YAML por concepto
- Formato: Markdown con secciones H2

Estructura:
1. Pods - Qué son y cuándo usarlos
2. Deployments - Gestión de réplicas
3. Services - Exponer aplicaciones
"""
# Resultado: estructurado, relevante, accionable
```

### Beneficios de Buenos Prompts

- ✅ **Reducción de iteraciones:** Resultado correcto en primer intento
- ✅ **Consistencia:** Outputs predecibles y reproducibles
- ✅ **Calidad superior:** Respuestas más precisas y útiles
- ✅ **Ahorro de tokens:** Menos correcciones = menos costo
- ✅ **Automatización efectiva:** Integrable en pipelines

## 📋 Anatomía de un Buen Prompt

### Componentes Fundamentales

```python
class PromptTemplate:
    def __init__(
        self,
        role: str,  # Personalidad/expertise del LLM
        task: str,  # Qué debe hacer
        context: str,  # Información de fondo
        constraints: list,  # Limitaciones y requisitos
        output_format: str,  # Formato deseado
        examples: list = None  # Ejemplos (few-shot)
    ):
        self.role = role
        self.task = task
        self.context = context
        self.constraints = constraints
        self.output_format = output_format
        self.examples = examples or []
    
    def build(self) -> str:
        """Construye el prompt completo."""
        
        prompt_parts = []
        
        # 1. Role/Persona
        if self.role:
            prompt_parts.append(f"Rol: {self.role}\n")
        
        # 2. Contexto
        if self.context:
            prompt_parts.append(f"Contexto:\n{self.context}\n")
        
        # 3. Ejemplos (few-shot)
        if self.examples:
            prompt_parts.append("Ejemplos:")
            for i, example in enumerate(self.examples, 1):
                prompt_parts.append(f"\nEjemplo {i}:")
                prompt_parts.append(f"Input: {example['input']}")
                prompt_parts.append(f"Output: {example['output']}\n")
        
        # 4. Tarea principal
        prompt_parts.append(f"Tarea:\n{self.task}\n")
        
        # 5. Constraints
        if self.constraints:
            prompt_parts.append("Requisitos:")
            for constraint in self.constraints:
                prompt_parts.append(f"- {constraint}")
            prompt_parts.append("")
        
        # 6. Formato de salida
        if self.output_format:
            prompt_parts.append(f"Formato de salida:\n{self.output_format}\n")
        
        return "\n".join(prompt_parts)

# Ejemplo de uso
template = PromptTemplate(
    role="Experto en seguridad de contenedores Docker",
    task="Audita este Dockerfile y sugiere mejoras de seguridad",
    context="""
    Dockerfile actual:
    FROM ubuntu:latest
    RUN apt-get update && apt-get install -y python3
    COPY . /app
    WORKDIR /app
    CMD ["python3", "app.py"]
    """,
    constraints=[
        "Priorizar imágenes oficiales y slim",
        "Usuario no-root obligatorio",
        "Multi-stage build si es posible",
        "Minimizar layers"
    ],
    output_format="""
    JSON con:
    {
      "issues": ["..."],
      "improvements": ["..."],
      "dockerfile_improved": "..."
    }
    """
)

prompt = template.build()
print(prompt)
```

## 🎓 Técnica 1: Zero-Shot Prompting

### Definición

Dar instrucciones claras sin ejemplos previos. El modelo debe inferir qué hacer solo por la descripción.

### Cuándo Usar

- Tareas simples y bien definidas
- Modelos grandes (13B+) con buena comprensión
- Cuando no hay ejemplos disponibles

### Ejemplo Práctico

```python
def zero_shot_classification(text: str, categories: list) -> str:
    """Clasifica texto en categorías sin ejemplos previos."""
    
    prompt = f"""
Clasifica el siguiente texto en UNA de estas categorías: {', '.join(categories)}

Texto: "{text}"

Responde SOLO con el nombre de la categoría, sin explicaciones.

Categoría:"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2:13b-chat-q4_0",
        "prompt": prompt,
        "temperature": 0.1,
        "stream": False
    })
    
    return response.json()["response"].strip()

# Uso
categories = ["Bug", "Feature Request", "Documentation", "Question"]
issue_text = "The application crashes when clicking the submit button"

category = zero_shot_classification(issue_text, categories)
print(f"Categoría: {category}")  # Output: Bug
```

### Mejores Prácticas Zero-Shot

```python
# ❌ Prompt vago
prompt_malo = "Clasifica esto: 'app crashes'"

# ✅ Prompt claro y específico
prompt_bueno = """
Tarea: Clasificación de tickets de soporte

Categorías válidas:
1. BUG - Error funcional en la aplicación
2. FEATURE - Solicitud de nueva funcionalidad
3. DOCS - Problema con documentación
4. QUESTION - Consulta de usuario

Texto a clasificar: "The application crashes when clicking the submit button"

Instrucciones:
- Responde SOLO con el nombre de la categoría
- Si no estás seguro, elige la más probable
- Formato: Una palabra en mayúsculas

Categoría:"""
```

## 🎯 Técnica 2: Few-Shot Prompting

### Definición

Proporcionar ejemplos de entrada-salida antes de la tarea real para guiar al modelo.

### Cuándo Usar

- Tareas complejas con formato específico
- Modelos medianos (7B-13B) que necesitan guía
- Cuando necesitas salidas consistentes

### Ejemplo Práctico

```python
def few_shot_entity_extraction(text: str) -> dict:
    """Extrae entidades usando few-shot learning."""
    
    prompt = f"""
Extrae entidades técnicas de descripciones de incidentes.

Ejemplo 1:
Texto: "PostgreSQL database on srv-db-01 is experiencing high CPU usage"
Entidades: {% raw %}{"technology": "PostgreSQL", "resource": "database", "server": "srv-db-01", "metric": "CPU usage", "status": "high"}{% endraw %}

Ejemplo 2:
Texto: "Nginx reverse proxy returning 502 errors for api.example.com"
Entidades: {% raw %}{"technology": "Nginx", "resource": "reverse proxy", "error": "502", "domain": "api.example.com"}{% endraw %}

Ejemplo 3:
Texto: "Kubernetes pod web-frontend-abc123 is in CrashLoopBackOff state"
Entidades: {% raw %}{"technology": "Kubernetes", "resource": "pod", "name": "web-frontend-abc123", "status": "CrashLoopBackOff"}{% endraw %}

Ahora extrae entidades de este texto:
Texto: "{text}"
Entidades:"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2:13b-chat-q4_0",
        "prompt": prompt,
        "temperature": 0.2,
        "stream": False,
        "format": "json"
    })
    
    import json
    return json.loads(response.json()["response"])

# Uso
incident = "Redis cache cluster on redis-prod-cluster-01 showing memory leak"
entities = few_shot_entity_extraction(incident)
print(entities)
# Output: {"technology": "Redis", "resource": "cache cluster", "name": "redis-prod-cluster-01", "issue": "memory leak"}
```

### Optimización de Few-Shot

```python
class FewShotOptimizer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def find_optimal_examples(
        self,
        task_description: str,
        candidate_examples: list,
        test_cases: list,
        max_examples: int = 5
    ) -> list:
        """
        Encuentra el número y selección óptima de ejemplos.
        
        Args:
            task_description: Descripción de la tarea
            candidate_examples: Pool de ejemplos posibles
            test_cases: Casos de prueba para evaluación
            max_examples: Máximo número de ejemplos a probar
        
        Returns:
            Lista de ejemplos óptimos
        """
        
        best_score = 0
        best_examples = []
        
        # Probar diferentes combinaciones
        from itertools import combinations
        
        for n in range(1, min(max_examples + 1, len(candidate_examples) + 1)):
            for example_combo in combinations(candidate_examples, n):
                # Probar con estos ejemplos
                score = self.evaluate_examples(
                    task_description,
                    list(example_combo),
                    test_cases
                )
                
                if score > best_score:
                    best_score = score
                    best_examples = list(example_combo)
        
        return best_examples
    
    def evaluate_examples(
        self,
        task: str,
        examples: list,
        test_cases: list
    ) -> float:
        """Evalúa calidad de ejemplos en casos de prueba."""
        
        correct = 0
        
        for test_case in test_cases:
            # Construir prompt con ejemplos
            prompt = self.build_few_shot_prompt(task, examples, test_case["input"])
            
            # Obtener respuesta
            response = requests.post(self.ollama_url, json={
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.1,
                "stream": False
            })
            
            output = response.json()["response"].strip()
            
            # Comparar con respuesta esperada
            if output == test_case["expected_output"]:
                correct += 1
        
        return correct / len(test_cases) if test_cases else 0
    
    def build_few_shot_prompt(self, task: str, examples: list, input_text: str) -> str:
        """Construye prompt con ejemplos."""
        
        prompt_parts = [task, ""]
        
        for i, example in enumerate(examples, 1):
            prompt_parts.append(f"Ejemplo {i}:")
            prompt_parts.append(f"Input: {example['input']}")
            prompt_parts.append(f"Output: {example['output']}")
            prompt_parts.append("")
        
        prompt_parts.append("Ahora tu turno:")
        prompt_parts.append(f"Input: {input_text}")
        prompt_parts.append("Output:")
        
        return "\n".join(prompt_parts)
```

## 🧠 Técnica 3: Chain-of-Thought (CoT)

### Definición

Instruir al modelo para que muestre su razonamiento paso a paso antes de dar la respuesta final.

### Cuándo Usar

- Problemas complejos que requieren múltiples pasos
- Debugging y troubleshooting
- Análisis y diagnóstico técnico

### Ejemplo Práctico

```python
def chain_of_thought_debug(error_log: str, context: str = "") -> dict:
    """Usa CoT para debugging complejo."""
    
    prompt = f"""
Actúa como un experto debugger. Analiza este error usando razonamiento paso a paso.

Error:
{error_log}

Contexto:
{context}

Piensa en voz alta, paso a paso:

Paso 1 - Identificar el tipo de error:
[Tu razonamiento aquí]

Paso 2 - Analizar el stack trace:
[Tu razonamiento aquí]

Paso 3 - Identificar variables/estado relevante:
[Tu razonamiento aquí]

Paso 4 - Hipótesis de causa raíz:
[Tu razonamiento aquí]

Paso 5 - Conclusión y solución:
[Tu razonamiento aquí]

Formato final en JSON:
{% raw %}
{
  "error_type": "...",
  "root_cause": "...",
  "reasoning_steps": ["paso 1", "paso 2", ...],
  "solution": "...",
  "confidence": 0.0-1.0
}
{% endraw %}
"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2:13b-chat-q4_0",
        "prompt": prompt,
        "temperature": 0.3,
        "stream": False
    })
    
    # Extraer JSON del final de la respuesta
    full_response = response.json()["response"]
    
    # Parsear el JSON
    import json
    import re
    json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    
    return {"error": "No se pudo parsear respuesta"}

# Uso
error = """
TypeError: Cannot read property 'id' of undefined
    at getUserProfile (app/controllers/user.js:42:18)
    at Router.handle (node_modules/express/lib/router/index.js:284:7)
"""

context = """
Endpoint: GET /api/users/:id/profile
Request: user_id=12345
Database query returned empty result
"""

debug_result = chain_of_thought_debug(error, context)
print("Razonamiento:")
for step in debug_result["reasoning_steps"]:
    print(f"- {step}")
print(f"\nSolución: {debug_result['solution']}")
print(f"Confianza: {debug_result['confidence']}")
```

### CoT con Auto-Consistency

```python
def chain_of_thought_with_consistency(
    question: str,
    num_samples: int = 5
) -> dict:
    """
    Genera múltiples razonamientos CoT y selecciona el más consistente.
    """
    
    prompt_template = f"""
Resuelve este problema paso a paso:

{question}

Razonamiento paso a paso:
1. [Primer paso]
2. [Segundo paso]
3. [Tercer paso]
...

Respuesta final: [Tu respuesta]
"""
    
    responses = []
    
    # Generar múltiples respuestas con temperatura alta
    for _ in range(num_samples):
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama2:13b-chat-q4_0",
            "prompt": prompt_template,
            "temperature": 0.7,  # Mayor variación
            "stream": False
        })
        
        responses.append(response.json()["response"])
    
    # Extraer respuestas finales
    final_answers = []
    for resp in responses:
        # Buscar "Respuesta final:" en la respuesta
        import re
        match = re.search(r'Respuesta final:\s*(.+)', resp, re.IGNORECASE)
        if match:
            final_answers.append(match.group(1).strip())
    
    # Encontrar respuesta más común (voting)
    from collections import Counter
    answer_counts = Counter(final_answers)
    most_common_answer, count = answer_counts.most_common(1)[0]
    
    return {
        "answer": most_common_answer,
        "confidence": count / num_samples,
        "all_responses": responses,
        "answer_distribution": dict(answer_counts)
    }

# Uso
question = """
Un pod de Kubernetes está consumiendo 800MB de memoria pero su límite es 512MB.
El pod no se reinicia pero las nuevas solicitudes fallan.
¿Por qué está sucediendo esto y cómo se soluciona?
"""

result = chain_of_thought_with_consistency(question, num_samples=5)
print(f"Respuesta consensuada: {result['answer']}")
print(f"Confianza: {result['confidence']:.1%}")
print(f"Distribución: {result['answer_distribution']}")
```

## 🎨 Técnica 4: Role Prompting

### Definición

Asignar un rol o personalidad específica al modelo para obtener respuestas más apropiadas.

### Ejemplo Práctico

```python
class RoleBasedPrompt:
    ROLES = {
        "devops_engineer": """
Eres un Senior DevOps Engineer con 10+ años de experiencia en:
- Kubernetes, Docker, Terraform
- AWS, GCP, Azure
- CI/CD (Jenkins, GitLab, GitHub Actions)
- Observabilidad (Prometheus, Grafana, ELK)

Tu estilo:
- Pragmático y orientado a soluciones
- Enfocado en automatización y escalabilidad
- Prefieres código sobre explicaciones largas
- Consideras seguridad y costos en tus recomendaciones
""",
        "security_expert": """
Eres un Security Architect especializado en:
- Application Security (OWASP Top 10)
- Cloud Security (CIS Benchmarks)
- Container Security (trivy, falco)
- Compliance (SOC2, ISO 27001, GDPR)

Tu estilo:
- Seguridad primero, siempre
- Asumes breach (zero trust)
- Proporcionas evidencia y referencias
- Balanceas seguridad con usabilidad
""",
        "sre": """
Eres un Site Reliability Engineer enfocado en:
- Disponibilidad y confiabilidad (SLIs, SLOs, SLAs)
- Incident Management y Postmortems
- Capacity Planning
- Chaos Engineering

Tu estilo:
- Basado en datos y métricas
- Proactivo en prevención
- Automatizas toil sin piedad
- Documentas todo para futura referencia
"""
    }
    
    def __init__(self, role: str, model: str = "llama2:13b-chat-q4_0"):
        self.role = self.ROLES.get(role, "")
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def ask(self, question: str, context: str = "") -> str:
        """Hace una pregunta con el rol asignado."""
        
        prompt = f"""
{self.role}

Contexto adicional:
{context}

Pregunta:
{question}

Tu respuesta (mantén el rol y estilo):
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.4,
            "stream": False
        })
        
        return response.json()["response"]

# Uso comparativo
question = "¿Cómo desplegar una aplicación Node.js en Kubernetes?"

# Perspectiva DevOps
devops = RoleBasedPrompt("devops_engineer")
devops_answer = devops.ask(question)
print("DevOps Engineer:")
print(devops_answer)
print("\n" + "="*80 + "\n")

# Perspectiva Security
security = RoleBasedPrompt("security_expert")
security_answer = security.ask(question)
print("Security Expert:")
print(security_answer)
print("\n" + "="*80 + "\n")

# Perspectiva SRE
sre = RoleBasedPrompt("sre")
sre_answer = sre.ask(question)
print("SRE:")
print(sre_answer)
```

## 📊 Evaluación de Prompts

### Framework de Evaluación

```python
from dataclasses import dataclass
from typing import Callable
import statistics

@dataclass
class PromptMetrics:
    relevance: float  # 0-1
    accuracy: float  # 0-1
    completeness: float  # 0-1
    consistency: float  # 0-1
    tokens_used: int
    latency_ms: float

class PromptEvaluator:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def evaluate_prompt(
        self,
        prompt: str,
        test_cases: list,
        evaluation_criteria: dict
    ) -> PromptMetrics:
        """
        Evalúa un prompt en múltiples dimensiones.
        
        Args:
            prompt: Template de prompt a evaluar
            test_cases: Lista de casos de prueba
            evaluation_criteria: Criterios de evaluación personalizados
        
        Returns:
            Métricas agregadas del prompt
        """
        
        import time
        
        results = []
        total_tokens = 0
        latencies = []
        
        for test_case in test_cases:
            # Ejecutar prompt
            full_prompt = prompt.format(**test_case["variables"])
            
            start_time = time.time()
            response = requests.post(self.ollama_url, json={
                "model": self.model,
                "prompt": full_prompt,
                "temperature": 0.2,
                "stream": False
            })
            latency = (time.time() - start_time) * 1000
            
            output = response.json()["response"]
            
            # Evaluar respuesta
            relevance = self._evaluate_relevance(output, test_case["expected_topics"])
            accuracy = self._evaluate_accuracy(output, test_case["ground_truth"])
            completeness = self._evaluate_completeness(output, test_case["required_elements"])
            
            results.append({
                "relevance": relevance,
                "accuracy": accuracy,
                "completeness": completeness
            })
            
            # Contar tokens (aproximado)
            total_tokens += len(full_prompt.split()) + len(output.split())
            latencies.append(latency)
        
        # Calcular métricas agregadas
        return PromptMetrics(
            relevance=statistics.mean([r["relevance"] for r in results]),
            accuracy=statistics.mean([r["accuracy"] for r in results]),
            completeness=statistics.mean([r["completeness"] for r in results]),
            consistency=1.0 - statistics.stdev([r["accuracy"] for r in results]) if len(results) > 1 else 1.0,
            tokens_used=total_tokens,
            latency_ms=statistics.mean(latencies)
        )
    
    def _evaluate_relevance(self, output: str, expected_topics: list) -> float:
        """Evalúa si la respuesta es relevante a los tópicos esperados."""
        
        output_lower = output.lower()
        matches = sum(1 for topic in expected_topics if topic.lower() in output_lower)
        return matches / len(expected_topics) if expected_topics else 0.0
    
    def _evaluate_accuracy(self, output: str, ground_truth: str) -> float:
        """Evalúa precisión comparando con ground truth."""
        
        # Usar otro LLM para evaluar (LLM-as-Judge)
        eval_prompt = f"""
Evalúa la precisión de esta respuesta en una escala de 0.0 a 1.0.

Respuesta correcta (ground truth):
{ground_truth}

Respuesta a evaluar:
{output}

Criterios:
- 1.0: Completamente correcta
- 0.8: Mayormente correcta con errores menores
- 0.6: Parcialmente correcta
- 0.4: Incorrecta pero relacionada
- 0.0: Completamente incorrecta

Responde SOLO con un número de 0.0 a 1.0:
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": eval_prompt,
            "temperature": 0.1,
            "stream": False
        })
        
        try:
            score = float(response.json()["response"].strip())
            return max(0.0, min(1.0, score))
        except:
            return 0.5  # Default si no se puede parsear
    
    def _evaluate_completeness(self, output: str, required_elements: list) -> float:
        """Evalúa si la respuesta incluye todos los elementos requeridos."""
        
        output_lower = output.lower()
        present = sum(1 for elem in required_elements if elem.lower() in output_lower)
        return present / len(required_elements) if required_elements else 1.0
    
    def compare_prompts(self, prompts: dict, test_cases: list) -> dict:
        """Compara múltiples variantes de prompts."""
        
        results = {}
        
        for name, prompt in prompts.items():
            print(f"Evaluando prompt: {name}...")
            metrics = self.evaluate_prompt(prompt, test_cases, {})
            results[name] = metrics
        
        # Generar reporte comparativo
        return self._generate_comparison_report(results)
    
    def _generate_comparison_report(self, results: dict) -> dict:
        """Genera reporte comparativo de prompts."""
        
        # Encontrar el mejor en cada métrica
        best = {
            "relevance": max(results.items(), key=lambda x: x[1].relevance),
            "accuracy": max(results.items(), key=lambda x: x[1].accuracy),
            "completeness": max(results.items(), key=lambda x: x[1].completeness),
            "consistency": max(results.items(), key=lambda x: x[1].consistency),
            "efficiency": min(results.items(), key=lambda x: x[1].tokens_used),
            "speed": min(results.items(), key=lambda x: x[1].latency_ms)
        }
        
        return {
            "all_results": results,
            "best_per_metric": best,
            "recommendation": self._recommend_best_prompt(results)
        }
    
    def _recommend_best_prompt(self, results: dict) -> str:
        """Recomienda el mejor prompt overall."""
        
        # Scoring ponderado
        scores = {}
        for name, metrics in results.items():
            score = (
                metrics.relevance * 0.3 +
                metrics.accuracy * 0.4 +
                metrics.completeness * 0.2 +
                metrics.consistency * 0.1
            )
            scores[name] = score
        
        best_name = max(scores.items(), key=lambda x: x[1])[0]
        return best_name

# Uso
evaluator = PromptEvaluator()

# Definir prompts a comparar
prompts = {
    "simple": """
Explica qué es Kubernetes.
""",
    
    "structured": """
Explica qué es Kubernetes.

Audiencia: Desarrolladores backend con experiencia en Docker
Longitud: 200-300 palabras
Incluir: Conceptos principales, beneficios, cuándo usar

Formato:
1. Definición breve
2. Conceptos clave
3. Beneficios
4. Cuándo usar vs Docker Compose
""",
    
    "role_based": """
Eres un Senior Platform Engineer explicando a tu equipo.

Explica qué es Kubernetes de forma práctica y clara.

Requisitos:
- Audiencia: Developers que usan Docker
- Enfoque: Pragmático, no teórico
- Ejemplos: Casos de uso reales
- Longitud: 250 palabras
"""
}

# Casos de prueba
test_cases = [
    {
        "variables": {},
        "expected_topics": ["containers", "orchestration", "pods", "clusters"],
        "ground_truth": "Kubernetes is a container orchestration platform...",
        "required_elements": ["pods", "services", "deployments"]
    }
]

# Comparar
comparison = evaluator.compare_prompts(prompts, test_cases)

print("\n📊 Resultados de Evaluación:\n")
for name, metrics in comparison["all_results"].items():
    print(f"{name}:")
    print(f"  Relevancia: {metrics.relevance:.2f}")
    print(f"  Precisión: {metrics.accuracy:.2f}")
    print(f"  Completitud: {metrics.completeness:.2f}")
    print(f"  Tokens: {metrics.tokens_used}")
    print(f"  Latencia: {metrics.latency_ms:.0f}ms\n")

print(f"🏆 Recomendación: {comparison['recommendation']}")
```

## 🔧 Técnicas Avanzadas

### 1. Self-Consistency con Voting

Ya cubierto en Chain-of-Thought, pero aquí la implementación completa:

```python
def self_consistency_voting(
    prompt: str,
    num_samples: int = 7,
    temperature: float = 0.8
) -> dict:
    """
    Genera múltiples respuestas y usa voting para determinar consenso.
    """
    
    responses = []
    
    for i in range(num_samples):
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama2:13b-chat-q4_0",
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        })
        
        responses.append(response.json()["response"])
    
    # Usar LLM para determinar consenso
    consensus_prompt = f"""
Estas son {num_samples} respuestas diferentes a la misma pregunta:

{chr(10).join([f"{i+1}. {r}" for i, r in enumerate(responses)])}

Analiza las respuestas y determina:
1. Puntos de consenso (qué dicen todas o la mayoría)
2. Puntos de divergencia (dónde difieren)
3. Respuesta final sintetizada (combina lo mejor de todas)

Formato JSON:
{% raw %}
{
  "consensus_points": ["..."],
  "divergence_points": ["..."],
  "final_answer": "...",
  "confidence": 0.0-1.0
}
{% endraw %}
"""
    
    consensus_response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2:13b-chat-q4_0",
        "prompt": consensus_prompt,
        "temperature": 0.2,
        "stream": False,
        "format": "json"
    })
    
    import json
    return json.loads(consensus_response.json()["response"])
```

### 2. Prompt Chaining

```python
class PromptChain:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.chain_history = []
    
    def add_step(self, prompt_template: str, use_previous: bool = True):
        """Añade un paso a la cadena."""
        
        def step_function(input_data: dict) -> str:
            # Construir prompt con datos previos si es necesario
            if use_previous and self.chain_history:
                previous_output = self.chain_history[-1]["output"]
                input_data["previous_output"] = previous_output
            
            prompt = prompt_template.format(**input_data)
            
            response = requests.post(self.ollama_url, json={
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.3,
                "stream": False
            })
            
            output = response.json()["response"]
            
            self.chain_history.append({
                "prompt": prompt,
                "output": output,
                "input_data": input_data
            })
            
            return output
        
        return step_function
    
    def execute(self, initial_data: dict) -> dict:
        """Ejecuta toda la cadena."""
        return {
            "final_output": self.chain_history[-1]["output"] if self.chain_history else None,
            "chain_history": self.chain_history
        }

# Ejemplo: Pipeline de análisis de código
chain = PromptChain()

# Paso 1: Analizar código
analyze_step = chain.add_step("""
Analiza este código y identifica:
1. Funcionalidad principal
2. Posibles bugs
3. Mejoras de rendimiento

Código:
{code}

Análisis:
""", use_previous=False)

# Paso 2: Generar refactor
refactor_step = chain.add_step("""
Basándote en este análisis:
{previous_output}

Genera código refactorizado que implemente las mejoras sugeridas.

Código refactorizado:
""")

# Paso 3: Documentar
document_step = chain.add_step("""
Genera documentación completa para este código refactorizado:
{previous_output}

Incluye:
- Docstring de función
- Comentarios inline
- Ejemplos de uso

Documentación:
""")

# Ejecutar cadena
code_to_analyze = """
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
"""

analyze_step({"code": code_to_analyze})
refactor_step({})
document_step({})

final_result = chain.execute({})
print(final_result["final_output"])
```

## 📚 Mejores Prácticas y Anti-Patrones

### ✅ DO's

1. **Sé específico y claro**
   ```python
   # ✅ Bueno
   prompt = "Genera una función Python que calcule el factorial de un número usando recursión. Incluye manejo de errores para inputs negativos y tipo de retorno anotado."
   ```

2. **Usa delimitadores claros**
   ```python
   # ✅ Bueno
   prompt = """
   Texto a analizar:
   '''
   {user_input}
   '''
   
   Análisis:
   """
   ```

3. **Especifica formato de salida**
   ```python
   # ✅ Bueno
   prompt = "Responde en formato JSON con estas keys: {status, message, data}"
   ```

4. **Proporciona contexto relevante**
   ```python
   # ✅ Bueno
   prompt = f"Contexto: Aplicación web de e-commerce con 1M usuarios/día\nPregunta: {question}"
   ```

### ❌ DON'Ts

1. **Ambigüedad**
   ```python
   # ❌ Malo
   prompt = "dame info sobre kubernetes"
   ```

2. **Prompts demasiado largos**
   ```python
   # ❌ Malo (>4000 palabras de contexto innecesario)
   prompt = f"{entire_documentation}\nAhora responde: {simple_question}"
   ```

3. **Asumir conocimiento implícito**
   ```python
   # ❌ Malo
   prompt = "Explica cómo funciona eso"  # ¿Qué es "eso"?
   ```

4. **No validar outputs**
   ```python
   # ❌ Malo
   response = llm.generate(prompt)
   use_directly(response)  # Sin validación
   ```

## 🔗 Recursos Adicionales

- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Engineering](https://docs.anthropic.com/claude/docs/introduction-to-prompt-design)
- [LangChain Prompts](https://python.langchain.com/docs/modules/model_io/prompts/)

## 📚 Próximos Pasos

Después de dominar prompt engineering, considera:

1. **[Fine-tuning Básico](fine_tuning_basico.md)** - Personalizar modelos para tu dominio
2. **[Evaluación de Modelos](model_evaluation.md)** - Métricas y benchmarks
3. **[LLMs en Producción](despliegue_kubernetes.md)** - Despliegue a escala

---

*¿Has desarrollado técnicas de prompting efectivas? Comparte tus estrategias y aprendizajes en los comentarios.*