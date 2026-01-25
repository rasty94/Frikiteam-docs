---
title: "Automated Technical Content Generation with LLMs"
description: "Complete guide to generating technical documentation, READMEs, blog posts, and changelogs using local LLMs"
date: 2026-01-25
tags: [ai, llm, automation, documentation, content-generation]
difficulty: intermediate
estimated_time: "30 min"
category: ai
status: published
prerequisites: ["llms_fundamentals", "ollama_basics", "chatbots_locales"]
---

# Automated Technical Content Generation with LLMs

> **Reading time:** 30 minutes | **Difficulty:** Intermediate | **Category:** Artificial Intelligence

## Summary

Technical content creation (documentation, READMEs, changelogs, blog posts) is time-consuming but essential. This guide shows how to automate these processes using local LLMs, from docstring generation to complete article production.

## 🎯 Use Cases

### 1. Documentation from Code
- Automatic docstring generation
- README creation from project analysis
- API documentation from endpoints

### 2. Technical Blogging
- Post generation from git commits
- Article summarization
- Tutorial creation from examples

### 3. Changelog Automation
- Generation from git history
- Semantic versioning
- Integration with CI/CD

## 💡 Case 1: Automatic Docstring Generation

### Problem

Code without documentation is difficult to maintain. Writing docstrings manually is tedious and often forgotten.

### Solution with LLM

```python
import ast
import requests
from pathlib import Path

class DocstringGenerator:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def generate_docstrings(self, file_path: str) -> str:
        """
        Analyzes Python file and generates docstrings for functions/classes.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Modified code with generated docstrings
        """
        
        # Read original code
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Parse AST
        tree = ast.parse(code)
        
        # Find functions without docstrings
        functions_to_document = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    functions_to_document.append({
                        'name': node.name,
                        'code': ast.get_source_segment(code, node),
                        'lineno': node.lineno
                    })
        
        # Generate docstrings
        documented_code = code
        
        for func_info in reversed(functions_to_document):  # Reverse to maintain line numbers
            docstring = self._generate_docstring(func_info['code'])
            
            # Insert docstring
            lines = documented_code.split('\n')
            func_line = func_info['lineno'] - 1
            
            # Find indentation
            indent = len(lines[func_line]) - len(lines[func_line].lstrip())
            
            # Insert docstring after function definition
            docstring_lines = [
                ' ' * (indent + 4) + '"""',
                ' ' * (indent + 4) + docstring,
                ' ' * (indent + 4) + '"""'
            ]
            
            lines.insert(func_line + 1, '\n'.join(docstring_lines))
            documented_code = '\n'.join(lines)
        
        return documented_code
    
    def _generate_docstring(self, function_code: str) -> str:
        """Generates a docstring for function using LLM."""
        
        prompt = f"""
Generate a concise Google-style docstring for this Python function.

Code:
{function_code}

Requirements:
- Brief description (1-2 sentences)
- Args section with types
- Returns section with type
- Raises section if applicable
- Maximum 5 lines

Docstring:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.3,
            "stream": False
        })
        
        return response.json()["response"].strip()

# Usage
generator = DocstringGenerator()

# Generate docstrings for entire file
documented_code = generator.generate_docstrings("app/utils.py")

# Save result
with open("app/utils_documented.py", 'w') as f:
    f.write(documented_code)

print("✅ Docstrings generated successfully")
```

### Advanced: Smart Docstring

```python
class SmartDocstringGenerator:
    """Generates context-aware docstrings."""
    
    def generate_docstring(
        self,
        function_code: str,
        file_context: str = "",
        project_type: str = "general"
    ) -> str:
        """
        Generates docstring considering code context.
        
        Args:
            function_code: Source code of function
            file_context: Surrounding code for context
            project_type: Type of project (api, cli, library, etc.)
            
        Returns:
            Generated docstring
        """
        
        prompt = f"""
You are a technical documentation expert specializing in {project_type} projects.

Generate a professional docstring for this function.

Full file context:
{file_context[:500]}... # Truncated for brevity

Function to document:
{function_code}

Docstring requirements for {project_type} projects:
- Clear and concise description
- Complete type hints in Args
- Usage examples if it's a public API
- Error handling documentation
- Performance considerations if relevant

Generated docstring:"""
        
        response = requests.post(self.ollama_url, json={
            "model": "llama2:13b-chat-q4_0",
            "prompt": prompt,
            "temperature": 0.4,
            "stream": False
        })
        
        return response.json()["response"].strip()
```

