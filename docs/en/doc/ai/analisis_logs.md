---
title: "Log Analysis and Troubleshooting with LLMs"
description: "Using Large Language Models for automatic log analysis, error detection and problem-solving suggestions"
date: 2026-01-25
tags: [ai, llm, logs, troubleshooting, observability, debugging]
difficulty: intermediate
estimated_time: "35 min"
category: ai
status: published
prerequisites: ["ollama_basics", "chatbots_locales"]
---

# Log Analysis and Troubleshooting with LLMs

> **Reading time:** 35 minutes | **Difficulty:** Intermediate | **Category:** Artificial Intelligence

## Summary

LLMs can analyze system logs, detect error patterns, and automatically suggest solutions. This guide covers practical techniques for using local models in infrastructure troubleshooting, significantly reducing mean time to resolution (MTTR).

## 🎯 Why Use LLMs for Log Analysis

### Common Problems in Troubleshooting

- **Overwhelming volume:** Millions of log lines per day
- **Excessive noise:** 99% of logs are normal information
- **Distributed context:** Errors span multiple services
- **Scarce expertise:** Not everyone knows every system
- **Critical time:** Downtime costs money

### LLM Benefits

- ✅ **Automatic anomaly detection** in logs
- ✅ **Intelligent correlation** of related events
- ✅ **Contextual solution suggestions**
- ✅ **Continuous learning** from past incidents
- ✅ **Multilingual analysis** of logs in different formats

## 🔍 Use Case 1: Application Log Analysis

### Intelligent Stack Trace Parser

```python
import re
import requests
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class LogAnalysis:
    error_type: str
    severity: str
    root_cause: str
    suggestions: List[str]
    confidence: float

class LogAnalyzer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def analyze_error_log(self, log_content: str, context: str = "") -> LogAnalysis:
        """
        Analyzes error logs using LLM to identify root causes and solutions.
        
        Args:
            log_content: Raw log content with error
            context: Additional context about the system/application
            
        Returns:
            Analysis with error type, severity, root cause and suggestions
        """
        
        prompt = f"""
Analyze this application error log and provide a detailed diagnosis.

Error Log:
{log_content}

Context:
{context}

Provide analysis in JSON format:
{% raw %}
{
  "error_type": "Type of error (Exception, Timeout, Database, etc.)",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "root_cause": "Most likely cause of the error",
  "suggestions": ["Step 1", "Step 2", "Step 3"],
  "confidence": 0.0-1.0
}
{% endraw %}

Focus on:
- Identifying the exact error type
- Determining severity level
- Finding the root cause
- Providing actionable solutions
- Being specific and technical
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.3,
            "stream": False,
            "format": "json"
        })
        
        import json
        result = json.loads(response.json()["response"])
        
        return LogAnalysis(
            error_type=result["error_type"],
            severity=result["severity"],
            root_cause=result["root_cause"],
            suggestions=result["suggestions"],
            confidence=result["confidence"]
        )

# Usage
analyzer = LogAnalyzer()

error_log = """
2024-01-25 10:30:15 ERROR [web-server] Connection refused: connect to database:5432
java.net.ConnectException: Connection refused
    at java.net.PlainSocketImpl.socketConnect(Native Method)
    at java.net.AbstractPlainSocketImpl.doConnect(AbstractPlainSocketImpl.java:412)
    at java.net.AbstractPlainSocketImpl.connectToAddress(AbstractPlainSocketImpl.java:255)
    at java.net.AbstractPlainSocketImpl.connect(AbstractPlainSocketImpl.java:241)
    at java.net.Socket.connect(Socket.java:589)
    at org.postgresql.core.PGStream.<init>(PGStream.java:70)
    at org.postgresql.core.v3.ConnectionFactoryImpl.tryConnect(ConnectionFactoryImpl.java:91)
    at org.postgresql.core.v3.ConnectionFactoryImpl.openConnectionImpl(ConnectionFactoryImpl.java:192)
    at org.postgresql.core.ConnectionFactory.openConnection(ConnectionFactory.java:49)
    at org.postgresql.jdbc.PgConnection.<init>(PgConnection.java:195)
    at org.postgresql.Driver.makeConnection(Driver.java:454)
    at org.postgresql.Driver.connect(Driver.java:256)
    at java.sql.DriverManager.getConnection(DriverManager.java:664)
"""

context = """
Spring Boot application connecting to PostgreSQL database.
Database service is running on db-server:5432.
Application is deployed in Kubernetes cluster.
"""

analysis = analyzer.analyze_error_log(error_log, context)

print(f"Error Type: {analysis.error_type}")
print(f"Severity: {analysis.severity}")
print(f"Root Cause: {analysis.root_cause}")
print(f"Confidence: {analysis.confidence:.1%}")
print("\nSuggestions:")
for i, suggestion in enumerate(analysis.suggestions, 1):
    print(f"{i}. {suggestion}")
```

