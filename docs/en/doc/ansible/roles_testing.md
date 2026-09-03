---
title: "Ansible — Roles and testing with Molecule"
description: "Role structure, the four levels of checking (syntax, lint, idempotence and functional verification), ansible-lint without the noise, Molecule scenarios and drivers, the idempotence test explained and CI integration."
keywords: "ansible, molecule, testing, ansible-lint, idempotence, testinfra, roles, assert, github actions, ci"
tags: ['ansible', 'testing', 'automation', 'ci-cd']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 25 min
category: DevOps
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "[Ansible — Infrastructure Automation](ansible_base.md)"
  - "Python and pip"
  - "Docker or Podman running locally"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ansible — Roles and testing with Molecule

## The problem

The playbook worked: you ran it against the new machine, it came out green, the service answered. And from that you draw a conclusion you shouldn't — that the role *works*. What you proved is that it works **once**, **on that machine**, **from that particular initial state**. What you still don't know: what happens on the second run, what happens on Debian if you wrote it looking at Rocky, and what happens when the file you manage already existed with different content. Ansible is sold as idempotent, but idempotence is not a property of the engine: it is a property of **your tasks**, and a badly written `shell` loses it. Testing a role closes that gap repeatably: clean machine, apply the role, apply it again, check the system ended up the way you say it does.

!!! note "What this covers and what it doesn't"
    This page continues where [Ansible — Infrastructure Automation](ansible_base.md) ends: it assumes you can write a playbook and want to package it as a tested role. It does not cover collections, AWX/AAP or signed publishing on Galaxy.

## 📋 Table of Contents

