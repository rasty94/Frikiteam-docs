# Terraform - Infrastructure as Code

## Introduction to Terraform

Terraform is an Infrastructure as Code (IaC) tool developed by HashiCorp that allows defining and managing infrastructure declaratively using configuration files.

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

### Official documentation
- **Official website:** [terraform.io](https://www.terraform.io/)
- **Documentation:** [developer.hashicorp.com/terraform](https://developer.hashicorp.com/terraform)
- **GitHub:** [github.com/hashicorp/terraform](https://github.com/hashicorp/terraform)
- **Registry:** [registry.terraform.io](https://registry.terraform.io/)

### Community
- **Reddit:** [r/terraform](https://www.reddit.com/r/terraform/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/terraform](https://stackoverflow.com/questions/tagged/terraform)
- **Discord:** [discord.gg/hashicorp](https://discord.gg/hashicorp)
- **Official forums:** [discuss.hashicorp.com](https://discuss.hashicorp.com/)
