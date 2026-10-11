---
title: "Log Analysis and Troubleshooting with LLMs"
description: "Using Large Language Models for automatic log analysis, error detection and troubleshooting suggestions"
tags: ['ai', 'llm', 'logs', 'troubleshooting', 'observability']
difficulty: intermediate
estimated_time: 71 min
category: Artificial Intelligence
status: published
prerequisites: ["ollama_basics", "chatbots_locales"]
updated: 2026-10-11
last_reviewed: 2026-10-11
---

# Log Analysis and Troubleshooting with LLMs

## Summary

LLMs can analyze system logs, detect error patterns and suggest solutions automatically. This guide covers practical techniques for using local models in infrastructure troubleshooting, with the goal of reducing mean time to resolution (MTTR).

## 🎯 Why Use LLMs for Log Analysis

### Common Troubleshooting Problems

- **Overwhelming volume:** Too many lines to read by hand
- **Excessive noise:** Most lines are routine information
- **Distributed context:** Errors span multiple services
- **Scarce expertise:** Not everyone knows every system
- **Time pressure:** Downtime costs money

### LLM Benefits

- ✅ **Automatic detection** of anomalies in logs
- ✅ **Smart correlation** of related events
- ✅ **Contextual suggestions** for solutions
- ✅ **Continuous learning** from past incidents
- ✅ **Multilingual analysis** of logs in different formats

## 🔍 Use Case 1: Application Log Analysis

### Smart Stack Trace Parser

```python
import json
import re
import requests
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class LogAnalysis:
    error_type: str
    root_cause: str
    affected_components: List[str]
    suggested_fix: str
    related_logs: List[str]
    severity: str  # critical, high, medium, low

class LogAnalyzer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def analyze_error(self, error_log: str, context_logs: List[str] = None) -> LogAnalysis:
        """
        Analyzes an error and its context to identify the root cause.
        
        Args:
            error_log: Stack trace or error message
            context_logs: Logs preceding the error (optional)
        
        Returns:
            LogAnalysis with a complete diagnosis
        """
        
        context = "\n".join(context_logs) if context_logs else "No hay contexto adicional"
        
        prompt = f"""
You are an expert in log analysis and systems troubleshooting. Analyze this error:

**ERROR:**
{error_log}

**CONTEXT (previous logs):**
{context}

Provide:
1. **Error type:** Specific classification
2. **Root cause:** Technical explanation of the problem
3. **Affected components:** Services/modules involved
4. **Suggested fix:** Concrete steps to resolve it
5. **Severity:** critical/high/medium/low

JSON format:
{% raw %}
{
  "error_type": "...",
  "root_cause": "...",
  "affected_components": ["...", "..."],
  "suggested_fix": "...",
  "severity": "..."
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},  # model parameters go in options
        })
        
        if response.status_code == 200:
            result = response.json()["response"]
            
            # Parsear JSON
            analysis_data = json.loads(result)
            
            return LogAnalysis(
                error_type=analysis_data["error_type"],
                root_cause=analysis_data["root_cause"],
                affected_components=analysis_data["affected_components"],
                suggested_fix=analysis_data["suggested_fix"],
                related_logs=context_logs or [],
                severity=analysis_data["severity"]
            )
        else:
            raise Exception(f"Error analyzing logs: {response.text}")

# Usage example
analyzer = LogAnalyzer()

error = """
Traceback (most recent call last):
  File "/app/api/users.py", line 245, in get_user
    user = db.query(User).filter(User.id == user_id).one()
  File "/venv/lib/sqlalchemy/orm/query.py", line 2827, in one
    raise NoResultFound("No row was found for one()")
sqlalchemy.orm.exc.NoResultFound: No row was found for one()
"""

context = [
    "2026-01-25 10:15:32 INFO Starting user query for user_id=12345",
    "2026-01-25 10:15:32 DEBUG Database pool: 8/10 connections active",
    "2026-01-25 10:15:32 WARNING Cache miss for user:12345"
]

analysis = analyzer.analyze_error(error, context)
print(f"🔴 Severity: {analysis.severity}")
print(f"🐛 Type: {analysis.error_type}")
print(f"💡 Root cause: {analysis.root_cause}")
print(f"🔧 Fix: {analysis.suggested_fix}")
```

### Example response

Illustrative: the model output changes on every run and must be validated before acting on it.

