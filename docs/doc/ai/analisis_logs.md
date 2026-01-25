---
title: "Análisis de Logs y Troubleshooting con LLMs"
description: "Uso de Large Language Models para análisis automático de logs, detección de errores y sugerencias de solución de problemas"
date: 2026-01-25
tags: [ai, llm, logs, troubleshooting, observability, debugging]
difficulty: intermediate
estimated_time: "35 min"
category: ai
status: published
prerequisites: ["ollama_basics", "chatbots_locales"]
---

# Análisis de Logs y Troubleshooting con LLMs

> **Tiempo de lectura:** 35 minutos | **Dificultad:** Intermedia | **Categoría:** Inteligencia Artificial

## Resumen

Los LLMs pueden analizar logs de sistemas, detectar patrones de errores y sugerir soluciones automáticamente. Esta guía cubre técnicas prácticas para usar modelos locales en troubleshooting de infraestructura, reduciendo significativamente el tiempo medio de resolución (MTTR).

## 🎯 Por Qué Usar LLMs para Análisis de Logs

### Problemas Comunes en Troubleshooting

- **Volumen abrumador:** Millones de líneas de logs por día
- **Ruido excesivo:** 99% de logs son información normal
- **Contexto distribuido:** Errores span múltiples servicios
- **Expertise escasa:** No todos conocen cada sistema
- **Tiempo crítico:** Downtime cuesta dinero

### Beneficios de LLMs

- ✅ **Detección automática** de anomalías en logs
- ✅ **Correlación inteligente** de eventos relacionados
- ✅ **Sugerencias contextuales** de soluciones
- ✅ **Aprendizaje continuo** de incidentes pasados
- ✅ **Análisis multilingüe** de logs en diferentes formatos

## 🔍 Caso de Uso 1: Análisis de Logs de Aplicación

### Parser Inteligente de Stack Traces

```python
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
        Analiza un error y su contexto para identificar causa raíz.
        
        Args:
            error_log: Stack trace o mensaje de error
            context_logs: Logs previos al error (opcional)
        
        Returns:
            LogAnalysis con diagnóstico completo
        """
        
        context = "\n".join(context_logs) if context_logs else "No hay contexto adicional"
        
        prompt = f"""
Eres un experto en análisis de logs y troubleshooting de sistemas. Analiza este error:

**ERROR:**
{error_log}

**CONTEXTO (logs previos):**
{context}

Proporciona:
1. **Tipo de error:** Clasificación específica
2. **Causa raíz:** Explicación técnica del problema
3. **Componentes afectados:** Servicios/módulos involucrados
4. **Solución sugerida:** Pasos concretos para resolver
5. **Severidad:** critical/high/medium/low

Formato JSON:
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
            "temperature": 0.2,  # Baja temperatura para precisión
            "format": "json"
        })
        
        if response.status_code == 200:
            result = response.json()["response"]
            
            # Parsear JSON
            import json
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
            raise Exception(f"Error analizando logs: {response.text}")

# Ejemplo de uso
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
print(f"🔴 Severidad: {analysis.severity}")
print(f"🐛 Tipo: {analysis.error_type}")
print(f"💡 Causa raíz: {analysis.root_cause}")
print(f"🔧 Solución: {analysis.suggested_fix}")
```

### Resultado Esperado

```
🔴 Severidad: medium
🐛 Tipo: Database Query Error - NoResultFound
💡 Causa raíz: La consulta SQL esperaba exactamente un resultado pero no encontró ninguno. 
   El usuario con ID 12345 no existe en la base de datos o fue eliminado recientemente.
🔧 Solución: 
   1. Usar .first() en lugar de .one() para retornar None si no hay resultados
   2. Implementar manejo de excepciones apropiado
   3. Validar existencia del usuario antes de la query
   4. Verificar integridad referencial en la DB
   Código sugerido:
   user = db.query(User).filter(User.id == user_id).first()
   if not user:
       raise HTTPException(status_code=404, detail="User not found")
```

## 📊 Caso de Uso 2: Análisis de Logs de Kubernetes

### Monitor de Pods con Anomalías

