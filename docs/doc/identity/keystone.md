---
tags:
  - identity
  - openstack
---

# OpenStack Keystone

Keystone es el servicio de identidad de OpenStack. Proporciona autenticación, descubrimiento de servicios y autorización multi-tenant.

## Funciones Principales

- **Identity:** Autenticación de usuarios/servicios (SQL, LDAP).
- **Resource:** Gestión de proyectos y dominios.
- **Assignment:** Roles y permisos (RBAC).
- **Catalog:** Registro de endpoints de la API de OpenStack.

## Comandos Básicos (OpenStack CLI)

```bash
# Listar usuarios
openstack user list

# Crear proyecto
openstack project create --domain default --description "Mi Proyecto" my-project

# Asignar rol
openstack role add --project my-project --user my-user member
```
