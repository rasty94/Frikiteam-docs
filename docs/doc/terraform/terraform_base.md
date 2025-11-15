# Terraform & OpenTofu - Infraestructura como Código

## 🚀 Iniciar con Terraform en 15 minutos

¿Nuevo en Terraform? Comienza aquí:

- **[Tutorial: Primeros pasos con Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/infrastructure-as-code)** - Crea tu primera infraestructura en AWS
- **[Guía de instalación rápida](https://developer.hashicorp.com/terraform/install)** - Instala Terraform en tu sistema
- **[Tutorial interactivo](https://learn.hashicorp.com/terraform)** - Aprende con ejemplos prácticos

## Introducción a Terraform

Terraform es una herramienta de Infraestructura como Código (IaC) desarrollada por HashiCorp que permite definir y gestionar infraestructura de manera declarativa usando archivos de configuración.

## Introducción a OpenTofu

OpenTofu es un fork de Terraform que surgió en 2023 como respuesta al cambio de licencia de HashiCorp de MPL 2.0 a BSL 1.1. OpenTofu mantiene la compatibilidad total con Terraform mientras garantiza que permanezca como software de código abierto bajo la licencia MPL 2.0.

## Comparativa: Terraform vs OpenTofu

### Compatibilidad
- **Terraform**: Versión original de HashiCorp
- **OpenTofu**: 100% compatible con Terraform, incluyendo:
  - Sintaxis HCL idéntica
  - Mismos providers y módulos
  - Mismos comandos y workflows
  - Migración transparente

### Licencias
- **Terraform**: BSL 1.1 (Business Source License) - restrictiva para uso comercial
- **OpenTofu**: MPL 2.0 (Mozilla Public License) - verdadero código abierto

### Desarrollo
- **Terraform**: Desarrollado por HashiCorp
- **OpenTofu**: Desarrollado por la comunidad, liderado por Gruntwork y otros contribuyentes

### Roadmap
- **Terraform**: Controlado por HashiCorp
- **OpenTofu**: Roadmap abierto y dirigido por la comunidad

### Migración
La migración de Terraform a OpenTofu es completamente transparente:
```bash
# Simplemente reemplaza el binario
# Los archivos .tf, .tfvars y .tfstate funcionan sin cambios
```

## Conceptos fundamentales

### Providers
Los providers son plugins que permiten a Terraform interactuar con diferentes servicios y plataformas.

```hcl
# Configuración de provider AWS
provider "aws" {
  region = "us-west-2"
}
```

### Resources
Los resources representan objetos de infraestructura que Terraform gestiona.

```hcl
# Crear una instancia EC2
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  
  tags = {
    Name = "ExampleInstance"
  }
}
```

### Data Sources
Los data sources permiten obtener información sobre recursos existentes.

```hcl
# Obtener información de una AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}
```

## Sintaxis básica

### Variables
```hcl
# variables.tf
variable "instance_type" {
  description = "Tipo de instancia EC2"
  type        = string
  default     = "t2.micro"
}

variable "environment" {
  description = "Ambiente de despliegue"
  type        = string
}
```

### Outputs
```hcl
# outputs.tf
output "instance_id" {
  description = "ID de la instancia creada"
  value       = aws_instance.example.id
}

output "public_ip" {
  description = "IP pública de la instancia"
  value       = aws_instance.example.public_ip
}
```

## Comandos básicos

```bash
# Inicializar Terraform
terraform init

# Planificar cambios
terraform plan

# Aplicar cambios
terraform apply

# Destruir infraestructura
terraform destroy

# Mostrar estado
terraform show

# Listar recursos
terraform state list
```

## Casos de uso

- Gestión de infraestructura en la nube
- Automatización de despliegues
- Gestión de configuraciones
- Multi-cloud deployments

## Mejores prácticas

- Usar versionado de código
- Separar configuración por ambientes
- Utilizar módulos reutilizables
- Implementar políticas de seguridad
- Documentar configuraciones

## Próximos pasos

En las siguientes secciones exploraremos:
- Módulos de Terraform
- Workspaces y estados remotos
- Integración con CI/CD
- Políticas con Sentinel
- Terraform Cloud

## Recursos adicionales

### Terraform (HashiCorp)
- **Sitio web oficial:** [terraform.io](https://www.terraform.io/)
- **Documentación:** [developer.hashicorp.com/terraform](https://developer.hashicorp.com/terraform)
- **GitHub:** [github.com/hashicorp/terraform](https://github.com/hashicorp/terraform)
- **Registry:** [registry.terraform.io](https://registry.terraform.io/)

### OpenTofu
- **Sitio web oficial:** [opentofu.org](https://opentofu.org/)
- **Documentación:** [opentofu.org/docs](https://opentofu.org/docs)
- **GitHub:** [github.com/opentofu/opentofu](https://github.com/opentofu/opentofu)
- **Registry:** [registry.opentofu.org](https://registry.opentofu.org/)
- **Migración:** [opentofu.org/docs/intro/migration](https://opentofu.org/docs/intro/migration)

### Comunidad
### Videos tutoriales

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;">
  <iframe src="https://www.youtube.com/embed/h970ZBgKINM" frameborder="0" allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe>
</div>

*Video: Terraform desde cero - Infraestructura como Código completa*

- **Reddit:** [r/terraform](https://www.reddit.com/r/terraform/), [r/opentofu](https://www.reddit.com/r/opentofu/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/terraform](https://stackoverflow.com/questions/tagged/terraform), [stackoverflow.com/questions/tagged/opentofu](https://stackoverflow.com/questions/tagged/opentofu)
- **Discord:** [discord.gg/hashicorp](https://discord.gg/hashicorp)
- **Foros oficiales:** [discuss.hashicorp.com](https://discuss.hashicorp.com/)

### Artículos y comparativas
- **Análisis de licencias:** [hashicorp.com/blog/announcing-hashicorp-license-v2](https://www.hashicorp.com/blog/announcing-hashicorp-license-v2)
- **Nacimiento de OpenTofu:** [opentofu.org/blog/opentofu-announcement](https://opentofu.org/blog/opentofu-announcement)
- **Guía de migración:** [gruntwork.io/blog/opentofu-vs-terraform](https://gruntwork.io/blog/opentofu-vs-terraform)
