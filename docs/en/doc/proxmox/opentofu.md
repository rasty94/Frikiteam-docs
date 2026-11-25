---
title: "Proxmox as code with OpenTofu"
description: "Managing Proxmox VE VMs with OpenTofu and the bpg/proxmox provider: least-privilege API token, cloning cloud-init templates, several VMs with for_each, remote state, drift and importing existing VMs."
keywords: "proxmox, opentofu, terraform, bpg/proxmox, cloud-init, api token, pveum, for_each, import, drift, infrastructure as code"
tags: ['proxmox', 'terraform', 'automation', 'virtualization']
updated: 2026-11-25
difficulty: intermediate
estimated_time: 30 min
category: Virtualization
status: published
last_reviewed: 2026-11-25
prerequisites:
  - "[Proxmox VE](proxmox_base.md)"
  - "[Cloud-init templates in Proxmox](cloud_init_templates.md)"
  - "[Terraform & OpenTofu — Infrastructure as Code](../terraform/terraform_base.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Proxmox as code with OpenTofu

## The problem

You have a well-built cloud-init template, and creating a new VM takes two minutes: right click, "Clone", change the name, adjust CPU and memory, set the IP in the Cloud-Init tab and start it. The trouble starts with the fifth VM: you no longer remember which IP each one got, one of them has 4 GB because "it was a test", and rebuilding the lab after reinstalling the node means repeating everything from memory.

With OpenTofu, your VMs become a text file in Git. You say how many you want and what they look like, `tofu plan` shows you what will change before touching anything, and `tofu apply` does it. If someone changes a VM by hand, the next `plan` gives it away.

!!! warning "Not yet tested in the homelab"
    Everything here has been checked against the official documentation of the `bpg/proxmox` provider (v0.123.1), OpenTofu (v1.13.10) and the Proxmox VE API, as of 2026-11-25. **It has not been run on a machine yet.** If something fails, open an erratum on GitHub and I will fix it.

## 📋 Table of Contents