- [Anatomy of a role](#anatomy-of-a-role)
- [Why a playbook that works is not tested](#why-a-playbook-that-works-is-not-tested)
- [The four levels of checking](#the-four-levels-of-checking)
- [ansible-lint without the noise](#ansible-lint-without-the-noise)
- [Molecule: scenarios and drivers](#molecule-scenarios-and-drivers)
- [The scenario cycle](#the-scenario-cycle)
- [Real idempotence](#real-idempotence)
- [Functional verification: assert or Testinfra](#functional-verification-assert-or-testinfra)
- [Test variables and the distribution matrix](#test-variables-and-the-distribution-matrix)
- [CI with GitHub Actions](#ci-with-github-actions)
- [What is not worth testing](#what-is-not-worth-testing)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Anatomy of a role

A role is a directory with reserved names. Ansible loads each `main.yml` automatically: there is no index file and no configuration declaring it.

```
roles/nginx/
├── defaults/main.yml    # default variables — LOWEST precedence
├── vars/main.yml        # internal constants — VERY HIGH precedence
├── tasks/main.yml       # the role's entry point
├── handlers/main.yml    # tasks triggered by notify (reload, restart)
├── templates/           # .j2 files rendered with template
├── files/               # static files served with copy
├── meta/main.yml        # metadata, dependencies, supported platforms
└── molecule/default/    # test scenario
```

The distinction that causes the most trouble is `defaults/` versus `vars/`. `defaults/` has the lowest precedence of all: anyone overrides it from the inventory, `group_vars` or the play. `vars/` sits above almost everything, including the play's own `vars`. When in doubt, it goes in `defaults/`: a variable in `vars/` leaves the role's user convinced their configuration is ignored — because it is. And dependencies declared in `meta/main.yml` run **before** the role, on every invocation; for conditional logic `include_role` inside `tasks/` is almost always better.

## Why a playbook that works is not tested

Four failures a successful manual run does not detect:

1. **No idempotence.** The first pass creates the file; the second reports `changed` again because you used `shell`. In production that means handlers firing and services restarting on every run.
2. **Dependence on the initial state.** Your test machine already had `curl`, `python3-apt` or the user created. The new machine does not.
3. **Drift across distributions.** `apache2` versus `httpd`, `sites-available` versus `conf.d`, `firewalld` versus `nftables`.
4. **Regression when a variable changes.** Someone touches a default six months later and nobody applies the role to a clean machine again until deployment day.

## The four levels of checking

Each level costs more and catches different things. In this order: the cheap one first.

| Level | Command | What it catches | What it does NOT catch |
|---|---|---|---|
| **Syntax** | `ansible-playbook --syntax-check` | Invalid YAML, non-existent modules, badly nested parameters | Anything semantic |
| **Lint** | `ansible-lint` | Antipatterns, avoidable `shell`, implicit permissions, missing names | Whether the role does what it claims |
| **Idempotence** | `molecule idempotence` | Tasks that change something on every pass | Whether the result is correct |
| **Functional verification** | `molecule verify` | That the service is installed, active and listening | Performance and real load |

There is also *check mode* (`ansible-playbook --check --diff`), useful against real machines to see what would change before touching anything. But **it is not a test**: not every module supports it faithfully, and any task depending on the `register` of an earlier one that check mode never ran gives a false result. It is for reviewing a change, not for validating a role.

## ansible-lint without the noise

With no configuration, `ansible-lint` on an existing role spits out hundreds of warnings —half of them irrelevant to you— and the team learns to ignore it within a week. Configuration is what makes it useful.

```yaml
# .ansible-lint
profile: moderate          # a progressive rule set, not everything at once
skip_list:
  - yaml[line-length]      # a style decision, not a bug
  - package-latest         # deliberate in the workstation role
warn_list: ["name[casing]"] # warns, does not break the build
```

Starting from a lax profile and raising it once the role is clean is far more realistic than turning everything on from day one. The rules that generate the most noise:

| Rule | What it complains about | Reasonable treatment |
|---|---|---|
| `name[missing]`, `name[casing]` | Unnamed or lowercase tasks | Fix: the name is what you read when it fails |
| `fqcn[action-core]` | `copy:` instead of `ansible.builtin.copy:` | Fix once with `--fix` and forget about it |
| `no-changed-when` | `command`/`shell` without `changed_when` | **Always fix**: it is exactly what breaks idempotence |
| `risky-file-permissions` | `copy`/`file` without `mode` | Fix: the implicit mode depends on the remote umask |
| `package-latest` | `state: latest` | Legitimate on workstations, wrong on servers |
| `yaml[line-length]` | Long lines | Silence it without remorse |

Careful with `ansible-lint --fix`: besides fixing rules it reformats the YAML. Run it with a clean working tree and review the diff before committing — it is not an innocent cosmetic operation.

## Molecule: scenarios and drivers

Molecule automates the "spin up, apply, check, destroy" loop. A **scenario** is a directory under `molecule/` with its own configuration (`molecule.yml`), the playbook that applies the role (`converge.yml`) and the checks (`verify.yml`). The one called `default` is what runs unless you say otherwise.

```bash
molecule init scenario -s proxy   # add a scenario to an existing role
molecule test                     # default scenario; -s proxy for another, --all for every one
```

The **driver** decides what you test on:

| Driver | Isolates | Cost | When |
|---|---|---|---|
| Container (Docker/Podman) | Processes and files | Seconds | 90 % of roles: packages, files, templates, users |
| Virtual machine (Vagrant, libvirt, cloud) | The whole kernel | Minutes | Kernel modules, firewalls, partitions, real systemd |
| `delegated` / `default` | Nothing: you supply the hosts | Variable | Existing infrastructure or technologies with no driver |

The container's limitation is not a minor detail: there is no `systemd` out of the box, no complete `/sys` and no applicable firewall rules. A role that installs packages and deploys templates tests perfectly in a container; one that manages `nftables` or mounts volumes needs a VM, or you will be testing the half that does not matter.

!!! danger "This is where the version bites you"
    Molecule's configuration structure **has changed across major versions**. What depends on your version and must not be copied blindly from a blog post: drivers stopped shipping in the main package (for a while as separate ones —`molecule-docker`, `molecule-podman`, `molecule-vagrant`— and later grouped into `molecule-plugins`); recent versions push toward the `default` driver with your own `create.yml`/`destroy.yml` playbooks instead of a per-technology driver; and the `lint:` key inside `molecule.yml` existed, changed shape and eventually disappeared. Before writing your `molecule.yml`, run `molecule --version` and `molecule drivers`, and read the documentation **for that version**. What is stable across all of them: the scenario directory layout, the phase names and the concept of idempotence. Running `ansible-lint` as its own CI step, outside Molecule, works with any version and saves you the whole problem.

## The scenario cycle

`molecule test` chains the scenario phases in order: `create` → `converge` → `idempotence` → `verify` → `destroy`.

| Phase | What it does |
|---|---|
| `dependency` | Downloads roles and collections from `requirements.yml`; `create` spins up the `platforms` instances and `prepare` sets the stage |
| `converge` | Applies the role — your real playbook |
| `idempotence` | Repeats `converge` and fails if anything reports `changed` |
| `verify` | Runs the checks, and `destroy` removes the instances |

While developing, **do not run `molecule test`**: it destroys the instance when it finishes, exactly when you wanted to inspect it. The fast loop is `molecule converge` to apply, `molecule login` to get in, `molecule verify` to check and `molecule destroy` when you are done; `molecule test` is for CI and final validation.

## Real idempotence

The `idempotence` phase does something very simple: it runs `converge` **a second time** and looks at the summary. If any task reports `changed`, it fails.

It is not a technicality: a non-idempotent role rewrites files and restarts services on every run across your fleet, the "just checking" pass becomes a destructive one, and people stop running Ansible out of fear.

**1. `command` and `shell` without declaring when they change something.** They always report `changed`, because Ansible cannot know what they did. If the command produces an artifact, `creates:` (or its twin `removes:`) settles it; if not, its output does — `changed_when: false` for anything that only queries, an expression over `stdout` or `rc` for anything that acts:

{% raw %}
```yaml
- name: Compile the assets
  ansible.builtin.command: npm run build
  args: { chdir: /opt/app, creates: /opt/app/dist/index.html }   # without creates: changed always

- name: Check the pending migrations
  ansible.builtin.command: /opt/app/bin/migrate --status
  register: migration
  changed_when: false

- name: Apply the migrations
  ansible.builtin.command: /opt/app/bin/migrate --apply
  when: migration.rc == 2
  register: result
  changed_when: "'applied' in result.stdout"
```
{% endraw %}

**2. `lineinfile` with an expression that does not recognise what it writes.** If the `regexp` looks for one pattern and the `line` writes another that no longer matches it, the second pass does not find it and adds it again: after twenty runs you have twenty lines. The `regexp` must match the **key**; the `line` carries key and value.

```yaml
- name: Set the port
  ansible.builtin.lineinfile:
    path: /etc/app.conf
    regexp: '^port\s*='      # ✅ matches the key; '^port = 8080' would duplicate it
    line: 'port = 9090'
```

If you are going to touch more than two lines of the same file, drop `lineinfile` and use `template`: the whole file becomes yours and idempotence comes for free.

**3. Templates with volatile content.** A template rendering {% raw %}`{{ ansible_date_time.iso8601 }}`{% endraw %} or a random value produces a different file on every pass, and therefore an eternal `changed`. The "generated by Ansible" header goes without a date.

**4. `state: latest` and unconditional downloads.** `package: state=latest` reports `changed` every time the repository publishes an update: correct, but not idempotent by definition. For anything that must be reproducible, `state: present` with the version pinned. When `idempotence` fails, the output points at the task but not always at the reason: the direct diagnosis is repeating the pass showing the diff with `molecule converge -- --diff -v`, which on `template`, `copy` and `lineinfile` shows the file diff — that is usually where the whitespace, the trailing newline or the wandering permission turns up.

## Functional verification: assert or Testinfra

After `converge` you have to check the system ended up the way you say. Two paths, both valid. **With the `assert` module** (verifier `ansible`, the default one): no new dependencies and in the language you already use.

{% raw %}
```yaml
# molecule/default/verify.yml
---
- name: Verify
  hosts: all
  tasks:
    - name: Gather the package facts
      ansible.builtin.package_facts: { manager: auto }

    - name: The package must be installed
      ansible.builtin.assert:
        that: "'nginx' in ansible_facts.packages"

    - name: The site must answer
      ansible.builtin.uri: { url: "http://localhost/", status_code: 200 }
```
{% endraw %}

**With Testinfra** (`test_*.py` files inside the scenario): pytest with a system introspection API; it pays off when the checks carry logic, parametrization or sheer volume.

```python
# molecule/default/tests/test_nginx.py
def test_service(host):
    svc = host.service("nginx")
    assert host.package("nginx").is_installed
    assert svc.is_running and svc.is_enabled
    assert host.socket("tcp://0.0.0.0:80").is_listening


def test_config(host):
    conf = host.file("/etc/nginx/nginx.conf")
    assert conf.user == "root" and conf.mode == 0o644
```

An honest choice: **start with `assert`**. One dependency fewer, anyone on the team understands it and it covers the vast majority of roles. Move to Testinfra when `verify.yml` starts asking for loops and conditionals — the sign that you are programming in YAML.

!!! tip "Check behaviour, not implementation"
    That the package is installed and the port is listening, fine; that line 42 of the configuration file exists exactly as written, no. The test must break when the service stops working, not when you rewrite the template.

## Test variables and the distribution matrix

`converge.yml` is an ordinary playbook: that is where the variables you want to test the role with go.

```yaml
# molecule/default/converge.yml
---
- name: Converge
  hosts: all
  become: true
  vars: { nginx_port: 8080 }
  tasks:
    - name: Apply the role
      ansible.builtin.include_role: { name: nginx }
```

One scenario per **meaningful combination**, not per variable: `default` with the factory values and `proxy` with the reverse proxy configuration both add something; twelve scenarios for twelve boolean flags are twelve ways of making CI take half an hour. Platforms go in `molecule.yml`: the exact syntax depends on the driver and the version, but the idea is stable — one entry per supported system, using images prepared for Ansible (Python and systemd already inside) rather than the bare official ones.

```yaml
# molecule/default/molecule.yml — fragment; adjust to your driver and version
platforms:
  - { name: debian12, image: "geerlingguy/docker-debian12-ansible:latest", pre_build_image: true }
  - { name: rocky9, image: "geerlingguy/docker-rockylinux9-ansible:latest", pre_build_image: true }
```

Test what you declare in `meta/main.yml` and nothing else. If the metadata says Debian and RHEL, the matrix is those two; adding Ubuntu, Alpine and Arch "just in case" multiplies CI time to cover platforms nobody will ever ask you about.

## CI with GitHub Actions

The minimum pattern that works: lint as a separate job and a matrix of scenarios.

{% raw %}
```yaml
# .github/workflows/molecule.yml
name: Molecule
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ansible-lint && ansible-lint

  molecule:
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      fail-fast: false                       # see every platform, not just the first
      matrix: { scenario: [default, proxy] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: pip install -r requirements-test.txt   # pinned versions
      - run: molecule test -s ${{ matrix.scenario }}
```
{% endraw %}

The three decisions that matter there: `fail-fast: false`, because you want to know whether it fails on Debian *and* on Rocky; pinned versions in `requirements-test.txt`, because Molecule and its plugins break compatibility across majors and an unpinned `pip install molecule` turns CI into a time bomb; and lint before Molecule, because it takes seconds and avoids spinning up containers to discover a style error. The `ubuntu-latest` runners ship Docker preinstalled, so the container driver works with no setup; the VM one does not, because it needs nested virtualization and a runner of your own. More workflow context in [Introduction to GitHub Actions](../cicd/github_actions.md).

## What is not worth testing

- **That Ansible works.** If `package: state=present` installs packages that is Ansible's problem, not yours.
- **Every value of every template.** Check that the service starts with the generated configuration; comparing the rendered file line by line duplicates the template inside the test.
- **Single-task roles.** One that installs a package and stops needs no scenario: lint is enough. Nor do external services: whether the remote database answers does not depend on your role.
- **Combinations nobody uses.** Test the default configuration and the one you actually deploy; the rest is hypothesis. And if a test cannot fail because of a change in the role, delete it.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `idempotence` fails while `converge` is fine | A task always reports `changed` | `molecule converge -- --diff` and find the task in the output |
| The container starts and dies instantly | Image with no init and the role uses `service` | Image with systemd (`*-ansible`) or the VM driver |
| `Failed to connect to the host via ssh` | The scenario uses SSH transport against a container | Review the driver's connection: in a container it must be the native one |
| `verify` passes but production breaks | The instance does not represent the target | Match distribution and version with `meta/main.yml` |
| Everything fails after `pip install --upgrade` | A major version change of Molecule or its plugins | Pin versions and read that version's release notes |
| `ansible-lint` throws hundreds of warnings | No configuration: every rule enabled | Create `.ansible-lint` with a lax `profile` |
| A variable is ignored while testing the role | It is in `vars/`, not in `defaults/` | Move it to `defaults/main.yml` |

When nothing makes sense: `molecule --debug converge` and `molecule login -h debian12` to go in and look.

## Best practices

- **A `default` scenario in every role meant to outlive this week**, and **`ansible-lint` in CI from the first commit.** Adding it to a 400-line role is a day's work; having it from the start is free.
- **No `command` or `shell` without `creates`, `changed_when` or both.** The number one cause of non-idempotence.
- **`defaults/` by default; `vars/` only for internal constants.**
- **Pinned versions in the test dependencies.** Let your CI decide when to upgrade, not PyPI.
- **`molecule converge` while developing, `molecule test` in CI**, on the platforms in `meta/main.yml` and not one more: every row of the matrix is paid on every push.

## References

- [Ansible roles — official docs](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
- [Molecule](https://ansible.readthedocs.io/projects/molecule/) · [ansible-lint — rules and profiles](https://ansible.readthedocs.io/projects/lint/) · [Testinfra](https://testinfra.readthedocs.io/)
- [Ansible — Infrastructure Automation](ansible_base.md) · [Introduction to GitHub Actions](../cicd/github_actions.md) · [Terraform](../terraform/terraform_base.md) · [Podman Quadlet](../docker/quadlets.md)
