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
