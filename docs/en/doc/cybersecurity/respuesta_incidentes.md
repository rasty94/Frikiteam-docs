---
title: "Incident Response: a practical playbook with TheHive and MISP"
description: "What to do once the alert has already fired. The NIST SP 800-61 lifecycle grounded in real infrastructure: evidence preservation, Kubernetes containment, case management with TheHive, threat intel with MISP and blameless post-mortems."
keywords: "incident response, thehive, misp, cortex, nist 800-61, forensics, memory dump, chain of custody, post-mortem, kubernetes, ioc"
date: 2026-07-19
tags: [cybersecurity, incident-response, thehive, misp, forensics, kubernetes, post-mortem]
draft: false
updated: 2026-07-19
difficulty: advanced
estimated_time: "18 min"
category: Cybersecurity
status: published
last_reviewed: 2026-07-19
prerequisites:
  - "Security monitoring deployed (Falco/Wazuh)"
  - "Administrative access to the infrastructure"
  - "Docker Compose and Kubernetes fundamentals"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

## You have the alert. Now what?

Everything else in this section builds defences. [Hardening](hardening_linux.md) reduces the attack surface, [Zero Trust](zero_trust.md) reduces the blast radius, [threat modelling](modelo_amenazas.md) tells you what to expect and [monitoring](monitoreo_seguridad.md) warns you. This document starts right after: it's 03:14, Falco has fired `Terminal shell in container` on a production pod and someone is staring at their phone with no idea what to do first. Incident response almost always fails for the same reason, and it isn't a lack of tools: people improvise under pressure, destroy the evidence in the first five minutes and nobody knows who has the authority to shut production down.

!!! danger "Mistake number one"
    Rebooting the compromised machine. It's the natural reflex ("maybe that fixes it") and it wipes RAM, live processes, open connections and often the malware itself if it only lived in memory. If you take one idea away from this guide, make it this: **do not reboot, do not power off, isolate**.

## The lifecycle according to NIST SP 800-61

```mermaid
graph LR
    A[Preparation] --> B[Detection and Analysis]
    B --> C[Containment]
    C --> D[Eradication]
    D --> E[Recovery]
    E --> F[Lessons Learned]
    F --> A
    B -.false positive.-> F
    D -.reinfection.-> B
    style A fill:#2d6a4f,color:#fff
    style F fill:#7f5539,color:#fff
```

The dotted arrows are the important ones. An incident is not a pipeline: if during eradication you discover the attacker had persistence somewhere else, you go back to analysis. And a false positive also produces lessons learned (usually: "tune that rule").

80% of the real effort sits in the phase nobody does: **preparation**. Improvising the rest is expensive.

## Preparation

### Severity matrix

Without a matrix agreed *beforehand*, every incident starts with an argument about whether it's serious. Define this and pin it in the channel:

| Level | Criteria | Response | Notification |
| --- | --- | --- | --- |
| **SEV1** | Customer data compromised, production down due to an attacker, active ransomware | Immediate, 24/7, whole team | Management + legal < 1 h |
| **SEV2** | Confirmed compromise with no known exfiltration, leaked production credential | < 30 min, wake the on-call | Security lead |
| **SEV3** | Confirmed suspicious activity in a non-production environment, crypto miner | Business hours, next working day | Team channel |
| **SEV4** | Anomaly with no confirmed impact, external scanning, alert pending validation | Backlog | None |

!!! warning "Escalate up, never down"
    When in doubt between SEV2 and SEV3, pick SEV2. Lowering the severity once you have more data is cheap; raising it three hours late is not.

### Roles

Three roles, and one person cannot hold two at once during a SEV1:

- **Incident Commander (IC)**: decides, does not execute. Their job is keeping the timeline, assigning tasks and deciding when to contain. If the IC has their hands in a `tcpdump`, nobody is coordinating.
- **Comms**: writes outward. Updates every 30 minutes even when there is no news ("still investigating" is a valid update). Shields the technical team from management's questions.
- **Ops / Investigator**: hands on the keyboard. One or several. Reports to the IC, does not make destructive decisions alone.

