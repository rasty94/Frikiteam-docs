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
  diagram=""
  while IFS= read -r line; do
    if [[ "$line" == "__MERMAID_END__" ]]; then
      tmp_out=$(mktemp /tmp/mermaid-XXXXXX.png)
      tmp_err=$(mktemp)
      # Render to a temp file to catch syntax errors; discard image, surface errors.
      if ! printf "%b" "$diagram" | mmdc -i /dev/stdin -o "$tmp_out" -p puppeteer-config.json >/dev/null 2>"$tmp_err"; then
        echo "[mermaid] Validation failed for $file"
        echo "[mermaid] Error output:" >&2
        cat "$tmp_err" >&2
        rm -f "$tmp_out" "$tmp_err"
        exit 1
      fi
      rm -f "$tmp_out" "$tmp_err"
      diagram=""
    else
      diagram+="$line\n"
    fi
  done < <(awk '
    /```mermaid/{inside=1; next}
    inside && /```/{inside=0; print "__MERMAID_END__"; next}
    inside
  ' "$file")
done < <(find docs -name "*.md" -exec grep -l '```mermaid' {} +)

echo "[mermaid] All Mermaid diagrams are valid"
