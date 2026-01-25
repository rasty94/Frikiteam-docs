---
title: "Observabilidad: Centralización de Logs con Wazuh"
description: "Integración de logs de aplicaciones en Wazuh SIEM: configuración de agentes, análisis de seguridad y auditoría"
keywords: "wazuh, logs, siem, security, monitoring"
tags: [monitoring, logs, wazuh, siem, security]
updated: 2026-01-25
---

# Observabilidad: Centralización de Logs con Wazuh

Guía para integrar logs de aplicaciones en la plataforma SIEM Wazuh.

## Resumen

Integración de logs estructurados (JSON) para análisis de seguridad y auditoría.

## Configuración del Agente

Añadir el siguiente bloque a `ossec.conf`:

```xml
<localfile>
  <location>/var/log/app/output.json</location>
  <log_format>json</log_format>
  <label key="app_name">frikiteam-service</label>
</localfile>
```

## Referencias

- [Wazuh Documentation](https://documentation.wazuh.com/)