### Who decides to shut production down, and where you talk

This is decided cold, today, not at 03:14. The rule that works:

> The **Incident Commander** has unilateral authority to isolate (network policy, revoke credentials, cut traffic). For actions involving **data loss or a full service outage** they need confirmation from a second person on a short, named list, with a timeout: if nobody answers within 15 minutes, the IC proceeds alone and documents it.

The timeout is the critical part. Without it, people wait indefinitely for someone to pick up the phone while the attacker works.

The **war channel** is one dedicated channel per incident (`#inc-2026-07-19-miner`), not the general one. Everything relevant is written there even if it was said out loud — the transcript **is** the post-mortem timeline. No threads: they get lost. And if the compromise could affect the chat platform itself (corporate SSO is suspected), you move to a previously agreed out-of-band channel.

## Detection and analysis: triage

The first question is not "what do we do?" but "is this real?". A five-question triage flow:

1. **What exactly fired the alert?** Read the rule, not the title. `Terminal shell in container` is critical on an API pod and expected on a maintenance pod.
2. **Is there a legitimate change that explains it?** Cross-reference the timestamp with deployment history, maintenance windows and CI. Most "incidents" are a colleague debugging.
3. **Is it reproducible or a one-off?** A single event at 04:00 weighs more than 400 events during business hours.
4. **Does the origin make sense?** Source IP, service account, user-agent. A `kubectl exec` from a residential IP at 4 in the morning needs no further analysis.
5. **Is there correlated activity?** A lone alert is noise; three different alerts about the same host within ten minutes is an incident.

```bash
# Quick triage on a suspicious Linux host — READ ONLY
# None of these commands modify the system

# Processes with active network connections
ss -tunap | grep ESTAB

# Processes running from temporary paths (classic malware pattern)
ls -la /proc/*/exe 2>/dev/null | grep -E '/tmp|/dev/shm|/var/tmp'

# Recent and failed logins
last -20; lastb -20

# Scheduled tasks for every user
for u in $(cut -f1 -d: /etc/passwd); do crontab -l -u "$u" 2>/dev/null | sed "s/^/$u: /"; done

# Authorized SSH keys modified in the last 7 days, and recent SUID binaries
find /home /root -name authorized_keys -mtime -7 -ls 2>/dev/null
find / -perm -4000 -mtime -30 -type f 2>/dev/null
```

!!! note "Document as you triage"
    Every command you run and its output go into the case. Three hours from now you will not remember whether that process was already there before you touched anything.

## Evidence preservation: before you touch anything

This is the section people get wrong most often and the one you can least fix afterwards. Volatile evidence disappears in order of fragility (RFC 3227): registers and cache, RAM, network state, processes, disk, backups.

The golden rule: **isolating is not powering off**. Cut the network, leave the machine running. An isolated machine with intact memory is a goldmine; a powered-off machine is a disk image and a lot of unanswered questions.

### Disk snapshot before anything else

```bash
# --- Cloud (AWS): snapshot the volume without touching the instance ---
aws ec2 create-snapshot --volume-id vol-0a1b2c3d4e5f \
  --description "IR-2026-07-19 evidence preserved by @rasty94" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=incident,Value=INC-2026-0042},{Key=legal-hold,Value=true}]'

# --- On-prem / KVM: live snapshot ---
virsh snapshot-create-as --domain web-prod-01 \
  --name "INC-2026-0042" --atomic --disk-only --no-metadata

# --- Bit-for-bit forensic copy of an unmounted disk ---
# dc3dd hashes while it copies: no window between copying and verifying
dc3dd if=/dev/sdb of=/evidence/INC-2026-0042-sdb.img \
  hash=sha256 log=/evidence/INC-2026-0042-sdb.log

# Verify the integrity of the copy
sha256sum /evidence/INC-2026-0042-sdb.img
```

### Memory dump

RAM holds what disk does not: plaintext keys, processes with no file on disk, established connections, decrypted commands.

