---
title: "Networking: Performance Comparison"
description: "How to measure network performance with iperf3, ping, mtr, ethtool and ss: reproducible methodology, MTU and offloads, and interpreting results to compare VPNs and overlays."
keywords: "iperf3, ping, mtr, ethtool, ss, benchmark, throughput, latency, jitter, mtu, offloads, wireguard, tailscale"
tags: ['networking']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 17 min
category: Networking
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "SSH access to two test nodes"
  - "Networking fundamentals (TCP, MTU, latency)"
  - "[MTU and MSS](mtu_mss_values.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Networking: Performance Comparison

## The problem

Someone claims "WireGuard does 9 Gbps and Tailscale 7". Without knowing the MTU, number of flows, hardware and repetitions, the figure is worthless: two measurements of the same link can differ more than two different technologies. A network benchmark is only useful if it is **reproducible** and you know **what limits** the result (the link, the CPU, the TCP window or the test itself).

This page gathers the classic tools, a methodology so numbers can be compared, and a guide to interpreting them. **It publishes no figures**: performance depends on your hardware, kernel and network. To compare solutions with your own data use the [vRouter Benchmark Template](vrouter_benchmark_template.md); for VPN and mesh analysis, [Tailscale vs NetBird: performance](tailscale_netbird_performance.md).

!!! note "What this covers and what it does not"
    Point-to-point performance measurement between two hosts. Diagnosing connectivity failures (DNS, routes, firewall) is in [Network Troubleshooting](troubleshooting.md).

## 📋 Table of Contents