```python
import subprocess
import json
from datetime import datetime, timedelta

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
        """Obtiene logs de un pod de Kubernetes."""
        
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
        """Detecta y analiza CrashLoopBackOff."""
        
        prompt = f"""
Analiza estos logs y eventos de un pod de Kubernetes que está en CrashLoopBackOff:

**LOGS DEL POD:**
{logs[-2000:]}  # Últimas 2000 chars

**EVENTOS DEL POD:**
{pod_events}

Identifica:
1. **Causa del crash:** ¿Por qué el pod se está reiniciando?
2. **Línea/código específico:** Señala el error exacto
3. **Dependencias faltantes:** ¿Falta algún servicio/config?
4. **Fix inmediato:** Acción rápida para resolver
5. **Fix permanente:** Solución definitiva

Formato JSON:
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
            "temperature": 0.2,
            "format": "json"
        })
        
        return json.loads(response.json()["response"])
    
    def analyze_resource_issues(self, namespace: str) -> List[Dict]:
        """Analiza problemas de recursos en un namespace."""
        
        # Obtener pods con problemas
        cmd = [
            "kubectl", "get", "pods",
            f"--namespace={namespace}",
            "--field-selector=status.phase!=Running",
            "-o", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        pods_data = json.loads(result.stdout)
        
        issues = []
        
        for pod in pods_data["items"]:
            pod_name = pod["metadata"]["name"]
            status = pod["status"]["phase"]
            
            # Obtener eventos del pod
            events_cmd = [
                "kubectl", "get", "events",
                f"--namespace={namespace}",
                f"--field-selector=involvedObject.name={pod_name}",
                "-o", "json"
            ]
            
            events_result = subprocess.run(events_cmd, capture_output=True, text=True)
            events = json.loads(events_result.stdout)
            
            # Analizar con LLM
            if status in ["Pending", "CrashLoopBackOff", "Error"]:
                logs = self.get_pod_logs(namespace, pod_name)
                
                analysis = self.detect_crash_loop(
                    logs,
                    json.dumps(events, indent=2)
                )
                
                issues.append({
                    "pod": pod_name,
                    "status": status,
                    "analysis": analysis
                })
        
        return issues
    
    def generate_incident_report(self, issues: List[Dict]) -> str:
        """Genera reporte de incidente para compartir con el equipo."""
        
        prompt = f"""
Genera un reporte de incidente profesional basado en estos problemas de Kubernetes:

{json.dumps(issues, indent=2)}

El reporte debe incluir:
1. **Resumen ejecutivo:** Qué pasó en 2-3 líneas
2. **Impacto:** Servicios afectados y usuarios impactados
3. **Causa raíz:** Explicación técnica
4. **Cronología:** Timeline del incidente
5. **Acciones tomadas:** Pasos de mitigación
6. **Prevención futura:** Cómo evitarlo

Formato Markdown, profesional, conciso.
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.4
        })
        
        return response.json()["response"]

# Uso
k8s_analyzer = KubernetesLogAnalyzer()

# Analizar namespace problemático
issues = k8s_analyzer.analyze_resource_issues("production")

for issue in issues:
    print(f"\n🔴 Pod: {issue['pod']}")
    print(f"📊 Status: {issue['status']}")
    print(f"💡 Causa: {issue['analysis']['crash_reason']}")
    print(f"🔧 Fix inmediato: {issue['analysis']['immediate_fix']}")

# Generar reporte
if issues:
    report = k8s_analyzer.generate_incident_report(issues)
    with open(f"incident_{datetime.now().strftime('%Y%m%d_%H%M')}.md", 'w') as f:
        f.write(report)
    print("\n📄 Reporte generado")
```

## 🌐 Caso de Uso 3: Análisis de Logs de Nginx/Apache

### Detector de Anomalías en Access Logs

