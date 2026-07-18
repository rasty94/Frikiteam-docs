---
title: "Generación de Contenido Técnico con LLMs"
description: "Automatización de documentación, generación de posts de blog y resumen de artículos técnicos usando Large Language Models"
date: 2026-01-25
tags: [ai, llm, documentation, automation, content-generation]
difficulty: intermediate
estimated_time: "30 min"
category: Inteligencia Artificial
status: published
prerequisites: ["ollama_basics", "chatbots_locales"]
---

# Generación de Contenido Técnico con LLMs

> **Tiempo de lectura:** 30 minutos | **Dificultad:** Intermedia | **Categoría:** Inteligencia Artificial

## Resumen

Los LLMs pueden automatizar la creación de documentación técnica, generar posts de blog y resumir artículos complejos. Esta guía cubre técnicas prácticas para usar modelos locales en workflows de documentación empresarial, manteniendo calidad y consistencia.

## 🎯 Por Qué Automatizar la Documentación

### Problemas Comunes en Documentación

- **Documentación obsoleta:** Código cambia más rápido que los docs
- **Inconsistencia de estilo:** Múltiples autores, múltiples estilos
- **Falta de tiempo:** Developers prefieren codear que documentar
- **Barreras de idioma:** Contenido en un solo idioma limita audiencia

### Beneficios de LLMs para Documentación

- ✅ **Generación automática** de docstrings y README
- ✅ **Traducción técnica** precisa a múltiples idiomas
- ✅ **Resumen automático** de PRs y changelogs
- ✅ **Consistencia de estilo** con templates personalizados
- ✅ **Actualización continua** con CI/CD integration

## 📝 Caso de Uso 1: Generación de Documentación API

### Automatización de Docstrings

```python
import ast
import requests

def generate_docstring(function_code: str, model: str = "llama2:7b-chat-q4_0") -> str:
    """
    Genera un docstring profesional para una función Python.
    
    Args:
        function_code: Código fuente de la función
        model: Modelo Ollama a usar
        
    Returns:
        Docstring generado en formato Google Style
    """
    
    prompt = f"""
Eres un experto en documentación Python. Genera un docstring profesional en formato Google Style para esta función:

```python
{function_code}
```

El docstring debe incluir:
1. Descripción breve (1 línea)
2. Descripción detallada (si es necesario)
3. Args: con tipos y descripciones
4. Returns: con tipo y descripción
5. Raises: si aplica
6. Examples: código de ejemplo

Responde SOLO con el docstring, sin explicaciones adicionales.
"""

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.3  # Baja temperatura para consistencia
    })
    
    if response.status_code == 200:
        return response.json()["response"].strip()
    else:
        raise Exception(f"Error generando docstring: {response.text}")

# Ejemplo de uso
code = """
def calculate_metrics(data: list, threshold: float = 0.5):
    filtered = [x for x in data if x > threshold]
    avg = sum(filtered) / len(filtered) if filtered else 0
    return {"count": len(filtered), "average": avg}
"""

docstring = generate_docstring(code)
print(docstring)
```

### Resultado Esperado

```python
"""
Calculate metrics for filtered data above a threshold.

Processes a list of numeric values, filters out values below the specified
threshold, and computes aggregated statistics.

Args:
    data (list): List of numeric values to process
    threshold (float, optional): Minimum value to include in calculations.
        Defaults to 0.5.

Returns:
    dict: Dictionary with keys:
        - 'count' (int): Number of values above threshold
        - 'average' (float): Mean of filtered values, or 0 if none

Examples:
    >>> calculate_metrics([0.3, 0.6, 0.8, 0.2], threshold=0.5)
    {'count': 2, 'average': 0.7}
    
    >>> calculate_metrics([0.1, 0.2], threshold=0.5)
    {'count': 0, 'average': 0}
"""
```

### Procesamiento por Lotes

