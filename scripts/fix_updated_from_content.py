#!/usr/bin/env python3
"""Corrige el campo `updated` para que refleje el último cambio de CONTENIDO.

El problema que resuelve: 95 documentos comparten `updated: 2026-01-25` porque
ese día se pasó un sellado masivo de metadatos. Esa fecha no dice cuándo cambió
el documento, solo cuándo se le añadió frontmatter. Con eso, `check_sync.py`
compara fechas que no significan nada y reporta como desincronizadas
traducciones que están bien.

Este script recorre el historial de cada archivo y busca el último commit cuyo
diff tocó el CUERPO del documento, ignorando los commits que solo cambiaron
frontmatter. Esa fecha sí es una afirmación verificable.

Uso:
    python scripts/fix_updated_from_content.py --dry-run
    python scripts/fix_updated_from_content.py --path docs/en
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Claves de frontmatter: un cambio que solo toca estas líneas no es contenido.
META_KEYS = (
    'title', 'description', 'keywords', 'tags', 'updated', 'difficulty',
    'estimated_time', 'category', 'status', 'last_reviewed', 'prerequisites',
    'reviewers', 'contributors', 'date', 'draft', 'sync_date', 'author', 'time',
)
META_LINE_RE = re.compile(r'^[+-](' + '|'.join(META_KEYS) + r'):')
LIST_ITEM_RE = re.compile(r'^[+-]\s+-\s')      # ítems de listas YAML
DELIM_RE = re.compile(r'^[+-]-{3}\s*$')        # delimitadores ---
FRONTMATTER_RE = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def commits_for(path):
    """[(sha, fecha)] del más reciente al más antiguo."""
    out = run(['git', 'log', '--format=%H %ad', '--date=short', '--', str(path)])
    return [tuple(line.split()) for line in out.splitlines() if line.strip()]


def touched_body(sha, path):
    """True si ese commit cambió algo fuera del frontmatter."""
    diff = run(['git', 'show', sha, '--unified=0', '--format=', '--', str(path)])
    for line in diff.splitlines():
        if not line or line[0] not in '+-':
            continue
        if line.startswith(('+++', '---')) and len(line) > 3:
            continue
        if DELIM_RE.match(line) or META_LINE_RE.match(line) or LIST_ITEM_RE.match(line):
            continue
        if line[1:].strip() == '':
            continue
        return True
    return False


def last_content_date(path):
    """Fecha del último commit que tocó el cuerpo; None si no se puede saber."""
    history = commits_for(path)
    for sha, date in history:
        if touched_body(sha, path):
            return date
    # Solo hubo cambios de metadatos: usar el commit inicial (cuando nació)
    return history[-1][1] if history else None


def main():
    parser = argparse.ArgumentParser(
        description="Ajusta 'updated' al último cambio real de contenido")
    parser.add_argument('--path', default='docs', help='directorio a procesar')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    root = Path(args.path)
    if not root.is_dir():
        sys.exit(f'no existe: {root}')

    cambiados, iguales, sin_fm = 0, 0, 0
    for md in sorted(root.rglob('*.md')):
        content = md.read_text(encoding='utf-8')
        match = FRONTMATTER_RE.match(content)
        if not match:
            sin_fm += 1
            continue

        real = last_content_date(md)
        if not real:
            continue

        actual = re.search(r'^updated:\s*(\S+)', match.group(1), re.MULTILINE)
        actual_val = actual.group(1) if actual else None
        if actual_val == real:
            iguales += 1
            continue

        if actual:
            nuevo_fm = re.sub(r'^updated:\s*\S+', f'updated: {real}',
                              match.group(1), count=1, flags=re.MULTILINE)
        else:
            nuevo_fm = match.group(1).rstrip() + f'\nupdated: {real}'

        if args.dry_run:
            print(f'  {md}: {actual_val or "(sin campo)"} -> {real}')
        else:
            md.write_text(content.replace(match.group(0), f'---\n{nuevo_fm}\n---\n', 1),
                          encoding='utf-8')
        cambiados += 1

    print(f'\nResumen:\n  ajustados: {cambiados}\n  ya correctos: {iguales}'
          f'\n  sin frontmatter: {sin_fm}')
    if args.dry_run:
        print('\n(dry-run: no se ha escrito nada)')


if __name__ == '__main__':
    main()