### Advanced Error Classification

```python
class AdvancedLogAnalyzer:
    """Advanced analyzer with pattern recognition and historical learning."""
    
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.error_patterns = self._load_error_patterns()
    
    def _load_error_patterns(self) -> Dict[str, Dict]:
        """Load known error patterns for faster classification."""
        
        return {
            "database_connection": {
                "patterns": ["Connection refused", "timeout", "connection pool exhausted"],
                "category": "Database",
                "common_causes": ["Service down", "Network issues", "Configuration error"]
            },
            "memory_error": {
                "patterns": ["OutOfMemoryError", "MemoryError", "heap space"],
                "category": "Memory",
                "common_causes": ["Memory leak", "Insufficient RAM", "Large data processing"]
            },
            "timeout": {
                "patterns": ["timeout", "timed out", "deadline exceeded"],
                "category": "Performance",
                "common_causes": ["Slow queries", "Network latency", "Resource contention"]
            }
        }
    
    def classify_error(self, error_message: str) -> str:
        """Quick classification using pattern matching."""
        
        for error_type, data in self.error_patterns.items():
            for pattern in data["patterns"]:
                if pattern.lower() in error_message.lower():
                    return data["category"]
        
        return "Unknown"
    
    def analyze_with_history(self, current_error: str, past_incidents: List[Dict]) -> Dict:
        """
        Analyze current error considering historical incidents.
        
        Args:
            current_error: Current error log
            past_incidents: List of past similar incidents with resolutions
            
        Returns:
            Analysis considering historical context
        """
        
        # Find similar past incidents
        similar_incidents = self._find_similar_incidents(current_error, past_incidents)
        
        prompt = f"""
Analyze this current error considering historical incidents.

CURRENT ERROR:
{current_error}

SIMILAR PAST INCIDENTS:
{chr(10).join([f"Incident {i+1}: {inc['error']} -> Resolution: {inc['resolution']}" 
               for i, inc in enumerate(similar_incidents[:3])])}

Provide analysis in JSON:
{% raw %}
{
  "pattern_recognized": "Is this a recurring pattern?",
  "historical_solutions": ["Solution 1", "Solution 2"],
  "recommended_action": "Immediate action to take",
  "preventive_measures": ["Measure 1", "Measure 2"],
  "escalation_needed": true/false
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False,
            "format": "json"
        })
        
        import json
        return json.loads(response.json()["response"])
    
    def _find_similar_incidents(self, error: str, incidents: List[Dict]) -> List[Dict]:
        """Find incidents similar to current error."""
        
        similar = []
        error_lower = error.lower()
        
        for incident in incidents:
            incident_error = incident.get("error", "").lower()
            
            # Simple similarity check (could be improved with embeddings)
            if any(word in incident_error for word in error_lower.split() if len(word) > 3):
                similar.append(incident)
        
        return similar[:5]  # Return top 5 similar incidents
```

## 🐳 Use Case 2: Kubernetes Pod Monitoring

### CrashLoopBackOff Analyzer

