#!/bin/bash
set -euo pipefail

echo "[mermaid] Validating diagrams..."

if ! command -v mmdc >/dev/null 2>&1; then
  echo "[mermaid] Mermaid CLI (mmdc) not found. Install with: npm install -g @mermaid-js/mermaid-cli"
  echo "[mermaid] Skipping Mermaid validation"
  exit 0
fi

while IFS= read -r file; do
  echo "[mermaid] Validating $file"
  tmp_out=$(mktemp)
  # Render to a temp file to catch syntax errors; output is discarded.
  if ! awk '/```mermaid/,/```/' "$file" | grep -v '```' | mmdc -i /dev/stdin -o "$tmp_out" >/dev/null 2>&1; then
    echo "[mermaid] Validation failed for $file"
    rm -f "$tmp_out"
    exit 1
  fi
  rm -f "$tmp_out"
done < <(find docs -name "*.md" -exec grep -l '```mermaid' {} +)

echo "[mermaid] All Mermaid diagrams are valid"