## 📝 Case 2: Automatic README Generation

### Problem

Well-structured READMEs are crucial but tedious to maintain. Information often becomes outdated.

### Solution with LLM

```python
import os
import subprocess
from pathlib import Path

class READMEGenerator:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def generate_readme(self, project_path: str) -> str:
        """
        Generates README.md for a project analyzing its structure.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Generated README content
        """
        
        # Gather project information
        project_info = self._analyze_project(project_path)
        
        # Generate README sections
        readme_sections = []
        
        readme_sections.append(self._generate_header(project_info))
        readme_sections.append(self._generate_description(project_info))
        readme_sections.append(self._generate_features(project_info))
        readme_sections.append(self._generate_installation(project_info))
        readme_sections.append(self._generate_usage(project_info))
        readme_sections.append(self._generate_contributing(project_info))
        
        return "\n\n".join(readme_sections)
    
    def _analyze_project(self, project_path: str) -> dict:
        """Analyzes project structure and extracts information."""
        
        info = {
            "path": project_path,
            "name": Path(project_path).name,
            "files": [],
            "dependencies": {},
            "languages": set(),
            "has_tests": False,
            "has_docker": False,
            "has_ci": False
        }
        
        # Scan files
        for root, dirs, files in os.walk(project_path):
            # Ignore common directories
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__']]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_path)
                
                info["files"].append(str(relative_path))
                
                # Detect language
                if file.endswith('.py'):
                    info["languages"].add("Python")
                elif file.endswith('.js') or file.endswith('.ts'):
                    info["languages"].add("JavaScript/TypeScript")
                elif file.endswith('.go'):
                    info["languages"].add("Go")
                
                # Detect special files
                if file == "requirements.txt":
                    with open(file_path) as f:
                        info["dependencies"]["python"] = f.read().splitlines()
                elif file == "package.json":
                    import json
                    with open(file_path) as f:
                        pkg = json.load(f)
                        info["dependencies"]["node"] = list(pkg.get("dependencies", {}).keys())
                elif file == "Dockerfile":
                    info["has_docker"] = True
                elif file in [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile"]:
                    info["has_ci"] = True
                elif "test" in file.lower():
                    info["has_tests"] = True
        
        return info
    
    def _generate_header(self, info: dict) -> str:
        """Generates README header."""
        
        prompt = f"""
Generate a header for a README.md for this project:

Project name: {info['name']}
Languages: {', '.join(info['languages'])}

Requirements:
- Create an attractive title with emoji
- Add relevant badges (language, license, build status)
- Brief tagline (1 sentence)

Header in Markdown:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.5,
            "stream": False
        })
        
        return response.json()["response"].strip()
    
    def _generate_description(self, info: dict) -> str:
        """Generates project description."""
        
        # Read main files to understand the project
        main_files_content = []
        
        for file in ["main.py", "app.py", "index.js", "main.go"]:
            if file in info["files"]:
                try:
                    with open(Path(info["path"]) / file) as f:
                        main_files_content.append(f.read()[:1000])  # First 1000 chars
                except:
                    pass
        
        prompt = f"""
Analyze this project and generate a description for the README.

Project: {info['name']}
Languages: {', '.join(info['languages'])}
Has Docker: {info['has_docker']}
Has Tests: {info['has_tests']}

Main code sample:
{main_files_content[0] if main_files_content else "No main files found"}

Generate:
1. Brief description (2-3 sentences)
2. Key features list (3-5 items)
3. Primary use case

Format in Markdown with ## Description section:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.4,
            "stream": False
        })
        
        return response.json()["response"].strip()
    
    def _generate_installation(self, info: dict) -> str:
        """Generates installation instructions."""
        
        steps = ["## Installation\n"]
        
        if "Python" in info["languages"]:
            steps.append("### Python")
            steps.append("```bash")
            steps.append("# Create virtual environment")
            steps.append("python -m venv venv")
            steps.append("source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
            steps.append("")
            steps.append("# Install dependencies")
            steps.append("pip install -r requirements.txt")
            steps.append("```")
        
        if "JavaScript/TypeScript" in info["languages"]:
            steps.append("\n### Node.js")
            steps.append("```bash")
            steps.append("npm install")
            steps.append("# or")
            steps.append("yarn install")
            steps.append("```")
        
        if info["has_docker"]:
            steps.append("\n### Docker")
            steps.append("```bash")
            steps.append("docker build -t " + info["name"] + " .")
            steps.append("docker run -p 8080:8080 " + info["name"])
            steps.append("```")
        
        return "\n".join(steps)
    
    def _generate_usage(self, info: dict) -> str:
        """Generates usage examples."""
        
        # This would ideally analyze the code to find entry points
        return f"""## Usage

### Basic Example

```bash
# Run the application
python main.py  # or npm start, go run main.go, etc.
```

### Configuration

See `config.yml` or `.env.example` for configuration options.
"""
    
    def _generate_contributing(self, info: dict) -> str:
        """Generates contribution guidelines."""
        
        return """## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
"""

# Usage
generator = READMEGenerator()

# Generate README for current project
readme_content = generator.generate_readme("./my-project")

# Save to file
with open("./my-project/README.md", 'w') as f:
    f.write(readme_content)

print("✅ README.md generated successfully")
```

## ✍️ Case 3: Technical Blog Post Generation

### Problem

Maintaining a technical blog requires significant time investment. We want to automate post creation from git commits or documentation.

### Solution with LLM

```python
import subprocess
from datetime import datetime
from typing import List, Dict

class BlogPostGenerator:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def generate_post_from_commits(
        self,
        repo_path: str,
        since_date: str,
        category: str = "development"
    ) -> str:
        """
        Generates blog post from git commits in a period.
        
        Args:
            repo_path: Path to git repository
            since_date: Start date (format: YYYY-MM-DD)
            category: Post category
            
        Returns:
            Generated post in Markdown
        """
        
        # Get git commits
        os.chdir(repo_path)
        
        git_log = subprocess.check_output([
            "git", "log",
            f"--since={since_date}",
            "--pretty=format:%h|%an|%ad|%s",
            "--date=short"
        ]).decode('utf-8')
        
        commits = []
        for line in git_log.split('\n'):
            if line:
                hash, author, date, message = line.split('|')
                commits.append({
                    "hash": hash,
                    "author": author,
                    "date": date,
                    "message": message
                })
        
        # Group by category
        categorized_commits = self._categorize_commits(commits)
        
        # Generate post
        post_content = self._generate_post_content(
            categorized_commits,
            since_date,
            category
        )
        
        return post_content
    
    def _categorize_commits(self, commits: List[Dict]) -> Dict:
        """Categorizes commits by type."""
        
        categories = {
            "features": [],
            "fixes": [],
            "docs": [],
            "refactor": [],
            "other": []
        }
        
        for commit in commits:
            msg = commit["message"].lower()
            
            if any(keyword in msg for keyword in ["feat", "feature", "add"]):
                categories["features"].append(commit)
            elif any(keyword in msg for keyword in ["fix", "bug", "resolve"]):
                categories["fixes"].append(commit)
            elif any(keyword in msg for keyword in ["docs", "documentation"]):
                categories["docs"].append(commit)
            elif any(keyword in msg for keyword in ["refactor", "cleanup", "improve"]):
                categories["refactor"].append(commit)
            else:
                categories["other"].append(commit)
        
        return categories
    
    def _generate_post_content(
        self,
        categorized_commits: Dict,
        since_date: str,
        category: str
    ) -> str:
        """Generates complete blog post from categorized commits."""
        
        # Summary of changes
        total_commits = sum(len(commits) for commits in categorized_commits.values())
        
        prompt = f"""
Generate an engaging technical blog post about recent project updates.

Period: since {since_date}
Total commits: {total_commits}

Changes by category:
- New features: {len(categorized_commits['features'])} commits
- Bug fixes: {len(categorized_commits['fixes'])} commits
- Documentation: {len(categorized_commits['docs'])} commits
- Refactoring: {len(categorized_commits['refactor'])} commits

Featured commits:
{self._format_commits_for_prompt(categorized_commits)}

Requirements:
- Engaging title with emoji
- Introduction explaining context (1-2 paragraphs)
- Sections for each category with highlights
- Technical details where relevant
- Conclusion with future plans
- Conversational but professional tone
- 800-1000 words

Blog post in Markdown:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.6,
            "stream": False
        })
        
        post = response.json()["response"]
        
        # Add frontmatter
        frontmatter = f"""---
title: "Project Updates - {datetime.now().strftime('%B %Y')}"
date: {datetime.now().isoformat()}
category: {category}
tags: [development, updates, changelog]
---

"""
        
        return frontmatter + post
    
    def _format_commits_for_prompt(self, categorized: Dict) -> str:
        """Formats commits for inclusion in prompt."""
        
        lines = []
        
        for category, commits in categorized.items():
            if commits:
                lines.append(f"\n{category.upper()}:")
                for commit in commits[:5]:  # Max 5 per category
                    lines.append(f"  - {commit['message']} ({commit['hash']})")
        
        return "\n".join(lines)

# Usage
generator = BlogPostGenerator()

# Generate post from last week's commits
post = generator.generate_post_from_commits(
    repo_path="./my-project",
    since_date="2024-01-15",
    category="development"
)

# Save to blog
with open("./blog/posts/2024/january-updates.md", 'w') as f:
    f.write(post)

print("✅ Blog post generated successfully")
```

## 📄 Case 4: Technical Article Summarization

### Problem

Need to quickly understand long technical articles or extract key points for newsletters.

### Solution with LLM

```python
import requests
from bs4 import BeautifulSoup

class TechnicalSummarizer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def summarize_url(
        self,
        url: str,
        summary_type: str = "executive"
    ) -> dict:
        """
        Summarizes technical article from URL.
        
        Args:
            url: Article URL
            summary_type: Type of summary (executive, technical, bullet-points)
            
        Returns:
            Dict with summary and metadata
        """
        
        # Fetch and parse article
        content = self._fetch_article(url)
        
        # Generate summary
        if summary_type == "executive":
            summary = self._generate_executive_summary(content)
        elif summary_type == "technical":
            summary = self._generate_technical_summary(content)
        else:
            summary = self._generate_bullet_points(content)
        
        return {
            "url": url,
            "type": summary_type,
            "summary": summary,
            "word_count": len(content.split()),
            "reading_time": len(content.split()) // 200  # ~200 words per minute
        }
    
    def _fetch_article(self, url: str) -> str:
        """Fetches and extracts article content."""
        
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:4000]  # Limit to 4000 chars
    
    def _generate_executive_summary(self, content: str) -> str:
        """Generates executive summary (high-level, non-technical)."""
        
        prompt = f"""
Generate an executive summary for this technical article.

Article content:
{content}

Requirements:
- 2-3 paragraphs
- Non-technical language
- Focus on business impact and key takeaways
- What, why, and impact - not how
- 150-200 words

Executive summary:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.4,
            "stream": False
        })
        
        return response.json()["response"].strip()
    
    def _generate_technical_summary(self, content: str) -> str:
        """Generates technical summary for developers."""
        
        prompt = f"""
Generate a technical summary for this article aimed at developers.

Article content:
{content}

Requirements:
- 3-4 paragraphs
- Include technical details
- Key technologies/approaches mentioned
- Implementation considerations
- 250-300 words

Technical summary:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.3,
            "stream": False
        })
        
        return response.json()["response"].strip()
    
    def _generate_bullet_points(self, content: str) -> str:
        """Generates bullet-point summary."""
        
        prompt = f"""
