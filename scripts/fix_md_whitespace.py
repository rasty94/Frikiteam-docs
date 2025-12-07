#!/usr/bin/env python3
"""Fix common Markdown whitespace issues automatically.

Fixes applied:
- Ensure a blank line before headings
- Ensure a blank line before top-level list blocks
- Reduce over-indented list items (4 spaces -> 2 spaces)

Run from the repo root. It will skip `site/`, `.git/`, `venv/` and `node_modules/`.
"""
import re
from pathlib import Path
EXCLUDE_DIRS = {"site", ".git", "venv", "node_modules"}

FENCE_RE = re.compile(r'^```')
LIST_RE = re.compile(r'^\s*[-+*]\s+')
INDENTED_LIST_RE = re.compile(r'^( {4,})([-+*]\s+)')


def should_skip(path: Path) -> bool:
    parts = path.parts
    return any(p in EXCLUDE_DIRS for p in parts)


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    new_lines = []
    in_code = False
    changed = False

    for idx, line in enumerate(lines):
        if FENCE_RE.match(line):
            new_lines.append(line)
            in_code = not in_code
            continue

        if in_code:
            new_lines.append(line)
            continue

        # Normalize trailing spaces removal
        raw = line.rstrip()

        # Reduce 4+ space indents for list items to 2 spaces
        m = INDENTED_LIST_RE.match(raw)
        if m:
            raw = '  ' + m.group(2) + raw[m.end():]
            changed = True

        # Ensure blank line before headings
        if raw.startswith('#'):
            if new_lines and new_lines[-1].strip() != '':
                new_lines.append('')
                changed = True
            new_lines.append(raw)
            continue

        # Ensure blank line before lists (unless previous is a list or heading or blockquote or code fence)
        if LIST_RE.match(raw):
            if new_lines:
                prev = new_lines[-1].strip()
                if prev != '' and not prev.startswith(('#', '>', '-', '*', '+', '```')):
                    new_lines.append('')
                    changed = True
            new_lines.append(raw)
            continue

        new_lines.append(raw)

    # Preserve final newline if original had it
    final_text = '\n'.join(new_lines) + ("\n" if text.endswith('\n') else '')
    if final_text != text:
        path.write_text(final_text, encoding='utf-8')
        return True
    return False


def main():
    root = Path('.').resolve()
    md_files = sorted(root.rglob('*.md'))
    fixed = []
    for p in md_files:
        if should_skip(p):
            continue
        # skip files inside site build dir explicitly
        if 'site' in p.parts:
            continue
        try:
            if fix_file(p):
                fixed.append(str(p))
        except Exception as e:
            print(f"Error processing {p}: {e}")

    if fixed:
        print('Fixed files:')
        for f in fixed:
            print(' -', f)
    else:
        print('No changes made')


if __name__ == '__main__':
    main()
