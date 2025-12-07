# Terraform & OpenTofu - Infrastructure as Code

## Introduction to Terraform

Terraform is an Infrastructure as Code (IaC) tool developed by HashiCorp that allows defining and managing infrastructure declaratively using configuration files.

## Introduction to OpenTofu

OpenTofu is a fork of Terraform that emerged in 2023 as a response to HashiCorp's license change from MPL 2.0 to BSL 1.1. OpenTofu maintains full compatibility with Terraform while ensuring it remains open-source software under the MPL 2.0 license.

## 🚀 Start with Terraform in 15 minutes

New to Terraform? Start here:

- **[Tutorial: First steps with Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/infrastructure-as-code)** - Create your first infrastructure in AWS
- **[Quick installation guide](https://developer.hashicorp.com/terraform/install)** - Install Terraform on your system
- **[Interactive tutorial](https://learn.hashicorp.com/terraform)** - Learn with practical examples

## Comparison: Terraform vs OpenTofu

### Compatibility
- **Terraform**: Original HashiCorp version
- **OpenTofu**: 100% compatible with Terraform, including:
  - Identical HCL syntax
  - Same providers and modules
  - Same commands and workflows
  - Transparent migration

### Licenses
- **Terraform**: BSL 1.1 (Business Source License) - restrictive for commercial use
- **OpenTofu**: MPL 2.0 (Mozilla Public License) - truly open source

### Development
- **Terraform**: Developed by HashiCorp
- **OpenTofu**: Community-developed, led by Gruntwork and other contributors

### Roadmap
- **Terraform**: Controlled by HashiCorp
- **OpenTofu**: Open roadmap driven by the community

### Migration
Migration from Terraform to OpenTofu is completely transparent:
```bash
# Simply replace the binary
# .tf, .tfvars, and .tfstate files work without changes
```

## Fundamental concepts

### Providers
Providers are plugins that allow Terraform to interact with different services and platforms.

```hcl
# AWS provider configuration
provider "aws" {
  region = "us-west-2"
}
```

### Resources
Resources represent infrastructure objects that Terraform manages.

```hcl
# Create an EC2 instance
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  
  tags = {
    Name = "ExampleInstance"
  }
}
```

### Data Sources
Data sources allow obtaining information about existing resources.

```hcl
# Get AMI information
data "aws_ami" "ubuntu" {
  most_recent = true
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}
```

## Basic syntax

### Variables
```hcl
# variables.tf
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}
```

### Outputs
```hcl
# outputs.tf
output "instance_id" {
  description = "ID of created instance"
  value       = aws_instance.example.id
}

output "public_ip" {
  description = "Public IP of instance"
  value       = aws_instance.example.public_ip
}
```

## Basic commands

```bash
# Initialize Terraform
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy

# Show state
terraform show

# List resources
terraform state list
```

## Use cases

- Cloud infrastructure management
- Deployment automation
- Configuration management
- Multi-cloud deployments

## Best practices

- Use code versioning
- Separate configuration by environments
- Use reusable modules
- Implement security policies
- Document configurations

## Next steps

In the following sections we will explore:

- Terraform modules
- Workspaces and remote states
- CI/CD integration
- Policies with Sentinel
- Terraform Cloud

## Additional resources

### Terraform (HashiCorp)
- **Official website:** [terraform.io](https://www.terraform.io/)
- **Documentation:** [developer.hashicorp.com/terraform](https://developer.hashicorp.com/terraform)
- **GitHub:** [github.com/hashicorp/terraform](https://github.com/hashicorp/terraform)
- **Registry:** [registry.terraform.io](https://registry.terraform.io/)

### OpenTofu
- **Official website:** [opentofu.org](https://opentofu.org/)
- **Documentation:** [opentofu.org/docs](https://opentofu.org/docs)
- **GitHub:** [github.com/opentofu/opentofu](https://github.com/opentofu/opentofu)
- **Registry:** [registry.opentofu.org](https://registry.opentofu.org/)
- **Migration guide:** [opentofu.org/docs/intro/migration](https://opentofu.org/docs/intro/migration)

### Community
- **Reddit:** [r/terraform](https://www.reddit.com/r/terraform/), [r/opentofu](https://www.reddit.com/r/opentofu/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/terraform](https://stackoverflow.com/questions/tagged/terraform), [stackoverflow.com/questions/tagged/opentofu](https://stackoverflow.com/questions/tagged/opentofu)
- **Discord:** [discord.gg/hashicorp](https://discord.gg/hashicorp)
- **Official forums:** [discuss.hashicorp.com](https://discuss.hashicorp.com/)

### Articles and comparisons
- **License analysis:** [hashicorp.com/blog/announcing-hashicorp-license-v2](https://www.hashicorp.com/blog/announcing-hashicorp-license-v2)
- **OpenTofu birth:** [opentofu.org/blog/opentofu-announcement](https://opentofu.org/blog/opentofu-announcement)
- **Migration guide:** [gruntwork.io/blog/opentofu-vs-terraform](https://gruntwork.io/blog/opentofu-vs-terraform)