```bash
# Linux: AVML produces a Volatility-compatible dump without compiling modules
sudo ./avml /evidence/INC-2026-0042-mem.lime
sha256sum /evidence/INC-2026-0042-mem.lime | tee /evidence/INC-2026-0042-mem.sha256

# Containers: the process lives in the host namespace
crictl inspect <container-id> | grep -i '"pid"'   # real PID
sudo gcore -o /evidence/INC-2026-0042-pid <PID>   # memory of that process

# Preserve the container filesystem without running it
docker export <container-id> > /evidence/INC-2026-0042-fs.tar
```

!!! danger "Order matters: memory before disk"
    Every second that passes, memory changes. The disk is not going anywhere once you have cut the network. If you only have time for one thing, dump the memory.

### Chain of custody

If the incident could end up in a courtroom, with an insurer or in a regulatory notification, evidence without a chain of custody is worthless. You do not need a complex system: one versioned file per incident is enough.

```yaml
# /evidence/INC-2026-0042/custody.yaml
incident: INC-2026-0042
opened: 2026-07-19T03:14:22Z
evidence_owner: "@rasty94"

items:
  - id: EV-001
    type: memory_dump
    source: web-prod-01 (10.20.3.14)
    file: INC-2026-0042-mem.lime
    sha256: "a3f2...c91d"
    collected_by: "@rasty94"
    collected_at: 2026-07-19T03:22:10Z
    method: "avml v0.14 run from a read-only USB stick"
    storage: "S3 forensics-bucket, object-lock COMPLIANCE 365d"
    transfers:
      - {from: "@rasty94", to: "forensics-store", when: 2026-07-19T03:41:00Z,
         hash_verified_at_destination: true}

  - id: EV-002
    type: disk_snapshot
    source: vol-0a1b2c3d4e5f
    identifier: snap-9f8e7d6c
    collected_by: "@rasty94"
    collected_at: 2026-07-19T03:19:45Z
    storage: "AWS, tag legal-hold=true"
```

Three rules that make this actually worth something: **hash immediately** after collection and verify the hash at the destination after every transfer; use **immutable storage** (S3 object-lock, WORM, or at minimum a bucket where operations has no delete permission); and **always work on copies** — the original is never mounted, never opened, never touched, and if you must mount it, `mount -o ro,noexec,nodev,noload`.

## Containment

Containing means cutting off the attacker's ability to act without destroying the evidence or, if it can be avoided, the service.

### Isolating a pod in Kubernetes

The right way is not deleting the pod (that destroys the evidence and the ReplicaSet recreates it). It is taking it out of service and locking it in:

```bash
# 1. Unhook it from the Service by changing its label — the ReplicaSet will
#    create a healthy replacement and the suspect stays alive but trafficless
kubectl label pod payments-7d9f-x2k4 -n prod app- quarantine=INC-2026-0042 --overwrite

# 2. Apply the quarantine network policy
kubectl apply -f quarantine-netpol.yaml

# 3. Verify it really is isolated
kubectl exec -n prod payments-7d9f-x2k4 -- timeout 5 curl -s https://example.internal || echo "isolated OK"
```

```yaml
# quarantine-netpol.yaml — a real deny-all: no egress, no ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: quarantine
  namespace: prod
spec:
  podSelector:
    matchLabels:
      quarantine: INC-2026-0042
  policyTypes:
    - Ingress
    - Egress
  # No ingress/egress rules = everything denied. For forensic access from a
  # jump host, add only: ingress with namespaceSelector {name: forensics}
```

!!! warning "The CNI must support egress"
    NetworkPolicies are only enforced by the network plugin. Calico and Cilium do; some older CNIs silently ignore egress rules. **Verify the isolation with step 3**, do not assume the YAML works. See [Kubernetes Security](kubernetes_security.md).

### Isolating a node

`cordon` is safe and always correct. `drain` **is not** during an incident: it moves workloads to other nodes, and if the compromise lives in an image or a DaemonSet, you have just spread it.

