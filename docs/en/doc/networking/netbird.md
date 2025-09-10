# NetBird: basic install and setup

> NetBird is a WireGuard-based mesh VPN with access control.

## Requirements

- Debian/Ubuntu with `curl` and `sudo`
- Outbound HTTP/HTTPS allowed

## Quick install (official script)

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sudo bash
```

Check service:

```bash
sudo systemctl status netbird
netbird --version
```

## Join the network

```bash
netbird up
```
Follow the browser flow, then verify:

```bash
netbird status
netbird peers
```

## Autostart and logs

```bash
sudo systemctl enable --now netbird
journalctl -u netbird -f
```

## Hardening and useful config

- ACLs: restrict traffic to required groups only (configure in the dashboard).
- DNS: set per-peer or network DNS; ensure `systemd-resolved` is active on Linux:

```bash
sudo systemctl enable --now systemd-resolved
resolvectl status
```

- Routes: advertise routes via the dashboard to reach LANs behind a gateway peer.

### systemd override (boot order)

```bash
sudo systemctl edit netbird
```
Drop-in content:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Apply:

```bash
sudo systemctl daemon-reload
sudo systemctl restart netbird
```

## Containerized examples (Docker)

### Connect your app containers to the VPN

- Option 1 (host networking): run NetBird with `--network host` and apps use the host stack.
- Option 2 (sidecar): share network namespace with your app:

```bash
docker run -d --name netbird --cap-add NET_ADMIN --device /dev/net/tun \
  -v netbird_state:/var/lib/netbird --network container:myapp netbird:latest
```

- Option 3 (dedicated Docker network + NAT): route via the NetBird container (requires iptables/MASQUERADE inside the VPN container).