```
🔴 Severity: medium
🐛 Type: Database Query Error - NoResultFound
💡 Root cause: The SQL query expected exactly one result but found none. 
   The user with ID 12345 does not exist in the database or was recently deleted.
🔧 Fix: 
   1. Use .first() instead of .one() to return None when there are no results
   2. Implement proper exception handling
   3. Validate that the user exists before the query
   4. Check referential integrity in the DB
   Suggested code:
   user = db.query(User).filter(User.id == user_id).first()
   if not user:
       raise HTTPException(status_code=404, detail="User not found")
```

## 📊 Use Case 2: Kubernetes Log Analysis

### Pod Anomaly Monitor

```python
import subprocess
import json
import requests
from datetime import datetime
from typing import List, Dict

class KubernetesLogAnalyzer:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def get_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        since: str = "1h",
        tail: int = 500
    ) -> str:
        """Gets the logs of a Kubernetes pod."""
        
        cmd = [
            "kubectl", "logs",
            f"--namespace={namespace}",
            pod_name,
            f"--since={since}",
            f"--tail={tail}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    
    def detect_crash_loop(self, logs: str, pod_events: str) -> Dict:
        """Detects and analyzes CrashLoopBackOff."""
        
        prompt = f"""
Analyze these logs and events from a Kubernetes pod that is in CrashLoopBackOff:

**POD LOGS:**
{logs[-2000:]}  # Últimas 2000 chars

**POD EVENTS:**
{pod_events}

Identify:
1. **Crash cause:** Why is the pod restarting?
2. **Specific line/code:** Point out the exact error
3. **Missing dependencies:** Is a service/config missing?
4. **Immediate fix:** Quick action to resolve it
5. **Permanent fix:** Definitive solution

JSON format:
{% raw %}
{
  "crash_reason": "...",
  "error_line": "...",
  "missing_dependencies": ["..."],
  "immediate_fix": "...",
  "permanent_fix": "..."
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        })
        
        return json.loads(response.json()["response"])
    
    def analyze_resource_issues(self, namespace: str) -> List[Dict]:
        """Analyzes resource problems in a namespace."""
        
        # Get all pods in the namespace
        cmd = [
            "kubectl", "get", "pods",
            f"--namespace={namespace}",
            "-o", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        pods_data = json.loads(result.stdout)
        
        issues = []
        
        for pod in pods_data["items"]:
            pod_name = pod["metadata"]["name"]
            phase = pod["status"]["phase"]
            
            # CrashLoopBackOff is not a pod phase (the pod stays Running):
            # it is the waiting reason of a container
            reasons = [
                cs.get("state", {}).get("waiting", {}).get("reason")
                for cs in pod["status"].get("containerStatuses", [])
            ]
            crash_loop = "CrashLoopBackOff" in reasons
            if phase not in ("Pending", "Failed", "Unknown") and not crash_loop:
                continue
            
            # Get the pod events
            events_cmd = [
                "kubectl", "get", "events",
                f"--namespace={namespace}",
                f"--field-selector=involvedObject.name={pod_name}",
                "-o", "json"
            ]
            
            events_result = subprocess.run(events_cmd, capture_output=True, text=True)
            events = json.loads(events_result.stdout)
            
            # Analyze with the LLM
            logs = self.get_pod_logs(namespace, pod_name)
            
            analysis = self.detect_crash_loop(
                logs,
                json.dumps(events, indent=2)
            )
            
            issues.append({
                "pod": pod_name,
                "status": "CrashLoopBackOff" if crash_loop else phase,
                "analysis": analysis
            })
        
        return issues
    
    def generate_incident_report(self, issues: List[Dict]) -> str:
        """Generates an incident report to share with the team."""
        
        prompt = f"""
Generate a professional incident report based on these Kubernetes problems:

{json.dumps(issues, indent=2)}

The report must include:
1. **Executive summary:** What happened in 2-3 lines
2. **Impact:** Affected services and impacted users
3. **Root cause:** Technical explanation
4. **Timeline:** Incident timeline
5. **Actions taken:** Mitigation steps
6. **Future prevention:** How to avoid it

Markdown format, professional, concise.
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4},
        })
        
        return response.json()["response"]

# Usage
k8s_analyzer = KubernetesLogAnalyzer()

# Analyze a problematic namespace
issues = k8s_analyzer.analyze_resource_issues("production")

for issue in issues:
    print(f"\n🔴 Pod: {issue['pod']}")
    print(f"📊 Status: {issue['status']}")
    print(f"💡 Cause: {issue['analysis']['crash_reason']}")
    print(f"🔧 Immediate fix: {issue['analysis']['immediate_fix']}")

# Generate report
if issues:
    report = k8s_analyzer.generate_incident_report(issues)
    with open(f"incident_{datetime.now().strftime('%Y%m%d_%H%M')}.md", 'w') as f:
        f.write(report)
    print("\n📄 Report generated")
```

