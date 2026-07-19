#!/usr/bin/env python3
"""Genera frontmatter para los documentos del árbol EN que no lo tienen.

No inventa contenido: cada campo sale de una fuente real.
  - title:    del encabezado H1 del propio archivo EN (ya está en inglés)
  - tags:     copiados del documento ES equivalente (son slugs, no se traducen)
  - category: la categoría del ES traducida con un mapa explícito
  - updated:  fecha del último commit de git que tocó el archivo EN

Si falta la fuente de un campo, ese campo se omite en vez de rellenarse con un
valor inventado. Un archivo sin H1 ni ES equivalente no se toca.

Uso:
    python scripts/backfill_frontmatter_en.py --dry-run
    python scripts/backfill_frontmatter_en.py
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Traducción de categorías ES -> EN, alineada con las ya usadas en docs/en/
CATEGORY_MAP = {
    'Inteligencia Artificial': 'Artificial Intelligence',
    'Redes': 'Networking',
    'Ciberseguridad': 'Cybersecurity',
    'Almacenamiento': 'Storage',
    'Contenedores': 'Containers',
    'Orquestación': 'Orchestration',
    'Monitoreo': 'Monitoring',
    'Virtualización': 'Virtualization',
    'Sistema Operativo': 'Operating System',
    'Bases de Datos': 'Databases',
    'Copias de Seguridad': 'Backups',
    'Gestión de Identidad': 'Identity Management',
    'Infraestructura como Código': 'Infrastructure as Code',
    'Automatización': 'Automation',
    'Desarrollo': 'Development',
    'Cloud Computing': 'Cloud Computing',
    'Load Balancing': 'Load Balancing',
    'CI/CD': 'CI/CD',
    'General': 'General',
}

FRONTMATTER_RE = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)


def git_date(path):
    r = subprocess.run(['git', 'log', '-1', '--format=%ad', '--date=short', '--', str(path)],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def field_from_es(es_path, field):
    """Extrae un campo del frontmatter del documento ES equivalente."""
    if not es_path.is_file():
        return None
    content = es_path.read_text(encoding='utf-8')
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None
    found = re.search(rf'^{field}:\s*(.+)$', match.group(1), re.MULTILINE)
    return found.group(1).strip() if found else None


def build_frontmatter(en_path, es_path):
    """Devuelve (texto_frontmatter, motivo_si_none)."""
    content = en_path.read_text(encoding='utf-8')
    if FRONTMATTER_RE.match(content):
        return None, 'ya_tiene'

    h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not h1:
        return None, 'sin_h1'  # sin título fiable: no inventamos uno

    lines = ['---', f'title: "{h1.group(1).strip()}"']

    tags = field_from_es(es_path, 'tags')
    if tags:
        lines.append(f'tags: {tags}')

    es_category = field_from_es(es_path, 'category')
    if es_category:
        en_category = CATEGORY_MAP.get(es_category)
        if en_category:
            lines.append(f'category: {en_category}')

    date = git_date(en_path)
    if date:
        lines.append(f'updated: {date}')

    lines.append('---')
    return '\n'.join(lines) + '\n\n', None


def main():
    parser = argparse.ArgumentParser(description='Genera frontmatter en el árbol EN')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    en_root = Path('docs/en')
    if not en_root.is_dir():
        sys.exit('no existe docs/en')

    counts = {}
    skipped = []
    for en_path in sorted(en_root.rglob('*.md')):
        rel = en_path.relative_to(en_root)
        es_path = Path('docs') / rel

        frontmatter, motivo = build_frontmatter(en_path, es_path)
        if frontmatter is None:
            counts[motivo] = counts.get(motivo, 0) + 1
            if motivo == 'sin_h1':
                skipped.append(f'  {en_path}: sin H1, no se genera título inventado')
            continue

        if args.dry_run:
            print(f'  [dry-run] {en_path}')
            print('    ' + frontmatter.strip().replace('\n', '\n    '))
        else:
            en_path.write_text(frontmatter + en_path.read_text(encoding='utf-8'),
                               encoding='utf-8')
        counts['generado'] = counts.get('generado', 0) + 1

    print('\nResumen:')
    for k, v in sorted(counts.items()):
        print(f'  {k}: {v}')
    if skipped:
        print('\nNo modificados:')
        print('\n'.join(skipped))
    if args.dry_run:
        print('\n(dry-run: no se ha escrito nada)')


if __name__ == '__main__':
    main()
