---
title: "Proxmox como código con OpenTofu"
description: "Gestionar VMs de Proxmox VE con OpenTofu y el provider bpg/proxmox: token de API con permisos mínimos, clonado de plantillas cloud-init, varias VMs con for_each, estado remoto, drift e importación de VMs existentes."
keywords: "proxmox, opentofu, terraform, bpg/proxmox, cloud-init, api token, pveum, for_each, import, drift, infraestructura como código"
tags: ['proxmox', 'terraform', 'automation', 'virtualization']
updated: 2026-11-25
difficulty: intermediate
estimated_time: 30 min
category: Virtualización
status: published
last_reviewed: 2026-11-25
prerequisites:
  - "[Proxmox VE](proxmox_base.md)"
  - "[Plantillas cloud-init en Proxmox](cloud_init_templates.md)"
  - "[Terraform & OpenTofu — Infraestructura como Código](../terraform/terraform_base.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Proxmox como código con OpenTofu

## El problema

Tienes una plantilla cloud-init bien hecha y crear una VM nueva son dos minutos de clic derecho, «Clonar», cambiar el nombre, ajustar CPU y memoria, poner la IP en la pestaña Cloud-Init y arrancar. El problema llega con la quinta VM: ya no recuerdas qué IP le diste a cada una, una tiene 4 GB porque «era una prueba», y reconstruir el laboratorio después de reinstalar el nodo significa repetir todo de memoria.

Con OpenTofu, las VMs pasan a ser un fichero de texto en Git. Dices cuántas quieres y cómo son, `tofu plan` te enseña qué va a cambiar antes de tocar nada y `tofu apply` lo hace. Si alguien cambia una VM a mano, el siguiente `plan` lo delata.

!!! warning "Sin probar todavía en el homelab"
    Todo lo que hay aquí está contrastado con la documentación oficial del provider `bpg/proxmox` (v0.123.1), de OpenTofu (v1.13.10) y de la API de Proxmox VE, a fecha de 25/11/2026. **Aún no se ha ejecutado en una máquina.** Si algo falla, abre una errata en GitHub y lo corrijo.

## 📋 Tabla de Contenidos

