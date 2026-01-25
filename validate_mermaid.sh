#!/bin/bash

# Script to validate Mermaid diagrams in Markdown files
# Usage: ./validate_mermaid.sh

set -e

echo "🔍 Validating Mermaid diagrams..."

# Find all .md files containing ```mermaid
find docs -name "*.md" -exec grep -l "```mermaid" {} \; | while read -r file; do
    echo "Validating $file"
    # Extract mermaid blocks and validate
    awk '/```mermaid/,/```/' "$file" | grep -v '```' | mmdc --validate
done

echo "✅ All Mermaid diagrams are valid!"