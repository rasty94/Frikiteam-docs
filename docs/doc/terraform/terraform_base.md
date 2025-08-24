# Terraform - Infraestructura como Código

## Introducción a Terraform

Terraform es una herramienta de Infraestructura como Código (IaC) desarrollada por HashiCorp que permite definir y gestionar infraestructura de manera declarativa usando archivos de configuración.

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

### Documentación oficial
- **Sitio web oficial:** [terraform.io](https://www.terraform.io/)
- **Documentación:** [developer.hashicorp.com/terraform](https://developer.hashicorp.com/terraform)
- **GitHub:** [github.com/hashicorp/terraform](https://github.com/hashicorp/terraform)
- **Registry:** [registry.terraform.io](https://registry.terraform.io/)

### Comunidad
- **Reddit:** [r/terraform](https://www.reddit.com/r/terraform/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/terraform](https://stackoverflow.com/questions/tagged/terraform)
- **Discord:** [discord.gg/hashicorp](https://discord.gg/hashicorp)
- **Foros oficiales:** [discuss.hashicorp.com](https://discuss.hashicorp.com/)
