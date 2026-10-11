---
title: "eBPF and Cilium: networking, security and observability in Kubernetes"
description: "What eBPF is and how Cilium uses it as a CNI: installation, kube-proxy replacement, L3/L4/L7 and FQDN policies, Hubble to debug blocked traffic, Tetragon and eBPF tools on the host."
keywords: "ebpf, cilium, hubble, tetragon, cni, kube-proxy, networkpolicy, ciliumnetworkpolicy, toFQDNs, bpftrace, bcc, kubernetes"
tags: ['ebpf', 'kubernetes', 'networking', 'observability']
updated: 2026-10-11
difficulty: advanced
estimated_time: 24 min
category: Containers
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Working Kubernetes cluster and kubectl (see Kubernetes base)"
  - "CNI, Services and NetworkPolicy concepts"
  - "Access to the nodes to check the kernel version"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# eBPF and Cilium: networking, security and observability in Kubernetes

## The problem

Your cluster works, until it stops working for no apparent reason. One pod cannot reach another and you do not know whether it is DNS, a `NetworkPolicy`, the `Service` or the node's `iptables` table. With kube-proxy in iptables mode that table grows with every Service and every endpoint; reading it with `iptables-save` is archaeology, and a `NetworkPolicy` that blocks traffic leaves no trace you can query.

eBPF changes where traffic is decided and observed: in the kernel, with structured per-connection data. Cilium is the CNI implementation that takes advantage of it: networking, Service load balancing, policies and observability (Hubble) with a single agent per node.

!!! note "What this covers and what it does not"
    This page treats Cilium as a **CNI and data plane**: installation, policies, Hubble and eBPF tools. The comparison of Cilium against Istio and Linkerd as a service mesh (mTLS, canary, overhead) lives in [Service Mesh](service_mesh.md) and is not repeated here.

## 📋 Table of Contents