Extract key points from this technical article.

Article content:
{content}

Generate:
- Main concept (1 sentence)
- Key points (5-7 bullet points)
- Technologies mentioned
- Actionable takeaways

Format:
## Main Concept
[one sentence]

## Key Points
- [point 1]
- [point 2]
...

## Technologies
- [tech 1]
- [tech 2]

## Actionable Takeaways
- [action 1]
- [action 2]

Summary:"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.3,
            "stream": False
        })
        
        return response.json()["response"].strip()

# Usage
summarizer = TechnicalSummarizer()

# Summarize article
summary = summarizer.summarize_url(
    url="https://kubernetes.io/blog/2024/01/new-features",
    summary_type="bullet-points"
)

print(f"Article: {summary['url']}")
print(f"Reading time: {summary['reading_time']} min")
print(f"\n{summary['summary']}")
```

## 📋 Case 5: Automatic Changelog Generation

### Problem

Maintaining changelogs manually is tedious and error-prone. We want to generate them automatically from git commits.

### Solution with LLM

```python
import subprocess
import re
from typing import List, Dict
from datetime import datetime

class ChangelogGenerator:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def generate_changelog(
        self,
        repo_path: str,
        from_tag: str = None,
        to_tag: str = "HEAD",
        version: str = None
    ) -> str:
        """
        Generates changelog from git commits.
        
        Args:
            repo_path: Path to git repository
            from_tag: Starting tag/commit
            to_tag: Ending tag/commit
            version: Version for this release
            
        Returns:
            Generated changelog in Keep a Changelog format
        """
        
        import os
        os.chdir(repo_path)
        
        # Get commits
        if from_tag:
            git_range = f"{from_tag}..{to_tag}"
        else:
            git_range = to_tag
        
        git_log = subprocess.check_output([
            "git", "log", git_range,
            "--pretty=format:%H|%s|%b|%an|%ad",
            "--date=short"
        ]).decode('utf-8')
        
        commits = self._parse_commits(git_log)
        
        # Categorize commits
        categorized = self._smart_categorize(commits)
        
        # Generate changelog
        return self._generate_changelog_content(categorized, version or "Unreleased")
    
    def _parse_commits(self, git_log: str) -> List[Dict]:
        """Parses git log output."""
        
        commits = []
        
        for line in git_log.split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0][:7],
                    "subject": parts[1],
                    "body": parts[2],
                    "author": parts[3],
                    "date": parts[4]
                })
        
        return commits
    
    def _smart_categorize(self, commits: List[Dict]) -> Dict:
        """Categorizes commits using LLM."""
        
        categories = {
            "added": [],
            "changed": [],
            "deprecated": [],
            "removed": [],
            "fixed": [],
            "security": []
        }
        
        # Batch commits for efficiency
        batch_size = 10
        
        for i in range(0, len(commits), batch_size):
            batch = commits[i:i + batch_size]
            
            # Create prompt for batch
            commit_list = "\n".join([
                f"{c['hash']}: {c['subject']}"
                for c in batch
            ])
            
            prompt = f"""
Categorize these git commits into semantic changelog categories.

Commits:
{commit_list}

Categories:
- ADDED: New features
- CHANGED: Changes in existing functionality
- DEPRECATED: Soon-to-be removed features
- REMOVED: Removed features
- FIXED: Bug fixes
- SECURITY: Security fixes

Respond in format:
HASH: CATEGORY

Response:"""
            
            response = requests.post(self.ollama_url, json={
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.2,
                "stream": False
            })
            
            # Parse response
            categorization = response.json()["response"]
            
            for line in categorization.split('\n'):
                match = re.match(r'(\w+):\s*(ADDED|CHANGED|DEPRECATED|REMOVED|FIXED|SECURITY)', line)
                if match:
                    commit_hash, category = match.groups()
                    
                    # Find commit
                    commit = next((c for c in batch if c['hash'].startswith(commit_hash)), None)
                    if commit:
                        categories[category.lower()].append(commit)
        
        return categories
    
    def _generate_changelog_content(self, categorized: Dict, version: str) -> str:
        """Generates changelog content in Keep a Changelog format."""
        
        lines = [
            f"# Changelog",
            "",
            f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}",
            ""
        ]
        
        category_titles = {
            "added": "### Added",
            "changed": "### Changed",
            "deprecated": "### Deprecated",
            "removed": "### Removed",
            "fixed": "### Fixed",
            "security": "### Security"
        }
        
        for category, title in category_titles.items():
            if categorized[category]:
                lines.append(title)
                
                for commit in categorized[category]:
                    # Clean up commit message
                    message = commit['subject']
                    
                    # Remove conventional commit prefix if present
                    message = re.sub(r'^(feat|fix|docs|style|refactor|test|chore)(\(.+?\))?:\s*', '', message)
                    
                    lines.append(f"- {message} ({commit['hash']})")
                
                lines.append("")
        
        return "\n".join(lines)

