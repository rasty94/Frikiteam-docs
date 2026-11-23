---
title: "Introduction to GitHub Actions"
description: "Getting started with GitHub Actions: workflows, events, jobs, steps and a practical Python build-and-test example."
tags: ['ci-cd', 'automation']
category: DevOps
updated: 2026-10-11
last_reviewed: 2026-10-11
difficulty: intermediate
status: published
estimated_time: 1 min
prerequisites: ["Basic DevOps knowledge"]
---

# Introduction to GitHub Actions

Building by hand, remembering to run tests before every push and deploying from a laptop works right up until the first slip-up. GitHub Actions automates that pipeline straight from the repository using YAML files triggered on every change. Below are the building blocks and a working Python workflow to get started.

## Key Concepts

- **Workflow**: Automated configurable process (YAML file in `.github/workflows`).
- **Event**: Activity that triggers the workflow (e.g., `push`, `pull_request`).
- **Job**: A set of steps that execute on the same runner.
- **Step**: Individual task (shell command or action).

## Example: Python Build and Test

```yaml
name: Python application

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Test with pytest
        run: |
          pytest
```

## Example: MkDocs Deployment

This is the workflow used in this repository to deploy the documentation:

```yaml
name: ci
on:
  push:
    branches:
      - master
      - main
permissions:
  contents: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - run: pip install -r requirements.txt
      - run: mkdocs gh-deploy --force
```

## References

- [GitHub Actions: documentation](https://docs.github.com/en/actions)
- [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [MkDocs: desplegar la documentation](https://www.mkdocs.org/user-guide/deploying-your-docs/)
