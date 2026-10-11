---
title: "Security Monitoring"
tags: ['cybersecurity', 'monitoring', 'siem']

updated: 2026-10-11
last_reviewed: 2026-10-11
difficulty: intermediate
category: Cybersecurity
status: published
estimated_time: 10 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Intermediate Linux"
---

## Summary

This guide explains how to implement security monitoring in DevOps environments, focusing on Falco for anomaly detection in Kubernetes and Wazuh for basic SIEM. It covers configuration, rules and alert integration.

## Prerequisites

- Basic knowledge of Kubernetes and Linux.
- Access to a K8s cluster or a Linux server.
- Familiarity with monitoring tools (Prometheus, Grafana).

## Falco

Runtime security tool for Kubernetes that detects anomalies and threats based on rules.

#### Features

- **Detection:** Based on eBPF, monitors syscalls and K8s events.
- **Rules:** Configurable YAML to define suspicious behaviors.
- **Integration:** With Prometheus, Elasticsearch, Slack.

#### Installation on Kubernetes

```bash
# Using Helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm install falco falcosecurity/falco

# Verify
kubectl get pods -n falco
```

#### Basic Rules

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

#### Custom Rules

```yaml
- rule: Suspicious file access
  desc: Access to sensitive files
  condition: open_read and (fd.name pmatch (/etc/shadow, /etc/passwd))
  output: Suspicious file access (file=%fd.name user=%user.name command=%proc.cmdline)
  priority: CRITICAL
```

#### Integration with Alertmanager

```yaml
# Configure webhook in Falco
webhook:
  enabled: true
  http_config:
    url: "http://alertmanager:9093/api/v2/alerts"
```

## Wazuh

Open-source platform for XDR (Extended Detection and Response), including SIEM, EDR and vulnerability management.

#### Components

- **Manager:** Central server.
- **Agents:** Installed on endpoints.
- **API:** For integration.

#### Installation

```bash
# Automatic script
curl -sO https://packages.wazuh.com/4.7/wazuh-install.sh
bash wazuh-install.sh -a

# Access the web interface
# https://wazuh-server (user: admin, password: generated)
```

#### Agent Configuration

```bash
# On the server to monitor
WAZUH_MANAGER="wazuh-server-ip" apt install wazuh-agent
systemctl enable wazuh-agent
systemctl start wazuh-agent

# Register the agent
/var/ossec/bin/agent-auth -m wazuh-server-ip
systemctl restart wazuh-agent
```

#### Rules and Alerts

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

Wazuh includes dashboards in Kibana/OpenSearch to visualize:
- Security alerts
- Agent status
- Vulnerabilities
- File integrity

## Integration with the Monitoring Stack

### Prometheus + Grafana

```yaml
# Falco metrics
scrape_configs:
  - job_name: 'falco'
    static_configs:
      - targets: ['falco:9376']
```

### Alerts in Slack

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

## Best Practices

- **Specific Rules:** Customize rules for the environment and avoid false positives.
- **Segmentation:** Monitor different zones (DMZ, internal, cloud).
- **Correlation:** Use the SIEM to correlate events.
- **Response:** Define playbooks for critical alerts.
- **Maintenance:** Update signatures and rules regularly.

## Detection Examples

### Falco: Crypto Mining Detection

```yaml
- rule: Crypto mining detection
  desc: Detect crypto mining activity
  condition: (spawned_process and (proc.cmdline contains "xmrig" or proc.cmdline contains "minerd"))
  output: Crypto mining process detected (command=%proc.cmdline user=%user.name)
  priority: CRITICAL
```

### Wazuh: Rootkit Detection

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
# View Falco logs
kubectl logs -n falco deployment/falco

# Check Wazuh agent status
/var/ossec/bin/agent_control -l

# View alerts in real time
tail -f /var/ossec/logs/alerts/alerts.log
```

## References

- [Falco Documentation](https://falco.org/docs/)
- [Wazuh Documentation](https://documentation.wazuh.com/)
- [CNCF Falco](https://github.com/falcosecurity/falco)