```python
class KubernetesLogAnalyzer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def analyze_crash_loop(self, pod_name: str, namespace: str, logs: str) -> Dict:
        """
        Analyzes Kubernetes pod in CrashLoopBackOff state.
        
        Args:
            pod_name: Name of the crashing pod
            namespace: Kubernetes namespace
            logs: Pod logs from kubectl logs command
            
        Returns:
            Analysis with root cause and solutions
        """
        
        prompt = f"""
Analyze this Kubernetes pod that is in CrashLoopBackOff state.

Pod: {pod_name}
Namespace: {namespace}

Recent logs:
{logs}

Common CrashLoopBackOff causes:
1. Application errors (exceptions, segfaults)
2. Resource constraints (memory, CPU)
3. Configuration errors (env vars, secrets)
4. Dependency issues (database, services)
5. Health check failures
6. Image issues (corrupted, wrong architecture)

Provide detailed analysis in JSON:
{% raw %}
{
  "root_cause_category": "Category from the list above",
  "specific_error": "Exact error or symptom identified",
  "confidence_level": 0.0-1.0,
  "immediate_actions": ["kubectl describe pod", "kubectl logs --previous"],
  "solutions": [
    {
      "description": "Solution description",
      "commands": ["kubectl command 1", "kubectl command 2"],
      "priority": "HIGH|MEDIUM|LOW"
    }
  ],
  "preventive_measures": ["Measure 1", "Measure 2"]
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False,
            "format": "json"
        })
        
        import json
        return json.loads(response.json()["response"])
    
    def generate_troubleshooting_script(self, analysis: Dict) -> str:
        """Generates a bash script to execute troubleshooting steps."""
        
        script_lines = [
            "#!/bin/bash",
            f"# Troubleshooting script for pod: {analysis.get('pod_name', 'unknown')}",
            "set -e",
            "",
            "# Immediate diagnostic commands"
        ]
        
        for action in analysis.get("immediate_actions", []):
            script_lines.append(f"echo 'Executing: {action}'")
            script_lines.append(action)
            script_lines.append("")
        
        script_lines.extend([
            "# Solutions to try:",
            "# 1. Check resource limits",
            "kubectl describe pod $POD_NAME | grep -A 10 'Limits:'",
            "",
            "# 2. Check events",
            "kubectl get events --sort-by='.lastTimestamp' | tail -10",
            "",
            "# 3. Check pod status",
            "kubectl get pods -o wide"
        ])
        
        return "\n".join(script_lines)

# Usage
k8s_analyzer = KubernetesLogAnalyzer()

# Example crash loop logs
crash_logs = """
2024-01-25 10:15:23 INFO Starting Spring Boot application...
2024-01-25 10:15:24 INFO Environment: prod
2024-01-25 10:15:25 ERROR Failed to connect to Redis at redis-service:6379
java.net.ConnectException: Connection refused (Connection refused)
2024-01-25 10:15:25 INFO Shutting down application...
2024-01-25 10:15:26 INFO Application stopped
"""

analysis = k8s_analyzer.analyze_crash_loop(
    pod_name="web-app-7f8b9c4d5e",
    namespace="production",
    logs=crash_logs
)

print("Root Cause Category:", analysis["root_cause_category"])
print("Specific Error:", analysis["specific_error"])
print("Confidence:", f"{analysis['confidence_level']:.1%}")
print("\nImmediate Actions:")
for action in analysis["immediate_actions"]:
    print(f"- {action}")

print("\nSolutions:")
for solution in analysis["solutions"]:
    print(f"- {solution['description']} (Priority: {solution['priority']})")
    for cmd in solution["commands"]:
        print(f"  $ {cmd}")

# Generate troubleshooting script
script = k8s_analyzer.generate_troubleshooting_script(analysis)
with open("troubleshoot_pod.sh", 'w') as f:
    f.write(script)

print("\n✅ Troubleshooting script generated: troubleshoot_pod.sh")
```

### Multi-Pod Analysis

```python
class ClusterAnalyzer:
    """Analyzes entire Kubernetes clusters for issues."""
    
    def analyze_cluster_health(self, kubectl_output: str) -> Dict:
        """
        Analyzes overall cluster health from kubectl commands.
        
        Args:
            kubectl_output: Combined output from multiple kubectl commands
            
        Returns:
            Cluster health analysis
        """
        
        prompt = f"""
Analyze this Kubernetes cluster status and identify issues.

Cluster Status:
{kubectl_output}

Look for:
- Pod status issues (CrashLoopBackOff, Pending, Failed)
- Resource constraints (CPU/Memory pressure)
- Network issues
- Storage problems
- Node problems

Provide analysis in JSON:
{% raw %}
{
  "overall_health": "HEALTHY|WARNING|CRITICAL",
  "issues_found": [
    {
      "type": "pod|node|resource|network",
      "severity": "HIGH|MEDIUM|LOW",
      "description": "Issue description",
      "affected_resources": ["resource1", "resource2"],
      "recommended_actions": ["action1", "action2"]
    }
  ],
  "resource_utilization": {
    "cpu_percent": 0,
    "memory_percent": 0,
    "storage_percent": 0
  },
  "summary": "Brief summary of cluster status"
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False,
            "format": "json"
        })
        
        import json
        return json.loads(response.json()["response"])
```