# Usage
generator = ChangelogGenerator()

# Generate changelog for new release
changelog = generator.generate_changelog(
    repo_path="./my-project",
    from_tag="v1.0.0",
    to_tag="HEAD",
    version="1.1.0"
)

# Update CHANGELOG.md
with open("./my-project/CHANGELOG.md", 'r') as f:
    existing_changelog = f.read()

# Insert new version at top
updated_changelog = changelog + "\n\n" + existing_changelog

with open("./my-project/CHANGELOG.md", 'w') as f:
    f.write(updated_changelog)

print("✅ Changelog updated successfully")
```

## 🔄 Integration with CI/CD

### GitHub Actions Example

```yaml
name: Auto-Generate Documentation

on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize]

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama serve &
          sleep 5
          ollama pull llama2:13b-chat-q4_0
      
      - name: Install dependencies
        run: |
          pip install requests beautifulsoup4 PyYAML
      
      - name: Generate docstrings
        run: |
          python scripts/generate_docstrings.py
      
      - name: Update README
        run: |
          python scripts/generate_readme.py
      
      - name: Update CHANGELOG
        if: github.event_name == 'push'
        run: |
          python scripts/generate_changelog.py
      
      - name: Commit changes
        if: github.event_name == 'push'
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git diff --quiet && git diff --staged --quiet || git commit -m "docs: Auto-generate documentation [skip ci]"
          git push