```bash
# Always: stop scheduling new workloads
kubectl cordon node-worker-07

# Mark it so nobody touches it by mistake
kubectl annotate node node-worker-07 incident=INC-2026-0042 do-not-touch=true

# Drain ONLY after confirming the compromise is confined to the node,
# and NEVER over pods that are still live evidence
kubectl drain node-worker-07 --ignore-daemonsets --delete-emptydir-data \
  --pod-selector='quarantine!=INC-2026-0042'
```

### Revoking credentials and rotating secrets

The order matters: **revoke the session first, then rotate the secret**. The other way round, the attacker keeps their session alive with the old token while you celebrate having rotated the key.

```bash
# --- AWS: cut existing sessions before touching the keys ---
# A deny with a time condition: invalidates the temporary credentials
# issued before this instant
aws iam put-user-policy --user-name deploy-bot \
  --policy-name IR-revoke-sessions \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*","Condition":{"DateLessThan":{"aws:TokenIssueTime":"2026-07-19T03:14:00Z"}}}]}'

aws iam update-access-key --user-name deploy-bot --access-key-id AKIA... --status Inactive

# --- Kubernetes: invalidate a ServiceAccount token ---
kubectl delete secret sa-token-payments -n prod
kubectl rollout restart deployment/payments -n prod

# --- SSH: revoke a specific key across the fleet ---
ansible all -m lineinfile -a \
  "path=/root/.ssh/authorized_keys regexp='AAAAB3NzaC1yc2EAAAA...' state=absent"

# --- Live sessions of a user on a host ---
pkill -KILL -u compromised_user
```

For rotating application secrets, the flow is already described in [Secrets Management](gestion_secretos.md) and [Secrets in GitOps](secrets_gitops.md). What is incident-specific: **rotate everything the compromised credential could read**, not just the credential. If the compromised pod mounted three secrets, that is three secrets rotated.

## TheHive: case management

During an incident, information scatters: screenshots in chat, hashes in a local `.txt`, the timeline in the IC's head. TheHive is an open-source security case management platform that centralises exactly that — cases, assignable tasks, observables (IoCs) and an automatic timeline. It is the difference between a post-mortem reconstructed from memory and one with real timestamps.

```yaml
# docker-compose.yml — TheHive 5 with Cassandra and Elasticsearch
services:
  cassandra:
    image: cassandra:4.1
    environment: [CASSANDRA_CLUSTER_NAME=thehive]
    volumes: [cassandra-data:/var/lib/cassandra]
    restart: unless-stopped

  elasticsearch:
    image: elasticsearch:8.14.3
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ulimits:
      memlock: {soft: -1, hard: -1}
    volumes: [es-data:/usr/share/elasticsearch/data]
    restart: unless-stopped

  thehive:
    image: strangebee/thehive:5.3
    depends_on: [cassandra, elasticsearch]
    ports: ["9000:9000"]
    environment: [JVM_OPTS=-Xms2g -Xmx2g]
    command: [--secret, "REPLACE_THIS_WITH_A_LONG_RANDOM_SECRET",
              --cql-hostnames, cassandra,
              --index-backend, elasticsearch, --es-hostnames, elasticsearch]
    volumes: [thehive-data:/opt/thp/thehive/data]
    restart: unless-stopped

volumes: {cassandra-data: , es-data: , thehive-data: }
```

!!! warning "This is not a production configuration"
    No TLS, no Elasticsearch authentication and a plaintext secret in the compose file. For production: TLS terminated at a reverse proxy, the secret pulled from your secrets manager and **verified backups** of Cassandra. A TheHive you lose takes your entire incident history with it.

### The model: cases, tasks, observables

- **Case**: an incident. It has a severity, a TLP (sharing traffic light), a status and a template.
- **Task**: an assignable unit of work inside the case ("dump memory of web-prod-01"). Each task carries a timestamped log — this is where the timeline comes from.
- **Observable**: a data point from the incident (IP, hash, domain, path). It is flagged as an IoC if it is an indicator of compromise, and TheHive warns you if it already appeared in an earlier case. That "we have seen this before" is the tool's greatest value.
- **Case templates**: one per recurring scenario (credential, miner, unauthorised access) with the tasks already defined. At 3 in the morning nobody remembers the 12 steps; with a template, you open the case and they are already there.