## 🌐 Use Case 3: Web Server Security Monitoring

### Attack Pattern Detection

```python
class WebServerLogAnalyzer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def analyze_attack_patterns(self, log_lines: List[str]) -> Dict:
        """
        Analyzes web server logs for security threats.
        
        Args:
            log_lines: List of log lines from web server (Nginx/Apache)
            
        Returns:
            Analysis of detected attack patterns
        """
        
        # Common attack patterns
        attack_patterns = {
            "sql_injection": [
                r"UNION\s+SELECT", r"1=1", r"OR\s+1=1", r"DROP\s+TABLE",
                r"SELECT\s+.*FROM\s+information_schema",
                r"'\s*OR\s*'\s*=\s*'"
            ],
            "xss_attempts": [
                r"<script>", r"javascript:", r"onload=", r"onerror=",
                r"<iframe", r"document\.cookie"
            ],
            "path_traversal": [
                r"\.\./\.\./", r"\.\.\\.\.\\", r"%2e%2e%2f",
                r"etc/passwd", r"windows/system32"
            ],
            "brute_force": [
                r"POST\s+/login", r"failed.*login", r"authentication.*failed"
            ]
        }
        
        # Quick pattern matching
        detected_attacks = self._quick_pattern_scan(log_lines, attack_patterns)
        
        # LLM analysis for complex patterns
        llm_analysis = self._llm_attack_analysis(log_lines, detected_attacks)
        
        return {
            "detected_attacks": detected_attacks,
            "llm_analysis": llm_analysis,
            "risk_assessment": self._assess_risk(detected_attacks),
            "recommendations": self._generate_security_recommendations(detected_attacks)
        }
    
    def _quick_pattern_scan(self, log_lines: List[str], patterns: Dict) -> Dict:
        """Quick regex-based attack detection."""
        
        import re
        
        results = {}
        
        for attack_type, regexes in patterns.items():
            matches = []
            
            for line in log_lines:
                for regex in regexes:
                    if re.search(regex, line, re.IGNORECASE):
                        matches.append({
                            "line": line.strip(),
                            "pattern": regex,
                            "timestamp": self._extract_timestamp(line)
                        })
            
            if matches:
                results[attack_type] = {
                    "count": len(matches),
                    "examples": matches[:5],  # First 5 examples
                    "severity": self._calculate_severity(attack_type, len(matches))
                }
        
        return results
    
    def _llm_attack_analysis(self, log_lines: List[str], detected: Dict) -> Dict:
        """Use LLM for deeper attack analysis."""
        
        # Sample of log lines for analysis
        sample_logs = "\n".join(log_lines[:50])  # First 50 lines
        
        prompt = f"""
Analyze these web server logs for security threats and attack patterns.

Sample Logs:
{sample_logs}

Detected patterns so far:
{detected}

Provide detailed security analysis in JSON:
{% raw %}
{
  "attack_summary": "Summary of detected attacks",
  "threat_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "attack_vectors": ["vector1", "vector2"],
  "targeted_resources": ["resource1", "resource2"],
  "attacker_behavior": "Description of attacker patterns",
  "timeline_analysis": "How attacks evolved over time",
  "false_positives": ["potential false positive 1"],
  "escalation_recommendations": ["immediate action 1", "immediate action 2"]
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False,
            "format": "json"
        })
        
        import json
        return json.loads(response.json()["response"])
    
    def _extract_timestamp(self, log_line: str) -> str:
        """Extract timestamp from log line."""
        
        import re
        
        # Common log formats
        patterns = [
            r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})\]',  # Apache format
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',     # ISO format
            r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'       # Syslog format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, log_line)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _calculate_severity(self, attack_type: str, count: int) -> str:
        """Calculate severity based on attack type and frequency."""
        
        severity_matrix = {
            "sql_injection": {"thresholds": [1, 5, 20], "levels": ["MEDIUM", "HIGH", "CRITICAL"]},
            "xss_attempts": {"thresholds": [5, 20, 50], "levels": ["LOW", "MEDIUM", "HIGH"]},
            "path_traversal": {"thresholds": [1, 3, 10], "levels": ["MEDIUM", "HIGH", "CRITICAL"]},
            "brute_force": {"thresholds": [10, 50, 100], "levels": ["LOW", "MEDIUM", "HIGH"]}
        }
        
        if attack_type in severity_matrix:
            matrix = severity_matrix[attack_type]
            for i, threshold in enumerate(matrix["thresholds"]):
                if count >= threshold:
                    return matrix["levels"][i]
        
        return "LOW"
    
    def _assess_risk(self, detected_attacks: Dict) -> str:
        """Overall risk assessment."""
        
        severity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        
        max_severity = 0
        total_score = 0
        
        for attack_data in detected_attacks.values():
            severity = attack_data["severity"]
            count = attack_data["count"]
            
            score = severity_scores.get(severity, 1) * min(count, 10)  # Cap at 10
            total_score += score
            max_severity = max(max_severity, severity_scores.get(severity, 1))
        
        if max_severity >= 4 or total_score > 20:
            return "CRITICAL"
        elif max_severity >= 3 or total_score > 10:
            return "HIGH"
        elif total_score > 5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_security_recommendations(self, detected_attacks: Dict) -> List[str]:
        """Generate security recommendations based on detected attacks."""
        
        recommendations = []
        
        if "sql_injection" in detected_attacks:
            recommendations.extend([
                "Implement prepared statements and parameterized queries",
                "Use Web Application Firewall (WAF) with SQL injection rules",
                "Input validation and sanitization for all user inputs"
            ])
        
        if "xss_attempts" in detected_attacks:
            recommendations.extend([
                "Implement Content Security Policy (CSP) headers",
                "Output encoding for all user-generated content",
                "Use XSS protection middleware"
            ])
        
        if "path_traversal" in detected_attacks:
            recommendations.extend([
                "Validate and sanitize file paths",
                "Use allowlists for file access",
                "Implement proper directory traversal protection"
            ])
        
        if "brute_force" in detected_attacks:
            recommendations.extend([
                "Implement rate limiting and CAPTCHA",
                "Account lockout policies",
                "Multi-factor authentication (MFA)"
            ])
        
        # General recommendations
        recommendations.extend([
            "Regular security audits and penetration testing",
            "Keep web server and dependencies updated",
            "Implement comprehensive logging and monitoring",
            "Set up intrusion detection systems"
        ])
        
        return list(set(recommendations))  # Remove duplicates

# Usage
web_analyzer = WebServerLogAnalyzer()

# Example Nginx logs with attacks
nginx_logs = [
    '192.168.1.100 - - [25/Jan/2024:10:15:23 +0000] "GET /?id=1\' OR \'1\'=\'1 HTTP/1.1" 200 234',
    '192.168.1.101 - - [25/Jan/2024:10:15:24 +0000] "POST /login HTTP/1.1" 401 123 "failed login attempt"',
    '192.168.1.102 - - [25/Jan/2024:10:15:25 +0000] "GET /../../../etc/passwd HTTP/1.1" 404 145',
    '192.168.1.103 - - [25/Jan/2024:10:15:26 +0000] "GET /<script>alert(\'xss\')</script> HTTP/1.1" 200 567',
    '192.168.1.100 - - [25/Jan/2024:10:15:27 +0000] "POST /login HTTP/1.1" 401 123 "failed login attempt"',
    '192.168.1.100 - - [25/Jan/2024:10:15:28 +0000] "POST /login HTTP/1.1" 401 123 "failed login attempt"'
]

analysis = web_analyzer.analyze_attack_patterns(nginx_logs)

print("🔍 Attack Pattern Analysis")
print("=" * 50)

print(f"Overall Risk Level: {analysis['risk_assessment']}")
print()

print("Detected Attacks:")
for attack_type, data in analysis['detected_attacks'].items():
    print(f"  {attack_type}: {data['count']} occurrences (Severity: {data['severity']})")

print()
print("Security Recommendations:")
for i, rec in enumerate(analysis['recommendations'], 1):
    print(f"{i}. {rec}")

print()
print("LLM Analysis Summary:")
print(analysis['llm_analysis']['attack_summary'])
```

