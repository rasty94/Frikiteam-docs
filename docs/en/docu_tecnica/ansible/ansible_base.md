# Ansible - Infrastructure Automation

## Introduction to Ansible

Ansible is an IT automation tool that can configure systems, deploy software, and orchestrate more complex IT tasks. Unlike other automation tools, Ansible doesn't require agent installation on managed nodes.

## Key features

- **Agentless**: No special software required on managed nodes
- **Simple**: Uses YAML to describe tasks
- **Powerful**: Can manage complex configurations
- **Secure**: Uses SSH for communication
- **Idempotent**: Can run multiple times without side effects

## Basic components

### Inventory
The inventory defines the hosts and host groups that Ansible will manage.

```yaml
# inventory.yml
[webservers]
web1.example.com
web2.example.com

[dbservers]
db1.example.com
db2.example.com
```

### Playbooks
Playbooks are YAML files that describe the tasks to be executed.

```yaml
# playbook.yml
---
- name: Configure web server
  hosts: webservers
  become: yes
  tasks:
    - name: Install Apache
      apt:
        name: apache2
        state: present
```

### Roles
Roles allow organizing playbooks and other files in a modular way.

## Common use cases

- Server configuration
- Application deployment
- Configuration management
- Automation of repetitive tasks

## Next steps

In the following sections we will explore:
- Advanced Ansible configuration
- Creating custom roles
- CI/CD integration
- Best practices
