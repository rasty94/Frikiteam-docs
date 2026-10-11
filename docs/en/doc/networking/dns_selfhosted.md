---
title: "Self-hosted DNS: resolver and authoritative server"
description: "Building the DNS of your own network: Unbound resolver, internal authoritative zone with BIND or PowerDNS, split-horizon, integration with DHCP, Proxmox and Kubernetes, high availability and diagnostics."
keywords: "dns, unbound, bind, bind9, powerdns, resolver, authoritative, split-horizon, home.arpa, tsig, axfr, dig"
tags: ['networking', 'linux']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 37 min
category: Networking
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Networking fundamentals (IP, ports, UDP/TCP)"
  - "Basic Linux administration (systemd, journalctl)"
  - "A domain of your own, or willingness to use home.arpa"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Self-hosted DNS: resolver and authoritative server

## The problem

Your network grows: three Proxmox nodes, a Kubernetes cluster, a couple of NAS boxes. You start with a hand-copied `/etc/hosts`, then the router's DNS, and one day a service moves to a new IP and half the clients keep pointing at the old one. Or worse: your ISP's DNS stops answering and suddenly "there is no internet" even though the link is perfectly fine.

The fix is to run **your own DNS**, but the usual mistake is to set up a single service that does everything. DNS is two different jobs with different requirements, and this page shows how to build them separately: a resolver that answers your clients and an authoritative server that is the source of truth for your internal zone.

!!! note "What this covers and what it does not"
    This is the foundation: resolver, internal zone, split-horizon, integration and high availability. Zone signing is in [DNSSEC](dnssec.md) and reverse zones are in [PTR records and reverse zones](registros_ptr_zonas_inversas.md); they are not repeated here.

## 📋 Table of Contents

