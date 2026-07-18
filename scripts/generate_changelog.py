#!/usr/bin/env python3
"""Regenera CHANGELOG.md a partir del historial de git.

Agrupa los commits por fecha y lista el mensaje de cada uno junto al número de
archivos tocados. Se puede volver a ejecutar en cualquier momento: reescribe el
fichero entero, así que el changelog nunca se queda obsoleto a mano.

Uso:
    python scripts/generate_changelog.py                 # escribe CHANGELOG.md
    python scripts/generate_changelog.py --stdout        # solo imprime
    python scripts/generate_changelog.py --since 2026-01-01
"""
import argparse
import subprocess
import sys
from collections import OrderedDict

SEP = '\x1f'  # separador de campos poco probable en un mensaje de commit


def run_git(args):
    result = subprocess.run(['git'] + args, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f'error de git: {result.stderr.strip()}')
    return result.stdout


def collect_commits(since=None):
    """Devuelve [(fecha, sha, asunto, n_archivos)] del más reciente al más antiguo."""
    args = ['log', '--date=short', '--no-merges',
            f'--pretty=format:{SEP}%h{SEP}%ad{SEP}%s', '--name-only']
    if since:
        args.append(f'--since={since}')

    commits = []
    current = None
    files = 0
    for line in run_git(args).splitlines():
        if line.startswith(SEP):
            if current:
                commits.append(current + (files,))
            _, sha, date, subject = line.split(SEP, 3)
            current = (date, sha, subject)
            files = 0
        elif line.strip():
            files += 1
    if current:
        commits.append(current + (files,))
    return commits


def render(commits):
    by_date = OrderedDict()
    for date, sha, subject, n_files in commits:
        by_date.setdefault(date, []).append((sha, subject, n_files))

    out = ['# Changelog', '',
           'Todos los cambios relevantes en el repositorio.',
           '',
           '> Generado con `python scripts/generate_changelog.py`. No editar a mano.',
           '']
    for date, entries in by_date.items():
        out.append(f'## {date}')
        out.append('')
        for sha, subject, n_files in entries:
            plural = 'archivo' if n_files == 1 else 'archivos'
            out.append(f'- `{sha}` {subject} ({n_files} {plural})')
        out.append('')
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description='Regenera CHANGELOG.md desde git')
    parser.add_argument('--output', default='CHANGELOG.md', help='fichero de salida')
    parser.add_argument('--since', help='solo commits desde esta fecha (YYYY-MM-DD)')
    parser.add_argument('--stdout', action='store_true', help='imprimir en vez de escribir')
    args = parser.parse_args()

    commits = collect_commits(args.since)
    if not commits:
        sys.exit('no se encontraron commits')

    content = render(commits)
    if args.stdout:
        print(content)
    else:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'{args.output} regenerado: {len(commits)} commits')


if __name__ == '__main__':
    main()
