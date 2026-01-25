#!/usr/bin/env python3
"""
Script para añadir automáticamente el campo 'updated' a archivos de documentación que no lo tienen.

Uso:
    python scripts/add_updated_field.py [--dry-run] [--files path/to/files.txt]
"""

import os
import re
from datetime import datetime
from pathlib import Path
import argparse


def extract_title_from_content(content):
    """Extrae el título del contenido del archivo."""
    # Buscar título en formato # Título
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()

    # Buscar título en frontmatter
    frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        title_match = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip().strip('"').strip("'")

    return None


def generate_frontmatter(title, file_path):
    """Genera frontmatter básico para un archivo."""
    # Inferir descripción basada en el título y ruta
    description = f"Documentación sobre {title.lower()}" if title else "Documentación técnica"

    # Inferir tags basados en la ruta del archivo
    path_parts = str(file_path).split('/')
    tags = []

    if 'cybersecurity' in path_parts:
        tags.extend(['security', 'cybersecurity'])
    if 'docker' in path_parts:
        tags.append('docker')
    if 'kubernetes' in path_parts:
        tags.append('kubernetes')
    if 'terraform' in path_parts:
        tags.append('terraform')
    if 'ansible' in path_parts:
        tags.append('ansible')
    if 'monitoring' in path_parts:
        tags.append('monitoring')
    if 'networking' in path_parts:
        tags.append('networking')
    if 'storage' in path_parts:
        tags.append('storage')
    if 'ai' in path_parts:
        tags.append('ai')

    if not tags:
        tags = ['documentation']

    frontmatter = f"""---
title: "{title}"
description: "{description}"
tags: {tags}
updated: 2026-01-25
---
"""
    return frontmatter


def add_updated_field_to_file(file_path, dry_run=False):
    """Añade el campo updated a un archivo."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificar si ya tiene campo updated
        if re.search(r'^updated:\s*\d{4}-\d{2}-\d{2}', content, re.MULTILINE):
            return False, "Ya tiene campo updated"

        # Verificar si tiene frontmatter
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)

        if frontmatter_match:
            # Tiene frontmatter, añadir campo updated
            frontmatter = frontmatter_match.group(1)

            # Verificar si ya tiene updated en el frontmatter
            if 'updated:' in frontmatter:
                return False, "Ya tiene campo updated en frontmatter"

            # Añadir campo updated al final del frontmatter
            new_frontmatter = frontmatter.rstrip() + f"\nupdated: 2026-01-25\n"
            new_content = content.replace(frontmatter_match.group(0), f"---\n{new_frontmatter}---")
            action = "Añadido campo updated a frontmatter existente"
        else:
            # No tiene frontmatter, extraer título y crear uno completo
            title = extract_title_from_content(content)
            if not title:
                # Intentar inferir título del nombre del archivo
                filename = Path(file_path).stem.replace('_', ' ').title()
                title = filename

            new_frontmatter = generate_frontmatter(title, file_path)
            new_content = new_frontmatter + '\n' + content.lstrip()
            action = f"Creado frontmatter completo con título: {title}"

        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        return True, action

    except Exception as e:
        return False, f"Error: {str(e)}"


def get_files_without_updated(docs_path):
    """Obtiene lista de archivos sin campo updated buscando directamente."""
    files_without_updated = []

    # Buscar todos los archivos .md en la ruta especificada
    for md_file in Path(docs_path).rglob('*.md'):
        # Ignorar archivos de blog e índices
        if 'blog' in str(md_file) or 'index.md' in str(md_file):
            continue

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Verificar si tiene campo updated
            if not re.search(r'^updated:\s*\d{4}-\d{2}-\d{2}', content, re.MULTILINE):
                files_without_updated.append(md_file)

        except Exception as e:
            print(f"Error leyendo {md_file}: {e}")
            continue

    return files_without_updated


def main():
    parser = argparse.ArgumentParser(description='Añadir campo updated a archivos sin él')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostrar cambios sin aplicarlos')
    parser.add_argument('--docs-path', type=str, default='docs/doc',
                        help='Ruta a la documentación (default: docs/doc)')
    parser.add_argument('--max-files', type=int, default=None,
                        help='Máximo número de archivos a procesar')

    args = parser.parse_args()

    docs_path = Path(args.docs_path)

    print("🔍 Buscando archivos sin campo 'updated'...")
    print(f"   Ruta: {docs_path}")
    print(f"   Modo dry-run: {'Sí' if args.dry_run else 'No'}")
    print()

    # Obtener lista de archivos sin updated
    files_to_process = get_files_without_updated(docs_path)

    if not files_to_process:
        print("✅ No se encontraron archivos sin campo 'updated'")
        return

    if args.max_files:
        files_to_process = files_to_process[:args.max_files]

    print(f"📝 Procesando {len(files_to_process)} archivos...")
    print()

    processed = 0
    errors = 0

    for file_path in files_to_process:
        if not file_path.exists():
            print(f"⚠️  Archivo no encontrado: {file_path}")
            errors += 1
            continue

        success, message = add_updated_field_to_file(file_path, args.dry_run)

        if success:
            status = "✅" if not args.dry_run else "📋"
            print(f"{status} {file_path.relative_to(docs_path.parent)} - {message}")
            processed += 1
        else:
            print(f"❌ {file_path.relative_to(docs_path.parent)} - {message}")
            errors += 1

    print()
    print("=" * 60)
    print("📊 RESUMEN:")
    print(f"  - Procesados: {processed}")
    print(f"  - Errores: {errors}")
    print(f"  - Total: {len(files_to_process)}")

    if args.dry_run:
        print("\n💡 Ejecuta sin --dry-run para aplicar los cambios")


if __name__ == '__main__':
    main()