```python
import os
import ast

def document_python_file(filepath: str, output_dir: str = "docs_generated"):
    """Documenta todas las funciones en un archivo Python."""
    
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    os.makedirs(output_dir, exist_ok=True)
    
    documented_functions = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Extraer código de la función
            function_code = ast.get_source_segment(open(filepath).read(), node)
            
            # Generar docstring
            docstring = generate_docstring(function_code)
            
            documented_functions.append({
                "name": node.name,
                "docstring": docstring,
                "code": function_code
            })
    
    # Guardar documentación en Markdown
    output_file = os.path.join(output_dir, f"{os.path.basename(filepath)}.md")
    with open(output_file, 'w') as f:
        f.write(f"# Documentación: {filepath}\n\n")
        for func in documented_functions:
            f.write(f"## `{func['name']}`\n\n")
            f.write(f"```python\n{func['docstring']}\n```\n\n")
            f.write(f"**Código fuente:**\n```python\n{func['code']}\n```\n\n")
    
    print(f"✅ Documentación generada: {output_file}")
    return output_file

# Uso
document_python_file("my_module.py")
```

## 📄 Caso de Uso 2: Generación de README Automático

### Template con Variables

```python
from pathlib import Path
import json

def generate_readme(
    repo_path: str,
    project_name: str = None,
    description: str = None,
    model: str = "llama2:7b-chat-q4_0"
) -> str:
    """
    Genera un README.md profesional analizando el repositorio.
    
    Args:
        repo_path: Ruta al repositorio
        project_name: Nombre del proyecto (auto-detecta si None)
        description: Descripción breve (LLM genera si None)
        model: Modelo Ollama a usar
    
    Returns:
        Contenido del README.md generado
    """
    
    repo = Path(repo_path)
    
    # Auto-detectar información del proyecto
    if not project_name:
        project_name = repo.name
    
    # Analizar estructura
    files = list(repo.rglob("*.py"))
    has_tests = any("test" in str(f) for f in files)
    has_requirements = (repo / "requirements.txt").exists()
    has_docker = (repo / "Dockerfile").exists()
    
    # Leer archivos principales
    main_files = []
    for file in ["main.py", "app.py", "__init__.py", "setup.py"]:
        filepath = repo / file
        if filepath.exists():
            with open(filepath, 'r') as f:
                main_files.append({"name": file, "content": f.read()[:500]})
    
    # Prompt para LLM
    prompt = f"""
Genera un README.md profesional para este proyecto Python:

**Proyecto:** {project_name}
**Descripción:** {description or "Analiza el código y genera una descripción"}
**Estructura:**
- {len(files)} archivos Python
- Tests: {"Sí" if has_tests else "No"}
- Docker: {"Sí" if has_docker else "No"}

**Archivos principales:**
{json.dumps(main_files, indent=2)}

Genera un README con estas secciones:
1. # {project_name} - Título y badges
2. ## Descripción - Qué hace el proyecto (2-3 párrafos)
3. ## Características - Lista de features principales
4. ## Requisitos - Python version, dependencias
5. ## Instalación - Paso a paso
6. ## Uso - Ejemplos básicos
7. ## Desarrollo - Cómo contribuir
8. ## Licencia

Usa formato Markdown profesional. Sé conciso pero completo.
"""

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.4
    })
    
    if response.status_code == 200:
        readme_content = response.json()["response"]
        
        # Guardar README
        with open(repo / "README.md", 'w') as f:
            f.write(readme_content)
        
        print(f"✅ README generado en {repo / 'README.md'}")
        return readme_content
    else:
        raise Exception(f"Error: {response.text}")

# Uso
readme = generate_readme(
    "/path/to/my-project",
    description="API REST para gestión de usuarios con autenticación JWT"
)
```

## ✍️ Caso de Uso 3: Generación de Posts de Blog

### Pipeline Completo

