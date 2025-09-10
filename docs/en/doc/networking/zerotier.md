# ZeroTier: basic install and setup

> ZeroTier provides easy L2/L3 virtual networks across devices.

## Requirements

- Debian/Ubuntu with `curl` and `sudo`
- Access to `https://my.zerotier.com` or your own controller

## Install

```bash
curl -s https://install.zerotier.com | sudo bash
```

Check:

```bash
sudo zerotier-cli -v
sudo systemctl status zerotier-one
```

## Join a network

```bash
sudo zerotier-cli join <NETWORK_ID>
```
Authorize the member in the web console, then verify:

```bash
ip -br a | grep zt
ping <peer_ip>
```

## Autostart and logs

```bash
sudo systemctl enable --now zerotier-one
journalctl -u zerotier-one -f
```

## Hardening and useful config

- Managed routes: define subnets and auto-install routes on authorized members.
- Flow rules minimal example (allow ICMP and SSH only):

```text
accept icmp;
accept tcp dport 22;
drop;
```

- MTU: adjust `zt*` MTU if fragmentation occurs.

### systemd override

```bash
sudo systemctl edit zerotier-one
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
sudo systemctl restart zerotier-one
```

## Containerized examples (Docker)

### Connect your app containers to the VPN

- Option 1 (host networking): `--network host` creates `zt*` on the host.
- Option 2 (sidecar): share network namespace with your app:

```bash
docker run -d --name zerotier \
  --cap-add NET_ADMIN --device /dev/net/tun \
  -v zt_state:/var/lib/zerotier-one \
  --network container:myapp \
  zerotier:latest
```

- Option 3 (router container): enable NAT inside ZeroTier container so a Docker network reaches the VPN (iptables MASQUERADE).
