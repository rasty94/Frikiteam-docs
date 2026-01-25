---
title: "Advanced Prompt Engineering for LLMs"
description: "Professional prompt engineering techniques: zero-shot, few-shot, chain-of-thought, and prompt evaluation for local models"
date: 2026-01-25
tags: [ai, llm, prompt-engineering, best-practices, optimization]
difficulty: intermediate
estimated_time: "40 min"
category: ai
status: published
prerequisites: ["llms_fundamentals", "ollama_basics"]
---

# Advanced Prompt Engineering for LLMs

> **Reading time:** 40 minutes | **Difficulty:** Intermediate | **Category:** Artificial Intelligence

## Summary

Prompt engineering is the art and science of designing effective instructions for LLMs. This guide covers professional techniques from zero-shot to chain-of-thought, with practical examples and evaluation frameworks for local models.

## 🎯 Why Prompt Engineering Matters

### Impact of Prompts on Results

```python
# Poorly designed prompt
bad_prompt = "give me info about kubernetes"
# Result: vague, not useful, unstructured

# Well-designed prompt
good_prompt = """
Act as a Kubernetes expert. Explain the concepts of Pods, Deployments and Services in the context of a 3-tier web application (frontend, backend, database).

Requirements:
- Audience: Developers with basic Docker knowledge
- Length: 300-400 words
- Include: 1 YAML example per concept
- Format: Markdown with H2 sections

Structure:
1. Pods - What they are and when to use them
2. Deployments - Replica management
3. Services - Exposing applications
"""
# Result: structured, relevant, actionable
```

### Benefits of Good Prompts

- ✅ **Reduced iterations:** Correct result on first attempt
- ✅ **Consistency:** Predictable and reproducible outputs
- ✅ **Superior quality:** More precise and useful responses
- ✅ **Token savings:** Fewer corrections = less cost
- ✅ **Effective automation:** Integrable into pipelines

## 📋 Anatomy of a Good Prompt

### Fundamental Components

```python
class PromptTemplate:
    def __init__(
        self,
        role: str,  # LLM personality/expertise
        task: str,  # What it should do
        context: str,  # Background information
        constraints: list,  # Limitations and requirements
        output_format: str,  # Desired format
        examples: list = None  # Few-shot examples
    ):
        self.role = role
        self.task = task
        self.context = context
        self.constraints = constraints
        self.output_format = output_format
        self.examples = examples or []
    
    def build(self) -> str:
        """Builds complete prompt."""
        
        prompt_parts = []
        
        # 1. Role/Persona
        if self.role:
            prompt_parts.append(f"Role: {self.role}\n")
        
        # 2. Context
        if self.context:
            prompt_parts.append(f"Context:\n{self.context}\n")
        
        # 3. Examples (few-shot)
        if self.examples:
            prompt_parts.append("Examples:")
            for i, example in enumerate(self.examples, 1):
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(f"Input: {example['input']}")
                prompt_parts.append(f"Output: {example['output']}\n")
        
        # 4. Main task
        prompt_parts.append(f"Task:\n{self.task}\n")
        
        # 5. Constraints
        if self.constraints:
            prompt_parts.append("Requirements:")
            for constraint in self.constraints:
                prompt_parts.append(f"- {constraint}")
            prompt_parts.append("")
        
        # 6. Output format
        if self.output_format:
            prompt_parts.append(f"Output format:\n{self.output_format}\n")
        
        return "\n".join(prompt_parts)

# Usage example
template = PromptTemplate(
    role="Senior Docker Security Expert",
    task="Audit this Dockerfile and suggest security improvements",
    context="""
Current Dockerfile:
FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3
COPY . /app
WORKDIR /app
CMD ["python3", "app.py"]
""",
    constraints=[
        "Prioritize official and slim images",
        "Non-root user mandatory",
        "Multi-stage build if possible",
        "Minimize layers"
    ],
    output_format="""
JSON with:
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

## 🎓 Technique 1: Zero-Shot Prompting

### Definition

Give clear instructions without prior examples. The model must infer what to do from the description alone.

### When to Use

- Simple and well-defined tasks
- Large models (13B+) with good comprehension
- When no examples are available

### Practical Example

```python
def zero_shot_classification(text: str, categories: list) -> str:
    """Classifies text into categories without prior examples."""
    
    prompt = f"""
Classify the following text into ONE of these categories: {', '.join(categories)}

Text: "{text}"

Respond ONLY with the category name, no explanations.

Category:"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2:13b-chat-q4_0",
        "prompt": prompt,
        "temperature": 0.1,
        "stream": False
    })
    
    return response.json()["response"].strip()

# Usage
categories = ["Bug", "Feature Request", "Documentation", "Question"]
issue_text = "The application crashes when clicking the submit button"

category = zero_shot_classification(issue_text, categories)
print(f"Category: {category}")  # Output: Bug
```

### Zero-Shot Best Practices

```python
# ❌ Vague prompt
bad_prompt = "Classify this: 'app crashes'"

# ✅ Clear and specific prompt
good_prompt = """
Task: Support ticket classification

