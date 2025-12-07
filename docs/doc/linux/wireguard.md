# WireGuard VPN

WireGuard es una VPN extremadamente simple pero rápida y moderna.

## Instalación

```bash
sudo apt install wireguard
```

## Generación de Claves

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

## Configuración del Servidor (`/etc/wireguard/wg0.conf`)

```ini
[Interface]
Address = 10.100.0.1/24
SaveConfig = true
ListenPort = 51820
PrivateKey = <CONTENIDO_DE_PRIVATEKEY_SERVIDOR>

# Peer (Cliente)
[Peer]
PublicKey = <PUBLICKEY_DEL_CLIENTE>
AllowedIPs = 10.100.0.2/32
```

## Iniciar

```bash
wg-quick up wg0
systemctl enable wg-quick@wg0
```
