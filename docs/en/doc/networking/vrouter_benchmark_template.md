# vRouter benchmark template

Use this reusable template to compare vRouters under equivalent conditions and make metric-driven decisions.

## 1) Scenario metadata

- Platform under test: `OPNsense | pfSense | MikroTik CHR | VyOS`
- Hypervisor: `Proxmox | KVM | VMware | Hyper-V | other`
- VM CPU/RAM: `____ vCPU / ____ GB`
- Virtual NIC type: `virtio | e1000 | vmxnet3 | other`
- Software version: `________`
- Test date: `YYYY-MM-DD`
- Topology: `intra-site | site-to-site | hybrid`

## 2) Pre-test setup

- Same base hardware for all platforms.
- Same `iperf3` and measurement tool versions.
- No external workload during benchmark window.
- Consistent MTU on both endpoints.
- NTP synchronized for event correlation.

## 3) Recommended test commands

Benchmark server:

```bash
iperf3 -s
```

TCP client (3 runs):

```bash
iperf3 -c <server_ip> -P 4 -t 30
```

UDP client (jitter/loss):

```bash
iperf3 -c <server_ip> -u -b 300M -t 30
```

Latency and packet loss:

```bash
ping -c 100 <server_ip>
mtr -rwzc 100 <server_ip>
```

## 4) Result capture table

| KPI | Run 1 | Run 2 | Run 3 | Average | Target | Pass/Fail |
| --- | ----- | ----- | ----- | ------- | ------ | --------- |
| L3 throughput (Gbps) | | | | | >= 1.0 | |
| VPN throughput (Mbps) | | | | | >= 300 | |
| Added latency (ms) | | | | | <= 5 | |
| Packet loss (%) | | | | | <= 0.5 | |
| Average CPU (%) | | | | | < 80 | |
| Failover time (s) | | | | | <= 30 | |

## 5) Failover test procedure

1. Keep continuous traffic running (`iperf3` or persistent ping).
2. Force primary link or peer failure.
3. Measure time until stable recovery.
4. Repeat 3 times and compute average.

## 6) Final acceptance criteria

- Accept platform if it meets at least:
  - 5/6 KPIs green.
  - No fail in session stability or failover.
  - No sustained CPU spikes above 90%.

## 7) Operational notes

- Issues observed: `________`
- Stabilization changes applied: `________`
- Pending risks: `________`
- Recommended decision: `adopt | conditional | reject`

## 8) Benchmark consistency rules

- Do not mix encrypted and non-encrypted results in one table.
- Keep packet size, parallelism and duration constant.
- Re-run benchmark after upgrades, driver changes or hypervisor changes.

## 9) Reference profiles (targets by environment)

| Profile | L3 throughput | VPN throughput | Added latency | Packet loss | Failover | Average CPU |
| ------- | ------------- | -------------- | ------------- | ----------- | -------- | ----------- |
| Homelab | >= 500 Mbps | >= 150 Mbps | <= 10 ms | <= 1.0% | <= 60 s | < 85% |
| SMB | >= 1 Gbps | >= 300 Mbps | <= 5 ms | <= 0.5% | <= 30 s | < 80% |
| ISP/WISP | >= 3 Gbps | >= 800 Mbps | <= 3 ms | <= 0.2% | <= 10 s | < 70% |

Recommendation:

- Start with the profile closest to your current environment and tighten targets in each iteration.

## 10) Common pitfalls and mitigations

| Symptom | Likely cause | Mitigation |
| ------- | ------------ | ---------- |
| Unstable throughput | CPU steal or noisy neighbors | Reserve resources, isolate host, rerun in controlled window |
| High UDP loss | MTU/MSS mismatch, queue saturation | Validate end-to-end MTU and tune queueing |
| Slow failover | Conservative timers or late detection | Tune HA/routing timers, validate link detection |
| Latency jitter spikes | Inconsistent offloading/NIC type | Standardize NIC model and offload settings |
| Excessive VPN CPU | No crypto acceleration or low parallelism | Enable acceleration where available, tune parallel streams |

## 11) Executive summary template

- Summary: `Platform ____ meets ____/6 KPIs and recommendation is ____.`
- Primary risk: `________`
- Secondary risk: `________`
- Immediate action (7 days): `________`
- Improvement action (30 days): `________`
- Final decision: `adopt | conditional | reject`

## 12) Benchmark exit criteria

- At least 2 time windows were tested (off-peak and peak).
- At least 3 runs per KPI and platform were executed.
- Exact platform configuration was documented.
- Evidence was attached (commands/output/charts).
- Decision was reviewed by NetOps/SecOps.
