# Systemd: Service Management

Systemd is the standard init system and service manager for most modern Linux distributions.

## Creating a Custom Service

To run a script or binary as a service, create a file at `/etc/systemd/system/my-service.service`:

```ini
[Unit]
Description=My Custom Service
After=network.target

[Service]
Type=simple
User=my_user
ExecStart=/usr/bin/python3 /home/my_user/script.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Useful Commands

- `systemctl start my-service`: Start.
- `systemctl enable my-service`: Enable at boot.
- `systemctl status my-service`: Check status and recent logs.
- `journalctl -u my-service -f`: Tail logs in real-time.