Valid categories:
1. BUG - Functional error in application
2. FEATURE - New functionality request
3. DOCS - Documentation problem
4. QUESTION - User query

Text to classify: "The application crashes when clicking the submit button"

Instructions:
- Respond ONLY with category name
- If unsure, choose the most probable
- Format: Uppercase single word

Category:"""
```

## 🎯 Technique 2: Few-Shot Prompting

### Definition

Provide input-output examples before the actual task to guide the model.

### When to Use

- Complex tasks with specific format
- Medium models (7B-13B) needing guidance
- When consistent outputs are needed

### Practical Example

```python
def few_shot_entity_extraction(text: str) -> dict:
    """Extracts entities using few-shot learning."""
    
    prompt = f"""
Extract technical entities from incident descriptions.

Example 1:
Text: "PostgreSQL database on srv-db-01 is experiencing high CPU usage"
Entities: {{"technology": "PostgreSQL", "resource": "database", "server": "srv-db-01", "metric": "CPU usage", "status": "high"}}

Example 2:
Text: "Nginx reverse proxy returning 502 errors for api.example.com"
Entities: {{"technology": "Nginx", "resource": "reverse proxy", "error": "502", "domain": "api.example.com"}}

Example 3:
Text: "Kubernetes pod web-frontend-abc123 is in CrashLoopBackOff state"
Entities: {{"technology": "Kubernetes", "resource": "pod", "name": "web-frontend-abc123", "status": "CrashLoopBackOff"}}

Now extract entities from this text:
Text: "{text}"
Entities:"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2:13b-chat-q4_0",
        "prompt": prompt,
        "temperature": 0.2,
        "stream": False,
        "format": "json"
    })
    
    import json
    return json.loads(response.json()["response"])

# Usage
incident = "Redis cache cluster on redis-prod-cluster-01 showing memory leak"
entities = few_shot_entity_extraction(incident)
print(entities)
# Output: {"technology": "Redis", "resource": "cache cluster", "name": "redis-prod-cluster-01", "issue": "memory leak"}
```

### Few-Shot Optimization

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
        Finds optimal number and selection of examples.
        
        Args:
            task_description: Task description
            candidate_examples: Pool of possible examples
            test_cases: Test cases for evaluation
            max_examples: Maximum examples to test
        
        Returns:
            Optimal examples list
        """
        
        best_score = 0
        best_examples = []
        
        # Try different combinations
        from itertools import combinations
        
        for n in range(1, min(max_examples + 1, len(candidate_examples) + 1)):
            for example_combo in combinations(candidate_examples, n):
                # Test with these examples
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
        """Evaluates example quality on test cases."""
        
        correct = 0
        
        for test_case in test_cases:
            # Build prompt with examples
            prompt = self.build_few_shot_prompt(task, examples, test_case["input"])
            
            # Get response
            response = requests.post(self.ollama_url, json={
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.1,
                "stream": False
            })
            
            output = response.json()["response"].strip()
            
            # Compare with expected output
            if output == test_case["expected_output"]:
                correct += 1
        
        return correct / len(test_cases) if test_cases else 0
    
    def build_few_shot_prompt(self, task: str, examples: list, input_text: str) -> str:
        """Builds prompt with examples."""
        
        prompt_parts = [task, ""]
        
        for i, example in enumerate(examples, 1):
            prompt_parts.append(f"Example {i}:")
            prompt_parts.append(f"Input: {example['input']}")
            prompt_parts.append(f"Output: {example['output']}")
            prompt_parts.append("")
        
        prompt_parts.append("Your turn:")
        prompt_parts.append(f"Input: {input_text}")
        prompt_parts.append("Output:")
        
        return "\n".join(prompt_parts)
```

## 🧠 Technique 3: Chain-of-Thought (CoT)

### Definition

Instruct the model to show its step-by-step reasoning before giving the final answer.

### When to Use

- Complex problems requiring multiple steps
- Debugging and troubleshooting
- Analysis and diagnosis

### Practical Example

