---
title: "Systemd: Gestión de Servicios"
description: "Documentación sobre systemd: gestión de servicios"
tags: ['documentation']
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Sistema Operativo
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Systemd: Gestión de Servicios

Systemd es el sistema de inicio y gestor de servicios estándar en la mayoría de distribuciones Linux modernas.

## Crear un Servicio Propio

Para ejecutar un script o binario como servicio, crea un archivo en `/etc/systemd/system/mi-servicio.service`:

```ini
[Unit]
Description=Mi Servicio Personalizado
After=network.target

[Service]
Type=simple
User=mi_usuario
ExecStart=/usr/bin/python3 /home/mi_usuario/script.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Comandos Útiles

- `systemctl start mi-servicio`: Iniciar.
- `systemctl enable mi-servicio`: Habilitar al arranque.
- `systemctl status mi-servicio`: Ver estado y logs recientes.
- `journalctl -u mi-servicio -f`: Ver logs en tiempo real.