```python
from datetime import datetime
import frontmatter

class BlogPostGenerator:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def generate_outline(self, topic: str, audience: str = "developers") -> list:
        """Genera un outline estructurado para el post."""
        
        prompt = f"""
Crea un outline detallado para un post de blog técnico sobre: {topic}

Audiencia: {audience}
Objetivo: Educativo, práctico, con ejemplos de código

Genera una estructura con:
1. Título atractivo (H1)
2. Introducción (problema que resuelve)
3. 4-5 secciones principales (H2) con subsecciones (H3)
4. Sección de conclusiones
5. Referencias/recursos

Formato: Lista con viñetas, indicando nivel de heading.
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.6
        })
        
        outline_text = response.json()["response"]
        # Parsear outline a estructura
        return self._parse_outline(outline_text)
    
    def generate_section(self, section_title: str, context: str = "") -> str:
        """Genera contenido para una sección específica."""
        
        prompt = f"""
Escribe la sección "{section_title}" de un post técnico.

Contexto del artículo: {context}

Requisitos:
- 300-500 palabras
- Incluir ejemplos de código si es relevante
- Tono profesional pero accesible
- Formato Markdown
- Incluir enlaces a recursos externos si aplica

Contenido:
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7
        })
        
        return response.json()["response"]
    
    def generate_full_post(
        self,
        topic: str,
        tags: list,
        category: str = "DevOps",
        audience: str = "developers"
    ) -> str:
        """Genera un post completo de blog."""
        
        # 1. Generar outline
        print("📝 Generando outline...")
        outline = self.generate_outline(topic, audience)
        
        # 2. Generar cada sección
        print("✍️  Generando secciones...")
        sections = []
        for item in outline:
            section_content = self.generate_section(
                item["title"],
                context=f"Post sobre {topic}"
            )
            sections.append({
                "level": item["level"],
                "title": item["title"],
                "content": section_content
            })
        
        # 3. Ensamblar post completo
        print("🔧 Ensamblando post...")
        post_content = self._assemble_post(sections)
        
        # 4. Agregar frontmatter
        post = frontmatter.Post(post_content)
        post.metadata = {
            "title": outline[0]["title"] if outline else topic,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "tags": tags,
            "category": category,
            "author": "AI Assistant",
            "draft": True  # Revisar antes de publicar
        }
        
        # 5. Guardar
        filename = f"blog_{datetime.now().strftime('%Y%m%d')}_{topic.lower().replace(' ', '_')}.md"
        with open(filename, 'w') as f:
            f.write(frontmatter.dumps(post))
        
        print(f"✅ Post generado: {filename}")
        return filename
    
    def _parse_outline(self, text: str) -> list:
        """Parsea texto de outline a estructura."""
        # Implementación simplificada
        lines = text.strip().split('\n')
        outline = []
        for line in lines:
            if line.startswith('#'):
                level = len(line.split()[0])
                title = line.lstrip('#').strip()
                outline.append({"level": level, "title": title})
        return outline
    
    def _assemble_post(self, sections: list) -> str:
        """Ensambla secciones en post completo."""
        content = []
        for section in sections:
            heading = '#' * section["level"]
            content.append(f"{heading} {section['title']}\n\n{section['content']}\n\n")
        return '\n'.join(content)

# Uso
generator = BlogPostGenerator()
post_file = generator.generate_full_post(
    topic="Optimización de Kubernetes en Producción",
    tags=["kubernetes", "devops", "performance"],
    category="Infrastructure"
)
```

## 📊 Caso de Uso 4: Resumen de Artículos Técnicos

### Resumen Inteligente con Extracción de Conceptos

```python
import requests
from bs4 import BeautifulSoup

class TechnicalSummarizer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def fetch_article(self, url: str) -> dict:
        """Extrae contenido de un artículo web."""
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraer título y contenido principal
        title = soup.find('h1').get_text() if soup.find('h1') else "Sin título"
        
        # Remover scripts y estilos
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extraer texto
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return {"title": title, "content": text[:4000]}  # Limitar a 4k chars
    
    def summarize(
        self,
        text: str,
        summary_type: str = "executive",  # executive, technical, bullet_points
        max_length: int = 500
    ) -> str:
        """Genera resumen del texto."""
        
        prompts = {
            "executive": f"""
Resume este artículo técnico en {max_length} palabras para ejecutivos no técnicos.
Enfócate en: problema, solución, beneficios, impacto de negocio.

Artículo:
{text}

Resumen ejecutivo:
""",
            "technical": f"""
Resume este artículo técnico en {max_length} palabras para desarrolladores.
Incluye: conceptos clave, arquitectura, implementación, trade-offs.

Artículo:
{text}

Resumen técnico:
""",
            "bullet_points": f"""
Extrae los puntos clave de este artículo técnico (máximo 10 puntos).
Formato: lista con viñetas, concisa y accionable.

Artículo:
{text}

Puntos clave:
"""
        }
        
        prompt = prompts.get(summary_type, prompts["technical"])
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3
        })
        
        return response.json()["response"]
    
    def extract_code_examples(self, text: str) -> list:
        """Extrae snippets de código del texto."""
        
        prompt = f"""
Identifica y extrae TODOS los ejemplos de código de este artículo.
Para cada snippet, indica:
1. Lenguaje de programación
2. Propósito/descripción breve
3. El código completo

Texto:
{text}

Ejemplos de código:
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2
        })
        
        return response.json()["response"]
    
    def generate_study_notes(self, url: str) -> dict:
        """Genera notas de estudio completas de un artículo."""
        
        # 1. Fetch artículo
        article = self.fetch_article(url)
        
        # 2. Generar diferentes resúmenes
        executive = self.summarize(article["content"], "executive", 300)
        technical = self.summarize(article["content"], "technical", 500)
        bullet_points = self.summarize(article["content"], "bullet_points")
        
        # 3. Extraer código
        code_examples = self.extract_code_examples(article["content"])
        
        # 4. Ensamblar notas
        notes = f"""# {article['title']}

## Resumen Ejecutivo
{executive}

## Resumen Técnico
{technical}

## Puntos Clave
{bullet_points}

## Ejemplos de Código
{code_examples}

---
*Fuente:* {url}
*Generado:* {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        
        # 5. Guardar
        filename = f"notes_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        with open(filename, 'w') as f:
            f.write(notes)
        
        print(f"✅ Notas generadas: {filename}")
        
        return {
            "executive": executive,
            "technical": technical,
            "bullet_points": bullet_points,
            "code_examples": code_examples,
            "filename": filename
        }

# Uso
summarizer = TechnicalSummarizer()
notes = summarizer.generate_study_notes("https://blog.example.com/kubernetes-optimization")
```