```python
import re
from collections import defaultdict
from datetime import datetime
from typing import List, Dict

class WebServerLogAnalyzer:
    def __init__(self, model: str = "llama2:7b-chat-q4_0"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def parse_nginx_log(self, log_line: str) -> Dict:
        """Parsea una línea de log de Nginx."""
        
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
        """Detecta patrones de ataque (SQL injection, XSS, brute force)."""
        
        # Agrupar por IP
        by_ip = defaultdict(list)
        for log in logs:
            if log:
                by_ip[log["ip"]].append(log)
        
        # Buscar IPs sospechosas
        suspicious_ips = []
        
        for ip, requests in by_ip.items():
            # Brute force: >100 requests/min desde misma IP
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
        
        # Analizar con LLM
        if suspicious_ips:
            analysis = self.analyze_suspicious_activity(suspicious_ips)
            return analysis
        
        return {"status": "normal", "threats": []}
    
    def analyze_suspicious_activity(self, suspicious_ips: List[Dict]) -> Dict:
        """Analiza actividad sospechosa con LLM."""
        
        prompt = f"""
Analiza esta actividad sospechosa detectada en logs de servidor web:

{json.dumps(suspicious_ips, indent=2)}

Para cada IP sospechosa, determina:
1. **Tipo de ataque:** Qué están intentando
2. **Nivel de amenaza:** critical/high/medium/low
3. **Acción recomendada:** Ban IP, rate limit, investigar, etc.
4. **Regla de firewall:** Comando específico para bloquear

Formato JSON:
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
            "temperature": 0.2,
            "format": "json"
        })
        
        return json.loads(response.json()["response"])
    
    def analyze_error_surge(self, logs: List[Dict]) -> Dict:
        """Analiza incremento anormal de errores 5xx."""
        
        # Contar errores por minuto
        errors_by_minute = defaultdict(int)
        
        for log in logs:
            if log and log["status"] >= 500:
                timestamp = datetime.strptime(log["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
                minute = timestamp.strftime("%Y-%m-%d %H:%M")
                errors_by_minute[minute] += 1
        
        # Detectar picos
        avg_errors = sum(errors_by_minute.values()) / max(len(errors_by_minute), 1)
        
        spikes = {
            minute: count
            for minute, count in errors_by_minute.items()
            if count > avg_errors * 3  # 3x el promedio
        }
        
        if spikes:
            # Obtener logs de ejemplo de los picos
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
        """Diagnostica causa de pico de errores."""
        
        prompt = f"""
Se detectó un pico anormal de errores 5xx. Analiza estos logs:

{json.dumps(error_logs, indent=2)}

Identifica:
1. **Patrón común:** ¿Qué tienen en común estos errores?
2. **Causa probable:** Backend down, database, timeout, etc.
3. **Endpoints afectados:** Rutas específicas
4. **Diagnóstico:** Pasos para investigar
5. **Mitigación:** Acciones inmediatas

Formato JSON.
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2,
            "format": "json"
        })
        
        return json.loads(response.json()["response"])

# Uso
analyzer = WebServerLogAnalyzer()

# Leer logs de Nginx
with open("/var/log/nginx/access.log", 'r') as f:
    raw_logs = f.readlines()

parsed_logs = [analyzer.parse_nginx_log(line) for line in raw_logs]

# Detectar ataques
attack_analysis = analyzer.detect_attack_patterns(parsed_logs)
if attack_analysis.get("threats"):
    print("🚨 Amenazas detectadas:")
    for threat in attack_analysis["threats"]:
        print(f"  IP: {threat['ip']} - {threat['attack_type']} ({threat['threat_level']})")
        print(f"  Acción: {threat['recommended_action']}")
        print(f"  Comando: {threat['firewall_rule']}")

# Detectar picos de errores
error_analysis = analyzer.analyze_error_surge(parsed_logs)
if error_analysis.get("status") != "normal":
    print(f"\n⚠️  Pico de errores detectado:")
    print(f"  Causa: {error_analysis['probable_cause']}")
    print(f"  Mitigación: {error_analysis['mitigation']}")
```

## 🔄 Caso de Uso 4: Pipeline Completo de Troubleshooting

### Sistema de Respuesta Automática a Incidentes

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import smtplib
from email.mime.text import MIMEText

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
        Monitorea logs continuamente y responde automáticamente.
        
        Args:
            log_source: Path al archivo de logs o comando para obtenerlos
            check_interval: Intervalo de chequeo en segundos
        """
        
        import time
        
        print(f"🔍 Iniciando monitoreo de {log_source}...")
        
        while True:
            try:
                # 1. Obtener logs recientes
                logs = self.get_recent_logs(log_source)
                
                # 2. Analizar con LLM
                anomalies = self.detect_anomalies(logs)
                
                # 3. Si hay anomalías, crear incidente
                if anomalies:
                    for anomaly in anomalies:
                        incident = self.create_incident(anomaly)
                        
                        # 4. Intentar auto-remediation
                        if incident.severity in [Severity.MEDIUM, Severity.LOW]:
                            self.attempt_auto_fix(incident)
                        else:
                            # 5. Escalar a humanos
                            self.escalate_incident(incident)
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoreo detenido")
                break
            except Exception as e:
                print(f"⚠️  Error en monitoreo: {e}")
                time.sleep(check_interval)
    
    def detect_anomalies(self, logs: str) -> List[Dict]:
        """Detecta anomalías en logs usando LLM."""
        
        prompt = f"""