### Integration with Falco and Wazuh

Alerts from [security monitoring](monitoreo_seguridad.md) should create TheHive alerts automatically. Falco does it via Falcosidekick without writing any code:

```yaml
# Falco values.yaml — direct delivery to TheHive
falcosidekick:
  enabled: true
  config:
    customfields: "cluster:prod,env:production"
    webhook:
      address: "http://thehive:9000/api/v1/alert"
      customHeaders: "Authorization:Bearer ${THEHIVE_API_KEY}"
      minimumpriority: "warning"
```

For Wazuh, an integrator that translates the alert into TheHive's format:

```python
#!/usr/bin/env python3
# /var/ossec/integrations/custom-thehive.py
# Wazuh invokes it as: script <alert_file> <api_key> <hook_url>
import json, sys, urllib.request

alert = json.load(open(sys.argv[1]))
api_key, url = sys.argv[2], sys.argv[3]
rule, level = alert["rule"], alert["rule"]["level"]
srcip = alert.get("data", {}).get("srcip")

payload = {
    "type": "wazuh",
    "source": alert.get("agent", {}).get("name", "unknown"),
    "sourceRef": alert.get("id"),
    "title": f"[Wazuh {level}] {rule['description']}",
    "description": json.dumps(alert, indent=2)[:4000],
    # Wazuh uses levels 0-15; TheHive severity 1-4
    "severity": 4 if level >= 12 else 3 if level >= 10 else 2 if level >= 7 else 1,
    "tlp": 2,
    "tags": ["wazuh"] + rule.get("groups", []),
    "observables": [{"dataType": "ip", "data": srcip, "ioc": False}] if srcip else [],
}

urllib.request.urlopen(urllib.request.Request(
    url, data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
), timeout=10)
```

```xml
<!-- /var/ossec/etc/ossec.conf -->
<integration>
  <name>custom-thehive</name>
  <hook_url>http://thehive:9000/api/v1/alert</hook_url>
  <api_key>YOUR_API_KEY</api_key>
  <level>7</level>
  <alert_format>json</alert_format>
</integration>
```

!!! note "A threshold, not everything"
    `<level>7</level>` is not arbitrary: below 7 Wazuh generates hundreds of events a day. A TheHive with 400 untriaged alerts is exactly as useful as having no TheHive at all.

## MISP: threat intelligence

TheHive tells you what is happening in your own house. MISP tells you whether it has happened to anyone else. It is an open-source threat intelligence sharing platform: events with attributes (IPs, hashes, domains, YARA rules), classified with taxonomies and synchronisable with other organisations.

