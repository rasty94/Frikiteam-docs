# Troubleshooting (Networking)

## No connectivity between peers

- Ensure both peers are online and authorized
- Check local firewalls (ufw/nftables/iptables)
- Avoid concurrent VPNs competing for routes/WireGuard

Useful commands:

```bash
ip -br a
ip r
ping <peer_ip>
traceroute <peer_ip>
```

## MTU and fragmentation

- Symptoms: slow SSH, drops, large packets failing
- Tune MTU on the VPN interface and/or bridge

```bash
sudo ip link set dev tailscale0 mtu 1280 || true
sudo ip link set dev ztXXXXXX mtu 1400 || true
```

## DNS

- Confirm the active resolver is the expected one (`resolvectl status`)
- If using VPN-provided DNS, enable DNS management on the client

## Overlapping routes

- Avoid subnet overlap between LAN and VPN
- Review advertised routes and metrics priority

## systemd boot order

- Ensure dependency on `network-online.target` in the VPN service
- Use `systemctl edit <service>` and add:

```ini
[Unit]
After=network-online.target
Wants=network-online.target
```