## 🤖 Use Case 4: Automated Troubleshooting Pipeline

### Intelligent Incident Response

```python
class AutomatedTroubleshooter:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.incident_history = []
    
    def handle_incident(self, incident_data: Dict) -> Dict:
        """
        Automated incident response using LLM analysis.
        
        Args:
            incident_data: Incident details (logs, metrics, alerts)
            
        Returns:
            Automated response plan
        """
        
        # Gather all available data
        context = self._gather_context(incident_data)
        
        # Analyze incident
        analysis = self._analyze_incident(incident_data, context)
        
        # Generate response plan
        response_plan = self._generate_response_plan(analysis)
        
        # Check if auto-remediation is safe
        if self._is_auto_remediation_safe(analysis):
            remediation_result = self._execute_auto_remediation(response_plan)
            response_plan["auto_remediation"] = remediation_result
        
        # Update incident history
        self.incident_history.append({
            "incident": incident_data,
            "analysis": analysis,
            "response": response_plan,
            "timestamp": datetime.now().isoformat()
        })
        
        return response_plan
    
    def _gather_context(self, incident: Dict) -> Dict:
        """Gather additional context from monitoring systems."""
        
        context = {
            "system_metrics": {},
            "recent_deployments": [],
            "similar_incidents": []
        }
        
        # This would integrate with actual monitoring systems
        # For demo, we'll simulate some context
        
        context["system_metrics"] = {
            "cpu_usage": 85,
            "memory_usage": 92,
            "disk_usage": 78,
            "network_errors": 5
        }
        
        context["recent_deployments"] = [
            {"service": "web-app", "version": "v2.1.0", "time": "2 hours ago"},
            {"service": "api-gateway", "version": "v1.8.3", "time": "1 hour ago"}
        ]
        
        # Find similar incidents
        context["similar_incidents"] = [
            inc for inc in self.incident_history
            if inc["analysis"]["error_type"] == incident.get("error_type")
        ][:3]
        
        return context
    
    def _analyze_incident(self, incident: Dict, context: Dict) -> Dict:
        """Comprehensive incident analysis."""
        
        prompt = f"""
Analyze this system incident and provide detailed diagnosis.

INCIDENT DETAILS:
{incident}

SYSTEM CONTEXT:
{context}

Provide analysis in JSON format:
{% raw %}
{
  "error_type": "Type of error/incident",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "root_cause": "Most likely root cause",
  "impact_assessment": "Impact on system/users",
  "contributing_factors": ["factor1", "factor2"],
  "similar_past_incidents": "Any similar incidents found",
  "confidence": 0.0-1.0
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False,
            "format": "json"
        })
        
        import json
        return json.loads(response.json()["response"])
    
    def _generate_response_plan(self, analysis: Dict) -> Dict:
        """Generate detailed response plan."""
        
        prompt = f"""
Based on this incident analysis, create a comprehensive response plan.

ANALYSIS:
{analysis}

Generate response plan in JSON:
{% raw %}
{
  "immediate_actions": [
    {
      "action": "Action description",
      "command": "CLI command or API call",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "estimated_time": "time estimate",
      "risk_level": "LOW|MEDIUM|HIGH"
    }
  ],
  "investigation_steps": ["step1", "step2"],
  "long_term_fixes": ["fix1", "fix2"],
  "monitoring_improvements": ["improvement1"],
  "communication_plan": {
    "stakeholders": ["team1", "team2"],
    "updates_frequency": "frequency",
    "escalation_criteria": ["criteria1"]
  },
  "rollback_plan": "How to rollback if needed"
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False,
            "format": "json"
        })
        
        import json
        return json.loads(response.json()["response"])
    
    def _is_auto_remediation_safe(self, analysis: Dict) -> bool:
        """Determine if auto-remediation is safe."""
        
        # Safety criteria
        safe_conditions = [
            analysis.get("confidence", 0) > 0.8,
            analysis.get("severity") in ["LOW", "MEDIUM"],
            analysis.get("error_type") in ["configuration", "resource", "dependency"]
        ]
        
        return all(safe_conditions)
    
    def _execute_auto_remediation(self, response_plan: Dict) -> Dict:
        """Execute safe auto-remediation actions."""
        
        results = {
            "executed_actions": [],
            "success_count": 0,
            "failure_count": 0,
            "errors": []
        }
        
        # Only execute LOW risk actions automatically
        for action in response_plan.get("immediate_actions", []):
            if action.get("risk_level") == "LOW":
                try:
                    # Simulate command execution
                    # In real implementation, this would execute actual commands
                    print(f"Executing: {action['command']}")
                    
                    # Simulate success/failure
                    success = True  # This would be actual execution result
                    
                    if success:
                        results["success_count"] += 1
                        results["executed_actions"].append(action)
                    else:
                        results["failure_count"] += 1
                        results["errors"].append(f"Failed: {action['action']}")
                        
                except Exception as e:
                    results["failure_count"] += 1
                    results["errors"].append(f"Error executing {action['action']}: {str(e)}")
        
        return results

# Usage
troubleshooter = AutomatedTroubleshooter()

# Example incident
incident = {
    "title": "Database Connection Pool Exhausted",
    "description": "Application unable to connect to database",
    "error_type": "database_connection",
    "affected_service": "web-app",
    "logs": "Connection pool exhausted, all connections in use",
    "metrics": {"active_connections": 50, "max_connections": 50},
    "timestamp": "2024-01-25T10:30:00Z"
}

response_plan = troubleshooter.handle_incident(incident)

print("🚨 Automated Incident Response")
print("=" * 50)

print(f"Incident: {incident['title']}")
print(f"Analysis: {response_plan['analysis']['root_cause']}")
print()

print("Immediate Actions:")
for action in response_plan["immediate_actions"][:3]:  # First 3 actions
    print(f"• {action['action']} (Priority: {action['priority']})")

if "auto_remediation" in response_plan:
    auto = response_plan["auto_remediation"]
    print(f"\nAuto-remediation: {auto['success_count']} successful, {auto['failure_count']} failed")

print(f"\nRollback Plan: {response_plan.get('rollback_plan', 'N/A')}")
```

