---
title: "Terraform — Backend de Estado y Migración"
description: "Gestionar el state de Terraform en equipo: backend remoto S3 con locking, migración de backend, workspaces, operaciones sobre el state, import, drift y credenciales OIDC en CI."
keywords: "terraform, state, backend, s3, dynamodb, locking, force-unlock, migrate-state, reconfigure, workspaces, terraform import, drift, refresh-only, oidc, opentofu"
tags: ['terraform', 'devops', 'best-practices']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 20 min
category: DevOps
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "[Terraform & OpenTofu — Infraestructura como Código](terraform_base.md)"
  - "Conceptos de cloud (IAM, almacenamiento de objetos)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Terraform — Backend de Estado y Migración

## El problema

Terraform no le pregunta al proveedor cloud qué gestiona: se lo pregunta al **state**. Ese fichero es el único sitio donde vive la correspondencia entre el `aws_instance.web` de tu código y el `i-0abc123…` real. Si el state desaparece, Terraform no cree que la instancia esté rota: cree que **no existe** y la vuelve a crear. Un `apply` sin state es un `apply` sobre una infraestructura fantasma.

Con un solo operador y un `terraform.tfstate` local eso casi nunca duele. En cuanto hay dos personas —o una persona y un pipeline— aparecen los tres fallos clásicos: dos `apply` simultáneos que se pisan y dejan el state describiendo una realidad que ya no existe; un `terraform.tfstate` commiteado a Git con la contraseña de la base de datos en texto plano; y el portátil que se formatea llevándose el único registro de qué había en producción.

El backend remoto resuelve los tres a la vez: **almacenamiento compartido, cifrado y con locking**. Esta página cubre cómo montarlo, cómo migrar sin recrear nada, y las operaciones de mantenimiento —`state mv`, `import`, `-refresh-only`— que hacen falta cuando la realidad y el state divergen. Todo ello es común a Terraform y a [OpenTofu](terraform_base.md), con `tofu` en lugar de `terraform`; en funcionalidades recientes, comprueba la documentación de **tu** versión antes de copiar un flag de cualquier guía, esta incluida.

## 📋 Tabla de Contenidos

