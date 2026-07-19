#!/usr/bin/env python3
"""Rellena el campo `updated` de los documentos que no lo tienen, usando la fecha
del último commit de git que tocó cada archivo.

Por qué existe, habiendo ya un `scripts/add_updated_field.py`: aquel escribe una
fecha FIJA hardcodeada, lo que inventa un dato. Aquí la fecha sale del historial,
así que es verificable. Eso importa porque `scripts/check_sync.py` compara la
fecha de ES contra la de EN para detectar traducciones obsoletas: si rellenamos
con una fecha inventada, un documento realmente desactualizado pasaría por
sincronizado y el problema quedaría oculto.

Uso:
    python scripts/backfill_updated_from_git.py --dry-run     # ver qué haría
    python scripts/backfill_updated_from_git.py               # aplicar a docs/en
    python scripts/backfill_updated_from_git.py --path docs   # otro árbol
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)


def last_commit_date(path):
    """Fecha (YYYY-MM-DD) del último commit que tocó el archivo, o None."""
    result = subprocess.run(
        ['git', 'log', '-1', '--format=%ad', '--date=short', '--', str(path)],
        capture_output=True, text=True)
    if result.returncode != 0:
        return None
    date = result.stdout.strip()
    return date or None


def process(path, dry_run=False):
    """Devuelve (estado, detalle) para un archivo."""
    content = path.read_text(encoding='utf-8')

    match = FRONTMATTER_RE.match(content)
    if not match:
        return 'sin_frontmatter', 'no tiene frontmatter; no se toca'

    frontmatter = match.group(1)
    if re.search(r'^updated:', frontmatter, re.MULTILINE):
        return 'ya_tiene', None

    date = last_commit_date(path)
    if not date:
        return 'sin_historial', 'sin commits (¿sin trackear?); no se toca'

    new_frontmatter = frontmatter.rstrip() + f'\nupdated: {date}'
    new_content = content.replace(match.group(0),
                                  f'---\n{new_frontmatter}\n---\n', 1)
    if not dry_run:
        path.write_text(new_content, encoding='utf-8')
    return 'actualizado', date


def main():
    parser = argparse.ArgumentParser(
        description="Rellena 'updated' con la fecha del último commit")
    parser.add_argument('--path', default='docs/en', help='directorio a procesar')
    parser.add_argument('--dry-run', action='store_true', help='no escribe nada')
    args = parser.parse_args()

    root = Path(args.path)
    if not root.is_dir():
        sys.exit(f'no existe el directorio: {root}')

    counts = {}
    avisos = []
    for md in sorted(root.rglob('*.md')):
        estado, detalle = process(md, args.dry_run)
        counts[estado] = counts.get(estado, 0) + 1
        if estado == 'actualizado' and args.dry_run:
            print(f'  [dry-run] {md} -> updated: {detalle}')
        elif estado in ('sin_frontmatter', 'sin_historial'):
            avisos.append(f'  {md}: {detalle}')

    print('\nResumen:')
    for estado, n in sorted(counts.items()):
        print(f'  {estado}: {n}')
    if avisos:
        print('\nNo modificados:')
        print('\n'.join(avisos))
    if args.dry_run:
        print('\n(dry-run: no se ha escrito nada)')


if __name__ == '__main__':
    main()