```

## ✅ Content Validation

### Ensuring Quality

```python
class ContentValidator:
    def __init__(self):
        self.checks = [
            self.check_spelling,
            self.check_broken_links,
            self.check_code_blocks,
            self.check_frontmatter
        ]
    
    def validate(self, content: str, file_type: str) -> dict:
        """Validates generated content."""
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        for check in self.checks:
            check_result = check(content, file_type)
            
            if check_result["errors"]:
                results["valid"] = False
                results["errors"].extend(check_result["errors"])
            
            results["warnings"].extend(check_result.get("warnings", []))
        
        return results
    
    def check_spelling(self, content: str, file_type: str) -> dict:
        """Check for common spelling errors."""
        # Implementation using spell checker
        return {"errors": [], "warnings": []}
    
    def check_broken_links(self, content: str, file_type: str) -> dict:
        """Check for broken links."""
        # Implementation to validate URLs
        return {"errors": [], "warnings": []}
    
    def check_code_blocks(self, content: str, file_type: str) -> dict:
        """Validate code blocks."""
        # Check that code blocks have language specified
        import re
        
        errors = []
        code_blocks = re.findall(r'```(\w*)\n', content)
        
        for i, lang in enumerate(code_blocks):
            if not lang:
                errors.append(f"Code block {i+1} missing language identifier")
        
        return {"errors": errors, "warnings": []}
    
    def check_frontmatter(self, content: str, file_type: str) -> dict:
        """Validate YAML frontmatter."""
        
        if file_type != "markdown":
            return {"errors": [], "warnings": []}
        
        errors = []
        
        if not content.startswith("---"):
            errors.append("Missing YAML frontmatter")
        else:
            try:
                import yaml
                # Extract frontmatter
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    
                    # Required fields
                    required = ["title", "date", "category"]
                    for field in required:
                        if field not in frontmatter:
                            errors.append(f"Missing required field: {field}")
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML: {e}")
        
        return {"errors": errors, "warnings": []}