- [What to measure](#what-to-measure)
- [Preparing the lab](#preparing-the-lab)
- [iperf3: bandwidth](#iperf3-bandwidth)
- [ping and mtr: latency and path](#ping-and-mtr-latency-and-path)
- [ethtool and ss: interface and sockets](#ethtool-and-ss-interface-and-sockets)
- [MTU and offloads](#mtu-and-offloads)
- [Methodology](#methodology)
- [Interpreting the results](#interpreting-the-results)
- [Comparing VPNs and overlays](#comparing-vpns-and-overlays)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## What to measure

| Metric | What it answers | Tool |
|---|---|---|
| **Throughput** | How many bits per second fit | `iperf3` |
| **Latency (RTT)** | How long a round trip takes | `ping`, `mtr` |
| **Jitter** | How much latency varies | `iperf3 -u`, `ping` (deviation) |
| **Loss** | What fraction of packets never arrives | `ping`, `mtr`, `iperf3 -u` |
| **CPU usage** | What encryption or forwarding costs | `top`, `mpstat` during the test |
| **TCP state** | Retransmits, window, RTT as seen by the kernel | `ss -ti` |

A single metric misleads: a link can have high throughput and bad latency under load (bufferbloat), or good latency and little bandwidth.

## Preparing the lab

- Two nodes you control, with the same hardware if possible, and **no other relevant traffic**.
- Tools installed: `iperf3`, `mtr`, `ping` and `ethtool`. On Debian/Ubuntu: `sudo apt install iperf3 mtr-tiny ethtool`.
- Note the kernel version (`uname -r`), the tool versions (`iperf3 --version`), each interface's MTU and the NIC model. Without that context the result is not comparable.
- Freeze the firewall: a different ruleset between two tests is one more variable.

```bash
# Minimum context worth saving next to each result
uname -r
ip -br link
ip -br addr
ethtool eth0 | grep -E 'Speed|Duplex'
```

## iperf3: bandwidth

One end acts as server and the other as client:

```bash
# Node B (server)
iperf3 -s

# Node A (client): 30 seconds, one TCP flow
iperf3 -c 192.0.2.10 -t 30
```

Common options:

| Option | Effect |
|---|---|
| `-t N` | Duration in seconds |
| `-P N` | N parallel TCP flows |
| `-R` | Reverse mode: the server sends and the client receives |
| `-u -b 100M` | UDP at a target rate; reports loss and jitter |
| `-i 1` | Report every second |
| `-J` | JSON output, handy to store and process |
| `-p PORT` | Port other than the default 5201 |

```bash
# Measure both directions separately: links can be asymmetric
iperf3 -c 192.0.2.10 -t 30
iperf3 -c 192.0.2.10 -t 30 -R

# Several flows: does a single flow exhaust the CPU or the window?
iperf3 -c 192.0.2.10 -t 30 -P 4

# UDP at a fixed rate to see loss and jitter
iperf3 -c 192.0.2.10 -u -b 200M -t 30

# JSON output to compare later
iperf3 -c 192.0.2.10 -t 30 -J > resultado.json
```

!!! warning "Version dependent"
    Some options (for example the simultaneous bidirectional test with `--bidir`) exist only in recent iperf3 versions. Check `iperf3 --help` on both ends, and use the same version on client and server.

With UDP, `-b` sets how much the client tries to send; if you set it above what the link supports, the "loss" you see is your own, not the link's. Raise the rate in steps until loss appears.

## ping and mtr: latency and path

```bash
# 100 packets, a summary at the end (min/avg/max/mdev)
ping -c 100 192.0.2.10

# Shorter interval (very low intervals may require privileges)
ping -c 100 -i 0.2 192.0.2.10

# mtr report: 100 cycles, no DNS, readable format
mtr -rwn -c 100 192.0.2.10
```

What to look at in `mtr`:

- **Loss%** on an intermediate hop but 0 % at the destination is almost always ICMP rate limiting on that router, not real loss.
- If loss or latency **starts at one hop and continues to the end**, the problem is there.
- A high `StDev` indicates jitter, even if the average is good.

`ping` and `mtr` use ICMP, which many devices deprioritise or filter. If the real service is TCP or UDP, cross-check with a measurement of the protocol itself (for example `iperf3` or a timed `curl`).

## ethtool and ss: interface and sockets

`ethtool` tells you what the NIC negotiated; `ss` tells you what the kernel sees inside TCP connections.

```bash
# Negotiated speed and duplex
ethtool eth0

# NIC counters: look for errors, drops, discards
ethtool -S eth0

# Kernel per-interface statistics
ip -s link show eth0

# Socket summary
ss -s

# TCP detail for connections to the iperf3 host during the test
ss -ti dst 192.0.2.10
```

From the `ss -ti` detail, what matters is the RTT the kernel measures, the congestion window size (`cwnd`) and retransmissions. Many retransmissions on a healthy link point to loss or an overflowing buffer somewhere; a `cwnd` that does not grow, to loss or a small receive window.

A negotiated speed lower than expected (100 Mb/s on a 1 Gb/s port) is usually a bad cable or port, and makes any later measurement useless.

## MTU and offloads

**MTU.** A wrong MTU fragments or drops packets and sinks performance without small pings revealing it. Tunnels (WireGuard, VXLAN, overlays) add headers and reduce the usable MTU. Find the maximum without fragmentation with `ping` and the do-not-fragment flag (on Linux, `-M do`; the size is the payload, without the IP and ICMP headers):

```bash
# If it answers, the path accepts that payload size without fragmenting
ping -M do -s 1472 -c 3 192.0.2.10
```

How the payload relates to the MTU and how to compute the MSS is in [MTU and MSS](mtu_mss_values.md).

**Offloads.** NICs and the kernel group and segment packets in hardware (TSO, GSO, GRO). They improve throughput and reduce CPU, but change what `tcpdump` and the counters show (you will see "packets" larger than the MTU).

```bash
# See which offloads are active
ethtool -k eth0

# Disable one for a specific test (lost on reboot)
sudo ethtool -K eth0 gro off
```

Disabling offloads is not an optimisation, it is a diagnostic tool: use it to isolate whether a problem depends on them, then re-enable them. Feature names vary by driver.

## Methodology

1. **One variable at a time.** Change the MTU, or the encryption, or the number of flows; never several at once.
2. **Repeat.** Several runs per configuration at least; keep every one, not just the best.
3. **Isolate.** No other traffic on the link, no backups or updates in the background. With virtual machines, pin which host runs each end.
4. **Warm up.** The first run may include TCP slow start, ARP caches or tunnel setup; discard it or ignore the first seconds.
5. **Measure both directions** (`-R`), UDP and TCP, one and several flows.
6. **Record the context**: versions, MTU, offloads, CPU, time. A result without context cannot be reproduced.
7. **Measure CPU too.** A tunnel that saturates one core is CPU-bound, not network-bound.
8. **Baseline first.** Measure the link without the VPN before measuring with it; the VPN's cost is the difference.

## Interpreting the results

| Observation | Likely reading |
|---|---|
| One flow performs poorly and `-P 4` much better | Limited by a single flow (TCP window, high RTT or one core), not by the link |
| Low throughput and CPU at 100 % on one core | CPU bottleneck (encryption, softirq), not bandwidth |
| Many retransmits in `ss -ti` | Loss, overflowing buffer or wrong MTU on the path |
| Normal and `-R` directions very different | Asymmetric link, or different configuration at each end |
| UDP with loss from low rates | Link or queue problem; lower the rate to find the threshold |
| Good latency at idle and bad under load | Bufferbloat: long queues on some device |
| Results vary a lot between repetitions | External interference or lack of isolation; the data is not reliable |
| Improvement after disabling an offload | Interaction with the driver or the tunnel; investigate before leaving it that way |

The theoretical rate of a 10 Gb/s line is not what you will see with TCP: headers and encryption overhead reduce the useful value. Always compare against your baseline, not the vendor's number.

## Comparing VPNs and overlays

To compare WireGuard, Tailscale, NetBird or ZeroTier rigorously:

- Same pair of hosts, same underlying network and the same set of tests for all.
- With encryption on in every case, and without relay hops if you are measuring the direct path: on mesh solutions check whether the connection is direct or goes through a relay, because it changes the result entirely.
- Set the tunnel MTU explicitly (see [MTU and MSS](mtu_mss_values.md)) and repeat.
- Record latency, throughput in both directions and CPU, and store it in the format of the [vRouter Benchmark Template](vrouter_benchmark_template.md).

The Tailscale and NetBird comparative analysis is in [Tailscale vs NetBird: performance](tailscale_netbird_performance.md). The approximate figures that appeared in earlier versions of this page have been removed: they had no hardware or method attached and were not reproducible.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `iperf3: error - unable to connect to server` | Server stopped, port 5201 filtered or wrong IP | Start `iperf3 -s`, open the port, check the IP |
| Throughput far below link speed | Single flow, saturated CPU or wrong MTU | Try `-P`, watch CPU, check MTU |
| Small ping works, large transfers hang | Broken MTU/PMTUD on the path | `ping -M do -s` to locate the MTU and adjust |
| Loss on an `mtr` hop but not at the destination | ICMP rate limiting on that router | Ignore if the destination shows no loss |
| Different results every time | Concurrent traffic or no warm-up | Isolate, discard the first run, repeat |
| `ethtool` shows lower speed than expected | Faulty cable, port or negotiation | Change cable or port and measure again |
| Capture shows packets larger than the MTU | Offloads (GRO/TSO) in the capture | Normal; disable them only to diagnose |
| UDP with high loss when raising `-b` | Requested rate exceeds the link | Lower the rate until the loss disappears |

## Best practices

- Keep the raw result (`-J`) together with the date, versions and configuration.
- A test is reproducible if someone else can repeat it from your notes and get similar numbers.
- Measure before optimising and measure again afterwards; a change without a measurement is not an improvement.
- Do not leave the `iperf3` server exposed: open it only during the test and from the client IP.
- Do not run saturation tests on production networks without warning.
- Disable offloads only to diagnose, and re-enable them.
- Document the topology (what sits between the two nodes) as much as the results.

## References

- [iperf3 documentation](https://iperf.fr/iperf-doc.php)
- [WireGuard documentation](https://www.wireguard.com/)
- [Manual pages for ethtool, ss and mtr](https://man7.org/linux/man-pages/)
- Related pages: [MTU and MSS](mtu_mss_values.md), [Tailscale vs NetBird: performance](tailscale_netbird_performance.md), [vRouter Benchmark Template](vrouter_benchmark_template.md), [Network Troubleshooting](troubleshooting.md)
