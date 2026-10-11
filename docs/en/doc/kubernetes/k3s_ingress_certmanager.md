---
title: "Kubernetes at Home: k3s, Ingress and cert-manager"
description: "From an empty k3s cluster to a service published with valid HTTPS: installation, bare-metal LoadBalancer (ServiceLB and MetalLB), Ingress with Traefik and Let's Encrypt certificates with cert-manager."
keywords: "k3s, kubernetes, homelab, ingress, traefik, ingress-nginx, metallb, servicelb, cert-manager, let's encrypt, clusterissuer, http-01, dns-01, helm"
tags: ['kubernetes', 'networking', 'helm']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 28 min
category: Containers
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Basic Kubernetes concepts (Pod, Deployment, Service)"
  - "A Linux server (VM or bare metal) with a fixed IP"
  - "A domain of your own with access to its DNS"
  - "Helm 3 installed on your machine"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Kubernetes at Home: k3s, Ingress and cert-manager

## The problem

You build a cluster, deploy your first application and the `LoadBalancer` `Service` stays at `<pending>` forever. You work around it with a `NodePort`, open `http://192.168.1.50:31874` and everything seems to work, until you want a domain name, a green padlock and more than one service listening on port 443. That is when you find out that in Kubernetes **none of that comes included**: IP allocation, HTTP routing and certificates are three separate pieces that a cloud provider gives you and that in your own rack you have to build yourself.

This page walks that whole path on k3s: an empty cluster, an IP for your services, an Ingress that routes by name and Let's Encrypt certificates that are issued and renewed on their own.

!!! note "What this covers and what it does not"
    This page covers **exposing and encrypting inbound traffic**. The basics of Pods, Deployments and Services are in [Kubernetes](kubernetes_base.md); application health in [Probes](probes.md); east-west traffic and mTLS in [Service Mesh](service_mesh.md). Persistent storage has its own page: [Kubernetes CSI](../storage/kubernetes_csi.md).

## 📋 Table of Contents