The practical use is twofold: **enrichment** (an IP shows up in your logs → does MISP know it? If it sits in an event from a ransomware campaign two weeks ago, your SEV3 just became a SEV1) and **contribution** (your incident's IoCs get published so others detect them sooner).

### Taxonomies and sharing levels

Taxonomies are controlled vocabularies for tagging. The two essential ones:

- **TLP** (Traffic Light Protocol): `tlp:red` never leaves the team, `tlp:amber` circulates inside the organisation, `tlp:green` within the community, `tlp:clear` is public. Tag **everything**; an IoC with no TLP ends up shared where it should not have been.
- **PAP** (Permissible Actions Protocol): what you can do with the indicator without tipping off the attacker. `pap:red` means you must not even resolve that domain from your network — the DNS query tells them you have spotted them.

```mermaid
graph LR
    F[Falco] --> TH[TheHive: alert]
    W[Wazuh] --> TH
    TH -->|triage| C[Case + observables]
    C --> CX[Cortex: analyzers]
    CX -->|IoC lookup| M[(MISP)]
    M -->|context: campaign, TTPs| C
    C -->|export confirmed IoCs| M
    M -->|sync| EXT[External communities]
    style TH fill:#1d3557,color:#fff
    style M fill:#6a040f,color:#fff
    style CX fill:#264653,color:#fff
```

### Cortex: the glue

TheHive does not query MISP directly: it does so through **Cortex**, an analyzer engine. You select an observable in the case, run the `MISP_2_1` analyzer and get back within seconds whether that indicator is already known and in what context.

```json
{
  "name": "MISP_2_1",
  "configuration": {
    "url": ["http://misp"], "key": ["YOUR_MISP_API_KEY"],
    "cert_check": [true], "name": ["MISP-internal"]
  },
  "rateLimit": { "count": 200, "duration": 3600 }
}
```

```bash
# Manual enrichment via the MISP API: do we know this IP?
curl -s -X POST http://misp/attributes/restSearch \
  -H "Authorization: YOUR_MISP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value":"203.0.113.44","type":"ip-dst","includeEventTags":true}' \
  | jq '.response.Attribute[] | {event_id, category, comment, tags: [.Tag[].name]}'
```

### Exporting your incident's IoCs

When the case closes, the observables flagged as IoCs are exported to MISP as a new event. In TheHive: *Case → Export → MISP*. Before you click, two checks: **that you are not exporting internal data** (paths with project names, internal hostnames and private IPs help nobody and describe you) and **that the TLP is correct** — by default, `tlp:amber` for anything coming out of one of your own incidents.

## Eradication and recovery

Eradicating means removing the attacker's presence; recovering means getting operational again. They get confused constantly, and that is why reinfections happen.

**Eradication** — it is not finished until you can answer how they got in. Identify the initial vector (without this, you rebuild the system and they walk back in through the same door), hunt for persistence in **every** place and not just where the alert fired (cron, systemd units, `authorized_keys`, webshells, modified container images, created ServiceAccounts, webhook rules) and rebuild from a clean image: a compromised host is not "cleaned", it is destroyed and redeployed.

**Recovery** — with conditions:

- Restore from a backup **predating the compromise**, and what counts as "predating" is decided by the timeline, not by intuition. If the attacker got in three weeks ago, yesterday's backup is compromised too.
- Monitor the restored system in more detail for at least two weeks: reinfections happen in the first few days.
- Restore in phases: a non-critical service first, verify, then the rest.

!!! danger "Do not close the incident when the service comes back"
    Service up is not incident closed. The incident closes when you know the vector, you have eradicated the persistence and you have done the post-mortem. Closing as soon as the site responds is how one incident becomes two.

## Blameless post-mortem

Blameless does not mean without accountability: it means assuming each person acted reasonably given the information they had at the time. If someone could wipe production with a single command, the failure is that the command was possible, not the person who typed it.

```markdown
# Post-mortem INC-2026-0042 — Crypto miner in the production cluster

**Severity:** SEV2 · **Duration:** 6 h 12 min · **Impact:** degradation across 3
services, no confirmed exfiltration
**IC:** @rasty94 · **Post-mortem date:** 2026-07-22 (< 5 working days)

## Executive summary
Three paragraphs maximum, readable by a non-technical person: what happened,
what impact it had, what has been done so it does not happen again.

## Timeline
Times in UTC. Exported from TheHive task logs.

| Time  | Event | Source |
|-------|-------|--------|
| 01:47 | First pod compromised (deduced after the fact) | kube-apiserver logs |
| 03:14 | Falco fires `Outbound connection to C2` | Falco alert |
| 03:19 | IC assigned, channel #inc-2026-0042 opened | Slack |
| 03:22 | Disk snapshot and memory dump completed | custody.yaml |
| 03:41 | Pod isolated with the quarantine network policy | kubectl audit |
| 05:30 | Vector identified: base image with an unpatched RCE | analysis |
| 07:59 | Service restored from a rebuilt image | ArgoCD |

## What happened?
Technical narrative. No individual names attached to mistakes: "the deployment
included an unscanned image", not "X deployed an unscanned image".

## Root cause analysis
Do not stop at the first cause. Five whys or similar:
- Why was there a miner? A pod was executing arbitrary code.
- Why? The image had a known RCE vulnerability.
- Why did it reach production? Scanning did not block the deployment.
- Why did it not block? It was set to warn-only so as not to slow releases.
- Why did it stay that way? Nobody revisited that temporary call from 8 months ago.

## What worked / what did not
Detection took 4 minutes: that is a rule someone wrote and it needs to be
maintained. Against us: 25 minutes to assign an IC (no automatic escalation)
and nobody knew where the pod isolation runbook lived.

## Actions
With an owner and a date. With no owner it is not an action, it is a wish.

| # | Action | Owner | Date | Status |
|---|--------|-------|------|--------|
| 1 | Trivy in blocking mode in the admission controller | @rasty94 | 2026-08-01 | In progress |
| 2 | Automatic on-call escalation after 10 min without ACK | @rasty94 | 2026-07-30 | Pending |
| 3 | Quarantine runbook linked from the Falco alert itself | @rasty94 | 2026-07-25 | Done |

## Open questions
Being honest beats inventing certainties: "we could not confirm whether there
was DB access between 01:47 and 03:14 because the audit log only retains 24 h".
```

Rules that make a post-mortem worth doing: **5 working days maximum** after closing (after that nobody remembers the details), **actions with an owner and a date** reviewed at the next retro, and **open internal publication** — a post-mortem only the security team reads teaches nobody else anything.

## Playbook 1: credential leaked in Git

**Typical detection**: a secret scanner in CI, a GitHub notification, or a third party emailing you.

```bash
# 1. REVOKE FIRST. The credential is considered compromised from the moment
#    of the commit, not from the moment you found out.
aws iam update-access-key --user-name $USER --access-key-id $KEY --status Inactive

# 2. Determine the exposure window: when it landed and whether it is still in HEAD
git log --all --oneline -S 'AKIAIOSFODNN7EXAMPLE' -- .
git log -1 --format='%aI %an %H' -S 'AKIAIOSFODNN7EXAMPLE'

# 3. Has it been used? This is the question that sets the severity.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAIOSFODNN7EXAMPLE \
  --start-time 2026-06-01 --query 'Events[].{t:EventTime,e:EventName,ip:CloudTrailEvent}'

# 4. Clean the history (only if the repo is private and you control every clone)
git filter-repo --replace-text <(echo 'AKIAIOSFODNN7EXAMPLE==>REDACTED')
```

!!! danger "Public repo: the history no longer matters"
    If the repository was public at any point, the credential is in third-party hands: there are bots scanning public commits within seconds. Rewriting the history is cosmetic. **The only things that count are revoking and auditing usage.**

**Severity**: SEV2 by default; SEV1 if CloudTrail shows usage from an unknown IP.
**Prevention**: secret scanning as a pre-commit hook and in CI (blocking), short-lived credentials via OIDC instead of static keys.

## Playbook 2: container running a crypto miner

**Typical detection**: sustained 100% CPU, Falco detecting connections to mining pools, a cloud bill through the roof.

```bash
# 1. Identify the pod and DO NOT delete it
kubectl top pods -A --sort-by=cpu | head -5

# 2. Preserve before containing
kubectl logs payments-7d9f-x2k4 -n prod --timestamps > /evidence/INC-0042-pod.log
kubectl get pod payments-7d9f-x2k4 -n prod -o yaml > /evidence/INC-0042-pod.yaml
crictl inspect $(crictl ps -q --name payments) > /evidence/INC-0042-runtime.json

# 3. Isolate (see the containment section) — do not delete, do not restart
kubectl label pod payments-7d9f-x2k4 -n prod app- quarantine=INC-2026-0042 --overwrite

# 4. Entry vector: was the image already compromised or did they get in later?
kubectl get pod payments-7d9f-x2k4 -n prod -o jsonpath='{.spec.containers[*].image}'
trivy image --severity CRITICAL,HIGH <that-image>

# 5. Look for spread: the same pattern in other pods
kubectl get pods -A -o json | jq -r '.items[] | select(.spec.containers[].image
  | contains("suspicious-image")) | "\(.metadata.namespace)/\(.metadata.name)"'
```

**Severity**: SEV3 if it is confined to a pod with no sensitive data; **SEV1 if the miner is the visible payload of a larger compromise** — a miner is often what they leave behind once they have done everything else. Never treat it as "just a miner" until you have ruled out data access.
**Prevention**: CPU `limits` on every pod, egress restricted by default, distroless images and blocking scanning in the admission controller.

## Playbook 3: unauthorised SSH access

**Typical detection**: Wazuh alerting on a login from an unusual geography, a new key in `authorized_keys`, an out-of-hours login.

```bash
# 1. DO NOT kill the session yet: first look at what they are doing
who; ps -u <user> -f; ss -tunap | grep <suspicious_ip>

# 2. Capture that session's traffic in parallel (to a file, for the case)
timeout 120 tcpdump -i any -w /evidence/INC-0042.pcap host <suspicious_ip> &

# 3. Dump memory BEFORE cutting (see the evidence section)
sudo ./avml /evidence/INC-0042-mem.lime

# 4. Now yes: cut access and kill sessions
iptables -I INPUT 1 -s <suspicious_ip> -j DROP
pkill -KILL -u <user>

# 5. Hunt for persistence — the attacker almost always leaves something
grep -rn 'ssh-' /home/*/.ssh/authorized_keys /root/.ssh/authorized_keys
systemctl list-units --type=service --state=running --no-pager | grep -vf /etc/known-services.txt
find /etc/cron* /var/spool/cron -mtime -7 -ls
last -F | head -40

# 6. Scope: did they reach other hosts from this one?
grep -h 'Accepted' /var/log/auth.log* | awk '{print $9, $11}' | sort -u
```

**Severity**: SEV2 minimum. SEV1 if the access had root privileges or if there is evidence of lateral movement.
**Prevention**: SSH by key only and through a bastion, MFA, explicit `AllowUsers`, and the measures in [Linux Hardening](hardening_linux.md).

## The first 60 minutes

Print this. Stick it where the on-call can see it.

**0-5 min — Confirm and declare**

- [ ] Is the alert real? Apply the five triage questions
- [ ] Assign a severity (when in doubt, **go up**)
- [ ] Declare the incident and open the channel `#inc-YYYY-MM-DD-name`
- [ ] Name the Incident Commander out loud. With no IC there is no managed incident

**5-20 min — Preserve**

- [ ] **DO NOT reboot. DO NOT power off. DO NOT delete the pod.**
- [ ] Disk snapshot of every affected system
- [ ] Memory dump of the compromised hosts
- [ ] Hash and record everything in `custody.yaml`
- [ ] Export logs at risk of rotation (auth.log, apiserver audit log)

**20-35 min — Contain**

- [ ] Isolate at the network level without powering off: network policy, security group, `iptables DROP`
- [ ] Revoke active sessions, **then** rotate credentials
- [ ] Verify the isolation actually works (egress test)
- [ ] Check whether the compromise has spread to other hosts or pods

**35-50 min — Document and assess**

- [ ] Open the case in TheHive using the scenario template
- [ ] Load the observables (IPs, hashes, domains) and flag them as IoCs
- [ ] Enrich with MISP via Cortex: a known campaign?
- [ ] Determine whether there is a notification obligation (GDPR: 72 h from awareness)

**50-60 min — Communicate and plan**

- [ ] First Comms update to management
- [ ] Decide: do we keep observing or do we eradicate now?
- [ ] If this is going long, organise shifts **now**. Nobody investigates well at hour 9
- [ ] Set the time of the next update and announce it

!!! note "The 4-hour rule"
    If an incident runs past 4 hours, relieve the IC. Exhaustion produces destructive, irreversible decisions, and the handover forces a briefing that often surfaces what the first IC had overlooked.
