#!/usr/bin/env python3
"""
Script para detectar y gestionar sincronización entre documentación ES y EN.

Funciones:
- Detectar archivos ES más recientes que sus versiones EN
- Añadir notas de "TRADUCCIÓN PENDIENTE" en archivos EN desactualizados
- Limpiar notas obsoletas cuando la traducción está al día
- Reportar estado de sincronización

Uso:
    python scripts/check_sync.py [--fix] [--verbose]
"""

import os
import re
from datetime import datetime
from pathlib import Path
import argparse


def get_file_modification_time(file_path):
    """Obtiene la fecha de modificación de un archivo."""
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path))
    except OSError:
        return None


def extract_updated_date(file_path):
    """Extrae la fecha 'updated' del frontmatter YAML."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Buscar frontmatter YAML
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return None

        frontmatter = frontmatter_match.group(1)

        # Buscar campo 'updated'
        updated_match = re.search(r'^updated:\s*(\d{4}-\d{2}-\d{2})', frontmatter, re.MULTILINE)
        if updated_match:
            date_str = updated_match.group(1)
            return datetime.strptime(date_str, '%Y-%m-%d')

        return None
    except Exception as e:
        print(f"Error leyendo {file_path}: {e}")
        return None


def has_translation_pending_note(file_path):
    """Verifica si un archivo EN tiene nota de traducción pendiente."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return '🚧 TRANSLATION PENDING' in content
    except Exception:
        return False


def add_translation_pending_note(file_path, es_updated_date):
    """Añade nota de traducción pendiente a un archivo EN."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Si ya tiene la nota, actualizar la fecha
        if '🚧 TRANSLATION PENDING' in content:
            # Actualizar fecha en nota existente
            new_note = f"🚧 **TRANSLATION PENDING** - Last updated in Spanish: {es_updated_date.strftime('%Y-%m-%d')}\n"
            content = re.sub(r'🚧 \*\*TRANSLATION PENDING\*\* - Last updated in Spanish: \d{4}-\d{2}-\d{2}\n', new_note, content)
        else:
            # Añadir nota al principio del archivo (después del título si existe)
            lines = content.split('\n')
            insert_index = 0

            # Buscar el final del frontmatter o el título
            for i, line in enumerate(lines):
                if line.startswith('# '):  # Título principal
                    insert_index = i + 1
                    break
                elif line == '---' and i > 0:  # Fin del frontmatter
                    insert_index = i + 1
                    break

            # Insertar nota
            new_note = f"\n🚧 **TRANSLATION PENDING** - Last updated in Spanish: {es_updated_date.strftime('%Y-%m-%d')}\n"
            lines.insert(insert_index, new_note)
            content = '\n'.join(lines)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"Error añadiendo nota a {file_path}: {e}")
        return False


def remove_translation_pending_note(file_path):
    """Remueve nota de traducción pendiente si la traducción está al día."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remover la nota
        content = re.sub(r'\n🚧 \*\*TRANSLATION PENDING\*\* - Last updated in Spanish: \d{4}-\d{2}-\d{2}\n', '\n', content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"Error removiendo nota de {file_path}: {e}")
        return False