## 🌐 Use Case 3: Nginx/Apache Log Analysis

### Access Log Anomaly Detector

```python
import json
import re
import requests
from collections import defaultdict
from datetime import datetime
from typing import List, Dict

class WebServerLogAnalyzer:
    def __init__(self, model: str = "llama2:7b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def parse_nginx_log(self, log_line: str) -> Dict:
        """Parses an Nginx log line."""
        
        pattern = r'(\S+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"'
        match = re.match(pattern, log_line)
        
        if match:
            return {
                "ip": match.group(1),
                "timestamp": match.group(2),
                "request": match.group(3),
                "status": int(match.group(4)),
                "bytes": int(match.group(5)),
                "referer": match.group(6),
                "user_agent": match.group(7)
            }
        return None
    
    def detect_attack_patterns(self, logs: List[Dict]) -> Dict:
        """Detects attack patterns (SQL injection, XSS, brute force)."""
        
        # Group by IP
        by_ip = defaultdict(list)
        for log in logs:
            if log:
                by_ip[log["ip"]].append(log)
        
        # Look for suspicious IPs
        suspicious_ips = []
        
        for ip, requests in by_ip.items():
            # Brute force: more than 100 requests from one IP in the analyzed fragment
            if len(requests) > 100:
                suspicious_ips.append({
                    "ip": ip,
                    "reason": "brute_force",
                    "requests": len(requests),
                    "sample": requests[:5]
                })
            
            # SQL injection attempts
            sql_patterns = ["'", "SELECT", "UNION", "DROP", "INSERT"]
            sql_attempts = [
                r for r in requests
                if any(p in r["request"] for p in sql_patterns)
            ]
            
            if sql_attempts:
                suspicious_ips.append({
                    "ip": ip,
                    "reason": "sql_injection",
                    "attempts": len(sql_attempts),
                    "sample": sql_attempts[:3]
                })
        
        # Analyze with the LLM
        if suspicious_ips:
            analysis = self.analyze_suspicious_activity(suspicious_ips)
            return analysis
        
        return {"status": "normal", "threats": []}
    
    def analyze_suspicious_activity(self, suspicious_ips: List[Dict]) -> Dict:
        """Analyzes suspicious activity with the LLM."""
        
        prompt = f"""
Analyze this suspicious activity detected in web server logs:

{json.dumps(suspicious_ips, indent=2)}

For each suspicious IP, determine:
1. **Attack type:** What they are attempting
2. **Threat level:** critical/high/medium/low
3. **Recommended action:** Ban IP, rate limit, investigate, etc.
4. **Firewall rule:** Specific command to block it

JSON format:
{% raw %}
{
  "threats": [
    {
      "ip": "...",
      "attack_type": "...",
      "threat_level": "...",
      "recommended_action": "...",
      "firewall_rule": "..."
    }
  ]
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        })
        
        return json.loads(response.json()["response"])
    
    def analyze_error_surge(self, logs: List[Dict]) -> Dict:
        """Analyzes an abnormal increase in 5xx errors."""
        
        # Count errors per minute
        errors_by_minute = defaultdict(int)
        
        for log in logs:
            if log and log["status"] >= 500:
                timestamp = datetime.strptime(log["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
                minute = timestamp.strftime("%Y-%m-%d %H:%M")
                errors_by_minute[minute] += 1
        
        # Detect spikes
        avg_errors = sum(errors_by_minute.values()) / max(len(errors_by_minute), 1)
        
        spikes = {
            minute: count
            for minute, count in errors_by_minute.items()
            if count > avg_errors * 3  # 3x the average
        }
        
        if spikes:
            # Get sample logs from the spikes
            spike_logs = []
            for log in logs:
                if log and log["status"] >= 500:
                    timestamp = datetime.strptime(log["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
                    minute = timestamp.strftime("%Y-%m-%d %H:%M")
                    if minute in spikes:
                        spike_logs.append(log)
            
            return self.diagnose_error_spike(spike_logs[:20])
        
        return {"status": "normal"}
    
    def diagnose_error_spike(self, error_logs: List[Dict]) -> Dict:
        """Diagnoses the cause of an error spike."""
        
        prompt = f"""
An abnormal spike of 5xx errors was detected. Analyze these logs:

{json.dumps(error_logs, indent=2)}

Identify:
1. **Common pattern:** What do these errors have in common?
2. **Probable cause:** Backend down, database, timeout, etc.
3. **Affected endpoints:** Specific routes
4. **Diagnosis:** Steps to investigate
5. **Mitigation:** Immediate actions

JSON format:
{% raw %}
{
  "common_pattern": "...",
  "probable_cause": "...",
  "affected_endpoints": ["..."],
  "diagnosis": "...",
  "mitigation": "..."
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        })
        
        return json.loads(response.json()["response"])

# Usage
analyzer = WebServerLogAnalyzer()

# Read Nginx logs
with open("/var/log/nginx/access.log", 'r') as f:
    raw_logs = f.readlines()

parsed_logs = [analyzer.parse_nginx_log(line) for line in raw_logs]

# Detect attacks
attack_analysis = analyzer.detect_attack_patterns(parsed_logs)
if attack_analysis.get("threats"):
    print("🚨 Threats detected:")
    for threat in attack_analysis["threats"]:
        print(f"  IP: {threat['ip']} - {threat['attack_type']} ({threat['threat_level']})")
        print(f"  Action: {threat['recommended_action']}")
        print(f"  Command: {threat['firewall_rule']}")

# Detect error spikes
error_analysis = analyzer.analyze_error_surge(parsed_logs)
if error_analysis.get("status") != "normal":
    print(f"\n⚠️  Error spike detected:")
    print(f"  Cause: {error_analysis['probable_cause']}")
    print(f"  Mitigation: {error_analysis['mitigation']}")
```

