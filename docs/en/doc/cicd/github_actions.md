# Introduction to GitHub Actions

GitHub Actions is a Continuous Integration and Continuous Deployment (CI/CD) platform that allows you to automate your build, test, and deployment pipeline.

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