def check_sync_status(es_docs_path, en_docs_path, fix=False, verbose=False):
    """Verifica el estado de sincronización entre ES y EN."""
    out_of_sync = []
    up_to_date = []
    errors = []

    # Recorrer archivos ES
    for es_file in Path(es_docs_path).rglob('*.md'):
        # Ignorar archivos de blog e índices
        if 'blog' in str(es_file) or 'index.md' in str(es_file):
            continue

        # Construir ruta correspondiente en EN
        relative_path = es_file.relative_to(es_docs_path)
        en_file = en_docs_path / relative_path

        if not en_file.exists():
            if verbose:
                print(f"⚠️  Archivo EN no existe: {en_file}")
            continue

        # Comparar fechas de actualización
        es_updated = extract_updated_date(es_file)
        en_updated = extract_updated_date(en_file)

        if es_updated is None:
            if verbose:
                print(f"⚠️  Archivo ES sin fecha updated: {es_file}")
            continue

        if en_updated is None:
            # EN no tiene fecha updated, verificar si tiene nota de traducción pendiente
            has_note = has_translation_pending_note(en_file)
            if not has_note:
                out_of_sync.append((es_file, en_file, es_updated, None, "EN sin fecha updated"))
                if fix:
                    success = add_translation_pending_note(en_file, es_updated)
                    if success:
                        print(f"✅ Añadida nota de traducción pendiente: {en_file}")
                    else:
                        errors.append(f"Error añadiendo nota: {en_file}")
            else:
                out_of_sync.append((es_file, en_file, es_updated, None, "EN tiene nota pendiente"))
        elif es_updated > en_updated:
            # ES es más reciente
            has_note = has_translation_pending_note(en_file)
            if not has_note:
                out_of_sync.append((es_file, en_file, es_updated, en_updated, "ES más reciente"))
                if fix:
                    success = add_translation_pending_note(en_file, es_updated)
                    if success:
                        print(f"✅ Añadida nota de traducción pendiente: {en_file}")
                    else:
                        errors.append(f"Error añadiendo nota: {en_file}")
            else:
                out_of_sync.append((es_file, en_file, es_updated, en_updated, "ES más reciente (nota existe)"))
        else:
            # Están sincronizados
            has_note = has_translation_pending_note(en_file)
            if has_note:
                up_to_date.append((es_file, en_file, es_updated, en_updated, "Sincronizado pero nota pendiente"))
                if fix:
                    success = remove_translation_pending_note(en_file)
                    if success:
                        print(f"✅ Removida nota obsoleta: {en_file}")
                    else:
                        errors.append(f"Error removiendo nota: {en_file}")
            else:
                up_to_date.append((es_file, en_file, es_updated, en_updated, "Sincronizado"))

    return out_of_sync, up_to_date, errors


def main():
    parser = argparse.ArgumentParser(description='Verificar sincronización ES/EN')
    parser.add_argument('--fix', action='store_true',
                        help='Aplicar correcciones automáticamente (añadir/remover notas)')
    parser.add_argument('--verbose', action='store_true',
                        help='Mostrar información detallada')
    parser.add_argument('--es-path', type=str, default='docs',
                        help='Ruta a documentación ES (default: docs)')
    parser.add_argument('--en-path', type=str, default='docs/en',
                        help='Ruta a documentación EN (default: docs/en)')

    args = parser.parse_args()

    print("🔄 Verificando sincronización ES/EN...")
    print(f"   ES: {args.es_path}")
    print(f"   EN: {args.en_path}")
    print(f"   Modo fix: {'Sí' if args.fix else 'No'}")
    print()

    out_of_sync, up_to_date, errors = check_sync_status(
        Path(args.es_path), Path(args.en_path), args.fix, args.verbose
    )

    if out_of_sync:
        print(f"📋 ARCHIVOS DESINCRONIZADOS ({len(out_of_sync)}):")
        print("=" * 80)
        for es_file, en_file, es_date, en_date, reason in out_of_sync:
            print(f"  ES: {es_file}")
            print(f"  EN: {en_file}")
            print(f"  Estado: {reason}")
            if es_date:
                print(f"  ES updated: {es_date.strftime('%Y-%m-%d')}")
            if en_date:
                print(f"  EN updated: {en_date.strftime('%Y-%m-%d')}")
            print()

    if up_to_date and args.verbose:
        print(f"✅ ARCHIVOS SINCRONIZADOS ({len(up_to_date)}):")
        print("=" * 80)
        for es_file, en_file, es_date, en_date, reason in up_to_date[:10]:  # Mostrar solo primeros 10
            print(f"  {es_file} - {reason}")
        if len(up_to_date) > 10:
            print(f"  ... y {len(up_to_date) - 10} más")
        print()

    if errors:
        print(f"❌ ERRORES ({len(errors)}):")
        print("=" * 80)
        for error in errors:
            print(f"  {error}")
        print()

    print("=" * 80)
    print("📊 RESUMEN:")
    print(f"  - Desincronizados: {len(out_of_sync)}")
    print(f"  - Sincronizados: {len(up_to_date)}")
    print(f"  - Errores: {len(errors)}")

    if out_of_sync and not args.fix:
        print("\n💡 Ejecuta con --fix para aplicar correcciones automáticamente")


if __name__ == '__main__':
    main()