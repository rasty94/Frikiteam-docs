---
title: Ansible — Roles and Testing with Molecule
---

# Ansible — Roles and Testing with Molecule

## Overview

Molecule is a testing framework for Ansible roles. This guide covers role structure, local testing, and CI integration.

## Ansible Role Structure

A well-organized role follows this convention:

```
my-role/
├── tasks/              # Main tasks executed
│   └── main.yml
├── handlers/           # Event handlers (restarts, reloads)
│   └── main.yml
├── defaults/           # Default variables (lowest precedence)
│   └── main.yml
├── vars/               # Role variables (higher precedence)
│   └── main.yml
├── files/              # Static files to copy
├── templates/          # Jinja2 templates
├── meta/               # Role metadata and dependencies
│   └── main.yml
├── library/            # Custom Ansible modules
├── molecule/           # Molecule testing configuration
│   └── default/
│       ├── converge.yml
│       ├── molecule.yml
│       └── verify.yml
└── README.md
```

## Getting Started with Molecule

### Installation

```bash
pip install molecule molecule-docker
```

### Initialize a New Role with Tests

```bash
# Create a new role with Docker driver
molecule init role -r my-apache-role -d docker

# Or add Molecule to existing role
cd my-existing-role
molecule init scenario -d docker
```

### Directory Layout Created

```
my-apache-role/
├── molecule/default/
│   ├── molecule.yml      # Molecule configuration
│   ├── converge.yml      # Playbook to apply role
│   └── verify.yml        # Tests to verify role
├── tasks/main.yml
├── handlers/main.yml
└── ...
```

## Writing Tests

### verify.yml Example

```yaml
---
- name: Verify role
  hosts: all
  gather_facts: true
  tasks:
    - name: Check if Apache is installed
      package_facts:
        manager: auto
      
    - name: Verify Apache installed
      assert:
        that:
          - "'apache2' in ansible_facts.packages or 'httpd' in ansible_facts.packages"
        fail_msg: "Apache not installed"
    
    - name: Check if Apache is running
      service_facts:
    
    - name: Verify Apache is running
      assert:
        that:
          - ansible_facts.services['apache2.service']['state'] == 'running' or 
            ansible_facts.services['httpd.service']['state'] == 'running'
        fail_msg: "Apache not running"
```

## Running Tests Locally

### Complete Test Cycle

```bash
cd my-apache-role

# Run all tests
molecule test

# Individual steps:
molecule create       # Spin up test instances
molecule converge     # Apply role playbook
molecule verify       # Run verification tasks
molecule destroy      # Clean up instances
```

### Test with Different Scenarios

```bash
# Create multiple test scenarios
molecule init scenario -s centos -d docker
molecule init scenario -s ubuntu -d docker

# Run specific scenario
molecule test -s centos
molecule test -s ubuntu
```

### Configuration Example (molecule.yml)

```yaml
---
dependency:
  name: galaxy

driver:
  name: docker

platforms:
  - name: ubuntu-22
    image: geerlingguy/docker-ubuntu2204-ansible:latest
    pre_build_image: true
  - name: centos-8
    image: geerlingguy/docker-centos8-ansible:latest
    pre_build_image: true

provisioner:
  name: ansible
  playbooks:
    converge: converge.yml
    verify: verify.yml

verifier:
  name: ansible
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Molecule Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        scenario: [default, centos, ubuntu]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install ansible molecule molecule-docker
      
      - name: Run Molecule tests
        run: molecule test -s ${{ matrix.scenario }}
```

### GitLab CI Example

```yaml
molecule:
  image: registry.gitlab.com/gitlab-org/gitlab-runner:latest
  services:
    - docker:dind
  script:
    - pip install ansible molecule molecule-docker
    - molecule test
```

## Best Practices

1. **Test multiple platforms**: Ubuntu, CentOS, Debian, etc.
2. **Keep scenarios simple**: One scenario per configuration variation
3. **Verify idempotence**: Run converge twice, verify no changes second run
4. **Use pre-built images**: Faster than building from scratch
5. **Mock external dependencies**: Don't rely on external services in tests
6. **Document role behavior**: README.md with usage examples

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Docker not found" | Docker daemon not running | Start Docker: `docker ps` |
| "Container failed to start" | Image not available | Pre-pull: `docker pull image-name` |
| "Converge fails" | Role dependencies missing | Install via `requirements.yml` |
| "Verify tasks fail" | Test assertions wrong | Debug with `molecule converge` then manual check |

## See Also

- [Molecule Documentation](https://molecule.readthedocs.io/)
- [Ansible Testing Best Practices](https://docs.ansible.com/ansible/latest/reference_appendices/test_strategies.html)
- [Community Tested Roles](https://galaxy.ansible.com/)