## 🔄 Caso de Uso 5: Changelog Automático desde Git

### Generación de Release Notes

```python
import subprocess
import re

class ChangelogGenerator:
    def __init__(self, model: str = "llama2:7b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def get_commits_since_tag(self, tag: str = None) -> list:
        """Obtiene commits desde el último tag."""
        
        if not tag:
            # Obtener último tag
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True
            )
            tag = result.stdout.strip() if result.returncode == 0 else None
        
        # Obtener commits
        cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%H|%s|%b"] if tag else \
              ["git", "log", "--pretty=format:%H|%s|%b", "-20"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        commits = []
        for line in result.stdout.split('\n'):
            if '|' in line:
                hash_id, subject, body = line.split('|', 2)
                commits.append({
                    "hash": hash_id[:7],
                    "subject": subject,
                    "body": body.strip()
                })
        
        return commits
    
    def categorize_commits(self, commits: list) -> dict:
        """Categoriza commits por tipo (feat, fix, docs, etc.)."""
        
        categories = {
            "features": [],
            "fixes": [],
            "docs": [],
            "refactor": [],
            "other": []
        }
        
        for commit in commits:
            subject = commit["subject"].lower()
            if subject.startswith("feat"):
                categories["features"].append(commit)
            elif subject.startswith("fix"):
                categories["fixes"].append(commit)
            elif subject.startswith("docs"):
                categories["docs"].append(commit)
            elif subject.startswith("refactor"):
                categories["refactor"].append(commit)
            else:
                categories["other"].append(commit)
        
        return categories
    
    def generate_changelog(
        self,
        version: str,
        since_tag: str = None,
        output_file: str = "CHANGELOG.md"
    ) -> str:
        """Genera changelog profesional."""
        
        # 1. Obtener commits
        commits = self.get_commits_since_tag(since_tag)
        
        # 2. Categorizar
        categorized = self.categorize_commits(commits)
        
        # 3. Generar descripción con LLM
        prompt = f"""
Genera un changelog profesional para la versión {version} basado en estos commits:

**Features:**
{chr(10).join([f"- {c['subject']}" for c in categorized['features']])}

**Fixes:**
{chr(10).join([f"- {c['subject']}" for c in categorized['fixes']])}

**Docs:**
{chr(10).join([f"- {c['subject']}" for c in categorized['docs']])}

Requisitos:
1. Agrupa cambios relacionados
2. Usa lenguaje user-friendly (no técnico)
3. Destaca breaking changes si los hay
4. Formato Markdown con secciones claras

Changelog:
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.4
        })
        
        changelog_content = response.json()["response"]
        
        # 4. Agregar header
        full_changelog = f"""# Changelog

## [{version}] - {datetime.now().strftime("%Y-%m-%d")}

{changelog_content}

### Commits Incluidos
{chr(10).join([f"- {c['hash']} - {c['subject']}" for c in commits])}

"""
        
        # 5. Guardar
        with open(output_file, 'w') as f:
            f.write(full_changelog)
        
        print(f"✅ Changelog generado: {output_file}")
        return full_changelog

# Uso
generator = ChangelogGenerator()
changelog = generator.generate_changelog(
    version="v2.1.0",
    since_tag="v2.0.0"
)
```

