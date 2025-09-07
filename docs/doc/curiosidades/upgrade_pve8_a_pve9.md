# Actualizar Proxmox VE 8 a Proxmox VE 9 (Debian 13 Trixie)

> Guía práctica para actualizar un nodo o clúster de Proxmox VE 8 (Debian 12) a Proxmox VE 9 (Debian 13). Recomendado probar primero en laboratorio o tener backups y ventana de mantenimiento.

## 1) Checklist previo (imprescindible)

- **Backup completo** de VMs/CTs y de la configuración (`/etc/pve`, `/etc/network/interfaces`, almacenamiento, etc.)
- **Salud del clúster OK**: `pvecm status`, `systemctl status pve*`, `journalctl -p err -b`
- **Espacio libre** suficiente (mín. 5-10 GB en `/` y en `/var`)
- **Repositorios limpios**: sin repos externos rotos, enterprise comentado si no hay suscripción
- **Kernel y paquetes actualizados** en PVE 8: `apt update && apt full-upgrade -y` y reboot
- **Versiones de CPU/BIOS/firmware** al día si aplican (especialmente para ZFS)
- **Ventana de mantenimiento**: planificada; interrupción de servicio probable

## 2) Preparación en PVE 8 (Bookworm)

Asegúrate de estar totalmente al día en PVE 8:

```bash
apt update && apt full-upgrade -y
reboot
```

Deshabilita repos enterprise si no tienes suscripción:

```bash
sed -i.bak 's/^deb /# deb /' /etc/apt/sources.list.d/pve-enterprise.list || true
apt update
```

## 3) Cambiar a repos Proxmox 9 (Trixie)

Crea keyring y repos `trixie`:

```bash
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg > /etc/apt/keyrings/proxmox-release.gpg

cat >/etc/apt/sources.list.d/pve-no-subscription.list <<'EOF'
deb [signed-by=/etc/apt/keyrings/proxmox-release.gpg] http://download.proxmox.com/debian/pve trixie pve-no-subscription
EOF
```

Ajusta otros repos a `trixie` (Debian base):

```bash
sed -ri 's/bookworm/trixie/g' /etc/apt/sources.list
```

Revisa archivos en `/etc/apt/sources.list.d/` y elimina/ajusta entradas antiguas.

## 4) Realizar la actualización mayor

Actualiza índices y realiza dist-upgrade:

```bash
apt update
apt dist-upgrade -y
```

Resuelve prompts de configuración si aparecen (mantener ficheros locales salvo que sepas lo contrario). Cuando finalice, reinicia:

```bash
reboot
```

Verifica versión tras el reinicio:

```bash
pveversion -v
cat /etc/os-release | grep PRETTY_NAME
```

## 5) Validaciones post-upgrade

- UI en `https://<host>:8006` funcional y sin errores
- Servicios OK:

```bash
systemctl status pvedaemon pve-cluster pveproxy
journalctl -p err -b | tail -n +1
```

- Red operativa; si usabas `ifupdown`, confirma `/etc/network/interfaces` y puentes/bonds
- Almacenamientos montados y accesibles (LVM, ZFS, NFS, CIFS)
- ZFS saludable:

```bash
zpool status
```

- Backups programados activos y probados

## 6) Notas y cambios frecuentes de PVE 9

- Base Debian 13 (trixie), paquetes y kernels más recientes
- Posibles cambios en controladores de red/almacenamiento; verifica nombres de interfaz
- Si usas `networkd` vs `ifupdown`, asegúrate de usar un solo stack de red
- El repos enterprise puede venir habilitado; comenta si no tienes suscripción

## 7) Rollback (opciones y advertencias)

No existe rollback soportado automático entre versiones mayores. Opciones:

- Restaurar desde backup completo de sistema (imagen o snapshot del host)
- Reinstalar PVE 8 y restaurar backups de VMs/CTs
- Si falla por red, conserva acceso físico para corregir `/etc/network/interfaces`

## 8) Comandos útiles

```bash
# Simular antes (opcional)
apt -o APT::Get::Trivial-Only=true dist-upgrade

# Ver paquetes retenidos
apt-mark showhold || true

# Limpiar paquetes obsoletos
autoremove --purge -y || true
apt clean
```

## 9) Referencias

- Upgrade oficial PVE 9: https://pve.proxmox.com/wiki/Upgrade_from_8_to_9
- Notas de lanzamiento: https://pve.proxmox.com/wiki/Roadmap
- Repos Debian 13: https://www.debian.org/releases/trixie/
