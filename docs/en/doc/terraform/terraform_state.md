---
title: Terraform — State Backend and Migration
---

# Terraform — State Backend and Migration

## Overview

Terraform state management is critical for teams. This guide covers remote backends, state locking, and safe migrations.

## What is Terraform State?

Terraform state is a JSON file that maps your configuration to real infrastructure resources. It's essential for:
- Tracking resource IDs created by providers
- Detecting configuration drift
- Enabling collaborative infrastructure management

**Important:** State may contain sensitive data (database passwords, API keys). Always encrypt and restrict access.

## Local vs Remote State

### Local State (Not Recommended for Teams)
```bash
# Default behavior
terraform init  # Creates terraform.tfstate locally
```

**Risks:**
- No collaboration (merge conflicts)
- Easy to accidentally commit to version control
- No backup or audit trail

### Remote State (Recommended)

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

## Common Backends

| Backend | Use Case | Features |
|---------|----------|----------|
| **S3 + DynamoDB** | AWS teams | Cost-effective, versioning, locking |
| **GCS** | Google Cloud | Native integration, versioning |
| **Consul** | On-premise | High availability, HTTP API |
| **Azure Blob** | Azure teams | Role-based access control |
| **Terraform Cloud** | All platforms | Remote runs, policy as code, teams |

## State Locking

Prevents concurrent modifications that could corrupt state:

```bash
# DynamoDB table for S3 locking
resource "aws_dynamodb_table" "terraform_locks" {
  name           = "terraform-lock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
```

When someone runs `terraform apply`, a lock is acquired. If not released (crash, etc.), subsequent applies fail until the lock is manually broken.

**Force unlock** (dangerous):
```bash
terraform force-unlock LOCK_ID
```

## Migrating State

### Safe Migration Process

1. **Backup existing state**:
   ```bash
   terraform state pull > terraform.tfstate.backup
   ```

2. **Reconfigure backend**:
   ```bash
   terraform init -backend-config="key=new_location/terraform.tfstate"
   ```

3. **Verify migration**:
   ```bash
   terraform state list
   terraform plan  # Should show no changes
   ```

### Example: Local → S3

```bash
# 1. Backup
terraform state pull > backup.json

# 2. Add backend config
cat >> main.tf << 'EOF'
terraform {
  backend "s3" {
    bucket = "my-state-bucket"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}
EOF

# 3. Initialize and migrate
terraform init  # Answer "yes" to migrate
```

## CI/CD Best Practices

### Validation
```bash
terraform validate
terraform plan -out=tfplan
```

### State in CI/CD
- **Never commit** `terraform.tfstate` or `*.tfstate.*`
- **Use remote backend** for CI/CD pipelines
- **Restrict access** to state files (IAM roles, service accounts)
- **Use separate states** per environment (dev, staging, prod)

```hcl
# Use workspaces for environment isolation
terraform {
  backend "s3" {
    bucket = "terraform-state"
    key    = "${terraform.workspace}/terraform.tfstate"
  }
}
```

## Sensitive Data in State

State files can contain:
- Database passwords
- API keys
- Private certificates

**Mitigation:**
- Encrypt state at rest (S3 encryption, AES-256)
- Encrypt in transit (TLS/HTTPS)
- Use separate sensitive variable files (never commit)
- Use a secrets backend (HashiCorp Vault, AWS Secrets Manager)

```hcl
# Don't do this:
variable "db_password" {
  type = string
}

# Do this:
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/db-password"
}
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Error acquiring the state lock" | Another process holds lock | Wait or `terraform force-unlock` |
| "Conflicting backend types" | Config mismatch | Reconfigure backend correctly |
| State not updating | Wrong credentials | Verify AWS/GCP credentials |
| Drift detected | Manual changes to infrastructure | Run `terraform import` or `terraform refresh` |

## See Also

- [Terraform Backend Documentation](https://www.terraform.io/language/settings/backends)
- [State Locking](https://www.terraform.io/language/state/locking)
- [Remote State Best Practices](https://developer.hashicorp.com/terraform/cloud-docs/state)