- [eBPF in two paragraphs](#ebpf-in-two-paragraphs)
- [Requirements](#requirements)
- [Installing Cilium](#installing-cilium)
- [Replacing kube-proxy](#replacing-kube-proxy)
- [Network policies](#network-policies)
- [Observability with Hubble](#observability-with-hubble)
- [Runtime security with Tetragon](#runtime-security-with-tetragon)
- [eBPF outside Kubernetes](#ebpf-outside-kubernetes)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## eBPF in two paragraphs

eBPF lets you load small programs into the Linux kernel without recompiling it or writing a module. Before running, the kernel **verifier** analyses them and rejects those that could hang the machine (unbounded loops, out-of-range memory accesses), and then a JIT compiler translates them to native code. The programs hold no state of their own: they share data with each other and with user space through **maps** (hash tables, arrays, queues), which is where an agent like Cilium keeps, for example, the endpoint table or the policy rules.

Each program attaches to a **hook**, a point in the kernel where it runs when something happens. The ones that show up most in networking and observability are:

| Hook | Where it acts | Typical use |
|---|---|---|
| **XDP** | In the NIC driver, before the packet exists in the stack | Drop or redirect traffic at top speed (anti-DDoS, load balancing) |
| **tc** (traffic control) | On the ingress or egress of an interface, with the packet already built | Pod routing, policies, Service NAT |
| **kprobes** | Entry or exit of almost any kernel function | Ad-hoc diagnostics; depends on the kernel version |
| **tracepoints** | Stable points the kernel declares explicitly | Tracing system calls and events in a portable way |

The reason it replaces iptables in the datapath is cost, not fashion. An iptables chain is evaluated **rule by rule**, so per-packet time and update time grow with the number of Services and rules. With eBPF the decision is a hash map lookup, with a cost practically independent of cluster size, and pod-to-pod traffic can skip stack layers that iptables forces it through.

## Requirements

!!! warning "Depends on the kernel"
    Cilium needs a kernel with sufficient eBPF support, and each feature (kube-proxy replacement, WireGuard encryption, `bpf host routing`, Egress Gateway) requires a different minimum version. There is no single figure valid for everything: check the requirements table for the Cilium version you are going to install and compare it with `uname -r` on **every node**. Current server distributions usually meet the basics; the old kernels of some cloud images or NAS devices do not.

Check the version with `uname -r` on every node, and that `CONFIG_BPF`, `CONFIG_BPF_SYSCALL` and `CONFIG_BPF_JIT` are enabled in the kernel configuration (`/boot/config-$(uname -r)` or `/proc/config.gz`, depending on the distribution).

Also, Cilium is the cluster's **only CNI**: it is not installed on top of Flannel or Calico, the previous one must be disabled first. On k3s, for example, the server is started with `--flannel-backend=none --disable-network-policy`.

## Installing Cilium

The `cilium` CLI is the shortest route for a homelab; Helm is better with GitOps, because the values live in a versioned file.

### With the CLI

```bash
cilium install
cilium status --wait
```

`cilium status --wait` waits until the agent (DaemonSet), the operator and the other components are ready, and summarises their state per component. To really validate the network, the test suite deploys temporary pods in its own namespace and tests connectivity between nodes, to Services and to the outside world:

```bash
cilium connectivity test
```

It takes several minutes; if only some external-access test fails, first check whether the cluster has internet access.

### With Helm

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update

helm install cilium cilium/cilium \
  --namespace kube-system \
  --values cilium-values.yaml
```

A minimal `cilium-values.yaml`, with Hubble enabled:

```yaml
# cilium-values.yaml
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

!!! warning "Depends on the version"
    Helm value names and CLI flags change between minor versions (see the next section). Pin the version with `--version` in Helm, and before upgrading read the *upgrade notes* of the target version, not those of the latest stable.

## Replacing kube-proxy

Cilium can take over Service load balancing (ClusterIP, NodePort, LoadBalancer) with eBPF and leave kube-proxy with nothing to do. This gives the biggest performance benefit, but it has a trap: without kube-proxy, the Cilium agent cannot use the `kubernetes` Service to reach the API server, because that Service would be implemented by Cilium itself. You must give it **the real address of the API server**.

```bash
cilium install \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=192.168.1.10 \
  --set k8sServicePort=6443
```

The Helm equivalent is the same trio of values under `kubeProxyReplacement`, `k8sServiceHost` and `k8sServicePort`. Use the IP or DNS name of a stable API server endpoint (the load balancer VIP if you have several control planes), not that of a single node.

!!! warning "Depends on the version"
    The value of `kubeProxyReplacement` has changed: old versions accepted strings such as `strict`, `partial` or `disabled`, and current ones use booleans (`true` / `false`). With the wrong value the agent fails to start or silently ignores your intent. Check the Helm reference for **your** version.

So that kube-proxy does not compete with Cilium, it has to be removed from the cluster: with kubeadm it is skipped at `init` (or its DaemonSet and ConfigMap are deleted) and on k3s the server is started with `--disable-kube-proxy`. Verify the result from the agent:

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep KubeProxyReplacement
```

The diagnostic binary inside the agent pod is called `cilium-dbg` in recent versions and `cilium` in earlier ones; do not confuse it with the `cilium` CLI on your machine.

## Network policies

Cilium enforces the standard Kubernetes `NetworkPolicy` (L3/L4: pods, namespaces, CIDRs and ports) and adds its own CRD, `CiliumNetworkPolicy`, for what the standard cannot express: L7 rules and destinations by DNS name. General policy and RBAC theory is in [Kubernetes Security](../cybersecurity/kubernetes_security.md); here only what is specific to Cilium.

| Capability | `NetworkPolicy` | `CiliumNetworkPolicy` |
|---|---|---|
| Selection by pod, namespace and CIDR | Yes | Yes |
| L4 ports and protocols | Yes | Yes |
| HTTP rules (method, path) | No | Yes (Envoy proxy on the node) |
| Egress to a domain (`toFQDNs`) | No | Yes |

### Default-deny and egress to a domain

A namespace without policies allows everything. The right pattern is to deny everything and open only what is needed. First the *default-deny* with the standard `NetworkPolicy`, which works on any CNI:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: apps
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

With that, not even DNS resolves. The following Cilium policy lets pods labelled `app: backend` query `kube-dns` and reach a single domain over HTTPS:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-egress
  namespace: apps
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
    # 1) Allow DNS and let Cilium observe the replies
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s:k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: ANY
          rules:
            dns:
              - matchPattern: "*"
    # 2) Egress only to this domain
    - toFQDNs:
        - matchName: "api.example.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

The DNS rule is not optional: Cilium learns which IPs `api.example.com` resolves to by intercepting DNS replies, and only then opens those IPs. Without the `rules.dns` block, `toFQDNs` has no source of addresses and traffic is dropped. Two caveats: `toFQDNs` filters on what DNS resolved, it does not inspect TLS content, and if the application caches IPs for longer than the TTL it can stop working when the domain changes address.

### L7 rules (HTTP)

To limit what a client can do on a service, not just which port it reaches:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-read-only
  namespace: apps
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          rules:
            http:
              - method: "GET"
                path: "/v1/.*"
```

The frontend can only do `GET` under `/v1/`; the proxy rejects the rest. `path` is a **regular expression**, not a prefix. HTTP rules divert that port through Envoy, with its latency cost: keep them for what justifies it.

## Observability with Hubble

Hubble is Cilium's observability layer: each agent records the flows it sees (source, destination, protocol, policy verdict) and Hubble Relay aggregates them for the whole cluster. It is enabled with the CLI or with the Helm values seen above:

```bash
cilium hubble enable --ui
```

To use the `hubble` CLI from your machine, open a tunnel to the Relay and check that it responds:

```bash
cilium hubble port-forward &
hubble status
```

### Querying flows

```bash
# Live traffic of a namespace
hubble observe --namespace apps --follow

# Only what is dropped by policy
hubble observe --verdict DROPPED

# Drops of a specific pod
hubble observe --pod apps/backend-7d9f --verdict DROPPED --follow
```

Each line shows source, destination, port, protocol and verdict (`FORWARDED` or `DROPPED`). L7 flows (HTTP, DNS) only appear if there is an L7 policy or L7 visibility enabled for those pods.

### Hubble UI

```bash
cilium hubble ui
```

It opens a service map per namespace with the traffic between them, and dropped flows marked separately. It is the quickest way to see at a glance that a service nobody calls (or that calls something unexpected) exists. If you expose it permanently, do it with authentication (SSO or VPN), like the rest of your [observability](../monitoring/observability_stack.md) dashboards.

### Debugging a policy that blocks

The workflow that repeats the most:

1. **Reproduce the failure** and, in parallel, run `hubble observe --namespace apps --verdict DROPPED --follow`.
2. **Read the drop**: the source, destination and port on the line are exactly what a rule is missing. If the destination is `kube-dns`, the DNS rule is missing; if it is an external IP, an egress rule or a `toFQDNs` is missing.
3. **Check which policy affects the pod**: `kubectl get cnp,netpol -n apps` and the pod's labels (`kubectl get pod --show-labels`). An `endpointSelector` with a mistyped label selects nothing and does not fail.
4. **Adjust the rule, reapply and repeat step 1**: the drop should disappear and a `FORWARDED` should appear.

## Runtime security with Tetragon

Network policies control who talks to whom; they do not see what a process does inside the container. **Tetragon** (a sibling project of Cilium, same eBPF ecosystem) fills that gap: it observes process executions, file accesses and network connections at kernel level, without modifying applications, and with `TracingPolicy` policies it can also **enforce** rules (for example, kill a process that opens a sensitive file). It is installed separately from Cilium and can be used with another CNI.

Start in observation mode: a policy that kills processes can take down a legitimate workload. The threat model, hardening and incident response are on other pages of the site and are not duplicated here:

- [Zero Trust](../cybersecurity/zero_trust.md): why identity-based segmentation is the basis of the policies above.
- [Kubernetes Security](../cybersecurity/kubernetes_security.md): RBAC, Pod Security and standard NetworkPolicies.
- [Security monitoring](../cybersecurity/monitoreo_seguridad.md): where to send Tetragon and Hubble events to alert on them.

## eBPF outside Kubernetes

You do not need a cluster to benefit from eBPF. On a Linux host (a node with a problem, a Proxmox VM) there are two families of diagnostic tools.

**bpftrace** is a one-liner language for tracing the kernel, similar to `awk`:

```bash
# Which process opens which file, live
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# System calls per process, summary on Ctrl-C
sudo bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'
```

**bcc-tools** is a collection of ready-made utilities, one per typical question:

| Tool | Answers |
|---|---|
| `execsnoop` | Which new processes are being launched? |
| `opensnoop` | Which files does each process open? |
| `tcpconnect` / `tcplife` | Who opens TCP connections and how long do they last? |
| `biolatency` | What is the disk latency like? |

!!! note "Names depend on the distribution"
    On Debian and Ubuntu the bcc binaries carry the `-bpfcc` suffix (`execsnoop-bpfcc`) and are installed with the `bpfcc-tools` package. On other distributions they are installed in `/usr/share/bcc/tools/`. Both tools need root and headers or BTF for the kernel you are running.

To inspect what the node itself has loaded (including Cilium), `bpftool prog list` and `bpftool map list` enumerate programs and maps. If what you want is a general view of host resources without eBPF, see [terminal monitoring](../linux/tui_monitoring.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pods stay in `ContainerCreating` after installing | Another CNI or its configuration was left in `/etc/cni/net.d/` | Remove the previous CNI, delete its files on every node and restart the pods |
| The Cilium agent fails to start with kube-proxy replaced | `k8sServiceHost` / `k8sServicePort` missing, or the `kubeProxyReplacement` value is not the one for your version | Set the real API server address and check the value in the reference for your version |
| After enabling `toFQDNs` all of the pod's traffic is dropped | The egress rule to `kube-dns` with `rules.dns` is missing | Add the DNS block from the example policy |
| `hubble observe` returns nothing | No port-forward to the Relay, or Relay disabled | `cilium hubble port-forward` and `hubble status` |
| I see no HTTP flows, only L3/L4 | L7 visibility only exists with an L7 policy or a visibility annotation | Apply a `CiliumNetworkPolicy` with `rules.http` to that port |
| A Cilium policy "does nothing" | The `endpointSelector` does not match any label | Compare with `kubectl get pod --show-labels` and look at the drop in Hubble |

## Best practices

- **A single CNI and a pinned version.** Read the *upgrade notes* before upgrading.
- **Enable Hubble from day one**, before writing policies. Writing rules from observed flows is safer than from memory.
- **Default-deny per namespace, with explicit DNS.** And keep the policies in Git next to the rest of your manifests.
- **Reserve L7 for where it adds value.** HTTP filtering goes through Envoy; for the rest, L3/L4 with identities is cheaper and enough.
- **If you only want mTLS and canary**, look at [Service Mesh](service_mesh.md) first: you may not need everything on this page.

## References

- [Kubernetes - Container orchestration](kubernetes_base.md)
- [Service Mesh in Kubernetes: Istio vs Linkerd vs Cilium](service_mesh.md)
- [Zero Trust](../cybersecurity/zero_trust.md)
- [Kubernetes Security](../cybersecurity/kubernetes_security.md)
- [Security monitoring](../cybersecurity/monitoreo_seguridad.md)
- [Observability stack](../monitoring/observability_stack.md)
- [Terminal monitoring](../linux/tui_monitoring.md)

### Official documentation

- [Cilium Docs](https://docs.cilium.io/en/stable/)
- [Cilium: system requirements](https://docs.cilium.io/en/stable/operations/system_requirements/)
- [Hubble](https://docs.cilium.io/en/stable/observability/hubble/)
- [Tetragon](https://tetragon.io/docs/)
- [bpftrace](https://github.com/bpftrace/bpftrace)
- [BCC tools](https://github.com/iovisor/bcc)
- [ebpf.io](https://ebpf.io/what-is-ebpf/)