```python
def chain_of_thought_debug(error_log: str, context: str = "") -> dict:
    """Uses CoT for complex debugging."""
    
    prompt = f"""
Act as an expert debugger. Analyze this error using step-by-step reasoning.

Error:
{error_log}

Context:
{context}

Think out loud, step by step:

Step 1 - Identify error type:
[Your reasoning here]

Step 2 - Analyze stack trace:
[Your reasoning here]

Step 3 - Identify relevant variables/state:
[Your reasoning here]

Step 4 - Root cause hypothesis:
[Your reasoning here]

Step 5 - Conclusion and solution:
[Your reasoning here]

Final format in JSON:
{{
  "error_type": "...",
  "root_cause": "...",
  "reasoning_steps": ["step 1", "step 2", ...],
  "solution": "...",
  "confidence": 0.0-1.0
}}
"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": self.model,
        "prompt": prompt,
        "temperature": 0.3,
        "stream": False
    })
    
    # Extract JSON from end of response
    full_response = response.json()["response"]
    
    # Parse JSON
    import json
    import re
    json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    
    return {"error": "Could not parse response"}

# Usage
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
print("Reasoning:")
for step in debug_result["reasoning_steps"]:
    print(f"- {step}")
print(f"\nSolution: {debug_result['solution']}")
print(f"Confidence: {debug_result['confidence']}")
```

### CoT with Self-Consistency

```python
def chain_of_thought_with_consistency(
    question: str,
    num_samples: int = 5
) -> dict:
    """
    Generates multiple CoT responses and selects most consistent.
    """
    
    prompt_template = f"""
Solve this problem step by step:

{question}

Step-by-step reasoning:
1. [First step]
2. [Second step]
3. [Third step]
...

Final answer: [Your answer]
"""
    
    responses = []
    
    # Generate multiple responses with high temperature
    for _ in range(num_samples):
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama2:13b-chat-q4_0",
            "prompt": prompt_template,
            "temperature": 0.7,  # Higher variation
            "stream": False
        })
        
        responses.append(response.json()["response"])
    
    # Extract final answers
    final_answers = []
    for resp in responses:
        # Search for "Final answer:" in response
        import re
        match = re.search(r'Final answer:\s*(.+)', resp, re.IGNORECASE)
        if match:
            final_answers.append(match.group(1).strip())
    
    # Find most common answer (voting)
    from collections import Counter
    answer_counts = Counter(final_answers)
    most_common_answer, count = answer_counts.most_common(1)[0]
    
    return {
        "answer": most_common_answer,
        "confidence": count / num_samples,
        "all_responses": responses,
        "answer_distribution": dict(answer_counts)
    }

# Usage
question = """
A Kubernetes pod is consuming 800MB of memory but its limit is 512MB.
The pod doesn't restart but new requests fail.
Why is this happening and how to fix it?
"""

result = chain_of_thought_with_consistency(question, num_samples=5)
print(f"Consensus answer: {result['answer']}")
print(f"Confidence: {result['confidence']:.1%}")
print(f"Distribution: {result['answer_distribution']}")
```

## 🎨 Technique 4: Role Prompting

### Definition

Assign a specific role or personality to the model to get more appropriate responses.

### Practical Example

```python
class RoleBasedPrompt:
    ROLES = {
        "devops_engineer": """
You are a Senior DevOps Engineer with 10+ years experience in:
- Kubernetes, Docker, Terraform
- AWS, GCP, Azure
- CI/CD (Jenkins, GitLab, GitHub Actions)
- Observability (Prometheus, Grafana, ELK)

Your style:
- Pragmatic and solution-oriented
- Focused on automation and scalability
- Prefers code over long explanations
- Considers security and costs in recommendations
""",
        "security_expert": """
You are a Security Architect specializing in:
- Application Security (OWASP Top 10)
- Cloud Security (CIS Benchmarks)
- Container Security (trivy, falco)
- Compliance (SOC2, ISO 27001, GDPR)

Your style:
- Security first, always
- Assumes breach (zero trust)
- Provides evidence and references
- Balances security with usability
""",
        "sre": """
You are a Site Reliability Engineer focused on:
- Availability and reliability (SLIs, SLOs, SLAs)
- Incident Management and Postmortems
- Capacity Planning
- Chaos Engineering

Your style:
- Data and metrics based
- Proactive in prevention
- Automates toil relentlessly
- Documents everything for future reference
"""
    }
    
    def __init__(self, role: str, model: str = "llama2:13b-chat-q4_0"):
        self.role = self.ROLES.get(role, "")
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def ask(self, question: str, context: str = "") -> str:
        """Asks question with assigned role."""
        
        prompt = f"""
{self.role}

Additional context:
{context}

Question:
{question}

Your response (maintain role and style):
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.4,
            "stream": False
        })
        
        return response.json()["response"]

# Comparative usage
question = "How to deploy a Node.js application in Kubernetes?"

# DevOps perspective
devops = RoleBasedPrompt("devops_engineer")
devops_answer = devops.ask(question)
print("DevOps Engineer:")
print(devops_answer)
print("\n" + "="*80 + "\n")

# Security perspective
security = RoleBasedPrompt("security_expert")
security_answer = security.ask(question)
print("Security Expert:")
print(security_answer)
print("\n" + "="*80 + "\n")

# SRE perspective
sre = RoleBasedPrompt("sre")
sre_answer = sre.ask(question)
print("SRE:")
print(sre_answer)
```