- [Qué necesitas](#que-necesitas)
- [Usuario y token con permisos mínimos](#usuario-y-token-con-permisos-minimos)
- [Configurar el provider](#configurar-el-provider)
- [Una VM clonando la plantilla](#una-vm-clonando-la-plantilla)
- [Varias VMs con for_each](#varias-vms-con-for_each)
- [Estado remoto](#estado-remoto)
- [plan, apply y destroy](#plan-apply-y-destroy)
- [Drift: cuando alguien toca la VM a mano](#drift-cuando-alguien-toca-la-vm-a-mano)
- [Importar VMs existentes](#importar-vms-existentes)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué necesitas

- **Proxmox VE 9.x.** El provider declara soporte completo para la 9; la 8 funciona «con algunas limitaciones» y no es prioridad de sus pruebas.
- **OpenTofu 1.10 o superior.** El provider pide 1.6+, pero el bloqueo nativo en S3 que se usa más abajo (`use_lockfile`) llegó en la 1.10. La última versión publicada es la 1.13.10.
- **Una plantilla cloud-init** ya creada en el nodo. Cómo hacerla está en [Plantillas cloud-init en Proxmox](cloud_init_templates.md); aquí se asume que es la VM `9000` del nodo `pve`.
- **TLS 1.3 en la API.** Es el mínimo por defecto del provider; si tu endpoint no lo ofrece, existe el argumento `min_tls`.

!!! note "Dos familias de nombres en el provider"
    El provider está renombrando sus recursos de `proxmox_virtual_environment_*` a nombres cortos (`proxmox_cloned_vm`, `proxmox_vm`…). Para VMs, los nombres cortos todavía están marcados como experimentales (`proxmox_vm` dice literalmente «DO NOT USE») y `proxmox_cloned_vm` no gestiona cloud-init. El recurso estable para clonar con cloud-init sigue siendo **`proxmox_virtual_environment_vm`**, que es el que se usa aquí. Revisa el changelog antes de subir de versión.

## Usuario y token con permisos mínimos

La documentación del provider propone un rol con casi cincuenta privilegios y advierte de que es «solo un ejemplo, probablemente demasiado permisivo». Para clonar, configurar, arrancar y borrar VMs basta con mucho menos. La lista sale de las comprobaciones de permisos que declara la propia API de Proxmox:

| Operación de la API | Privilegio |
|---|---|
| Clonar (`POST /qemu/{vmid}/clone`) | `VM.Clone` en la plantilla, `VM.Allocate` en la VM nueva, `Datastore.AllocateSpace` en el almacenamiento y `SDN.Use` en el bridge |
| Cambiar configuración (`/qemu/{vmid}/config`) | `VM.Config.*` según lo que cambies (`CPU`, `Memory`, `Disk`, `Network`, `Cloudinit`, `Options`…) |
| Leer la configuración | `VM.Audit` |
| Arrancar y apagar | `VM.PowerMgmt` |
| Borrar la VM | `VM.Allocate` |
| Leer las IPs del agente QEMU | `VM.GuestAgent.Audit` |

A eso el provider añade un aviso: sin `SDN.Audit` o `SDN.Use`, Proxmox oculta los bridges al listar la red del nodo y algunas lecturas fallan con «interface not found».

En la shell del nodo:

```bash
# Usuario del realm pve (sin cuenta de sistema)
pveum user add tofu@pve --comment "OpenTofu"

# Rol con lo necesario para clonar y gestionar VMs
pveum role add TofuVM --privs "VM.Allocate VM.Clone VM.Audit VM.PowerMgmt \
VM.Config.CPU VM.Config.Memory VM.Config.Disk VM.Config.Network VM.Config.Cloudinit \
VM.Config.Options VM.Config.HWType VM.Config.CDROM VM.GuestAgent.Audit \
Datastore.AllocateSpace Datastore.Audit SDN.Use SDN.Audit Sys.Audit"

# Token con privilegios separados (el valor por defecto)
pveum user token add tofu@pve provider --privsep 1

# Con privsep, el permiso efectivo es la intersección de usuario y token:
# hay que dárselo a los dos
pveum acl modify / --users tofu@pve --roles TofuVM
pveum acl modify / --tokens 'tofu@pve!provider' --roles TofuVM
```

`token add` muestra el secreto **una sola vez**. El valor que usa el provider es `tofu@pve!provider=<secreto>`.

!!! tip "Acotar más"
    Dar el rol en `/` es lo cómodo. Si el nodo comparte espacio con VMs que OpenTofu no debe tocar, mete las VMs gestionadas en un pool y da `VM.Allocate` sobre `/pool/<pool>`: la API de clonado lo acepta como alternativa a `/vms/{newid}`. Y si el `apply` devuelve un 403 que nombra un privilegio, añade ese y solo ese.

Hay operaciones que Proxmox reserva a `root@pam` y que **ningún token** puede hacer, aunque sea de root: `hookscript`, la arquitectura de CPU, passthrough PCI/USB sin mapeo o `initialization.upgrade`. Si las necesitas, la doc del provider explica la opción `ssh.root_ticket`; en la configuración de este artículo no hace falta.

## Configurar el provider

```hcl
# versions.tf
terraform {
  required_version = ">= 1.10"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.123.0" # 0.123.x; antes de la 1.0 cada minor puede romper
    }
  }
}
```

```hcl
# provider.tf
provider "proxmox" {
  endpoint = var.pve_endpoint # https://pve.lan:8006/  (sin /api2/json)
  insecure = var.pve_insecure # true solo con certificado autofirmado
  # api_token se lee de PROXMOX_VE_API_TOKEN
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

El token nunca entra en un `.tf` ni en un `.tfvars` versionado. Sin bloque `ssh`: clonar, configurar y borrar VMs va entero por la API. SSH solo hace falta para subir *snippets* (por ejemplo, un `user-data` propio con `proxmox_virtual_environment_file`) o importar discos desde una ruta local.

## Una VM clonando la plantilla

```hcl
# vm.tf
resource "proxmox_virtual_environment_vm" "web" {
  name      = "web01"
  node_name = "pve"
  vm_id     = 201
  tags      = ["tofu", "web"]

  clone {
    vm_id = 9000 # la plantilla cloud-init
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
    enabled = true # solo si la plantilla arranca qemu-guest-agent
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

Tres detalles de la documentación que muerden si no los conoces:

1. **El clon hereda todo de la plantilla**, discos incluidos. Pero si cambias un atributo del disco (aquí, `size`), el provider aplica sus valores por defecto al resto (`discard`, `cache`, `aio`…) salvo que los declares. Si la plantilla tiene `discard=on`, ponlo también en el bloque `disk`.
2. **El agente QEMU también se hereda.** Si la plantilla lo tiene activado y omites el bloque `agent`, el provider esperará al agente hasta 15 minutos en cada `apply` y cada `refresh`. Decláralo siempre de forma explícita, `true` o `false`.
3. **`local-lvm` es el almacenamiento por defecto** del disco cloud-init (`initialization.datastore_id`). Si tu nodo no lo tiene, indícalo a mano.

`user_account` y `user_data_file_id` son excluyentes: o usuario y claves sencillos, o un `user-data` completo subido como snippet (y entonces sí necesitas SSH).

## Varias VMs con for_each

Copiar el bloque anterior tres veces es justo lo que querías evitar. Con `for_each` sobre un mapa, cada VM es una entrada:

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
    retries = 3 # Proxmox a veces da timeout con varios clones a la vez
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

Por qué `for_each` y no `count`: con `count`, las VMs son `vm[0]`, `vm[1]`, `vm[2]`; borra la primera de la lista y OpenTofu querrá recrear las otras dos porque han cambiado de índice. Con un mapa, la dirección es `vm["web02"]` y quitar `web01` solo destruye `web01`.

`ipv4_addresses` lo rellena el agente QEMU: con `agent.enabled = false` sale vacío. Y si no fijas `vm_id`, Proxmox asigna el siguiente libre; fijarlo hace que la VM sea reconocible fuera de OpenTofu y facilita importarla otra vez si pierdes el estado.

## Estado remoto

El estado guarda la correspondencia entre `proxmox_virtual_environment_vm.vm["web01"]` y la VM 201 real, y además los atributos leídos, incluidas contraseñas si las pones en `user_account`. Todo lo que explica [Backend de estado y migración](../terraform/terraform_state.md) vale aquí: fuera de Git, cifrado y con bloqueo.

En un homelab, lo habitual es un almacenamiento compatible con S3 propio:

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket = "tofu-state"
    key    = "proxmox/homelab.tfstate"
    region = "us-east-1" # obligatorio aunque el servicio lo ignore

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

`use_lockfile` bloquea con escrituras condicionales (`If-None-Match`) en el propio bucket, sin DynamoDB. Comprueba que tu servicio S3 compatible las soporta antes de fiarte del bloqueo. Las credenciales, como siempre, por `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`.

## plan, apply y destroy

```bash
tofu fmt -check
tofu validate
tofu plan -out=tfplan      # revisa qué se crea, cambia o destruye
tofu apply tfplan          # aplica exactamente ese plan

# Una sola VM (para emergencias, no como rutina)
tofu apply -replace='proxmox_virtual_environment_vm.vm["web02"]'

# Ver lo que se borraría antes de borrarlo
tofu plan -destroy
tofu destroy
```

Fíjate en el símbolo de cada recurso del `plan`: `~` es un cambio en caliente, `-/+` es **destruir y recrear**. En una VM, recrear significa perder el disco. Un ejemplo que da la propia documentación: cambiar `node_name` recrea la VM salvo que pongas `migrate = true`, que la migra. Lee el plan entero antes de escribir `yes`.

Para las VMs que no deben desaparecer por un error de edición, `lifecycle { prevent_destroy = true }` hace que el `plan` falle en lugar de proponer el borrado.

## Drift: cuando alguien toca la VM a mano

Si subes la memoria desde la interfaz web, el siguiente `tofu plan` propondrá volver al valor del código. Eso es el *drift*. Para verlo sin mezclarlo con tus propios cambios:

```bash
tofu plan -refresh-only    # solo qué ha cambiado fuera
tofu apply -refresh-only   # aceptar la realidad en el estado, sin tocar la VM
```

Luego decides: o llevas el cambio al código, o dejas que el próximo `apply` lo revierta.

Hay drift que no es real. La documentación del provider avisa de uno concreto: Proxmox **siempre ordena las etiquetas**, así que si tu lista `tags` no está ordenada verás una diferencia eterna. Ordénala o ignórala:

```hcl
  lifecycle {
    ignore_changes = [tags]
  }
```

No abuses de `ignore_changes`: cada atributo que ignoras es un atributo que ya no gestionas.

## Importar VMs existentes

Las VMs creadas a mano pueden pasar a OpenTofu sin recrearlas. El identificador que espera el provider es `nodo/vmid`. Con un bloque `import` (OpenTofu 1.6+), el import se revisa en el `plan` como cualquier otro cambio:

```hcl
# import.tf
import {
  to = proxmox_virtual_environment_vm.legacy
  id = "pve/105"
}
```

```bash
# Genera un borrador de configuración a partir de la VM real
tofu plan -generate-config-out=legacy.tf
```

`-generate-config-out` exige un fichero que no exista y su formato puede cambiar entre versiones: trata el resultado como borrador. Límpialo, quita lo que sean valores por defecto y ejecuta `tofu plan` hasta que diga que no hay cambios **antes** del primer `apply`. Si el plan tras importar propone cambios, aplicarlo modificará la VM real.

Para varias a la vez, `import` admite `for_each`:

```hcl
import {
  for_each = { web01 = 201, web02 = 202 }
  to       = proxmox_virtual_environment_vm.vm[each.key]
  id       = "pve/${each.value}"
}
```

Cuando el import está aplicado, borra el bloque `import`: ya no hace nada. Más detalle sobre `import` y el estado en [Backend de estado y migración](../terraform/terraform_state.md#importar-recursos-preexistentes).

## Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `403 ... Permission check failed` | Falta un privilegio en el rol o en el token | Lee qué privilegio nombra y añádelo al rol; con `privsep 1`, ACL al usuario **y** al token |
| `Permission check failed (user != root@pam)` | Atributo reservado a `root@pam` (`hookscript`, `arch`, `upgrade`…) | Quita el atributo o usa `ssh.root_ticket` |
| `apply` o `refresh` tardan ~15 min | Agente activado (o heredado de la plantilla) y sin `qemu-guest-agent` corriendo | Instala el agente en la plantilla o pon `agent { enabled = false }` |
| `interface not found` | Al token le falta `SDN.Audit` o `SDN.Use` | Añade ambos al rol |
| Error de TLS al conectar | El endpoint no ofrece TLS 1.3 | Argumento `min_tls` o certificado válido |
| Diferencia en `tags` en cada `plan` | Proxmox ordena las etiquetas | Lista ordenada o `ignore_changes = [tags]` |
| Timeout al crear varios clones | Proxmox a veces da timeout con varios clones simultáneos | `clone.retries` o `tofu apply -parallelism=2` |
| El disco clonado pierde `discard` u otra opción | Al tocar el disco se aplican los valores por defecto del provider | Declara en `disk` todo lo que difiera del valor por defecto |

## Buenas prácticas

- **Token por herramienta**, con `privsep` y fecha de caducidad (`--expire`). Si se filtra, lo revocas sin tocar el usuario.
- **Versión del provider fijada** con `~>` y el `.terraform.lock.hcl` en Git. Antes de la 1.0, una subida de minor se lee con el changelog delante.
- **`for_each` con claves estables**, nunca `count` para VMs con nombre propio.
- **`vm_id` explícito** en todo lo que importe: facilita reimportar y localizar la VM en la interfaz.
- **Estado remoto con bloqueo desde el primer día**, y sin secretos en `user_account` si puedes evitarlo: las claves SSH públicas no son secreto, las contraseñas sí.
- **`plan -refresh-only` periódico** para enterarte del drift antes de que un `apply` lo revierta sin avisar.
- **`prevent_destroy`** en las VMs con datos.

## Referencias

- [Provider bpg/proxmox — documentación](https://registry.terraform.io/providers/bpg/proxmox/latest/docs) · [Repositorio y releases](https://github.com/bpg/terraform-provider-proxmox/releases)
- [Recurso `proxmox_virtual_environment_vm`](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_vm)
- [Proxmox VE — gestión de usuarios y permisos (pveum)](https://pve.proxmox.com/pve-docs/pveum.1.html) · [API viewer](https://pve.proxmox.com/pve-docs/api-viewer/)
- [OpenTofu — bloque import](https://opentofu.org/docs/language/import/) · [Backend s3](https://opentofu.org/docs/language/settings/backends/s3/) · [Releases](https://github.com/opentofu/opentofu/releases)
- [Plantillas cloud-init en Proxmox](cloud_init_templates.md) · [Proxmox VE](proxmox_base.md)
- [Terraform & OpenTofu](../terraform/terraform_base.md) · [Backend de estado y migración](../terraform/terraform_state.md)
