#!/bin/bash
set -euo pipefail

# Uso: scripts/new_post.sh "Titulo del post" 2025-08-24 general es|en

TITLE=${1:-}
DATE=${2:-}
CATEGORY=${3:-General}
LANG=${4:-es}

if [[ -z "$TITLE" || -z "$DATE" ]]; then
  echo "Uso: $0 \"Titulo del post\" YYYY-MM-DD [categoria] [es|en]" >&2
  exit 1
fi

YEAR=$(echo "$DATE" | cut -d- -f1)

if [[ "$LANG" == "en" ]]; then
  BASE="docs/en/blog/posts/$YEAR"
else
  BASE="docs/blog/posts/$YEAR"
fi

mkdir -p "$BASE"

SLUG=$(echo "$TITLE" | iconv -t ascii//TRANSLIT | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')
FILE="$BASE/$SLUG.md"

cat > "$FILE" <<EOF
---
date: $DATE
title: "$TITLE"
categories:
  - $CATEGORY
---

# $TITLE

Contenido del post...
EOF

echo "Creado: $FILE"