## 📊 Prompt Evaluation

### Evaluation Framework

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
        Evaluates prompt across multiple dimensions.
        
        Args:
            prompt: Template prompt to evaluate
            test_cases: Test case list
            evaluation_criteria: Custom evaluation criteria
        
        Returns:
            Aggregated prompt metrics
        """
        
        import time
        
        results = []
        total_tokens = 0
        latencies = []
        
        for test_case in test_cases:
            # Execute prompt
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
            
            # Evaluate response
            relevance = self._evaluate_relevance(output, test_case["expected_topics"])
            accuracy = self._evaluate_accuracy(output, test_case["ground_truth"])
            completeness = self._evaluate_completeness(output, test_case["required_elements"])
            
            results.append({
                "relevance": relevance,
                "accuracy": accuracy,
                "completeness": completeness
            })
            
            # Count tokens (approximate)
            total_tokens += len(full_prompt.split()) + len(output.split())
            latencies.append(latency)
        
        # Calculate aggregated metrics
        return PromptMetrics(
            relevance=statistics.mean([r["relevance"] for r in results]),
            accuracy=statistics.mean([r["accuracy"] for r in results]),
            completeness=statistics.mean([r["completeness"] for r in results]),
            consistency=1.0 - statistics.stdev([r["accuracy"] for r in results]) if len(results) > 1 else 1.0,
            tokens_used=total_tokens,
            latency_ms=statistics.mean(latencies)
        )
    
    def _evaluate_relevance(self, output: str, expected_topics: list) -> float:
        """Evaluates if response is relevant to expected topics."""
        
        output_lower = output.lower()
        matches = sum(1 for topic in expected_topics if topic.lower() in output_lower)
        return matches / len(expected_topics) if expected_topics else 0.0
    
    def _evaluate_accuracy(self, output: str, ground_truth: str) -> float:
        """Evaluates accuracy by comparing with ground truth."""
        
        # Use another LLM for evaluation (LLM-as-Judge)
        eval_prompt = f"""
Evaluate the accuracy of this response on a 0.0 to 1.0 scale.

Correct answer (ground truth):
{ground_truth}

Response to evaluate:
{output}

Criteria:
- 1.0: Completely correct
- 0.8: Mostly correct with minor errors
- 0.6: Partially correct
- 0.4: Incorrect but related
- 0.0: Completely incorrect

Respond ONLY with a number from 0.0 to 1.0:
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
            return 0.5  # Default if cannot parse
    
    def _evaluate_completeness(self, output: str, required_elements: list) -> float:
        """Evaluates if response includes all required elements."""
        
        output_lower = output.lower()
        present = sum(1 for elem in required_elements if elem.lower() in output_lower)
        return present / len(required_elements) if required_elements else 1.0
    
    def compare_prompts(self, prompts: dict, test_cases: list) -> dict:
        """Compares multiple prompt variants."""
        
        results = {}
        
        for name, prompt in prompts.items():
            print(f"Evaluating prompt: {name}...")
            metrics = self.evaluate_prompt(prompt, test_cases, {})
            results[name] = metrics
        
        # Generate comparative report
        return self._generate_comparison_report(results)
    
    def _generate_comparison_report(self, results: dict) -> dict:
        """Generates comparative report of prompts."""
        
        # Find best in each metric
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
        """Recommends overall best prompt."""
        
        # Weighted scoring
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

# Usage
evaluator = PromptEvaluator()

# Prompts to compare
prompts = {
    "simple": """
Explain what Kubernetes is.
""",
    
    "structured": """
Explain what Kubernetes is.

Audience: Backend developers with Docker experience
Length: 200-300 words
Include: Main concepts, benefits, when to use

Format:
1. Brief definition
2. Key concepts
3. Benefits
4. When to use vs Docker Compose
""",
    
    "role_based": """
You are a Senior Platform Engineer explaining to your team.

Explain what Kubernetes is practically and clearly.

Requirements:
- Audience: Developers using Docker
- Focus: Pragmatic, not theoretical
- Examples: Real use cases
- Length: 250 words
"""
}