- [What you need](#what-you-need)
- [Least-privilege user and token](#least-privilege-user-and-token)
- [Configuring the provider](#configuring-the-provider)
- [One VM cloned from the template](#one-vm-cloned-from-the-template)
- [Several VMs with for_each](#several-vms-with-for_each)
- [Remote state](#remote-state)
- [plan, apply and destroy](#plan-apply-and-destroy)
- [Drift: when someone touches the VM by hand](#drift-when-someone-touches-the-vm-by-hand)
- [Importing existing VMs](#importing-existing-vms)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## What you need

- **Proxmox VE 9.x.** The provider declares full support for 9; 8 works "with some limitations" and is not a testing priority.
- **OpenTofu 1.10 or later.** The provider asks for 1.6+, but the native S3 locking used further down (`use_lockfile`) arrived in 1.10. The latest published release is 1.13.10.
- **A cloud-init template** already created on the node. How to build one is in [Cloud-init templates in Proxmox](cloud_init_templates.md); here it is assumed to be VM `9000` on node `pve`.
- **TLS 1.3 on the API.** It is the provider's default minimum; if your endpoint does not offer it, there is the `min_tls` argument.

!!! note "Two families of names in the provider"
    The provider is renaming its resources from `proxmox_virtual_environment_*` to short names (`proxmox_cloned_vm`, `proxmox_vm`…). For VMs, the short names are still marked experimental (`proxmox_vm` literally says "DO NOT USE") and `proxmox_cloned_vm` does not manage cloud-init. The stable resource for cloning with cloud-init is still **`proxmox_virtual_environment_vm`**, which is the one used here. Check the changelog before upgrading.

## Least-privilege user and token

The provider documentation suggests a role with almost fifty privileges and warns that it is "only an example, likely too permissive". Cloning, configuring, starting and deleting VMs needs far less. The list comes from the permission checks declared by the Proxmox API itself:

| API operation | Privilege |
|---|---|
| Clone (`POST /qemu/{vmid}/clone`) | `VM.Clone` on the template, `VM.Allocate` on the new VM, `Datastore.AllocateSpace` on the storage and `SDN.Use` on the bridge |
| Change configuration (`/qemu/{vmid}/config`) | `VM.Config.*` depending on what you change (`CPU`, `Memory`, `Disk`, `Network`, `Cloudinit`, `Options`…) |
| Read the configuration | `VM.Audit` |
| Start and shut down | `VM.PowerMgmt` |
| Delete the VM | `VM.Allocate` |
| Read IPs from the QEMU agent | `VM.GuestAgent.Audit` |

On top of that, the provider adds a warning: without `SDN.Audit` or `SDN.Use`, Proxmox hides bridges when listing the node network and some reads fail with "interface not found".

In the node shell:

```bash
# User in the pve realm (no system account)
pveum user add tofu@pve --comment "OpenTofu"

# Role with what is needed to clone and manage VMs
pveum role add TofuVM --privs "VM.Allocate VM.Clone VM.Audit VM.PowerMgmt \
VM.Config.CPU VM.Config.Memory VM.Config.Disk VM.Config.Network VM.Config.Cloudinit \
VM.Config.Options VM.Config.HWType VM.Config.CDROM VM.GuestAgent.Audit \
Datastore.AllocateSpace Datastore.Audit SDN.Use SDN.Audit Sys.Audit"

# Token with separated privileges (the default)
pveum user token add tofu@pve provider --privsep 1

# With privsep, the effective permission is the intersection of user and token:
# both need it
pveum acl modify / --users tofu@pve --roles TofuVM
pveum acl modify / --tokens 'tofu@pve!provider' --roles TofuVM
```

`token add` shows the secret **only once**. The value the provider uses is `tofu@pve!provider=<secret>`.

!!! tip "Narrowing it further"
    Granting the role on `/` is the easy way. If the node shares space with VMs OpenTofu must not touch, put the managed VMs in a pool and grant `VM.Allocate` on `/pool/<pool>`: the clone API accepts it as an alternative to `/vms/{newid}`. And if `apply` returns a 403 naming a privilege, add that one and only that one.

There are operations Proxmox reserves for `root@pam` that **no token** can perform, not even a root one: `hookscript`, CPU architecture, PCI/USB passthrough without a mapping, or `initialization.upgrade`. If you need them, the provider docs explain the `ssh.root_ticket` option; the configuration in this article does not need it.

## Configuring the provider

```hcl
# versions.tf
terraform {
  required_version = ">= 1.10"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.123.0" # 0.123.x; before 1.0 every minor can break
    }
  }
}
```

```hcl
# provider.tf
provider "proxmox" {
  endpoint = var.pve_endpoint # https://pve.lan:8006/  (without /api2/json)
  insecure = var.pve_insecure # true only with a self-signed certificate
  # api_token is read from PROXMOX_VE_API_TOKEN
}

variable "pve_endpoint" {
  type = string
}

variable "pve_insecure" {
  type    = bool
  default = false
}
```

```bash
export PROXMOX_VE_API_TOKEN='tofu@pve!provider=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
tofu init
```

The token never goes into a `.tf` file or a versioned `.tfvars`. No `ssh` block: cloning, configuring and deleting VMs goes entirely through the API. SSH is only needed to upload *snippets* (for example, your own `user-data` with `proxmox_virtual_environment_file`) or to import disks from a local path.

## One VM cloned from the template

```hcl
# vm.tf
resource "proxmox_virtual_environment_vm" "web" {
  name      = "web01"
  node_name = "pve"
  vm_id     = 201
  tags      = ["tofu", "web"]

  clone {
    vm_id = 9000 # the cloud-init template
    full  = true
  }

  cpu {
    cores = 2
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = 2048
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 20
  }

  network_device {
    bridge = "vmbr0"
  }

  agent {
    enabled = true # only if the template starts qemu-guest-agent
  }

  initialization {
    ip_config {
      ipv4 {
        address = "192.168.1.201/24"
        gateway = "192.168.1.1"
      }
    }

    dns {
      servers = ["192.168.1.1"]
    }

    user_account {
      username = "admin"
      keys     = [trimspace(file("~/.ssh/id_ed25519.pub"))]
    }
  }
}
```

Three details from the documentation that bite if you do not know them:

1. **The clone inherits everything from the template**, disks included. But if you change a disk attribute (here, `size`), the provider applies its defaults to the rest (`discard`, `cache`, `aio`…) unless you declare them. If the template has `discard=on`, set it in the `disk` block too.
2. **The QEMU agent is inherited as well.** If the template has it enabled and you omit the `agent` block, the provider will wait for the agent for up to 15 minutes on every `apply` and every `refresh`. Always declare it explicitly, `true` or `false`.
3. **`local-lvm` is the default storage** for the cloud-init disk (`initialization.datastore_id`). If your node does not have it, set it by hand.

`user_account` and `user_data_file_id` are mutually exclusive: either a simple user and keys, or a full `user-data` uploaded as a snippet (and then you do need SSH).

## Several VMs with for_each

Copying the previous block three times is exactly what you wanted to avoid. With `for_each` over a map, each VM is an entry:

```hcl
# vms.tf
locals {
  vms = {
    web01 = { id = 201, ip = "192.168.1.201", cores = 2, memory = 2048 }
    web02 = { id = 202, ip = "192.168.1.202", cores = 2, memory = 2048 }
    db01  = { id = 210, ip = "192.168.1.210", cores = 4, memory = 8192 }
  }
}

resource "proxmox_virtual_environment_vm" "vm" {
  for_each = local.vms

  name      = each.key
  node_name = "pve"
  vm_id     = each.value.id
  tags      = ["tofu"]

  clone {
    vm_id   = 9000
    retries = 3 # Proxmox sometimes times out with several clones at once
  }

  cpu {
    cores = each.value.cores
  }

  memory {
    dedicated = each.value.memory
  }

  network_device {
    bridge = "vmbr0"
  }

  agent {
    enabled = true
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${each.value.ip}/24"
        gateway = "192.168.1.1"
      }
    }

    user_account {
      username = "admin"
      keys     = [trimspace(file("~/.ssh/id_ed25519.pub"))]
    }
  }
}

output "ips" {
  value = { for k, v in proxmox_virtual_environment_vm.vm : k => v.ipv4_addresses }
}
```

Why `for_each` and not `count`: with `count`, the VMs are `vm[0]`, `vm[1]`, `vm[2]`; remove the first one from the list and OpenTofu will want to recreate the other two because their index changed. With a map, the address is `vm["web02"]` and removing `web01` only destroys `web01`.

`ipv4_addresses` is filled in by the QEMU agent: with `agent.enabled = false` it is empty. And if you do not set `vm_id`, Proxmox assigns the next free one; setting it makes the VM recognisable outside OpenTofu and makes it easier to import again if you lose the state.

## Remote state

The state holds the mapping between `proxmox_virtual_environment_vm.vm["web01"]` and the real VM 201, plus the attributes it read, including passwords if you put them in `user_account`. Everything explained in [State backend and migration](../terraform/terraform_state.md) applies here: out of Git, encrypted and locked.

In a homelab, the usual choice is your own S3-compatible storage:

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket = "tofu-state"
    key    = "proxmox/homelab.tfstate"
    region = "us-east-1" # required even if the service ignores it

    endpoints = {
      s3 = "https://s3.lan:9000"
    }

    use_path_style              = true
    use_lockfile                = true
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
  }
}
```

`use_lockfile` locks with conditional writes (`If-None-Match`) in the bucket itself, without DynamoDB. Check that your S3-compatible service supports them before trusting the lock. Credentials, as always, via `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

## plan, apply and destroy

```bash
tofu fmt -check
tofu validate
tofu plan -out=tfplan      # review what is created, changed or destroyed
tofu apply tfplan          # apply exactly that plan

# A single VM (for emergencies, not as a routine)
tofu apply -replace='proxmox_virtual_environment_vm.vm["web02"]'

# See what would be deleted before deleting it
tofu plan -destroy
tofu destroy
```

Watch the symbol next to each resource in the `plan`: `~` is an in-place change, `-/+` is **destroy and recreate**. For a VM, recreating means losing the disk. One example the documentation itself gives: changing `node_name` recreates the VM unless you set `migrate = true`, which migrates it. Read the whole plan before typing `yes`.

For VMs that must not disappear because of an editing mistake, `lifecycle { prevent_destroy = true }` makes the `plan` fail instead of proposing the deletion.

## Drift: when someone touches the VM by hand

If you raise the memory from the web interface, the next `tofu plan` will propose going back to the value in the code. That is *drift*. To see it without mixing it with your own changes:

```bash
tofu plan -refresh-only    # only what changed outside
tofu apply -refresh-only   # accept reality into the state, without touching the VM
```

Then you decide: either you bring the change into the code, or you let the next `apply` revert it.

Some drift is not real. The provider documentation warns about one in particular: Proxmox **always sorts tags**, so if your `tags` list is not sorted you will see a never-ending difference. Sort it or ignore it:

```hcl
  lifecycle {
    ignore_changes = [tags]
  }
```

Do not abuse `ignore_changes`: every attribute you ignore is an attribute you no longer manage.

## Importing existing VMs

VMs created by hand can move into OpenTofu without being recreated. The identifier the provider expects is `node/vmid`. With an `import` block (OpenTofu 1.6+), the import is reviewed in the `plan` like any other change:

```hcl
# import.tf
import {
  to = proxmox_virtual_environment_vm.legacy
  id = "pve/105"
}
```

```bash
# Generates a draft configuration from the real VM
tofu plan -generate-config-out=legacy.tf
```

`-generate-config-out` requires a file that does not exist and its format may change between versions: treat the result as a draft. Clean it up, remove whatever is just default values, and run `tofu plan` until it says there are no changes **before** the first `apply`. If the plan after importing proposes changes, applying it will modify the real VM.

For several at once, `import` accepts `for_each`:

```hcl
import {
  for_each = { web01 = 201, web02 = 202 }
  to       = proxmox_virtual_environment_vm.vm[each.key]
  id       = "pve/${each.value}"
}
```

Once the import has been applied, delete the `import` block: it no longer does anything. More on `import` and state in [State backend and migration](../terraform/terraform_state.md#importing-pre-existing-resources).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `403 ... Permission check failed` | A privilege is missing from the role or the token | Read which privilege it names and add it to the role; with `privsep 1`, ACL for the user **and** the token |
| `Permission check failed (user != root@pam)` | Attribute reserved for `root@pam` (`hookscript`, `arch`, `upgrade`…) | Remove the attribute or use `ssh.root_ticket` |
| `apply` or `refresh` take ~15 min | Agent enabled (or inherited from the template) with no `qemu-guest-agent` running | Install the agent in the template or set `agent { enabled = false }` |
| `interface not found` | The token lacks `SDN.Audit` or `SDN.Use` | Add both to the role |
| TLS error on connect | The endpoint does not offer TLS 1.3 | `min_tls` argument or a valid certificate |
| Difference in `tags` on every `plan` | Proxmox sorts tags | Sorted list or `ignore_changes = [tags]` |
| Timeout when creating several clones | Proxmox sometimes times out with simultaneous clones | `clone.retries` or `tofu apply -parallelism=2` |
| The cloned disk loses `discard` or another option | Touching the disk applies the provider defaults | Declare in `disk` everything that differs from the default |

## Best practices

- **One token per tool**, with `privsep` and an expiry date (`--expire`). If it leaks, you revoke it without touching the user.
- **Pinned provider version** with `~>` and `.terraform.lock.hcl` in Git. Before 1.0, a minor upgrade is read with the changelog open.
- **`for_each` with stable keys**, never `count` for VMs with their own name.
- **Explicit `vm_id`** on anything that matters: it makes re-importing and finding the VM in the interface easier.
- **Remote state with locking from day one**, and no secrets in `user_account` if you can avoid it: public SSH keys are not secret, passwords are.
- **Periodic `plan -refresh-only`** to learn about drift before an `apply` silently reverts it.
- **`prevent_destroy`** on VMs that hold data.

## References

- [bpg/proxmox provider — documentation](https://registry.terraform.io/providers/bpg/proxmox/latest/docs) · [Repository and releases](https://github.com/bpg/terraform-provider-proxmox/releases)
- [`proxmox_virtual_environment_vm` resource](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_vm)
- [Proxmox VE — user and permission management (pveum)](https://pve.proxmox.com/pve-docs/pveum.1.html) · [API viewer](https://pve.proxmox.com/pve-docs/api-viewer/)
- [OpenTofu — import block](https://opentofu.org/docs/language/import/) · [s3 backend](https://opentofu.org/docs/language/settings/backends/s3/) · [Releases](https://github.com/opentofu/opentofu/releases)
- [Cloud-init templates in Proxmox](cloud_init_templates.md) · [Proxmox VE](proxmox_base.md)
- [Terraform & OpenTofu](../terraform/terraform_base.md) · [State backend and migration](../terraform/terraform_state.md)
