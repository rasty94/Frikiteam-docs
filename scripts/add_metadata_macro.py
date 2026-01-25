#!/usr/bin/env python3
"""
Script to add document_metadata macro calls to all documentation pages with frontmatter.
This ensures metadata badges are displayed on all pages automatically.
"""

import os
import re
from pathlib import Path

def has_frontmatter(content: str) -> bool:
    """Check if content has YAML frontmatter."""
    return content.startswith('---\n') and '\n---\n' in content

def has_metadata_macro(content: str) -> bool:
    """Check if content already has the document_metadata macro."""
    return '{{ document_metadata() }}' in content

def add_metadata_macro(content: str) -> str:
    """Add the document_metadata macro call right after frontmatter."""
    # Find the end of frontmatter
    frontmatter_end = content.find('\n---\n', 4)
    if frontmatter_end == -1:
        return content

    # Insert the macro call after frontmatter
    insert_pos = frontmatter_end + 5  # After '\n---\n'
    macro_call = '\n{{ document_metadata() }}\n\n'

    return content[:insert_pos] + macro_call + content[insert_pos:]

def process_file(file_path: Path) -> bool:
    """Process a single markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not has_frontmatter(content):
            return False  # Skip files without frontmatter

        if has_metadata_macro(content):
            print(f"✓ Already has metadata macro: {file_path}")
            return False  # Already has the macro

        # Add the macro
        new_content = add_metadata_macro(content)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✓ Added metadata macro to: {file_path}")
        return True

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all documentation files."""
    docs_dir = Path('docs')

    if not docs_dir.exists():
        print("Error: docs directory not found")
        return

    processed_count = 0
    skipped_count = 0

    # Process all .md files in docs directory recursively
    for md_file in docs_dir.rglob('*.md'):
        # Skip certain directories if needed
        if any(part.startswith('.') for part in md_file.parts):
            continue

        if process_file(md_file):
            processed_count += 1
        else:
            skipped_count += 1

    print(f"\nSummary:")
    print(f"- Files processed: {processed_count}")
    print(f"- Files skipped: {skipped_count}")
    print(f"- Total files checked: {processed_count + skipped_count}")

if __name__ == '__main__':
    main()