- [Qué guarda el state y por qué es sensible](#que-guarda-el-state-y-por-que-es-sensible)
- [Local frente a remoto](#local-frente-a-remoto)
- [Backend S3 con locking](#backend-s3-con-locking)
- [Política IAM mínima](#politica-iam-minima)
- [Locking y locks huérfanos](#locking-y-locks-huerfanos)
- [migrate-state frente a reconfigure](#migrate-state-frente-a-reconfigure)
- [Workspaces frente a directorios separados](#workspaces-frente-a-directorios-separados)
- [Operar sobre el state](#operar-sobre-el-state)
- [Importar recursos preexistentes](#importar-recursos-preexistentes)
- [Drift y refresh-only](#drift-y-refresh-only)
- [State en CI: OIDC en lugar de claves](#state-en-ci-oidc-en-lugar-de-claves)
- [Backup y versionado](#backup-y-versionado)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué guarda el state y por qué es sensible

El state es un JSON con el mapeo entre direcciones de recurso (`module.db.aws_db_instance.main`) e identificadores reales del proveedor, más una copia de los atributos leídos en el último refresco y las dependencias entre recursos. De ahí salen tres cosas: qué crear, qué destruir y en qué orden.

La consecuencia incómoda es que **guarda los atributos completos, incluidos los sensibles**. Una contraseña de RDS, una `private_key` generada por el provider TLS, el contenido de un `kubernetes_secret`: todo eso está en el state en claro. `sensitive = true` afecta a lo que se imprime en pantalla, **no** a lo que se escribe en el fichero. Compruébalo tú mismo con `terraform state pull | jq '.resources[].instances[].attributes'`.

!!! danger "El state es un secreto, trátalo como tal"
    - **Nunca** en Git: `*.tfstate`, `*.tfstate.*` y `.terraform/` al `.gitignore` desde el primer commit.
    - Cifrado en reposo y acceso restringido a quien pueda hacer `apply`: leer el state equivale a leer todos los secretos que toca ese código.
    - Si un secreto ha pasado por el state, considéralo expuesto ante quien haya tenido acceso al bucket. Rótalo.
    - Referenciar secretos desde un gestor (Vault, Secrets Manager) reduce la superficie, aunque el valor leído siga acabando en el state. Ver [gestión de secretos](../cybersecurity/gestion_secretos.md).

## Local frente a remoto

| | Local (por defecto) | Remoto |
|---|---|---|
| Ubicación | `terraform.tfstate` en el directorio | Bucket o servicio compartido |
| Colaboración | Ninguna: el fichero es tuyo | Equipo y CI ven lo mismo |
| Locking | No existe | Sí, si el backend lo soporta |
| Cifrado y backup | Los de tu disco | SSE/KMS y versionado del bucket |
| Riesgo de fuga | Alto (commit accidental) | Controlado por IAM |

Local es razonable para un laboratorio de un día. Para cualquier cosa que dos personas puedan tocar, o que un pipeline vaya a aplicar, remoto.

## Backend S3 con locking

El bloque `backend` va dentro de `terraform { }` y **no admite variables ni interpolación**: sus valores deben ser literales o venir por `-backend-config`. Es la limitación que más sorprende al llegar del resto de HCL.

```hcl
terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket         = "acme-tfstate-prod"
    key            = "plataforma/red/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:eu-west-1:123456789012:key/abcd-1234"
    dynamodb_table = "acme-tfstate-locks"
  }
}
```

`key` es la ruta dentro del bucket: **un `key` distinto por componente y por entorno**, que es lo que separa de verdad los states. `encrypt = true` fuerza cifrado en reposo y `kms_key_id` añade control de acceso a la clave, auditable en CloudTrail. La tabla de locks se crea **una vez**, en una configuración de bootstrap aparte —el bucket y la tabla no pueden vivir en el state que ellos mismos guardan—:

```hcl
resource "aws_dynamodb_table" "locks" {
  name         = "acme-tfstate-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
```

El atributo **debe** llamarse `LockID` y ser la clave de partición; con cualquier otro nombre falla la adquisición del lock. Una sola tabla sirve para todos los states de la cuenta: la fila se identifica por la ruta del state.

!!! warning "Locking nativo de S3: depende de tu versión — no verificado aquí"
    Versiones recientes del backend S3 admiten locking sin DynamoDB, mediante un objeto `.tflock` junto al state (argumento `use_lockfile`), y `dynamodb_table` queda como opción heredada. No des por hecho cuál aplica a tu instalación: consulta la documentación del backend S3 de la versión exacta que uses —y de OpenTofu, si es tu caso— y confírmalo con un `terraform init`. Lo innegociable es no quedarte **sin ningún** mecanismo de locking.

## Política IAM mínima

Permisos justos para operar sobre **un** state, sin acceso al resto del bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::acme-tfstate-prod",
      "Condition": { "StringLike": { "s3:prefix": ["plataforma/red/*"] } }
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::acme-tfstate-prod/plataforma/red/*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
      "Resource": "arn:aws:dynamodb:eu-west-1:123456789012:table/acme-tfstate-locks"
    }
  ]
}
```

- El bloque de DynamoDB sobra con locking por fichero: el lock es entonces un objeto más bajo el mismo prefijo.
- Con `kms_key_id` hay que añadir `kms:Encrypt`, `kms:Decrypt` y `kms:GenerateDataKey` sobre el ARN de la clave, o todo falla con un `AccessDenied` que no menciona KMS por ninguna parte.
- Un rol **de solo lectura** (`s3:GetObject` y `s3:ListBucket`) para revisar planes es la mejor separación de privilegio de esta página: mucha gente necesita ver el `plan`, muy poca necesita aplicarlo.

## Locking y locks huérfanos

Antes de escribir, Terraform adquiere un lock; al terminar, lo libera. Si el proceso muere entre medias —Ctrl+C agresivo, runner cancelado, red caída— **el lock se queda** y el siguiente `apply` falla con `Error: Error acquiring the state lock`, seguido de un bloque `Lock Info` con el `ID`, el `Operation`, el `Who` y el `Created`. Ese bloque es información, no solo un error: dice si hay alguien trabajando de verdad o si es un resto de hace tres horas.

```bash
terraform force-unlock 7c1e2b58-...
```

!!! danger "Comprueba antes de forzar"
    `force-unlock` no cancela ninguna operación: solo borra el lock. Si el `apply` original **sigue vivo** en otra máquina, acabas con dos escrituras concurrentes y un state corrupto, que es exactamente el daño que el lock evitaba.

    Protocolo: mirar `Who` y `Created`, preguntar en el canal del equipo, revisar si hay un job en marcha. Solo entonces desbloquear. Existe un flag para saltarse la confirmación interactiva; no lo pongas en un script desatendido.

Para lecturas puntuales donde el lock estorba —y **solo** lecturas— la mayoría de comandos aceptan `-lock=false`. Con `plan`, nunca con `apply`.

## migrate-state frente a reconfigure

Es la confusión que más states rompe. Al cambiar el bloque `backend`, `terraform init` ofrece dos caminos incompatibles:

| Flag | Qué hace con el state existente | Cuándo |
|---|---|---|
| `-migrate-state` | **Lo copia** al nuevo backend | Mover el state de sitio conservando la infraestructura |
| `-reconfigure` | **Lo ignora**: empieza limpio en el nuevo backend | El backend destino ya tiene el state correcto |

Traducido: `-migrate-state` conserva, `-reconfigure` olvida. Si ejecutas `-reconfigure` cuando querías migrar, el backend nuevo arranca vacío, el siguiente `plan` propone **crear toda la infraestructura desde cero** y el state antiguo se queda huérfano donde estaba. Es recuperable —el fichero original no se borra— pero solo si reconoces el síntoma a tiempo.

```bash
terraform state pull > backup-$(date +%F).tfstate   # 1. copia de seguridad, siempre
# 2. añadir el bloque backend "s3" a la configuración
terraform init -migrate-state                       # 3. migrar
terraform state list                                # 4. verificar
terraform plan                                      #    debe decir "No changes"
```

Ese `plan` limpio del paso 4 es la única prueba válida de que la migración fue bien. Si propone crear o destruir algo, **para**: el state migrado no corresponde con la infraestructura.

Cuando el backend se parametriza por entorno, los valores van en ficheros `.hcl` sueltos (`bucket`, `key`, `region`, una clave por línea) porque el bloque no admite variables, y se cargan con `-backend-config`:

```bash
terraform init -reconfigure -backend-config=backends/prod.hcl
```

Aquí `-reconfigure` es lo correcto: no mueves un state, apuntas el directorio de trabajo a otro que ya existe. `-migrate-state` intentaría copiar el state de *staging* encima del de *prod*.

## Workspaces frente a directorios separados

Los workspaces (`terraform workspace new staging`, `select`, `list`, `show`) crean varios states para **una misma configuración**. Lo que un workspace sí aísla es el state. Lo que **no** aísla:

- **Las credenciales.** El proveedor se configura igual en todos los workspaces, y las variables `AWS_*` que tengas cargadas valen para cualquiera. Un `apply` en el workspace equivocado ejecuta contra la cuenta que estuviera activa, sin barrera alguna.
- **El código.** Un cambio en el `.tf` afecta a todos a la vez: no hay promoción gradual de *staging* a *prod*.
- **El backend.** Mismo bucket y mismos permisos: quien lee un workspace los lee todos.
- **El despiste.** Nada en el prompt dice en qué workspace estás.

La alternativa es un directorio por entorno (`envs/dev`, `envs/staging`, `envs/prod`), cada uno con su backend, su provider y sus `tfvars`, compartiendo código a través de módulos en `modules/`. Regla práctica: **workspaces para variaciones efímeras del mismo entorno** —una rama de pruebas, un despliegue temporal—, **directorios separados para entornos con fronteras de seguridad distintas**. Si dev y prod están en cuentas separadas —y deberían—, los workspaces no son la herramienta.

## Operar sobre el state

Estos comandos modifican el **inventario**, no la infraestructura: Terraform no toca nada en el proveedor, cambia lo que cree que existe.

```bash
terraform state list                      # todo lo que gestiona
terraform state show aws_instance.web     # atributos de un recurso
terraform state pull > snapshot.tfstate   # descargar el state completo
terraform state mv aws_instance.web module.frontend.aws_instance.this
```

`state mv` renombra o mueve una dirección: es lo que evita destruir y recrear al refactorizar. Si renombras en el `.tf` **sin** hacer el `mv`, Terraform ve desaparecer la dirección antigua y aparecer la nueva, y planifica destruir y crear. En una base de datos, eso es un incidente.

!!! danger "`state rm` no destruye, y ese es el problema"
    `terraform state rm aws_instance.web` **olvida** el recurso: sigue existiendo y facturando en el proveedor, pero Terraform deja de gestionarlo. Nadie lo destruirá, nadie lo actualizará y no aparecerá en ningún `plan`. Es la forma más limpia de crear recursos huérfanos que nadie recuerda seis meses después.

    Uso legítimo: sacar un recurso de un state para llevarlo a otro. En ese caso **haz el `import` en el destino antes del `rm` en el origen**, y anota el ID.

Dos precauciones que ahorran disgustos: `terraform state pull > antes.tfstate` antes de cualquier `mv` o `rm`, y un `terraform plan` después, que debe salir sin cambios.

## Importar recursos preexistentes

Cuando la infraestructura existe pero el state no la conoce —creada a mano, heredada, migrada de otra herramienta—, `import` la adopta. Escribe primero el bloque de recurso en el `.tf`, aunque sea incompleto, y después asocia la dirección de Terraform con el ID real del proveedor:

```bash
terraform import aws_instance.web i-0abc123def456
terraform plan     # ¿qué diferencias hay entre el código y la realidad?
```

Ese `plan` es el trabajo de verdad. `import` rellena el state con los atributos reales pero **no escribe tu configuración**: hasta que el `.tf` describa el recurso tal como es, el `plan` propondrá cambios. Se itera —ajustar HCL, `plan`, repetir— hasta llegar a "No changes".

El formato del ID depende del proveedor y del recurso: una instancia EC2 usa `i-…`, una regla de security group usa una cadena compuesta, un recurso de Kubernetes usa `namespace/nombre`. Está documentado en la sección *Import* de cada recurso; no lo adivines.

!!! tip "Bloques `import` declarativos — verifica tu versión"
    Las versiones recientes de Terraform admiten bloques `import` en el propio HCL, planificables y revisables en un PR en lugar de ejecutados a mano, con la opción de generar un esqueleto de configuración. Es más cómodo para importaciones masivas, pero confirma disponibilidad y sintaxis exacta en la documentación de tu versión antes de meterlo en un pipeline.

## Drift y refresh-only

*Drift* es la diferencia entre lo que dice el state y lo que hay realmente en el proveedor: alguien tocó algo por consola, un autoscaler cambió una capacidad, un proceso externo añadió una etiqueta.

```bash
terraform plan -refresh-only     # solo compara, no propone cambios de configuración
terraform apply -refresh-only    # actualiza el state con la realidad, sin tocar recursos
terraform plan -refresh=false    # lo contrario: no consulta al proveedor
```

La diferencia con un `plan` normal importa: `plan` mezcla dos cosas —lo que cambió fuera y lo que quieres cambiar tú— en una salida difícil de leer. `-refresh-only` aísla la primera pregunta: *¿qué ha cambiado sin mi permiso?* El comando suelto `terraform refresh` está **deprecado** en favor de `apply -refresh-only`, precisamente porque el antiguo actualizaba el state sin mostrar antes qué iba a cambiar.

`-refresh=false` acelera el `plan` en configuraciones grandes a costa de trabajar con datos posiblemente obsoletos: útil en un bucle de desarrollo rápido, mala idea antes de un `apply` en producción. Y un job periódico que ejecute `plan -refresh-only` y avise si hay diferencias es de las alertas más baratas y útiles que puedes añadir a un entorno con IaC; ver [GitHub Actions](../cicd/github_actions.md) para el andamiaje.

## State en CI: OIDC en lugar de claves

Guardar un `AWS_ACCESS_KEY_ID` de larga duración en los secretos del repositorio significa tener una credencial permanente, con permisos de escritura sobre el state y sobre la infraestructura, en un sitio que mucha gente puede leer o exfiltrar desde un workflow modificado. Con OIDC, el proveedor de CI emite un token de corta duración que la nube valida contra un proveedor de identidad: **no hay clave que rotar ni que filtrar**.

{% raw %}

```yaml
permissions:
  id-token: write        # imprescindible para pedir el token OIDC
  contents: read

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/terraform-ci-plan
          aws-region: eu-west-1
      - run: terraform init
      - run: terraform plan -out=tfplan
```

{% endraw %}

La pieza crítica está del lado de la nube: la *trust policy* del rol debe limitar quién puede asumirlo —repositorio y, a ser posible, rama o entorno concretos—. Un rol que confía en cualquier repositorio de la organización deja el `apply` de producción al alcance de cualquiera con permisos de workflow. Usa **dos roles**: `terraform-ci-plan` con acceso de lectura al state, asumible desde cualquier PR, y `terraform-ci-apply` con escritura, asumible solo desde la rama principal y con aprobación. Así un PR externo genera un `plan` revisable sin poder escribir el state. Detalles en [seguridad en IaC](../cybersecurity/seguridad_iac.md) y [secretos en GitOps](../cybersecurity/secrets_gitops.md).

!!! warning "El plan también es sensible"
    Un fichero de plan (`-out=tfplan`) contiene los valores que se van a escribir, secretos incluidos. No lo publiques como artefacto accesible ni pegues su salida completa en un comentario público del PR.

## Backup y versionado

El versionado del bucket convierte un `state rm` desafortunado en un susto de cinco minutos: actívalo con `aws_s3_bucket_versioning` y `status = "Enabled"` sobre el bucket de state. Recuperar consiste entonces en sacar la versión anterior del objeto y subirla con `terraform state push`. Ese comando **sobrescribe** el state remoto: descarga primero el actual, compruébalo, y solo entonces empuja.

- **Snapshot antes de cada operación manual.** `terraform state pull > antes.tfstate` cuesta un segundo.
- **Bloquear el acceso público** del bucket explícitamente, sin confiar en el valor por defecto.
- **Object Lock o política de retención** si el requisito es que nadie, ni siquiera un administrador, pueda borrar el histórico.
- **Bucket en una cuenta distinta** a la infraestructura que gestiona: comprometer producción no debería llevarse por delante el registro de qué había en ella. Mismo razonamiento que en [la estrategia 3-2-1](../backups/strategy_321.md).

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `Error acquiring the state lock` | Lock huérfano de un proceso muerto | Verificar `Who`/`Created` y `terraform force-unlock <ID>` |
| `Backend configuration changed` | Cambió el bloque `backend` | `init -migrate-state` (copiar) o `-reconfigure` (apuntar a otro) |
| El `plan` propone crear todo tras migrar | Se usó `-reconfigure` en vez de `-migrate-state` | Restaurar el state antiguo y repetir con `-migrate-state` |
| `Resource already exists` al aplicar | El recurso existe pero no está en el state | `terraform import` con el ID real |
| El `plan` destruye y recrea tras renombrar | Cambió la dirección sin `state mv` | `terraform state mv <vieja> <nueva>` |
| Cambios que nadie ha pedido | Drift: modificación manual fuera de Terraform | `plan -refresh-only` para verlo y decidir |
| `AccessDenied` sin mención a KMS | Faltan permisos sobre la clave de cifrado | Añadir `kms:Decrypt`, `kms:Encrypt`, `kms:GenerateDataKey` al rol |
| Se aplicó en el entorno equivocado | Workspace o `-backend-config` incorrecto | `terraform workspace show` antes de cada `apply` |

Cuando el state parece inconsistente y no sabes por dónde empezar, `terraform state pull | jq '.serial, .lineage'` da la pista: `serial` sube con cada escritura y `lineage` identifica el linaje. Dos states con `lineage` distinto **no** son versiones del mismo, y Terraform se negará a mezclarlos; es la señal de que en algún momento se creó un state nuevo en lugar de migrar el existente.

## Buenas prácticas

- **Backend remoto con locking desde el primer día.** Migrar después funciona, pero el incidente que te convence de migrar es caro.
- **Un state por componente y entorno**, no un state monolítico: reduce el radio de impacto y el tiempo de `plan`.
- **`.gitignore` con `*.tfstate*` y `.terraform/`** antes del primer commit, no después del primer susto.
- **Snapshot antes de cualquier `state mv`, `rm` o `push`.** Son las tres operaciones sin deshacer.
- **`plan` limpio como criterio de éxito** de toda migración o importación: "No changes" o no has terminado.
- **OIDC en CI**, con roles separados de lectura y escritura.
- **Detección de drift periódica**, aunque solo sea un aviso semanal.

## Referencias

- [Backends: bloque `terraform` y configuración](https://developer.hashicorp.com/terraform/language/backend)
- [Backend S3 — argumentos y locking](https://developer.hashicorp.com/terraform/language/backend/s3)
- [State locking](https://developer.hashicorp.com/terraform/language/state/locking)
- [Comandos `terraform state`](https://developer.hashicorp.com/terraform/cli/commands/state)
- [Importar infraestructura existente](https://developer.hashicorp.com/terraform/cli/import)
- [Terraform & OpenTofu — base](terraform_base.md) · [Seguridad en IaC](../cybersecurity/seguridad_iac.md)
- [Gestión de secretos](../cybersecurity/gestion_secretos.md) · [GitHub Actions](../cicd/github_actions.md)
