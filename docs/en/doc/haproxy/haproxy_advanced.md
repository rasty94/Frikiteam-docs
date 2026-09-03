---
title: "Advanced HAProxy — Load Balancing, TLS and High Availability"
description: "Load balancing algorithms, active and passive health checks, persistence with cookies and stick tables, ACLs, TLS termination, rate limiting, maxconn and queues, seamless reload and HA with keepalived."
keywords: "haproxy, load balancing, leastconn, stick table, httpchk, tls, rate limiting, maxconn, seamless reload, keepalived, vrrp"
tags: ['networking', 'high-availability', 'performance']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 25 min
category: Networking
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "[HAProxy — base guide](haproxy_base.md)"
  - "HTTP and TLS at the concept level"
  - "Root access to the load balancer"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Advanced HAProxy — Load Balancing, TLS and High Availability

## The problem

The three-line configuration works. `balance roundrobin`, two servers, `check`, and traffic gets shared. Until a backend stops answering correctly but keeps accepting TCP connections, and HAProxy sends it half your users for hours. Or until you deploy and everyone loses their session. Or until a bot finds `/login` and takes down the database while the load balancer distributes the attack with great diligence. None of those failures is fixed by switching load balancer: they are fixed by configuring the one you already have.

!!! note "What this covers and what it doesn't"
    Installation and the minimal `haproxy.cfg` live in [HAProxy — base guide](haproxy_base.md). Here you already have traffic flowing and we talk about **why** you pick each option. The comparison against other proxies is in [Load balancer comparison](../networking/load_balancer_comparison.md).

## 📋 Table of Contents