- [Resolver vs authoritative](#resolver-vs-authoritative)
- [Resolver with Unbound](#resolver-with-unbound)
- [Internal authoritative zone with BIND](#internal-authoritative-zone-with-bind)
- [PowerDNS as an alternative with an API](#powerdns-as-an-alternative-with-an-api)
- [Internal domain and split-horizon](#internal-domain-and-split-horizon)
- [Integrating with the network](#integrating-with-the-network)
- [High availability](#high-availability)
- [Diagnostics](#diagnostics)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Resolver vs authoritative

| | Recursive resolver | Authoritative server |
|---|---|---|
| Question it answers | "What is the IP of `ejemplo.org`?" (for any name) | "What is the IP of `nas.lab.ejemplo.org`?" (only for its zones) |
| Who queries it | Your clients (laptops, VMs, pods) | Resolvers, never the end client |
| What it does | Asks the root, the TLDs and the authoritative servers until it gets the answer, and **caches** it | Serves data from a zone file or a database |
| State | Cache (can be lost without losing data) | Zone data (must be backed up) |
| Examples | Unbound, BIND with `recursion yes`, Knot Resolver | BIND, PowerDNS Authoritative, NSD, Knot DNS |
| Exposure | Your network only | Can be public if the zone is |

Mixing them in one process works at home, but it has real costs:

- **Security.** A resolver open to the internet is a DDoS amplifier; an authoritative server must not recurse for anyone. With `recursion no` on the authoritative and `access-control` on the resolver, each one fails closed.
- **Lifecycle.** The authoritative server is touched whenever you change records; the resolver almost never. Restarting one should not take down the other.
- **High availability.** Two identical resolvers are trivial. A replicated authoritative server needs zone transfers. They are different problems.

The layout used in the rest of the page: clients ask the resolver; the resolver forwards internal-zone queries to the authoritative server and resolves everything else on its own or through an encrypted upstream.

```text
cliente --> resolutor (192.168.10.2)
               |-- lab.ejemplo.org --> autoritativo (192.168.10.3)
               '-- resto del mundo --> raíz/TLD, o upstream DoT
```

## Resolver with Unbound

Unbound is a recursive resolver with DNSSEC validation, small, with no authoritative zones of its own beyond local data. On Debian/Ubuntu the package is `unbound` and extra files are read from `/etc/unbound/unbound.conf.d/*.conf`.

### Minimal configuration

```yaml
# /etc/unbound/unbound.conf.d/resolutor.conf
server:
    interface: 127.0.0.1
    interface: 192.168.10.2
    port: 53

    # Quién puede preguntar. Lo que no case se rechaza.
    access-control: 127.0.0.0/8 allow
    access-control: 192.168.10.0/24 allow
    access-control: 0.0.0.0/0 refuse

    do-ip6: no
    hide-identity: yes
    hide-version: yes

    # Protección contra DNS rebinding: bloquea respuestas públicas
    # que apunten a IPs privadas, salvo para los dominios internos.
    private-address: 192.168.0.0/16
    private-address: 10.0.0.0/8
    private-domain: "lab.ejemplo.org"
```

It looks like YAML but **is not**: it is Unbound's own format (`key: value` under sections such as `server:`). Three details that bite:

- `interface` is repeated once per address. If you put `0.0.0.0` on a host running `systemd-resolved`, you will collide with its stub on `127.0.0.53:53`; bind to specific IPs.
- `access-control` applies the most specific rule. By default Unbound only allows localhost, so without these lines your clients get `REFUSED`.
- `do-ip6: no` disables IPv6 as a transport: it neither answers nor sends queries over IPv6 (it does not affect the AAAA records carried inside). If your network has real IPv6 connectivity, leave it at `yes`.

### Cache

The cache is the reason a resolver exists. The parameters that matter:

```yaml
server:
    num-threads: 2
    msg-cache-size: 64m
    rrset-cache-size: 128m   # regla práctica: el doble que msg-cache
    prefetch: yes            # renueva entradas populares antes de que caduquen
    cache-min-ttl: 60        # modesto: subirlo viola los TTL del propietario
    serve-expired: yes       # sirve caducadas si el upstream no responde
```

!!! warning "Version dependent"
    `serve-expired` is not available in the oldest Unbound releases, and its related options (`serve-expired-ttl`, `serve-expired-client-timeout`) have changed across versions. Check `unbound -V` and the manual page for your version before tuning them.

`cache-min-ttl` is tempting, but a five-minute TTL is usually set for a reason (a failover, a load balancer). Use low values or do not use it.

### Forward-zone: internal zone and encrypted upstream

Two uses of `forward-zone`. The first sends the internal zone to the authoritative server; the second, optional, sends **everything else** to an upstream over DNS over TLS instead of recursing from the root:

```yaml
forward-zone:
    name: "lab.ejemplo.org."
    forward-addr: 192.168.10.3

# Opcional: delegar el resto en un upstream por DoT (puerto 853)
server:
    tls-cert-bundle: /etc/ssl/certs/ca-certificates.crt

forward-zone:
    name: "."
    forward-tls-upstream: yes
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 9.9.9.9@853#dns.quad9.net
```

The `IP@port#name` format is what lets Unbound validate the upstream's certificate; without the `#name` the encryption works but the server is not authenticated. Before deciding whether to use an upstream, think about what you gain and lose:

- **Recursing yourself** (no `forward-zone: "."`): you depend on nobody and tell nobody what you query, but the world's authoritative servers see your IP and the traffic leaves in clear text.
- **DoT to an upstream**: your network operator cannot see the queries, but you disclose them to a third party and depend on it.

If the internal zone hangs off a public domain signed with DNSSEC and the internal authoritative server does not sign, Unbound may return `SERVFAIL` when validating; `domain-insecure: "lab.ejemplo.org"` exists for that case. Validation details in [DNSSEC](dnssec.md).

### Validate and operate

```bash
unbound-checkconf                      # sintaxis y ficheros incluidos
sudo systemctl restart unbound
dig @192.168.10.2 debian.org +short
```

Run `unbound-checkconf` **always** before restarting: a broken file leaves the resolver down and the whole network without DNS. To operate live, enable the control channel:

```yaml
remote-control:
    control-enable: yes
    control-interface: 127.0.0.1
```

Generate the certificates with `unbound-control-setup` if your package did not. Then:

```bash
unbound-control status                  # versión, uptime, hilos
unbound-control stats_noreset           # contadores sin ponerlos a cero
unbound-control flush nombre.ejemplo.org   # borra un nombre de la caché
unbound-control flush_zone ejemplo.org     # borra toda una zona
unbound-control list_forwards           # forward-zones activas
unbound-control reload                  # relee la configuración
```

`flush` is the first thing you do after fixing a record: the resolver will keep serving the old data until the TTL expires.

## Internal authoritative zone with BIND

BIND (`bind9` on Debian, `bind` on RHEL; the service is called `named`) is the reference authoritative server. We configure it as authoritative only: **no recursion**.

!!! warning "Version dependent"
    `type primary` and `type secondary` (and `primaries` instead of `masters`) arrived with BIND 9.16. Earlier versions use `type master` / `type slave`, which newer ones still accept as aliases. Check `named -v`.

### named.conf

```text
// /etc/bind/named.conf.options
options {
    directory "/var/cache/bind";
    listen-on { 192.168.10.3; };
    recursion no;
    allow-query { 192.168.10.0/24; };
    allow-transfer { none; };
    notify yes;
};
```

```text
// /etc/bind/named.conf.local
zone "lab.ejemplo.org" {
    type primary;
    file "/etc/bind/zones/db.lab.ejemplo.org";
};
```

`recursion no` is the important line: without it your authoritative server answers anyone's queries for any domain. `allow-transfer { none; }` closes transfers by default; they are opened later for the secondary (see [High availability](#high-availability)).

### Zone file

```text
; /etc/bind/zones/db.lab.ejemplo.org
$TTL 1h
@   IN  SOA ns1.lab.ejemplo.org. hostmaster.lab.ejemplo.org. (
            2026101101  ; serial (AAAAMMDDNN)
            1h          ; refresh
            15m         ; retry
            1w          ; expire
            5m )        ; TTL negativo

    IN  NS  ns1.lab.ejemplo.org.

ns1     IN  A     192.168.10.3
pve1    IN  A     192.168.10.11
pve2    IN  A     192.168.10.12
nas     IN  A     192.168.10.20
k8s-api IN  A     192.168.10.30
grafana IN  CNAME nas
```

The SOA rules that break most often:

- **The serial must increase on every change.** Secondaries only transfer the zone if the primary's serial is higher. Editing a record without bumping it is the number one failure: the primary serves the new data and the secondary the old. The `YYYYMMDDNN` format allows up to 100 changes per day.
- **Absolute names must end with a dot.** `ns1.lab.ejemplo.org` without the trailing dot is read as `ns1.lab.ejemplo.org.lab.ejemplo.org.`.
- **The second SOA field** (`hostmaster.lab.ejemplo.org.`) is the owner's email with the first dot in place of the `@`.
- **A CNAME cannot coexist with other records of the same name**, and cannot sit at the zone apex.

### Check and reload

```bash
named-checkconf                                           # sintaxis de named.conf
named-checkconf -z                                        # además, carga cada zona
named-checkzone lab.ejemplo.org /etc/bind/zones/db.lab.ejemplo.org

sudo rndc reload                      # recarga todo
sudo rndc reload lab.ejemplo.org      # solo esa zona
sudo rndc zonestatus lab.ejemplo.org  # serial cargado, tipo, última recarga
```

`named-checkzone` answers `OK` and the loaded serial if the zone is valid; errors give the line and cause (name without dot, duplicate record, CNAME with other data). `rndc` talks over port 953 on localhost with a key that the package install usually generates by itself (`rndc-confgen` if you need to create it by hand).

For the reverse zones of `192.168.10.0/24` and PTR records, see [PTR records and reverse zones](registros_ptr_zonas_inversas.md).

## PowerDNS as an alternative with an API

[PowerDNS Authoritative Server](https://doc.powerdns.com/authoritative/) stores zones in a **database** (SQLite, MySQL/MariaDB or PostgreSQL) instead of files, and exposes an **HTTP API** to create zones and records. It is the option when records are managed by a tool (Terraform, scripts, a panel such as PowerDNS-Admin) and not by a person editing files.

```ini
# /etc/powerdns/pdns.conf (fragmento)
launch=gsqlite3
gsqlite3-database=/var/lib/powerdns/pdns.sqlite3
local-address=192.168.10.3
api=yes
api-key=CAMBIA-ESTE-VALOR
webserver=yes
webserver-address=127.0.0.1
webserver-port=8081
```

```bash
pdnsutil create-zone lab.ejemplo.org ns1.lab.ejemplo.org
pdnsutil add-record lab.ejemplo.org nas A 3600 192.168.10.20
pdnsutil check-all-zones

curl -s -H 'X-API-Key: CAMBIA-ESTE-VALOR' \
  http://127.0.0.1:8081/api/v1/servers/localhost/zones
```

!!! warning "Version dependent"
    Backend option names and `pdnsutil` syntax have changed between PowerDNS 3.x, 4.x and 5.x. The example follows the 4.x line (current `pdnsutil` documentation uses `zone create`, `rrset add` and `zone check-all`); confirm with `pdnsutil --help` and the documentation for your version before copying it. The initial SQL schema ships with the package.

Differences from BIND that matter in practice:

- **The server can manage the serial** (per-zone `SOA-EDIT` option) instead of you editing it by hand.
- **Replication** can be the usual one (AXFR/NOTIFY) or the database's native one (MySQL/PostgreSQL replicas), with no zone transfers.
- **It does not recurse**: PowerDNS Recursor is a different product. With Unbound in front you already have a resolver.
- The API key gives full control over the zones: keep it on `127.0.0.1` or behind a TLS proxy and do not publish it.

## Internal domain and split-horizon

### Which domain to use

| Option | Verdict |
|---|---|
| `lab.yourdomain.org` (subdomain of a domain you own) | **Recommended.** Nobody else can register it, allows real certificates via DNS-01 challenge and avoids collisions |
| `home.arpa` | **Good** if you have no domain. Reserved by RFC 8375 precisely for home networks; it will never be delegated |
| `.local` | **Avoid.** Reserved for mDNS (RFC 6762) |
| `.lan`, `.home`, `.corp` | Avoid. Not reserved and may end up publicly delegated |
| `.internal` | Reserved by ICANN for private use in 2024; valid if your software accepts it |

The problem with `.local`: systems with Avahi, Bonjour (macOS) or `systemd-resolved` send those names over multicast (mDNS) **instead of asking your DNS**. The symptom is as baffling as it gets: `dig nas.local` works and `ping nas.local` takes five seconds or fails, because each tool uses a different resolution path. Certificates valid for internal names (DNS-01 challenge) are covered in [TLS certificates](certificados_tls.md).

### Split-horizon

*Split-horizon* means answering the same question differently depending on who asks: from inside `app.ejemplo.org` is `192.168.10.20`; from outside, the public IP. There are two ways to do it without overcomplicating things:

**1. In the resolver (the simplest).** Unbound serves local data that takes precedence over public DNS:

```yaml
server:
    local-zone: "app.ejemplo.org." transparent
    local-data: "app.ejemplo.org. 300 IN A 192.168.10.20"
```

`transparent` means names in that zone **without** `local-data` resolve normally through the usual path; with other types (`static`) an undefined name would get `NXDOMAIN`.

**2. In the authoritative server with BIND `view`.** Two versions of the same zone depending on the client:

```text
acl interna { 192.168.10.0/24; 127.0.0.1; };

view "interna" {
    match-clients { interna; };
    zone "ejemplo.org" { type primary; file "/etc/bind/zones/db.ejemplo.org.int"; };
};

view "externa" {
    match-clients { any; };
    zone "ejemplo.org" { type primary; file "/etc/bind/zones/db.ejemplo.org.ext"; };
};
```

With views, **every zone must live inside some view**. The two versions of the zone are independent files that you must keep in sync, which in the long run costs more than option 1. Keep views for when the same server serves different networks. The mail records of the public zone are in [SPF, DKIM and DMARC](spf_dkim_dmarc.md).

## Integrating with the network

### DHCP hands out the resolver

Clients use the DNS that DHCP gives them. With dnsmasq:

```ini
# /etc/dnsmasq.d/dhcp.conf
dhcp-range=192.168.10.100,192.168.10.200,12h
dhcp-option=option:dns-server,192.168.10.2,192.168.10.5
dhcp-option=option:domain-search,lab.ejemplo.org
domain=lab.ejemplo.org
```

In Kea the equivalent option is `domain-name-servers` and in ISC DHCP, `option domain-name-servers`. Hand out **two resolvers** (see [High availability](#high-availability)) and a `domain-search` so that `ping nas` completes to `nas.lab.ejemplo.org`. With dnsmasq acting as DHCP **and** DNS at once, remember that dnsmasq also listens on port 53 and will collide with Unbound if they share an IP.

### Pi-hole or AdGuard Home as a filter

If you want ad and tracker blocking, Pi-hole or AdGuard Home go **in front** as a filter and use Unbound as upstream. Clients ask the filter; the filter asks Unbound; Unbound asks the authoritative server or the internet. Two consequences to keep in mind:

- Unbound sees every query with the filter's IP, not the client's. Add that IP to `access-control` and look for per-client logs in the filter, not in Unbound.
- The filter becomes a single point of failure for the whole network: either you duplicate it, or DHCP also hands out an "unfiltered" fallback resolver.

They are not deployed here; this only describes how they fit with the resolver.

### Proxmox

On each node, `Node → System → DNS` sets servers and search domain, and it is reflected in `/etc/resolv.conf`. LXC containers inherit the host's DNS unless you set it per container, and cloud-init VMs receive it through configuration:

```bash
pct set 201 --nameserver 192.168.10.2 --searchdomain lab.ejemplo.org
qm set 301 --nameserver 192.168.10.2 --searchdomain lab.ejemplo.org
```

Each node's name must resolve to its **real** IP (not `127.0.1.1`) and, for cluster communication, it is wise not to depend on DNS alone: keep the nodes in `/etc/hosts` too. A cluster that will not start because the DNS lives in a VM of that same cluster is a classic. Details in [Proxmox base](../proxmox/proxmox_base.md).

### Kubernetes

CoreDNS resolves cluster names and forwards the rest to the node's `resolv.conf`. For pods to see your internal zone, add a block to the `Corefile` in the `coredns` ConfigMap of `kube-system`:

```text
lab.ejemplo.org:53 {
    errors
    cache 30
    forward . 192.168.10.2
}
```

Then restart the CoreDNS pods (`kubectl -n kube-system rollout restart deployment coredns`). If the node's `resolv.conf` points to the systemd-resolved stub `127.0.0.53`, point the kubelet at the real file (`/run/systemd/resolve/resolv.conf`) or CoreDNS will end up forwarding to itself in a loop. Cluster context in [Kubernetes base](../kubernetes/kubernetes_base.md).

### Firewall and ports

DNS uses **53/UDP and 53/TCP** (TCP for large responses and zone transfers; blocking it causes intermittent failures that are hard to see). DoT uses **853/TCP** towards the upstream, and `rndc` uses 953 on localhost only. See [Common port tables](tablas_puertos_comunes.md).

## High availability

### Resolvers

Two **identical** Unbound resolvers on different hosts, both handed out by DHCP. That is all. Each cache is independent and does not need replication.

Be aware of how clients behave: the Linux library tries servers **in order** and, if the first is down, waits for the timeout (5 s by default) before moving to the second, so every query becomes slow, not just the first. In `/etc/resolv.conf` you can shorten it:

```text
options timeout:1 attempts:2
```

If you need a single IP that stays alive, a virtual IP with keepalived between the two resolvers solves it without touching the clients.

### Authoritative: primary and secondary

The secondary obtains the zone by **transfer** (AXFR/IXFR) and the primary tells it about changes with NOTIFY. Generate a TSIG key to authenticate the transfer instead of trusting the source IP:

```bash
tsig-keygen -a hmac-sha256 xfer-key
```

It prints a `key "xfer-key" { ... };` block with the secret. Paste it on **both** servers and configure:

```text
// Primario (192.168.10.3)
zone "lab.ejemplo.org" {
    type primary;
    file "/etc/bind/zones/db.lab.ejemplo.org";
    allow-transfer { key xfer-key; };
    also-notify { 192.168.10.4; };
};
```

```text
// Secundario (192.168.10.4)
server 192.168.10.3 { keys { xfer-key; }; };

zone "lab.ejemplo.org" {
    type secondary;
    file "/var/cache/bind/db.lab.ejemplo.org";
    primaries { 192.168.10.3; };
};
```

The secondary stores the zone in `/var/cache/bind` because `named` can usually write there and not in `/etc/bind`. Add the second server as an `NS` in the zone (and its `A` record) so resolvers know it exists. After reloading:

```bash
dig @192.168.10.3 lab.ejemplo.org SOA +short   # el serial del primario
dig @192.168.10.4 lab.ejemplo.org SOA +short   # debe coincidir
sudo rndc retransfer lab.ejemplo.org           # en el secundario: forzar
```

`also-notify` is needed when the secondary is not listed as an `NS` of the zone (or you do not want to depend on that); if it is already in the `NS` set, BIND notifies it by itself. If the primary goes down, the secondary keeps serving the zone until the SOA `expire` value runs out.

## Diagnostics

`dig` (package `dnsutils` or `bind-utils`) is the main tool. The four patterns that solve almost everything:

```bash
dig nas.lab.ejemplo.org                      # consulta con el resolutor del sistema
dig @192.168.10.2 nas.lab.ejemplo.org        # a un servidor concreto
dig @192.168.10.3 nas.lab.ejemplo.org +norecurse +short   # al autoritativo, solo la IP
dig +trace nas.lab.ejemplo.org               # sigue la delegación desde la raíz
```

What to look at in the response:

- **`status:`** `NOERROR` (exists), `NXDOMAIN` (the name does not exist), `SERVFAIL` (the server failed: DNSSEC validation, upstream down, broken zone), `REFUSED` (the server does not want to talk to you: `access-control` or `allow-query`).
- **`aa` flag** (authoritative answer): present only if the authoritative server answered. If you query the authoritative server and it is missing, it is not serving that zone.
- **`ra` flag** (recursion available): indicates that server recurses. A properly configured authoritative server does **not** have it.
- **`+trace`** ignores your resolver and walks from the root; it helps tell whether the problem is public delegation or your local configuration.

More useful options: `+tcp` forces TCP (check that 53/TCP is open), `-x 192.168.10.20` does the reverse query, `+dnssec` asks for the signature records, and `+short` leaves only the data.

`drill` (package `ldnsutils`) follows the same idea with a different syntax and is very handy for DNSSEC:

```bash
drill @192.168.10.2 nas.lab.ejemplo.org
drill -T nas.lab.ejemplo.org       # traza desde la raíz
drill -S ejemplo.org               # persigue las firmas DNSSEC
```

On a host with systemd-resolved, `resolvectl status` and `resolvectl query name` show which server and path the system **actually** uses, which is not always the one in `/etc/resolv.conf`.

### Logs

```bash
journalctl -u unbound -f
journalctl -u named -f        # en Debian el servicio también se llama bind9

sudo rndc querylog on         # BIND: registra cada consulta (y se apaga con off)
```

For Unbound, `verbosity: 2` under `server:` gives resolution detail, and `log-queries: yes` logs every query; both generate a lot of volume, enable them only while debugging. More general methodology in [Network troubleshooting](troubleshooting.md).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `REFUSED` from a client | The client's IP is not in `access-control` (Unbound) or `allow-query` (BIND) | Add the subnet and reload; test with `dig @server` |
| Unbound or BIND will not start: "address already in use" | Another service holds port 53 (systemd-resolved, dnsmasq) | `ss -lntup \| grep ':53'`; bind to specific IPs or disable the stub |
| The secondary serves old data | The serial did not increase, or NOTIFY/transfer is missing | Bump the serial; compare `SOA +short`; `rndc retransfer` on the secondary |
| Transfer refused | TSIG missing or `allow-transfer` does not include the key | Check the key is identical on both and the `named` logs |
| `name.local` fails in some tools and not others | `.local` is resolved by mDNS, not by DNS | Migrate to `home.arpa` or to a subdomain of your own |
| `SERVFAIL` only in the internal zone | Unbound validates DNSSEC and the internal zone hangs off a signed domain | `domain-insecure` for that zone, or sign it ([DNSSEC](dnssec.md)) |
| Resolution with ~5 s delays | The first server in `resolv.conf` is down | Fix it or reduce `timeout`; review the order |
| You change a record and clients see the old one | Resolver cache | `unbound-control flush name`; wait for the TTL |
| Fails with large responses | 53/TCP blocked in the firewall | Open TCP as well as UDP; test with `dig +tcp` |
| Pods do not resolve the internal zone | The block is missing from the CoreDNS `Corefile` | Add the `forward` and restart CoreDNS |

## Best practices

- **Resolver and authoritative as separate services**, even if they share a machine at first. Recursion off on the authoritative, `access-control` closed on the resolver.
- **Validate before reloading**: `unbound-checkconf`, `named-checkconf -z` and `named-checkzone` on every change. A script or a Git hook that runs them prevents most incidents.
- **One place to edit, and the serial always goes up.** Zones are text: version them in Git and deploy with [Ansible](../ansible/ansible_base.md).
- **Two resolvers from day one**, handed out by DHCP, on different physical hosts. DNS must not live only inside the cluster that depends on it.
- **TSIG for transfers**, not trust in the source IP.
- **A domain you own (or `home.arpa`)**, never `.local`.
- **Back up the zones** and keep the files off the machine that serves them; a cache is rebuilt, a zone is not.
- **Do not expose the resolver to the internet**; if you must offer DNS outside the LAN, do it over a VPN.

## References

- [Unbound documentation](https://unbound.docs.nlnetlabs.nl/en/latest/)
- [BIND 9 Administrator Reference Manual](https://bind9.readthedocs.io/)
- [PowerDNS Authoritative Server](https://doc.powerdns.com/authoritative/)
- [RFC 8375: home.arpa](https://www.rfc-editor.org/rfc/rfc8375)
- [RFC 6762: Multicast DNS](https://www.rfc-editor.org/rfc/rfc6762)
- [DNSSEC](dnssec.md) · [PTR records and reverse zones](registros_ptr_zonas_inversas.md)
- [Network troubleshooting](troubleshooting.md) · [Common port tables](tablas_puertos_comunes.md) · [SPF, DKIM and DMARC](spf_dkim_dmarc.md)
- [Proxmox base](../proxmox/proxmox_base.md) · [Kubernetes base](../kubernetes/kubernetes_base.md)