## 📊 Metrics and KPIs

### Tracking Troubleshooting Effectiveness

```python
from datetime import datetime, timedelta
from typing import List, Dict
import statistics

class TroubleshootingMetrics:
    def __init__(self):
        self.incidents = []
    
    def record_incident(self, incident: Dict):
        """Record incident resolution data."""
        
        self.incidents.append({
            "id": incident["id"],
            "type": incident["type"],
            "severity": incident["severity"],
            "detection_time": incident["detection_time"],
            "resolution_time": incident["resolution_time"],
            "auto_resolved": incident.get("auto_resolved", False),
            "false_positive": incident.get("false_positive", False),
            "escalated": incident.get("escalated", False)
        })
    
    def calculate_mttr(self, days: int = 30) -> Dict:
        """Calculate Mean Time To Resolution."""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_incidents = [
            inc for inc in self.incidents
            if datetime.fromisoformat(inc["resolution_time"]) > cutoff_date
        ]
        
        if not recent_incidents:
            return {"mttr_minutes": 0, "sample_size": 0}
        
        resolution_times = []
        for inc in recent_incidents:
            detection = datetime.fromisoformat(inc["detection_time"])
            resolution = datetime.fromisoformat(inc["resolution_time"])
            mttr = (resolution - detection).total_seconds() / 60  # minutes
            resolution_times.append(mttr)
        
        return {
            "mttr_minutes": statistics.mean(resolution_times),
            "median_mttr": statistics.median(resolution_times),
            "min_mttr": min(resolution_times),
            "max_mttr": max(resolution_times),
            "sample_size": len(resolution_times)
        }
    
    def calculate_auto_resolution_rate(self, days: int = 30) -> float:
        """Calculate percentage of incidents auto-resolved."""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_incidents = [
            inc for inc in self.incidents
            if datetime.fromisoformat(inc["resolution_time"]) > cutoff_date
        ]
        
        if not recent_incidents:
            return 0.0
        
        auto_resolved = sum(1 for inc in recent_incidents if inc["auto_resolved"])
        return auto_resolved / len(recent_incidents)
    
    def get_incident_trends(self, days: int = 30) -> Dict:
        """Analyze incident trends."""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_incidents = [
            inc for inc in self.incidents
            if datetime.fromisoformat(inc["resolution_time"]) > cutoff_date
        ]
        
        # Group by type
        by_type = {}
        for inc in recent_incidents:
            inc_type = inc["type"]
            if inc_type not in by_type:
                by_type[inc_type] = []
            by_type[inc_type].append(inc)
        
        # Group by severity
        by_severity = {}
        for inc in recent_incidents:
            severity = inc["severity"]
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(inc)
        
        return {
            "total_incidents": len(recent_incidents),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "false_positive_rate": sum(1 for inc in recent_incidents if inc["false_positive"]) / len(recent_incidents) if recent_incidents else 0,
            "escalation_rate": sum(1 for inc in recent_incidents if inc["escalated"]) / len(recent_incidents) if recent_incidents else 0
        }

# Usage
metrics = TroubleshootingMetrics()

# Record some sample incidents
sample_incidents = [
    {
        "id": "INC-001",
        "type": "database_connection",
        "severity": "HIGH",
        "detection_time": "2024-01-20T10:00:00Z",
        "resolution_time": "2024-01-20T10:30:00Z",
        "auto_resolved": True,
        "false_positive": False,
        "escalated": False
    },
    {
        "id": "INC-002",
        "type": "memory_leak",
        "severity": "CRITICAL",
        "detection_time": "2024-01-21T15:00:00Z",
        "resolution_time": "2024-01-21T17:00:00Z",
        "auto_resolved": False,
        "false_positive": False,
        "escalated": True
    }
]

for inc in sample_incidents:
    metrics.record_incident(inc)

# Calculate metrics
mttr = metrics.calculate_mttr()
auto_rate = metrics.calculate_auto_resolution_rate()
trends = metrics.get_incident_trends()

print("📊 Troubleshooting Metrics")
print("=" * 40)

print(f"MTTR: {mttr['mttr_minutes']:.1f} minutes (n={mttr['sample_size']})")
print(f"Auto-resolution Rate: {auto_rate:.1%}")
print()

print("Incident Trends (last 30 days):")
print(f"Total Incidents: {trends['total_incidents']}")
print(f"By Type: {trends['by_type']}")
print(f"By Severity: {trends['by_severity']}")
print(f"False Positive Rate: {trends['false_positive_rate']:.1%}")
print(f"Escalation Rate: {trends['escalation_rate']:.1%}")
```