```

## 📈 Metrics and Tracking

```python
class ContentMetrics:
    def __init__(self):
        self.metrics = []
    
    def track_generation(
        self,
        content_type: str,
        input_size: int,
        output_size: int,
        time_taken: float,
        quality_score: float
    ):
        """Track content generation metrics."""
        
        self.metrics.append({
            "timestamp": datetime.now().isoformat(),
            "type": content_type,
            "input_size": input_size,
            "output_size": output_size,
            "time_taken": time_taken,
            "quality_score": quality_score,
            "efficiency": output_size / time_taken if time_taken > 0 else 0
        })
    
    def get_summary(self) -> dict:
        """Get metrics summary."""
        
        if not self.metrics:
            return {}
        
        return {
            "total_content_generated": len(self.metrics),
            "total_words": sum(m["output_size"] for m in self.metrics),
            "avg_quality": sum(m["quality_score"] for m in self.metrics) / len(self.metrics),
            "avg_time": sum(m["time_taken"] for m in self.metrics) / len(self.metrics),
            "by_type": self._group_by_type()
        }
    
    def _group_by_type(self) -> dict:
        """Group metrics by content type."""
        
        from collections import defaultdict
        
        by_type = defaultdict(list)
        
        for metric in self.metrics:
            by_type[metric["type"]].append(metric)
        
        return {
            content_type: {
                "count": len(metrics),
                "total_words": sum(m["output_size"] for m in metrics),
                "avg_quality": sum(m["quality_score"] for m in metrics) / len(metrics)
            }
            for content_type, metrics in by_type.items()
        }
```

## 🔐 Security Considerations

- **Input Validation:** Always sanitize user input before passing to LLM
- **Output Verification:** Review generated content before publication
- **API Keys:** Store credentials in environment variables
- **Rate Limiting:** Implement limits to avoid abuse
- **Content Filtering:** Check for inappropriate or harmful content

## 📚 Additional Resources

- [Documentation as Code](https://www.writethedocs.org/guide/docs-as-code/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Technical Writing Best Practices](https://developers.google.com/tech-writing)

## 📊 Next Steps

After mastering content generation, consider:

1. **[Log Analysis](analisis_logs.md)** - Troubleshooting with LLMs
2. **[Prompt Engineering](prompt_engineering.md)** - Advanced techniques
3. **[Model Optimization](model_optimization.md)** - Improve performance

---

*Have you automated your documentation workflow? Share your experience and tools in the comments.*