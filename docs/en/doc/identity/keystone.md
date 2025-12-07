# OpenStack Keystone

Keystone is the OpenStack Identity service. It provides authentication, service discovery, and multi-tenant authorization.

## Main Functions

- **Identity:** User/service authentication (SQL, LDAP).
- **Resource:** Project and domain management.
- **Assignment:** Roles and permissions (RBAC).
- **Catalog:** OpenStack API endpoint registry.

## Basic Commands (OpenStack CLI)

```bash
# List users
openstack user list

# Create project
openstack project create --domain default --description "My Project" my-project

# Assign role
openstack role add --project my-project --user my-user member
```
