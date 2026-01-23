# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: "Monitoreo de Seguridad"
date: 2026-01-09
tags: [cybersecurity, monitoring, falco, wazuh, siem]
draft: false
---

## Resumen

Esta guía explica cómo implementar monitoreo de seguridad en entornos DevOps, enfocándose en Falco para detección de anomalías en Kubernetes y Wazuh para SIEM básico. Incluye configuración, reglas y integración con alertas.

## Prerrequisitos

- Conocimientos básicos de Kubernetes y Linux.
- Acceso a cluster K8s o servidor Linux.
- Familiaridad con herramientas de monitoreo (Prometheus, Grafana).

## Falco

Herramienta de runtime security para Kubernetes, detecta anomalías y amenazas basadas en reglas.

#### Características

- **Detección:** Basada en eBPF, monitorea syscalls y eventos de K8s.
- **Reglas:** YAML configurables para definir comportamientos sospechosos.
- **Integración:** Con Prometheus, Elasticsearch, Slack.

#### Instalación en Kubernetes

```bash
# Usando Helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm install falco falcosecurity/falco

# Verificar
kubectl get pods -n falco
```

#### Reglas Básicas

```yaml
# /etc/falco/falco_rules.yaml
- rule: Unexpected network connection
  desc: Detect unexpected outbound connection
  condition: outbound and not (fd.sip in (trusted_ips))
  output: Unexpected outbound connection (command=%proc.cmdline connection=%fd.name)
  priority: WARNING

- rule: Shell spawned by unusual process
  desc: Detect shell spawned by unusual parent
  condition: spawned_process and proc.name = bash and proc.pparent.name != sshd
  output: Shell spawned by unusual process (parent=%proc.pparent.name cmdline=%proc.cmdline)
  priority: WARNING
```

#### Reglas Personalizadas

```yaml
- rule: Suspicious file access
  desc: Access to sensitive files
  condition: open_read and (fd.name pmatch (/etc/shadow, /etc/passwd))
  output: Suspicious file access (file=%fd.name user=%user.name command=%proc.cmdline)
  priority: CRITICAL
```

#### Integración con Alertmanager

```yaml
# Configurar webhook en Falco
webhook:
  enabled: true
  http_config:
    url: "http://alertmanager:9093/api/v2/alerts"
```

## Wazuh

Plataforma open-source para XDR (Extended Detection and Response), incluye SIEM, EDR y gestión de vulnerabilidades.

#### Componentes

- **Manager:** Servidor central.
- **Agents:** Instalados en endpoints.
- **API:** Para integración.

#### Instalación

```bash
# Script automático
curl -sO https://packages.wazuh.com/4.7/wazuh-install.sh
bash wazuh-install.sh -a

# Acceder a interfaz
# https://wazuh-server (usuario: admin, password: generado)
```

#### Configuración de Agentes

```bash
# En servidor a monitorear
WAZUH_MANAGER="wazuh-server-ip" apt install wazuh-agent
systemctl enable wazuh-agent
systemctl start wazuh-agent

# Registrar agente
/var/ossec/bin/agent-auth -m wazuh-server-ip
systemctl restart wazuh-agent
```

#### Reglas y Alertas

```xml
<!-- /var/ossec/etc/rules/local_rules.xml -->
<group name="syslog,sshd,">
  <rule id="100001" level="5">
    <if_sid>5716</if_sid>
    <match>Failed password</match>
    <description>SSH authentication failed.</description>
  </rule>
</group>
```

#### Dashboards

Wazuh incluye dashboards en Kibana/Opensearch para visualizar:
- Alertas de seguridad
- Estado de agentes
- Vulnerabilidades
- Integridad de archivos

## Integración con Stack de Monitoreo

### Prometheus + Grafana

```yaml
# Falco metrics
scrape_configs:
  - job_name: 'falco'
    static_configs:
      - targets: ['falco:9376']
```

### Alertas en Slack

```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'slack'
receivers:
- name: 'slack'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#security'
```

## Mejores Prácticas

- **Reglas Específicas:** Personalizar reglas para el entorno, evitar falsos positivos.
- **Segmentación:** Monitorear diferentes zonas (DMZ, internal, cloud).
- **Correlación:** Usar SIEM para correlacionar eventos.
- **Respuesta:** Definir playbooks para alertas críticas.
- **Mantenimiento:** Actualizar firmas y reglas regularmente.

## Ejemplos de Detección

### Falco: Detección de Crypto Mining

```yaml
- rule: Crypto mining detection
  desc: Detect crypto mining activity
  condition: (spawned_process and (proc.cmdline contains "xmrig" or proc.cmdline contains "minerd"))
  output: Crypto mining process detected (command=%proc.cmdline user=%user.name)
  priority: CRITICAL
```

### Wazuh: Detección de Rootkits

```xml
<rule id="100002" level="12">
  <if_sid>530</if_sid>
  <match>Possible rootkit</match>
  <description>Rootkit detected by rkhunter.</description>
  <group>rootkit,</group>
</rule>
```

## Troubleshooting

```bash
# Ver logs de Falco
kubectl logs -n falco deployment/falco

# Ver estado de agentes Wazuh
/var/ossec/bin/agent_control -l

# Ver alertas en tiempo real
tail -f /var/ossec/logs/alerts/alerts.log
```

## Referencias

- [Falco Documentation](https://falco.org/docs/)
- [Wazuh Documentation](https://documentation.wazuh.com/)
- [CNCF Falco](https://github.com/falcosecurity/falco)
- [SIEM Best Practices](https://www.csoonline.com/article/3656967/what-is-siem-a-guide-to-security-information-and-event-management.html)