- [Choosing a balancing algorithm](#choosing-a-balancing-algorithm)
- [Health checks: active and passive](#health-checks-active-and-passive)
- [Persistence: cookies vs stick tables](#persistence-cookies-vs-stick-tables)
- [ACLs and routing](#acls-and-routing)
- [TLS termination](#tls-termination)
- [Rate limiting with stick tables](#rate-limiting-with-stick-tables)
- [maxconn and queues](#maxconn-and-queues)
- [Reloading without dropping connections](#reloading-without-dropping-connections)
- [Statistics and logs](#statistics-and-logs)
- [High availability for HAProxy itself](#high-availability-for-haproxy-itself)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Choosing a balancing algorithm

The real criterion is not "which one is best", but **how long a request lasts**.

| Algorithm | Distributes by | Pick it when |
|---|---|---|
| `roundrobin` | Weighted rotation | Short, homogeneous requests (typical HTTP), servers of similar capacity |
| `leastconn` | Fewest active connections | Long or highly variable sessions: WebSocket, LDAP, SQL, downloads |
| `source` | Hash of the source IP | You need affinity without cookies (TCP mode, clients that don't handle them) |
| `uri` | Hash of the left part of the URI | Cache farms: the same object always lands on the same node |

The common mistake is using `leastconn` "because it sounds smarter". With 20 ms requests the number of active connections is statistical noise, and `roundrobin` distributes just as well with less work. `leastconn` wins exactly where `roundrobin` fails: when a request may last 200 ms or 20 minutes and the rotation piles the long ones onto the same server.

```haproxy
backend app
  balance roundrobin
  server app1 10.0.0.11:8080 check weight 100
  server app2 10.0.0.12:8080 check weight 50     # half the traffic

backend ws
  balance leastconn                              # WebSocket: long connections
  server ws1 10.0.0.21:8080 check
  server ws2 10.0.0.22:8080 check
```

`source` and `uri` spread a hash across the **live** servers. In the default mode (`map-based`), one node goes down and the whole mapping is recalculated: *every* client changes server. Adding `hash-type consistent` to the backend limits redistribution to the failed node's share; with more than two servers it is almost always what you want. And `source` distributes by IP, not by user: behind CGNAT or an office NAT, thousands of clients are a single IP and the balance skews on its own.

## Health checks: active and passive

`server app1 10.0.0.11:8080 check` performs a **layer 4** check: it opens a TCP connection and closes it. That answers a single question —is anything listening?— and none of the ones that matter. A server with an exhausted connection pool accepts TCP and returns 500. A Tomcat with a badly deployed WAR accepts TCP and returns 404 for everything. A process that is alive but wedged accepts TCP and never answers. In all three cases the check passes and HAProxy keeps sending users to a broken server.

```haproxy
backend app
  option httpchk GET /healthz
  http-check expect status 200
  server app1 10.0.0.11:8080 check inter 3s fall 3 rise 2 observe layer7 error-limit 10 on-error mark-down
  server app2 10.0.0.12:8080 check inter 3s fall 3 rise 2 observe layer7 error-limit 10 on-error mark-down
```

| Parameter | What it controls | Criterion |
|---|---|---|
| `inter` | Interval between probes | 2–5 s; going much lower adds load to the backend |
| `fall` | Consecutive failures before marking it down | 3, so a one-off spike doesn't evict a server |
| `rise` | Successes before readmitting it | 2 or more: readmitting too fast causes flapping |
| `observe layer7` | Watches **real traffic**, not the probes | Detects the failure without waiting for the next `inter` |
| `on-error mark-down` | What to do past `error-limit` | Take the server out of rotation immediately |

The two mechanisms complement each other: the passive one (`observe`) detects fast because it sees every request; the active one (`check`) decides when to readmit. And a good `/healthz` verifies the critical dependencies: an endpoint that always returns 200 is a layer 4 check with extra steps.

!!! warning "The `option httpchk` syntax depends on the branch"
    `option httpchk GET /healthz` works on every maintained branch. What changed is how headers are added: stuffing `Host` into the `option httpchk` line itself has been discouraged since HAProxy 2.2, which introduced `http-check send` to do the same thing readably. Check the documentation for **your** version (`haproxy -v`) before copying an example from a blog: this is where the examples in circulation diverge the most.

## Persistence: cookies vs stick tables

If the application keeps state in the server's memory, the user has to come back to the same node. There are two ways and they are not equivalent.

```haproxy
# Option A: cookie inserted by HAProxy (HTTP mode only)
backend app
  balance roundrobin
  cookie SRVID insert indirect nocache httponly secure
  server app1 10.0.0.11:8080 check cookie a1
  server app2 10.0.0.12:8080 check cookie a2

# Option B: stick table, invisible to the client, works in TCP mode too
backend tcpapp
  balance roundrobin
  stick-table type ip size 200k expire 30m
  stick on src
  server t1 10.0.0.21:5432 check
  server t2 10.0.0.22:5432 check
```

`insert` creates the cookie, `indirect` strips it before passing the request to the backend, `nocache` prevents an intermediate proxy from caching the response with it. The value (`a1`) is opaque: don't put the server's IP there.

| | Cookie | Stick table |
|---|---|---|
| Works in TCP mode | No | Yes |
| Depends on the client | Yes: delete it and affinity is gone | No |
| Survives a proxy restart | Yes | No (in-memory table) |
| Memory cost on the proxy | None | Proportional to the number of entries |

Rule of thumb: **HTTP with normal clients, cookie; TCP or cookie-less clients, stick table**. In a pair of load balancers the table is only shared if you declare a `peers` section and reference it with `stick-table ... peers name`; otherwise each node has its own memory and failover loses every session. Either way, persistence is a band-aid: it turns any server failure into session loss for its users. The real fix is moving state out to Redis or the database and not needing affinity at all.

## ACLs and routing

An ACL is a named condition; `use_backend` uses it to pick a destination. They are evaluated top to bottom and the first match wins.

```haproxy
frontend web
  bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1

  acl host_api    hdr(host) -i api.example.com      # by host
  acl host_admin  hdr_beg(host) -i admin.
  acl path_static path_beg /static/ /assets/        # by path

  use_backend api    if host_api
  use_backend admin  if host_admin
  use_backend static if path_static
  default_backend app
```

`hdr(host) -i` compares the full header case-insensitively; `hdr_beg(host) -i admin.` matches any subdomain starting like that. `path_beg` takes several values and matches if **any** of them does. They combine: `if host_api path_static` is an AND, `if host_api || host_admin` an OR, `if !host_api` negates. And there must always be a `default_backend`: without it, anything that doesn't match gets a 503 and the log only says `NOSRV`.

## TLS termination

```haproxy
global
  ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

frontend web
  bind *:80
  bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1
  http-request redirect scheme https code 301 unless { ssl_fc }

  http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains"
  http-response set-header X-Content-Type-Options nosniff
  http-response set-header Referrer-Policy strict-origin-when-cross-origin
  http-request set-header X-Forwarded-Proto https if { ssl_fc }
  default_backend app
```

- **`crt` takes a file or a directory.** With a directory, HAProxy loads every `.pem` it finds and selects by SNI. Each `.pem` must contain the full chain **and** the private key concatenated.
- **`alpn h2,http/1.1`** is what enables HTTP/2 towards the client. Without that parameter there is no HTTP/2, no matter what the browser supports.
- **The redirect goes first** in the frontend, with `unless { ssl_fc }` so you don't loop on traffic that already arrives encrypted. And **HSTS only when you are sure**: a year of `max-age` with an expired certificate is an unreachable site the user cannot click past; add `preload` only if you are going to submit the domain to the preload list.
- **Re-encryption towards the backend** if the internal network isn't trusted: `server app1 10.0.0.11:8443 ssl verify required ca-file /etc/ssl/certs/ca.pem check check-ssl`. `verify required` is what makes this worth anything; `verify none` encrypts without authenticating anything.

Managing the certificates themselves (ACME, renewal, chains) is covered in [TLS certificates](../networking/certificados_tls.md).

## Rate limiting with stick tables

A stick table is a key → counters map with expiration: the same structure behind persistence, used here to count.

```haproxy
frontend web
  bind *:443 ssl crt /etc/haproxy/certs/

  # Key = IP, up to 100k entries, forgotten after 10 min of inactivity.
  stick-table type ip size 100k expire 10m store http_req_rate(10s),http_err_rate(60s)
  http-request track-sc0 src                        # this is what counts

  acl too_many_requests sc_http_req_rate(0) gt 100
  acl too_many_errors   sc_http_err_rate(0) gt 20
  http-request deny deny_status 429 if too_many_requests
  http-request deny deny_status 403 if too_many_errors
  default_backend app
```

1. `store http_req_rate(10s)` is a **sliding rate**: requests in the last 10 seconds, not an absolute counter you have to reset.
2. `http-request track-sc0 src` is what increments the counter. Without this line the table exists but stays empty and the ACLs never fire. It is the number one omission.
3. `sc_http_req_rate(0)` reads slot 0, the same one `track-sc0` declared; there are several (`sc0`, `sc1`, `sc2`) to track different keys at once. And `deny_status 429` returns *Too Many Requests*: a legitimate client can retry with backoff and the log distinguishes abuse from a policy block.

`http_err_rate` counts 4xx responses and spots brute force better than the total rate: a password scanner produces few successes and many 401s.

!!! tip "Count before you block"
    Deploy the table and the `track-sc0` without the `deny` rules, let a day go by and look at the real values with `echo "show table web" | socat stdio /run/haproxy/admin.sock`. A threshold picked by eye blocks your own uptime monitor or a whole office behind one NAT. If you sit behind a CDN, track the real IP from `X-Forwarded-For` and not `src`, which will always be the CDN's.

At the network level this pairs with [nftables and fail2ban](../cybersecurity/nftables_fail2ban.md): HAProxy filters at layer 7, the firewall drops before you spend CPU on TLS.

## maxconn and queues

`maxconn` shows up in three places and means something different in each:

```haproxy
global
  maxconn 20000              # process-wide cap
frontend web
  maxconn 15000              # cap for this frontend
backend app
  timeout queue 10s
  server app1 10.0.0.11:8080 check maxconn 200
  server app2 10.0.0.12:8080 check maxconn 200
```

The per-server one is the interesting one: once reached, HAProxy **does not reject**, it queues until a slot frees up. That protects the backend from more concurrency than it can take, but it has a time limit (`timeout queue`); when it expires the client gets a 503.

The right number can't be guessed: it is the concurrency at which the backend still answers in acceptable time. A PHP-FPM with `pm.max_children = 50` has a natural `maxconn` of 50; sending it 500 connections doesn't make it faster, it just moves the queue from the proxy —where it is visible and measurable— to the server, where it turns into timeouts. And if you raise the global `maxconn`, raise the service's open file limit too: every connection consumes descriptors.

## Reloading without dropping connections

`systemctl reload haproxy` does not kill the process: it starts new workers with the new configuration and lets the old ones finish the connections they already had.

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg    # ALWAYS validate first
systemctl reload haproxy
```

What breaks it: **not validating first** (an invalid configuration makes the reload fail, and losing service over a comma is avoidable with one command); **`hard-stop-after` set too short**, which caps how long old workers may live and is necessary —without it an eternal connection leaves an old process forever— but cuts long requests if it is shorter than their real duration; **very long connections**, because WebSocket and streaming keep old processes alive until the client leaves, and reloading every few minutes piles up processes and memory; and **external files** such as certificate lists or maps, which will fail the reload just the same if they are broken at that moment.

!!! warning "The part that depends on the version"
    That **existing** connections survive is standard behavior. That no **new** connection is lost during the reload window depends on the new process inheriting the listening sockets from the old one, something HAProxy supports since the 1.8 branch through the admin socket (`expose-fd listeners` and the `-x` option) and which on 2.x branches with master-worker is handled by the distribution's systemd unit. If you need a zero-loss guarantee, check how **your** unit is wired instead of assuming: packages don't all configure it the same way.

To pull a server out of rotation before a deploy you don't need to reload. `drain` stops sending new connections but honors existing ones; `maint` cuts abruptly.

```bash
echo "set server app/app1 state drain" | socat stdio /run/haproxy/admin.sock
echo "set server app/app1 state ready" | socat stdio /run/haproxy/admin.sock
```

## Statistics and logs

```haproxy
listen stats
  bind 127.0.0.1:8404
  stats enable
  stats uri /
  stats refresh 10s
  stats hide-version
  stats auth admin:a-long-password
  stats admin if LOCALHOST
```

The page exposes server names, internal IPs, error rates and —with `stats admin`— **buttons to take backends down from the browser**. It must never be on the Internet. Three layers, and you want all three: `bind` to an internal interface or to `127.0.0.1` behind an SSH tunnel; authentication or an IP restriction (`http-request deny unless { src 10.0.0.0/8 }`); and `stats hide-version` so you don't hand a scanner the exact version. For Prometheus, HAProxy ships a native exporter **if the binary was built with `USE_PROMEX`** — check with `haproxy -vv | grep -i prometheus` before configuring `http-request use-service prometheus-exporter`; if it isn't there, you need an external exporter. Integration in [Observability](../monitoring/observability_stack.md).

With `option httplog` every request produces one line; these are the fields you read first when something goes wrong:

| Field | What it tells you |
|---|---|
| Timers (5 values with `/`) | Where the time went: client wait, queue, connect, server response, total |
| Status code | If it is `-1` there was no response: the problem is the connection, not the application |
| Termination state | **The most informative field**: who cut, and in which phase |
| `srv_conn` / `srv_queue` / `backend_queue` | If there is a queue, your per-server `maxconn` is the bottleneck |
| `retries` | Connection retries; a sustained high value points at the network or an unstable backend |
| Backend/server | `NOSRV` means no server was available |

| State | Reading |
|---|---|
| `----` | Request completed normally |
| `sH--` | Timeout waiting for response headers: the backend is slower than `timeout server` |
| `sQ--` | Expired in queue: the server's `maxconn` was hit and `timeout queue` ran out |
| `SC--` | HAProxy could not connect to the server (refused or network) |
| `SD--` | The server cut mid-transfer |
| `cD--` | The client stopped reading: slow network or a client that gave up |
| `PR--` | Denied by a rule in the proxy itself |

Telling `sH` from `SD` saves hours: the first is your application taking too long, the second is your application dying halfway through the response. Different problems, identical browser message. And if a health monitor generates thousands of lines a day it masks the interesting ones: `option dontlognull` drops connections with no data and `monitor-uri` lets you isolate the probe in a separate frontend.

## High availability for HAProxy itself

A single load balancer is a single point of failure in disguise: you gave the application high availability and took it away at the entrance. The usual pattern is a pair of nodes running **keepalived** with a virtual IP (VIP) over VRRP.

1. Both nodes advertise their priority over VRRP on the local network. The highest priority keeps the VIP and answers ARP for it.
2. If the BACKUP stops receiving advertisements, it assumes the MASTER died, takes the VIP and sends a gratuitous ARP so the switches update their tables.
3. A `vrrp_script` checks that HAProxy is still alive and **subtracts priority** when it fails. This is the piece that makes failover happen when HAProxy dies and not only when the machine dies: without it, a node with keepalived alive and HAProxy dead keeps the VIP and blackholes the service.

The three places where this breaks in practice: a **duplicated `virtual_router_id`** on the same segment, where two different pairs with the same ID step on each other and fail intermittently; **VRRP filtered by the firewall or the switch**, so each node believes the other is dead, both take the VIP and you get split brain with a duplicated IP; and **HAProxy failing to start on the BACKUP** because it binds to an IP that node doesn't have yet — solved with `net.ipv4.ip_nonlocal_bind=1` or by binding to `0.0.0.0`, and it is the classic failure the first time you build the pair.

This scheme is active/passive: the BACKUP serves no traffic. For active/active you have to spread traffic with DNS or ECMP on the router, and then stick table persistence requires the `peers` section so both nodes see the same associations.

## Troubleshooting

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Immediate 503, log says `NOSRV` | No server passes the health check | `echo "show stat" \| socat stdio /run/haproxy/admin.sock`; try `/healthz` with `curl` |
| 503 after a few seconds, `sQ--` | Queue full and `timeout queue` expired | Raise the server's `maxconn` if the backend can take it; otherwise it is real capacity |
| 504 or state `sH--` | The backend is slower than `timeout server` | Measure the real time before raising the timeout: it may be an unindexed query |
| Sessions lost at random | Incomplete persistence or an unstable backend | Check there is a `cookie` on **every** `server` line; look for flaps in `show stat` |
| All users on a single server | `balance source` with clients behind NAT | Move to `roundrobin` with a cookie, or at least `hash-type consistent` |
| Rate limiting never fires | Missing `http-request track-sc0 src` | `show table <name>`: if it is empty, nothing is being tracked |
| `bind` fails on the BACKUP node | The VIP isn't on that node | `sysctl -w net.ipv4.ip_nonlocal_bind=1` |
| Reload cuts long connections | `hard-stop-after` shorter than the connection's life | Set it to the real duration of WebSocket or downloads |
| TLS fails only on some domains | A `.pem` missing the full chain or the key | Verify each file: chain and private key concatenated |

The four commands that solve most cases:

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg               # syntax
haproxy -vv                                          # version and compiled options
echo "show stat" | socat stdio /run/haproxy/admin.sock
journalctl -u haproxy -f
```

## Best practices

- **`haproxy -c` before every reload**, no exceptions. It is the difference between a change and an outage.
- **Layer 7 health check on anything serving HTTP**, against an endpoint that verifies real dependencies.
- **Per-server `maxconn` matched to measured capacity.** Queue in the proxy, never drown the backend.
- **Persistence only if the application needs it.** If you can move state to Redis, do it and delete the affinity config.
- **The stats page never on the Internet**, with `stats hide-version`, and rate limiting measured before it is enforced: count first, block later.
- **HAProxy never alone.** A pair with keepalived and a `vrrp_script` that checks the process, not just the machine, with explicit timeouts in `defaults` and the configuration in Git deployed with [Ansible](../ansible/ansible_base.md).

## References

- [HAProxy configuration documentation](https://docs.haproxy.org/) — pick your branch before copying anything
- [HAProxy Management Guide](https://docs.haproxy.org/2.8/management.html) · [keepalived documentation](https://keepalived.readthedocs.io/)
- [HAProxy — base guide](haproxy_base.md) · [Load balancer comparison](../networking/load_balancer_comparison.md) · [TLS certificates](../networking/certificados_tls.md) · [Traefik](../traefik/traefik_base.md) · [Observability](../monitoring/observability_stack.md)