## 🔄 Use Case 4: Complete Troubleshooting Pipeline

### Automated Incident Response System

```python
import json
import shlex
import subprocess
import requests
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Incident:
    id: str
    title: str
    severity: Severity
    description: str
    affected_services: List[str]
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    status: str = "open"

class AutomatedTroubleshooter:
    def __init__(self, model: str = "llama2:13b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.incidents = []
    
    def monitor_and_respond(self, log_source: str, check_interval: int = 60):
        """
        Monitors logs continuously and responds automatically.
        
        Args:
            log_source: Path to the log file or command to obtain the logs
            check_interval: Check interval in seconds
        """
        
        import time
        
        print(f"🔍 Starting monitoring of {log_source}...")
        
        while True:
            try:
                # 1. Get recent logs
                logs = self.get_recent_logs(log_source)
                
                # 2. Analyze with the LLM
                anomalies = self.detect_anomalies(logs)
                
                # 3. If there are anomalies, create an incident
                if anomalies:
                    for anomaly in anomalies:
                        incident = self.create_incident(anomaly)
                        
                        # 4. Intentar auto-remediation
                        if incident.severity in [Severity.MEDIUM, Severity.LOW]:
                            self.attempt_auto_fix(incident)
                        else:
                            # 5. Escalate to humans
                            self.escalate_incident(incident)
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped")
                break
            except Exception as e:
                print(f"⚠️  Monitoring error: {e}")
                time.sleep(check_interval)
    
    def detect_anomalies(self, logs: str) -> List[Dict]:
        """Detects anomalies in logs using the LLM."""
        
        prompt = f"""
Analyze these logs and detect ONLY real anomalies (errors, critical warnings, abnormal behavior):

{logs[-3000:]}  # Últimos 3000 chars

For each anomaly found, respond in JSON:
{% raw %}
{
  "anomalies": [
    {
      "type": "error|warning|performance|security",
      "severity": "critical|high|medium|low",
      "description": "...",
      "affected_component": "...",
      "evidence": "specific log line"
    }
  ]
}
{% endraw %}

If there are NO anomalies, respond: {% raw %}{"anomalies": []}{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        })
        
        result = json.loads(response.json()["response"])
        return result.get("anomalies", [])
    
    def create_incident(self, anomaly: Dict) -> Incident:
        """Creates a structured incident."""
        
        incident = Incident(
            id=f"INC-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            title=anomaly["description"][:100],
            severity=Severity(anomaly["severity"]),
            description=anomaly["evidence"],
            affected_services=[anomaly["affected_component"]]
        )
        
        self.incidents.append(incident)
        
        print(f"\n🚨 Incident created: {incident.id}")
        print(f"   Severity: {incident.severity.value}")
        print(f"   Description: {incident.title}")
        
        return incident
    
    def attempt_auto_fix(self, incident: Incident) -> bool:
        """Attempts to remediate the incident automatically."""
        
        prompt = f"""
Given this incident, suggest specific commands to auto-remediate it:

**Incident:** {incident.title}
**Description:** {incident.description}
**Affected services:** {', '.join(incident.affected_services)}

If auto-remediation is possible, respond:
{% raw %}
{
  "can_auto_fix": true,
  "commands": ["comando1", "comando2"],
  "explanation": "what the commands do"
}
{% endraw %}

If it requires human intervention:
{% raw %}
{
  "can_auto_fix": false,
  "reason": "why it cannot be auto-fixed"
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        })
        
        fix_plan = json.loads(response.json()["response"])
        
        if fix_plan.get("can_auto_fix"):
            print(f"🔧 Intentando auto-remediar {incident.id}...")
            print(f"   Plan: {fix_plan['explanation']}")
            
            # Run commands (with safety validation)
            for cmd in fix_plan["commands"]:
                if self.is_safe_command(cmd):
                    # No shell: a command from the LLM is never interpreted as a script
                    result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
                    print(f"   ✓ Executed: {cmd}")
                    print(f"     Result: {result.stdout[:200]}")
                else:
                    print(f"   ✗ Command rejected for safety: {cmd}")
            
            incident.status = "resolved"
            incident.resolution = fix_plan["explanation"]
            return True
        else:
            print(f"⚠️  No se puede auto-remediar: {fix_plan['reason']}")
            return False
    
    def is_safe_command(self, cmd: str) -> bool:
        """Validates that a command is safe to run."""
        
        # Allowlist of permitted commands
        safe_prefixes = [
            "kubectl scale",
            "kubectl rollout restart",
            "systemctl restart",
            "docker restart",
            "pm2 restart"
        ]
        
        dangerous_keywords = ["rm -rf", "dd if", "> /dev", "mkfs"]
        
        # Reject shell metacharacters: they are used to chain commands
        if any(c in cmd for c in ";&|`$<>\n"):
            return False
        
        # Check the allowlist
        is_safe = any(cmd.startswith(prefix) for prefix in safe_prefixes)
        
        # Check the denylist
        has_dangerous = any(keyword in cmd for keyword in dangerous_keywords)
        
        return is_safe and not has_dangerous
    
    def escalate_incident(self, incident: Incident):
        """Escalates the incident to the human team."""
        
        print(f"📢 Escalating {incident.id} to the on-call team...")
        
        # Generate a detailed report
        report = self.generate_detailed_report(incident)
        
        # Send a notification (Slack, PagerDuty, email, etc.)
        self.send_notification(
            channel="oncall",
            message=f"🚨 Incident {incident.severity.value.upper()}: {incident.title}",
            report=report
        )
    
    def generate_detailed_report(self, incident: Incident) -> str:
        """Generates a detailed incident report."""
        
        prompt = f"""
Generate a detailed, professional incident report:

**ID:** {incident.id}
**Title:** {incident.title}
**Severity:** {incident.severity.value}
**Services:** {', '.join(incident.affected_services)}
**Evidence:** {incident.description}

The report must include:
1. Executive summary
2. Estimated impact
3. Suggested troubleshooting steps
4. Possible root causes
5. Useful commands to investigate

Markdown format.
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3},
        })
        
        return response.json()["response"]
    
    def send_notification(self, channel: str, message: str, report: str):
        """Sends a notification to the appropriate channel."""
        
        # Simplified implementation - in production use the Slack SDK, etc.
        print(f"\n📧 Notification sent to {channel}:")
        print(f"   {message}")
        print(f"\n{report}")

# Usage
troubleshooter = AutomatedTroubleshooter()

# Continuous monitoring
troubleshooter.monitor_and_respond(
    log_source="/var/log/app/production.log",
    check_interval=60
)
```

## 📈 Metrics and KPIs

```python
from datetime import datetime

class TroubleshootingMetrics:
    def __init__(self):
        self.metrics = {
            "incidents_detected": 0,
            "auto_resolved": 0,
            "escalated": 0,
            "mttr_minutes": [],  # Mean Time To Resolution
            "false_positives": 0
        }
    
    def record_incident(
        self,
        detected_at: datetime,
        resolved_at: datetime,
        auto_resolved: bool,
        was_false_positive: bool = False
    ):
        self.metrics["incidents_detected"] += 1
        
        if was_false_positive:
            self.metrics["false_positives"] += 1
            return
        
        if auto_resolved:
            self.metrics["auto_resolved"] += 1
        else:
            self.metrics["escalated"] += 1
        
        # Calculate MTTR
        resolution_time = (resolved_at - detected_at).total_seconds() / 60
        self.metrics["mttr_minutes"].append(resolution_time)
    
    def report(self) -> str:
        avg_mttr = sum(self.metrics["mttr_minutes"]) / len(self.metrics["mttr_minutes"]) if self.metrics["mttr_minutes"] else 0
        
        auto_resolution_rate = (
            self.metrics["auto_resolved"] / max(self.metrics["incidents_detected"], 1) * 100
        )
        
        return f"""
