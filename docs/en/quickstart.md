---
title: Quickstart — Get Started and Contribute
summary: Quick guide to get the site up and running and contribute content.
---

# Quickstart — Get Started and Contribute

This document helps new contributors get the site up and running and contribute content in less than 10 minutes.

## Prerequisites
- Python 3.10+ (recommended)
- Git
- Optional: Docker (for container examples)

## Prepare environment (recommended with virtualenv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Serve locally

```bash
mkdocs serve
# Open http://127.0.0.1:8000 in your browser
```

## Build the site

```bash
mkdocs build
# Output goes to the 'site/' folder
```

## Quick Docker example (view content on the site)

```bash
# Run an example nginx
docker run --rm -p 8080:80 nginx
# Open http://127.0.0.1:8080
```

## Create a post (blog)

Use the included `scripts/new_post.sh` script to create blog posts with basic front-matter:

```bash
./scripts/new_post.sh "My new post" 2025-11-15 general en
```

Then edit the created file in `docs/blog/posts/` or `docs/en/blog/posts/` and add content.

## Check and submit changes

- Check links and errors with `mkdocs build`.
- If everything is good, create a PR following `CONTRIBUTING.md`.

---

If you want, I can add test commands and additional examples (e.g.: pre-commit hooks, linters).