- [k3s: what it ships and how to install it](#k3s-what-it-ships-and-how-to-install-it)
- [Kubeconfig and additional nodes](#kubeconfig-and-additional-nodes)
- [Exposing services on bare metal](#exposing-services-on-bare-metal)
- [Ingress: routing by name](#ingress-routing-by-name)
- [cert-manager: automatic certificates](#cert-manager-automatic-certificates)
- [Publishing a service with HTTPS](#publishing-a-service-with-https)
- [Debugging certificate issuance](#debugging-certificate-issuance)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## k3s: what it ships and how to install it

k3s is a certified Kubernetes distribution packaged as a single binary and designed for modest resources. On single-server installs it uses SQLite instead of etcd (embedded etcd if you build a high-availability setup) and it ships with what an empty cluster needs to be useful:

| Component | Purpose | Disabled with |
|---|---|---|
| containerd | Container runtime | (cannot be disabled) |
| Flannel | Pod network (CNI) | `--flannel-backend=none` |
| CoreDNS | Cluster-internal DNS | `--disable coredns` |
| Traefik | Ingress controller | `--disable traefik` |
| ServiceLB | `LoadBalancer` implementation | `--disable servicelb` |
| local-path-provisioner | StorageClass backed by node directories | `--disable local-storage` |
| metrics-server | Metrics for `kubectl top` and HPA | `--disable metrics-server` |

!!! warning "Depends on the version"
    The list of bundled components, their versions and the exact flag names change between k3s versions. Check the table against the documentation for the version you install (`k3s server --help` lists the flags of yours) before automating anything.

### Installation

The official script installs the binary, creates the `k3s` systemd unit and starts the server:

```bash
curl -sfL https://get.k3s.io | sh -
```

It downloads and runs a script as root: read it first, and **pin the version** with `INSTALL_K3S_VERSION="<version>"` (before `sh -`) as soon as you leave the lab, so the same recipe gives you the same cluster.

Check that the service is up and the node registers:

```bash
sudo systemctl status k3s
sudo k3s kubectl get nodes
```

The node becomes `Ready` in a minute or two; k3s bundles its own `kubectl`.

### Disabling components

You can do it with flags at install time (`sh -s - --disable traefik --disable servicelb`) or, better, with a versionable file, `/etc/rancher/k3s/config.yaml`, before starting (or restarting `k3s` afterwards):

```yaml
# /etc/rancher/k3s/config.yaml
disable:
  - traefik
  - servicelb
write-kubeconfig-mode: "0644"
```

The keys mirror the flag names without the leading dashes. `write-kubeconfig-mode` opens the kubeconfig to other users: convenient in a single-admin homelab, a risk on a shared server.

## Kubeconfig and additional nodes

### Access from your laptop

k3s writes the administrator credentials to `/etc/rancher/k3s/k3s.yaml`, readable only by root by default. Copy it to your machine and replace the server address, which comes as `127.0.0.1`:

```bash
scp user@192.168.1.50:/etc/rancher/k3s/k3s.yaml ~/.kube/k3s-homelab.yaml
sed -i 's/127.0.0.1/192.168.1.50/' ~/.kube/k3s-homelab.yaml   # on macOS: sed -i ''
export KUBECONFIG=~/.kube/k3s-homelab.yaml
kubectl get nodes
```

If `scp` cannot read it because it is root-only, enable `write-kubeconfig-mode` (see above) or copy it with `sudo cat`. That kubeconfig grants full admin access: treat it like a password. If you reach the API through a domain name, add it with `tls-san` in `config.yaml` so it appears in the API certificate.

### Adding nodes

An agent needs the server URL (the API listens on 6443) and the token, which lives on the server:

```bash
# On the server
sudo cat /var/lib/rancher/k3s/server/node-token

# On the new node
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.50:6443 K3S_TOKEN="<token>" sh -
```

The script detects `K3S_URL` and installs the `k3s-agent` service. The agent must reach port 6443 on the server, and nodes must reach each other over the pod network's UDP port (Flannel with VXLAN uses 8472): if there is a firewall or VLANs between nodes, open them. The token grants access to the cluster: do not paste it into repositories or tickets.

## Exposing services on bare metal

A `LoadBalancer` `Service` does not create anything by itself: it asks a controller to do it. On AWS or GCP that controller belongs to the provider and returns a public IP. On your own cluster **nobody answers the request** and the `EXTERNAL-IP` field stays at `<pending>` forever. You have to install something that answers it.

| | ServiceLB (k3s) | MetalLB |
|---|---|---|
| Installation | Bundled | Helm or manifests |
| IP assigned | Those of the cluster nodes | One from a pool you define |
| Several services on 443 | No: the port belongs to the node, they collide | Yes: each service gets its own IP |

### ServiceLB: what you already have

For each `LoadBalancer` `Service`, ServiceLB starts a pod on every node that reserves the port on the host itself and forwards traffic to the service. The `EXTERNAL-IP` you see is the node's IP (or all of them). For a single-node cluster with Traefik listening on 80 and 443 it is enough and there is nothing to configure. Its limit is structural: two services cannot use the same port, because the port belongs to the node, not to the service.

### MetalLB in L2 mode

As soon as you want several service IPs or real failover, MetalLB assigns IPs from a range of your own. In L2 mode, one node answers the ARP requests (NDP on IPv6) for that IP and, if it goes down, another takes over. It is the right mode for a home network because it does not need a BGP router. Its cost: all traffic for an IP enters through a single node, so it is high availability, not load distribution. To compare with other options, see the [load balancer comparison](../networking/load_balancer_comparison.md).

First disable ServiceLB in k3s (the `servicelb` key under `disable`, as above), or both will fight over the `LoadBalancer` services. Then install MetalLB:

```bash
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm install metallb metallb/metallb --namespace metallb-system --create-namespace
```

Wait for the `metallb-system` pods to be `Running` and declare the range with two resources: the address pool and the L2 advertisement that publishes it.

```yaml
# metallb-pool.yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: homelab-pool
  namespace: metallb-system
spec:
  addresses:
    - 192.168.1.240-192.168.1.250
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: homelab-l2
  namespace: metallb-system
spec:
  ipAddressPools:
    - homelab-pool
```

```bash
kubectl apply -f metallb-pool.yaml
```

The range must belong to your LAN, **outside your router's DHCP pool** and with no IPs already in use. Without an `L2Advertisement`, MetalLB assigns the IP but does not announce it: the service will have an `EXTERNAL-IP` and still be unreachable.

!!! warning "Depends on the version"
    The `metallb.io/v1beta1` API group and the chart value names have changed between MetalLB versions. If `kubectl apply` rejects the resources, check the documentation for your installed version. Old versions configured everything with a ConfigMap, which current ones no longer read.

## Ingress: routing by name

With a single IP (or a handful) and many web services, you do not want one IP per service: you want a single entry point that looks at the host name and path and dispatches. That is an **Ingress controller** (the process that receives the traffic) plus `Ingress` resources (the rules). The Ingress controller is itself exposed through a `LoadBalancer` `Service`, and everything else hangs from it.

A standard `Ingress` resource (the full example is in [Publishing a service with HTTPS](#publishing-a-service-with-https)) works the same with any controller. It declares `ingressClassName`, one or more `host` entries, paths with their `pathType` and the target `Service`.

`ingressClassName` says which controller handles the rule; the available classes are listed with `kubectl get ingressclass`.

### Traefik (the k3s one) versus ingress-nginx

Traefik ships with k3s, is configured with CRDs (`IngressRoute`, `Middleware`) as well as annotations, and reloads its configuration dynamically. ingress-nginx does not ship with k3s, is configured with `nginx.ingress.kubernetes.io/*` annotations and has far more examples online.

For a homelab, **stick with Traefik**: it is already installed, understands standard `Ingress` and, if you later need middlewares (redirects, basic auth, rate limiting), you have them without changing controller. Its configuration and dashboard are covered in [Traefik](../traefik/traefik_base.md). To customize the Traefik that k3s ships (ports, logs, plugins) do not edit its manifests, which k3s regenerates: create a `HelmChartConfig` resource named `traefik` in the `kube-system` namespace with your `valuesContent`.

!!! warning "Depends on the version"
    The Kubernetes community's ingress-nginx project announced its retirement and a move to limited maintenance. Before choosing it for anything new, check its status in the repository. If you need a replacement, look at the other controllers and, above all, Gateway API.

### Gateway API: where this is heading

`Ingress` only covers host and path; everything else (headers, weights, TCP) ends up in controller-specific annotations, which are not portable. Gateway API is its successor (`GatewayClass`, `Gateway`, `HTTPRoute`): it separates roles and is portable across implementations. Traefik supports it and cert-manager can work with it. Today, for a homelab, `Ingress` is still the simplest and best documented option; it is worth knowing about because it is where the ecosystem is moving.

## cert-manager: automatic certificates

cert-manager is a controller that **requests, stores and renews certificates** as Kubernetes resources. You declare which certificate you want and from where; it talks to the authority (here, Let's Encrypt), passes the validation challenge and stores the result in a `Secret` that the Ingress consumes. TLS and ACME concepts in general are in [TLS Certificates](../networking/certificados_tls.md).

### Installation with Helm

The official chart installs the pods (controller, webhook, cainjector) and the CRDs, which are the new types (`ClusterIssuer`, `Certificate`...). **Without the CRDs nothing below works**:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

!!! warning "Depends on the version"
    The value that enables the CRDs was called `installCRDs=true` in old chart versions and is `crds.enabled=true` in current ones. Also pin the chart version with `--version`. If `helm install` silently ignores the value, `kubectl get crd | grep cert-manager` tells you whether the CRDs exist.

Check that the three pods are `Running` before moving on:

```bash
kubectl get pods -n cert-manager
```

The webhook takes a few more seconds to be ready; if the next `kubectl apply` fails with a webhook error, wait and retry.

### ClusterIssuer: staging and production

A `ClusterIssuer` is the cluster-wide definition of *who issues* the certificates. Create **two**: one against Let's Encrypt's test environment (the one shown) and one against the real one.

```yaml
# clusterissuers.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-staging-account-key
    solvers:
      - http01:
          ingress:
            ingressClassName: traefik
```

The production one is identical, changing `name` to `letsencrypt-prod`, `server` to `https://acme-v02.api.letsencrypt.org/directory` and the account Secret to `letsencrypt-prod-account-key`. Apply both:

```bash
kubectl apply -f clusterissuers.yaml
kubectl get clusterissuer
```

Both should show `READY` as `True`: it means the ACME account has been registered. `privateKeySecretRef` is the Secret where cert-manager stores that account's key (it creates it, you do not); the email receives expiry notices.

**Staging first, always.** Its certificates are signed by a CA no browser recognizes, but the flow is identical and its limits are far more generous. Production limits apply per registered domain, per duplicate certificate and per failed validation: a retry loop with a wrong configuration can lock you out for a few days. Check Let's Encrypt's rate limits page for current values.

### HTTP-01 versus DNS-01

The *solver* is the method by which you prove you control the domain.

| | HTTP-01 | DNS-01 |
|---|---|---|
| How it validates | Let's Encrypt requests a file over HTTP on port 80 | It looks up a TXT record at `_acme-challenge.<domain>` |
| Requirements | Cluster reachable from the Internet on 80, DNS pointing at it | API access to your DNS provider |
| Wildcard (`*.example.com`) | No | Yes |
| Cluster not exposed to the Internet | No | Yes |

**Use HTTP-01 if the cluster is reachable from outside** (port 80 forwarded to your MetalLB IP or to the node). You need **DNS-01** in two cases: wildcard certificates, or internal services with a public name that you never want to open to the Internet. An example with Cloudflare, one of the providers with a built-in solver (cert-manager supports others; see its documentation):

```yaml
# Inside spec.acme.solvers of the ClusterIssuer
solvers:
  - dns01:
      cloudflare:
        apiTokenSecretRef:
          name: cloudflare-api-token
          key: api-token
```

The `cloudflare-api-token` Secret must be in the `cert-manager` namespace (where the controller pods run, for a `ClusterIssuer`) and the token should be able to edit only the DNS zone needed, never the whole account.

## Publishing a service with HTTPS

Test with `traefik/whoami`, which returns request details. Use a domain of your own whose DNS points at your cluster's entry IP.

```bash
kubectl create deployment whoami --image=traefik/whoami --port=80
kubectl expose deployment whoami --port=80
```

And the Ingress, which ties together Traefik, the Service and cert-manager:

```yaml
# whoami-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whoami
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - whoami.example.com
      secretName: whoami-tls
  rules:
    - host: whoami.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: whoami
                port:
                  number: 80
```

```bash
kubectl apply -f whoami-ingress.yaml
kubectl get certificate
```

The `cert-manager.io/cluster-issuer` annotation is the only thing connecting the two halves: cert-manager sees the Ingress, reads the `tls` block and **creates a `Certificate` resource for you** that produces the `whoami-tls` Secret. When the `Certificate` becomes `READY: True`, Traefik starts serving that Secret on the given host.

To move to a real certificate, change the annotation to `letsencrypt-prod` and apply again. Since the Secret already exists with the staging certificate, delete it to force reissuance:

```bash
kubectl delete secret whoami-tls
```

From inside your LAN, the public domain resolves to your public IP and many routers do not loop traffic back inside (*hairpin NAT*). The fix is an internal DNS that resolves that name to the balancer's IP (split-horizon).

## Debugging certificate issuance

An ACME issuance is a chain of resources, each created by the previous one. When something fails, the error is at the link where the chain breaks:

| Resource | What it represents |
|---|---|
| `Certificate` | What you want: names, issuer, target Secret |
| `CertificateRequest` | The specific signing request sent to the issuer |
| `Order` | The ACME order placed with Let's Encrypt, one per request |
| `Challenge` | Each validation challenge (one per name) |

Walk it from top to bottom, stopping where the error shows up:

```bash
kubectl get certificate,certificaterequest,order,challenge -A
kubectl describe certificate whoami-tls
kubectl describe challenge -A
```

The `describe` of each resource carries the reason in the `Events` and `Status` sections. The `Challenge` is the most informative: its `Reason` is usually the literal error (connection refused, timeout, wrong response). If no child resource exists, the problem is further up: in the `ClusterIssuer` (`kubectl describe clusterissuer letsencrypt-staging`) or in the controller itself:

```bash
kubectl logs -n cert-manager deploy/cert-manager --tail=100
```

There is also `cmctl`, a separate project tool that summarizes the state of a `Certificate` and its chain (`cmctl status certificate <name>`).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Certificate` stuck at `READY: False` for a long time | The `Order` / `Challenge` chain is stuck | `kubectl describe challenge`: read `Reason` |
| `Challenge` in `pending` with a connection error or 404 | Let's Encrypt cannot reach port 80 on the cluster, or the solver Ingress is not being served | Check DNS, port 80 forwarding on the router and that the solver's `ingressClassName` matches your controller |
| `EXTERNAL-IP` at `<pending>` | No LoadBalancer controller (ServiceLB disabled and no MetalLB) | Install MetalLB or re-enable ServiceLB |
| MetalLB assigns an IP but it answers neither ping nor HTTP | Missing `L2Advertisement`, or the range overlaps with DHCP | `kubectl get l2advertisement,ipaddresspool -n metallb-system` |
| Browser warns of an untrusted certificate | It is a `letsencrypt-staging` certificate | Change the annotation to `letsencrypt-prod` and delete the Secret |
| The `Order` fails with a rate limit error | A Let's Encrypt limit has been reached | Wait; use staging to test; do not repeat production issuances |
| HTTP-01 fails with the cluster behind CGNAT | Port 80 of your public IP does not reach home | Use DNS-01 |

The workflow for a stuck certificate, from least to most effort: read the `Challenge`, confirm from **outside your network** (for example over mobile data) that `http://<domain>/.well-known/acme-challenge/` reaches the cluster, and only then delete the `Certificate` and its Secret to start over. If the problem is network-related, repeating the issuance will not fix it and may burn through your quota.

## Best practices

- **Staging for anything new.** Switch to production only once the whole flow has worked on staging. It is the only defense against rate limits.
- **Pinned versions**: k3s (`INSTALL_K3S_VERSION`), the MetalLB and cert-manager charts (`--version`). A `helm upgrade` without a pinned version is a surprise CRD upgrade.
- **Everything in Git.** `config.yaml`, the MetalLB pool, the `ClusterIssuer` and the Ingress resources are declarative YAML: infrastructure as code with no extra tooling.
- **DNS tokens with minimal scope** (one zone, TXT edit only) and rotated. The DNS token is the key to your domain.
- **A [service mesh](service_mesh.md) if you need internal mTLS**: the TLS on this page only protects the entry point.
- **Define [probes](probes.md)** on everything you publish: an Ingress routing to a pod that is not ready returns 502/503 errors to your users.

## References

- [k3s documentation](https://docs.k3s.io/)
- [Services, LoadBalancer and ServiceLB in k3s](https://docs.k3s.io/networking/networking-services)
- [MetalLB documentation](https://metallb.io/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [cert-manager documentation](https://cert-manager.io/docs/)
- [Let's Encrypt rate limits](https://letsencrypt.org/docs/rate-limits/)
- [Kubernetes](kubernetes_base.md) · [Probes](probes.md) · [Service Mesh](service_mesh.md)
- [TLS Certificates](../networking/certificados_tls.md) · [Traefik](../traefik/traefik_base.md) · [Kubernetes CSI](../storage/kubernetes_csi.md)
- [Load balancer comparison](../networking/load_balancer_comparison.md)
