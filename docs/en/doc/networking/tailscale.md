# Tailscale: basic install and setup

> Tailscale builds a secure WireGuard-based mesh with SSO.

## Requirements

- Debian/Ubuntu with `curl` and `sudo`
- Access to `https://login.tailscale.com`

## Quick install

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Check:

```bash
tailscale version
sudo systemctl status tailscaled
```

## Authenticate and bring up

```bash
sudo tailscale up
```
Approve the device in the admin console if required.

## Useful commands

```bash
 tailscale status
 ip -4 addr show tailscale0
 sudo systemctl enable --now tailscaled
 sudo tailscale down
```

## Hardening and useful options

- ACLs (admin console) minimal example (allow admins everywhere):

```json
{
  "acls": [
    {"action": "accept", "src": ["group:admins"], "dst": ["*"]}
  ]
}
```

- DNS: enable MagicDNS; force DNS if needed:

```bash
sudo tailscale up --accept-dns=true
```

- Subnet router (reach a LAN):

```bash
sudo tailscale up --advertise-routes=192.168.10.0/24
```
Authorize the route in the admin console.

### systemd override

```bash
sudo systemctl edit tailscaled
```
Content:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Apply:

```bash
sudo systemctl daemon-reload
sudo systemctl restart tailscaled
```

## Containerized examples (Docker)

### Connect your app containers to the VPN

- Option 1 (userspace subnet router): expose app ports via the Tailscale container; use `--advertise-routes`/exit-node as needed.
- Option 2 (sidecar namespace):

```bash
docker run -d --name tailscale \
  --cap-add NET_ADMIN --device /dev/net/tun \
  -v tailscale_state:/var/lib/tailscale \
  --network container:myapp \
  tailscale:latest
```

- Option 3 (host networking): run Tailscale on host or container with `--network host` and apps use host stack.