📊 LLM Troubleshooting Metrics

Incidents detected: {self.metrics['incidents_detected']}
Auto-resolved: {self.metrics['auto_resolved']} ({auto_resolution_rate:.1f}%)
Escalated: {self.metrics['escalated']}
False positives: {self.metrics['false_positives']}

Average MTTR: {avg_mttr:.1f} minutes
Minimum MTTR: {min(self.metrics['mttr_minutes']) if self.metrics['mttr_minutes'] else 0:.1f} min
Maximum MTTR: {max(self.metrics['mttr_minutes']) if self.metrics['mttr_minutes'] else 0:.1f} min
"""

metrics = TroubleshootingMetrics()
```

## ⚠️ Security Considerations

### Command Validation

- ✅ **Strict allowlist** of permitted commands
- ✅ **Sandboxing** for safe execution
- ✅ **Complete logging** of every action
- ✅ **Human approval** for destructive commands
- ✅ **Rate limiting** to avoid infinite loops

### Protecting Sensitive Data

```python
import re

def sanitize_logs(logs: str) -> str:
    """Removes sensitive information from logs before sending them to the LLM."""
    
    # Remove API tokens
    logs = re.sub(r'token["\s:=]+[\w\-\.]+', 'token=REDACTED', logs, flags=re.IGNORECASE)
    
    # Remove passwords
    logs = re.sub(r'password["\s:=]+\S+', 'password=REDACTED', logs, flags=re.IGNORECASE)
    
    # Remove private IPs (optional, depends on the case)
    logs = re.sub(r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '10.x.x.x', logs)
    logs = re.sub(r'\b192\.168\.\d{1,3}\.\d{1,3}\b', '192.168.x.x', logs)
    
    # Remove emails
    logs = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', 'email@REDACTED', logs)
    
    return logs
```

## References

- [Ollama: API (parameters in `options`)](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Kubernetes: pod lifecycle (phases versus CrashLoopBackOff)](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Python: shlex](https://docs.python.org/3/library/shlex.html)
- [ELK Stack](https://www.elastic.co/what-is/elk-stack)
- [Prometheus + Grafana](https://prometheus.io/)
- [Kubernetes Logging](https://kubernetes.io/docs/concepts/cluster-administration/logging/)
- [Kubernetes Troubleshooting Guide](https://kubernetes.io/docs/tasks/debug/)
- [ELK Stack for Log Analysis](https://www.elastic.co/elastic-stack)
- [Prometheus Monitoring](https://prometheus.io/docs/introduction/overview/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

## 📚 Next Steps

After implementing log analysis, consider:

1. **[Prompt Engineering](prompt_engineering.md)** - Techniques for better diagnoses
2. **[LLM Monitoring](monitoreo_llms.md)** - Metrics for the analysis system
3. **[Fine-tuning](fine_tuning_basico.md)** - Customize for your specific systems

---

*Have you used LLMs for troubleshooting? Share your experiences and use cases in the comments.*