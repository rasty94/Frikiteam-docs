---
title: "Mermaid — Validation and usage"
description: "How to validate Mermaid diagrams locally and in GitHub Actions using mermaid-cli and validate_mermaid.sh."
tags: ['documentation']
updated: 2026-11-23
---

# Mermaid — Validation and usage

## The problem

MkDocs does not validate Mermaid diagram syntax during `mkdocs build`: an unquoted parenthesis or a malformed arrow passes the build silently and only surfaces when a reader opens the page and hits a syntax error box.

In FrikiTeam we validate every diagram before publishing using `@mermaid-js/mermaid-cli` (`mmdc`) and the `validate_mermaid.sh` script at the repository root.

## Local validation

Install the same major version pinned in CI (pinning prevents syntax changes between major releases):

```bash
npm install -g @mermaid-js/mermaid-cli@12
```

Then run the validator from the root of `Frikiteam-docs`:

```bash
./validate_mermaid.sh
```

The script scans every `.md` file under `docs/`, extracts each Mermaid block with `awk`, and renders it through headless Chromium with:

```bash
printf "%b" "$diagram" | mmdc -i /dev/stdin -o "$tmp_out" -p puppeteer-config.json
```

When every diagram renders cleanly, it removes the temporary outputs and exits `0`. If any block fails, it prints the offending file and exits non-zero.

## CI integration

The `.github/workflows/docs-ci.yml` workflow defines a `quality` job that runs the check on every `push` and `pull_request` targeting `main`:

```yaml
- run: npm install -g @mermaid-js/mermaid-cli@12
- name: Validate Mermaid diagrams
  run: ./validate_mermaid.sh
```

## Best practices

- **Quote labels with special characters**: parentheses, brackets, or colons inside a node often break the parser unless quoted (`A["API (v2)"]`).
- **Keep diagrams focused**: once a diagram grows past ~15 nodes, splitting it into an overview and a specific flow is usually easier to read.
- **Avoid literal Mermaid fences in prose examples**: the extractor in `validate_mermaid.sh` scans all of `docs/` for Mermaid fence openers and would try to compile them.
- **Validate before committing**: running `./validate_mermaid.sh` locally avoids CI round-trips.

## Common problems

- **Diagram fails to render in the browser**: check the output of `./validate_mermaid.sh` or the browser console; it is almost always an unquoted reserved character or a diagram type unsupported by the Mermaid version bundled with MkDocs Material.
- **`mmdc` fails to launch Chromium on Linux/CI**: make sure `-p puppeteer-config.json` is passed (already handled by the script) so Chromium disables the sandbox in unprivileged containers.
- **Theme style collisions**: check `docs/stylesheets/extra.css` if a diagram looks clipped or low-contrast in dark mode.