## 🔧 Integración con CI/CD

### GitHub Actions Workflow

```yaml
name: Auto-generate Documentation

on:
  push:
    branches: [main]
  pull_request:

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama pull llama2:7b-chat-q4_0
      
      - name: Install dependencies
        run: pip install requests python-frontmatter beautifulsoup4
      
      - name: Generate API docs
        run: python scripts/generate_docs.py --input src/ --output docs/api/
      
      - name: Generate changelog
        run: python scripts/generate_changelog.py --version {% raw %}${{ github.ref_name }}{% endraw %}
      
      - name: Commit changes
        run: |
          git config --global user.name 'Documentation Bot'
          git config --global user.email 'bot@example.com'
          git add docs/ CHANGELOG.md
          git commit -m "docs: Auto-generate documentation [skip ci]" || true
          git push
```

## ⚠️ Mejores Prácticas

### Validación de Contenido Generado

```python
class ContentValidator:
    def validate_markdown(self, content: str) -> dict:
        """Valida formato Markdown."""
        issues = []
        
        # Verificar headers
        if not re.search(r'^# ', content, re.MULTILINE):
            issues.append("Falta título principal (H1)")
        
        # Verificar enlaces rotos
        links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
        for text, url in links:
            if url.startswith('http'):
                try:
                    response = requests.head(url, timeout=5)
                    if response.status_code >= 400:
                        issues.append(f"Enlace roto: {url}")
                except:
                    issues.append(f"No se puede validar: {url}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def check_code_syntax(self, content: str) -> dict:
        """Valida sintaxis de bloques de código."""
        code_blocks = re.findall(r'```(\w+)\n(.*?)\n```', content, re.DOTALL)
        issues = []
        
        for lang, code in code_blocks:
            if lang == "python":
                try:
                    compile(code, '<string>', 'exec')
                except SyntaxError as e:
                    issues.append(f"Error de sintaxis Python: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

# Uso
validator = ContentValidator()
validation_result = validator.validate_markdown(generated_content)
if not validation_result["valid"]:
    print("⚠️  Problemas encontrados:")
    for issue in validation_result["issues"]:
        print(f"  - {issue}")
```

### Control de Calidad

- ✅ **Revisión humana** siempre antes de publicar
- ✅ **Validación de sintaxis** de código generado
- ✅ **Verificación de enlaces** para evitar rotos
- ✅ **Spell checking** con herramientas como `aspell`
- ✅ **Tone consistency** validar con otro LLM

## 📊 Métricas y Monitoreo

```python
class DocumentationMetrics:
    def __init__(self):
        self.metrics = {
            "documents_generated": 0,
            "total_words": 0,
            "total_cost_saved_hours": 0,
            "errors": 0
        }
    
    def record_generation(self, word_count: int, time_taken: float):
        self.metrics["documents_generated"] += 1
        self.metrics["total_words"] += word_count
        
        # Estimar ahorro (promedio 500 palabras/hora manual)
        hours_saved = word_count / 500
        self.metrics["total_cost_saved_hours"] += hours_saved
    
    def report(self):
        return f"""
📊 Métricas de Generación de Documentación

Documentos generados: {self.metrics['documents_generated']}
Palabras totales: {self.metrics['total_words']:,}
Horas ahorradas: {self.metrics['total_cost_saved_hours']:.1f}h
Errores: {self.metrics['errors']}
"""

metrics = DocumentationMetrics()
```

## 🔗 Recursos Adicionales

- [Ollama API Documentation](https://github.com/jmorganca/ollama/blob/main/docs/api.md)
- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Docusaurus](https://docusaurus.io/)

## 📚 Próximos Pasos

Después de automatizar documentación, considera:

1. **[Análisis de Logs](analisis_logs.md)** - Troubleshooting asistido por IA
2. **[Prompt Engineering](prompt_engineering.md)** - Técnicas para mejores resultados
3. **[Fine-tuning](fine_tuning_basico.md)** - Personalizar modelos para tu dominio

---

*¿Has automatizado tu documentación con LLMs? Comparte tus experiencias y mejores prácticas en los comentarios.*