Analiza estos logs y detecta SOLO anomalías reales (errores, warnings críticos, comportamiento anormal):

{logs[-3000:]}  # Últimos 3000 chars

Para cada anomalía encontrada, responde en JSON:
{% raw %}
{
  "anomalies": [
    {
      "type": "error|warning|performance|security",
      "severity": "critical|high|medium|low",
      "description": "...",
      "affected_component": "...",
      "evidence": "línea específica del log"
    }
  ]
}
{% endraw %}

Si NO hay anomalías, responde: {% raw %}{"anomalies": []}{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1,
            "format": "json"
        })
        
        result = json.loads(response.json()["response"])
        return result.get("anomalies", [])
    
    def create_incident(self, anomaly: Dict) -> Incident:
        """Crea un incidente estructurado."""
        
        incident = Incident(
            id=f"INC-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            title=anomaly["description"][:100],
            severity=Severity(anomaly["severity"]),
            description=anomaly["evidence"],
            affected_services=[anomaly["affected_component"]]
        )
        
        self.incidents.append(incident)
        
        print(f"\n🚨 Incidente creado: {incident.id}")
        print(f"   Severidad: {incident.severity.value}")
        print(f"   Descripción: {incident.title}")
        
        return incident
    
    def attempt_auto_fix(self, incident: Incident) -> bool:
        """Intenta remediar automáticamente el incidente."""
        
        prompt = f"""
Dado este incidente, sugiere comandos específicos para auto-remediar:

**Incidente:** {incident.title}
**Descripción:** {incident.description}
**Servicios afectados:** {', '.join(incident.affected_services)}

Si es posible auto-remediar, responde:
{% raw %}
{
  "can_auto_fix": true,
  "commands": ["comando1", "comando2"],
  "explanation": "qué hacen los comandos"
}
{% endraw %}

Si requiere intervención humana:
{% raw %}
{
  "can_auto_fix": false,
  "reason": "por qué no se puede auto-fix"
}
{% endraw %}
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2,
            "format": "json"
        })
        
        fix_plan = json.loads(response.json()["response"])
        
        if fix_plan.get("can_auto_fix"):
            print(f"🔧 Intentando auto-remediar {incident.id}...")
            print(f"   Plan: {fix_plan['explanation']}")
            
            # Ejecutar comandos (con validación de seguridad)
            for cmd in fix_plan["commands"]:
                if self.is_safe_command(cmd):
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    print(f"   ✓ Ejecutado: {cmd}")
                    print(f"     Resultado: {result.stdout[:200]}")
                else:
                    print(f"   ✗ Comando rechazado por seguridad: {cmd}")
            
            incident.status = "resolved"
            incident.resolution = fix_plan["explanation"]
            return True
        else:
            print(f"⚠️  No se puede auto-remediar: {fix_plan['reason']}")
            return False
    
    def is_safe_command(self, cmd: str) -> bool:
        """Valida que un comando es seguro de ejecutar."""
        
        # Lista blanca de comandos permitidos
        safe_prefixes = [
            "kubectl scale",
            "kubectl rollout restart",
            "systemctl restart",
            "docker restart",
            "pm2 restart"
        ]
        
        dangerous_keywords = ["rm -rf", "dd if", "> /dev", "mkfs"]
        
        # Verificar lista blanca
        is_safe = any(cmd.startswith(prefix) for prefix in safe_prefixes)
        
        # Verificar lista negra
        has_dangerous = any(keyword in cmd for keyword in dangerous_keywords)
        
        return is_safe and not has_dangerous
    
    def escalate_incident(self, incident: Incident):
        """Escala incidente a equipo humano."""
        
        print(f"📢 Escalando {incident.id} a equipo de oncall...")
        
        # Generar reporte detallado
        report = self.generate_detailed_report(incident)
        
        # Enviar notificación (Slack, PagerDuty, email, etc.)
        self.send_notification(
            channel="oncall",
            message=f"🚨 Incidente {incident.severity.value.upper()}: {incident.title}",
            report=report
        )
    
    def generate_detailed_report(self, incident: Incident) -> str:
        """Genera reporte detallado del incidente."""
        
        prompt = f"""
Genera un reporte de incidente detallado y profesional:

**ID:** {incident.id}
**Título:** {incident.title}
**Severidad:** {incident.severity.value}
**Servicios:** {', '.join(incident.affected_services)}
**Evidencia:** {incident.description}

El reporte debe incluir:
1. Resumen ejecutivo
2. Impacto estimado
3. Pasos de troubleshooting sugeridos
4. Posibles causas raíz
5. Comandos útiles para investigar

Formato Markdown.
"""
        
        response = requests.post(self.ollama_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3
        })
        
        return response.json()["response"]
    
    def send_notification(self, channel: str, message: str, report: str):
        """Envía notificación a canal apropiado."""
        
        # Implementación simplificada - en producción usar Slack SDK, etc.
        print(f"\n📧 Notificación enviada a {channel}:")
        print(f"   {message}")
        print(f"\n{report}")

# Uso
troubleshooter = AutomatedTroubleshooter()

# Monitoreo continuo
troubleshooter.monitor_and_respond(
    log_source="/var/log/app/production.log",
    check_interval=60
)
```

## 📈 Métricas y KPIs

```python
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
        
        # Calcular MTTR
        resolution_time = (resolved_at - detected_at).total_seconds() / 60
        self.metrics["mttr_minutes"].append(resolution_time)
    
    def report(self) -> str:
        avg_mttr = sum(self.metrics["mttr_minutes"]) / len(self.metrics["mttr_minutes"]) if self.metrics["mttr_minutes"] else 0
        
        auto_resolution_rate = (
            self.metrics["auto_resolved"] / max(self.metrics["incidents_detected"], 1) * 100
        )
        
        return f"""
📊 Métricas de Troubleshooting con LLM

Incidentes detectados: {self.metrics['incidents_detected']}
Auto-resueltos: {self.metrics['auto_resolved']} ({auto_resolution_rate:.1f}%)
Escalados: {self.metrics['escalated']}
Falsos positivos: {self.metrics['false_positives']}

MTTR promedio: {avg_mttr:.1f} minutos
MTTR mínimo: {min(self.metrics['mttr_minutes']) if self.metrics['mttr_minutes'] else 0:.1f} min
MTTR máximo: {max(self.metrics['mttr_minutes']) if self.metrics['mttr_minutes'] else 0:.1f} min
"""

metrics = TroubleshootingMetrics()
```

## ⚠️ Consideraciones de Seguridad

### Validación de Comandos

- ✅ **Whitelist estricta** de comandos permitidos
- ✅ **Sandboxing** para ejecución segura
- ✅ **Logging completo** de todas las acciones
- ✅ **Aprobación humana** para comandos destructivos
- ✅ **Rate limiting** para evitar loops infinitos

### Protección de Datos Sensibles

```python
import re

def sanitize_logs(logs: str) -> str:
    """Remueve información sensible de logs antes de enviar a LLM."""
    
    # Remover tokens de API
    logs = re.sub(r'token["\s:=]+[\w\-\.]+', 'token=REDACTED', logs, flags=re.IGNORECASE)
    
    # Remover passwords
    logs = re.sub(r'password["\s:=]+\S+', 'password=REDACTED', logs, flags=re.IGNORECASE)
    
    # Remover IPs privadas (opcional, depende del caso)
    logs = re.sub(r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '10.x.x.x', logs)
    logs = re.sub(r'\b192\.168\.\d{1,3}\.\d{1,3}\b', '192.168.x.x', logs)
    
    # Remover emails
    logs = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email@REDACTED', logs)
    
    return logs
```

## 🔗 Recursos Adicionales

- [Ollama API Documentation](https://github.com/jmorganca/ollama/blob/main/docs/api.md)
- [ELK Stack](https://www.elastic.co/what-is/elk-stack)
- [Prometheus + Grafana](https://prometheus.io/)
- [Kubernetes Logging](https://kubernetes.io/docs/concepts/cluster-administration/logging/)

## 📚 Próximos Pasos

Después de implementar análisis de logs, considera:

1. **[Prompt Engineering](prompt_engineering.md)** - Técnicas para mejores diagnósticos
2. **[Monitoreo de LLMs](model_evaluation.md)** - Métricas del sistema de análisis
3. **[Fine-tuning](fine_tuning_basico.md)** - Personalizar para tus sistemas específicos

---

*¿Has usado LLMs para troubleshooting? Comparte tus experiencias y casos de uso en los comentarios.*