# Test cases
test_cases = [
    {
        "variables": {},
        "expected_topics": ["containers", "orchestration", "pods", "clusters"],
        "ground_truth": "Kubernetes is a container orchestration platform...",
        "required_elements": ["pods", "services", "deployments"]
    }
]

# Compare
comparison = evaluator.compare_prompts(prompts, test_cases)

print("\n📊 Evaluation Results:\n")
for name, metrics in comparison["all_results"].items():
    print(f"{name}:")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Tokens: {metrics.tokens_used}")
    print(f"  Latency: {metrics.latency_ms:.0f}ms\n")

print(f"🏆 Recommendation: {comparison['recommendation']}")
```

## 🔧 Advanced Techniques

### 1. Self-Consistency with Voting

Already covered in Chain-of-Thought, but here's the complete implementation:

```python
def self_consistency_voting(
    prompt: str,
    num_samples: int = 7,
    temperature: float = 0.8
) -> dict:
    """
    Generates multiple responses and uses voting to determine consensus.
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
    
    # Use LLM to determine consensus
    consensus_prompt = f"""
These are {num_samples} different responses to the same question:

{chr(10).join([f"{i+1}. {r}" for i, r in enumerate(responses)])}

Analyze the responses and determine:
1. Consensus points (what all or most say)
2. Divergence points (where they differ)
3. Final synthesized answer (combine the best from all)

JSON format:
{{
  "consensus_points": ["..."],
  "divergence_points": ["..."],
  "final_answer": "...",
  "confidence": 0.0-1.0
}}
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
        """Adds step to chain."""
        
        def step_function(input_data: dict) -> str:
            # Build prompt with previous data if needed
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
        """Executes entire chain."""
        return {
            "final_output": self.chain_history[-1]["output"] if self.chain_history else None,
            "chain_history": self.chain_history
        }

# Example: Code analysis pipeline
chain = PromptChain()

# Step 1: Analyze code
analyze_step = chain.add_step("""
Analyze this code and identify:
1. Main functionality
2. Potential bugs
3. Performance improvements

Code:
{code}

Analysis:
""", use_previous=False)

# Step 2: Generate refactor
refactor_step = chain.add_step("""
Based on this analysis:
{previous_output}

Generate refactored code implementing suggested improvements.

Refactored code:
""")

# Step 3: Document
document_step = chain.add_step("""
Generate complete documentation for this refactored code:
{previous_output}

Include:
- Function docstring
- Inline comments
- Usage examples

Documentation:
""")

# Execute chain
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

## 📚 Best Practices and Anti-Patterns

### ✅ DO's

1. **Be specific and clear**
   ```python
   # ✅ Good
   prompt = "Generate a Python function that calculates factorial using recursion. Include error handling for negative inputs and type annotations for return value."
   ```

2. **Use clear delimiters**
   ```python
   # ✅ Good
   prompt = """
   Text to analyze:
   '''
   {user_input}
   '''
   
   Analysis:
   """
   ```

3. **Specify output format**
   ```python
   # ✅ Good
   prompt = "Respond in JSON format with these keys: {status, message, data}"
   ```

4. **Provide relevant context**
   ```python
   # ✅ Good
   prompt = f"Context: E-commerce web application with 1M daily users\nQuestion: {question}"
   ```

### ❌ DON'Ts

1. **Ambiguity**
   ```python
   # ❌ Bad
   prompt = "Give me info about that"
   ```

2. **Overly long prompts**
   ```python
   # ❌ Bad (>4000 words of unnecessary context)
   prompt = f"{entire_documentation}\nNow answer: {simple_question}"
   ```

3. **Implicit knowledge assumptions**
   ```python
   # ❌ Bad
   prompt = "Explain how this works"
   ```

4. **No output validation**
   ```python
   # ❌ Bad
   response = llm.generate(prompt)
   use_directly(response)  # No validation
   ```

## 🔗 Additional Resources

- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Engineering](https://docs.anthropic.com/claude/docs/introduction-to-prompt-design)
- [LangChain Prompts](https://python.langchain.com/docs/modules/model_io/prompts/)

## 📚 Next Steps

After mastering prompt engineering, consider:

1. **[Fine-tuning Basics](../fine_tuning_basics/)** - Customize models for your domain
2. **[Model Evaluation](../model_evaluation/)** - Metrics and benchmarks
3. **[LLMs in Production](../llms_kubernetes/)** - Deploy at scale

---

*Have you developed effective prompting techniques? Share your strategies and learnings in the comments.*