## 🔒 Security Considerations

### Safe Command Execution

```python
class SecureCommandExecutor:
    def __init__(self):
        self.allowed_commands = {
            "kubectl": ["get", "describe", "logs", "exec"],
            "docker": ["ps", "logs", "inspect"],
            "systemctl": ["status", "is-active"],
            "journalctl": ["--since", "--until", "-u"]
        }
        
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"> /dev/",
            r"mkfs",
            r"dd\s+if=",
            r"shutdown",
            r"reboot"
        ]
    
    def is_command_safe(self, command: str) -> bool:
        """Check if command is safe to execute."""
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False
        
        # Parse command
        parts = command.split()
        if not parts:
            return False
        
        base_command = parts[0]
        
        # Check if command is allowed
        if base_command not in self.allowed_commands:
            return False
        
        # Check if subcommand is allowed
        allowed_subcommands = self.allowed_commands[base_command]
        if len(parts) > 1 and parts[1] not in allowed_subcommands:
            return False
        
        return True
    
    def execute_safe_command(self, command: str) -> Dict:
        """Execute command if it's safe."""
        
        if not self.is_command_safe(command):
            return {
                "success": False,
                "error": "Command not allowed for security reasons",
                "command": command
            }
        
        try:
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

# Usage
executor = SecureCommandExecutor()

# Safe commands
safe_commands = [
    "kubectl get pods",
    "docker ps",
    "systemctl status nginx",
    "journalctl -u apache2 --since '1 hour ago'"
]

# Dangerous commands (blocked)
dangerous_commands = [
    "rm -rf /",
    "shutdown now",
    "dd if=/dev/zero of=/dev/sda"
]

print("🛡️ Secure Command Execution")
print("=" * 40)

for cmd in safe_commands + dangerous_commands:
    result = executor.execute_safe_command(cmd)
    status = "✅ ALLOWED" if result["success"] else "❌ BLOCKED"
    print(f"{status}: {cmd}")
    if not result["success"] and "error" in result:
        print(f"  Reason: {result['error']}")
```

## 📚 Additional Resources

- [Kubernetes Troubleshooting Guide](https://kubernetes.io/docs/tasks/debug/)
- [ELK Stack for Log Analysis](https://www.elastic.co/elastic-stack)
- [Prometheus Monitoring](https://prometheus.io/docs/introduction/overview/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

## 🔄 Next Steps

After implementing log analysis, consider:

1. **[Testing de Seguridad](testing_seguridad.md)** - Inyección de prompts y jailbreaking
2. **[Evaluación de Coherencia](evaluacion_coherencia.md)** - Consistencia de respuestas
3. **[Monitoreo de LLMs](model_evaluation.md)** - Métricas y observabilidad

---

*Have you implemented automated log analysis? Share your experiences and tools in the comments.*