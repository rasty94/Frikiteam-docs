#!/usr/bin/env python3
"""
Script para validar y mostrar estadísticas de metadatos en archivos de documentación.

Funciones:
- Validar que todos los archivos tienen metadatos completos
- Mostrar estadísticas por categoría, dificultad, etc.
- Identificar archivos con metadatos incompletos
- Generar reportes de calidad de metadatos

Uso:
    python scripts/validate_metadata.py [--report] [--category CATEGORY]
"""

import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import argparse


def extract_frontmatter(file_path):
    """Extrae y parsea el frontmatter de un archivo."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Buscar frontmatter YAML
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return None

        frontmatter = frontmatter_match.group(1)

        # Parsear campos
        fields = {}
        current_key = None
        current_list = None

        for line in frontmatter.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Detectar listas YAML
            if line.startswith('- '):
                if current_list is not None:
                    current_list.append(line[2:].strip().strip('"').strip("'"))
                continue

            # Detectar arrays en una línea
            if '[' in line and ']' in line:
                key_match = re.match(r'^(\w+):\s*\[(.*)\]', line)
                if key_match:
                    key, value_str = key_match.groups()
                    # Parsear valores separados por coma
                    values = [v.strip().strip('"').strip("'") for v in value_str.split(',')]
                    fields[key] = values
                    continue

            # Detectar inicio de lista
            if line.endswith(':'):
                current_key = line[:-1]
                current_list = []
                fields[current_key] = current_list
                continue

            # Campo regular
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                fields[key] = value
                current_key = None
                current_list = None

        return fields

    except Exception as e:
        return {'error': str(e)}


def validate_metadata_fields(fields):
    """Valida que los campos requeridos estén presentes."""
    required_fields = ['title', 'updated', 'difficulty', 'category', 'status']
    recommended_fields = ['description', 'estimated_time', 'last_reviewed', 'prerequisites', 'reviewers', 'contributors']

    missing_required = []
    missing_recommended = []

    for field in required_fields:
        if field not in fields:
            missing_required.append(field)

    for field in recommended_fields:
        if field not in fields:
            missing_recommended.append(field)

    return missing_required, missing_recommended


def analyze_metadata(docs_path, category_filter=None):
    """Analiza metadatos de todos los archivos."""
    stats = {
        'total_files': 0,
        'files_with_frontmatter': 0,
        'files_without_frontmatter': 0,
        'complete_metadata': 0,
        'missing_required': 0,
        'by_category': defaultdict(int),
        'by_difficulty': defaultdict(int),
        'by_status': defaultdict(int),
        'estimated_times': [],
        'issues': []
    }

    for md_file in Path(docs_path).rglob('*.md'):
        # Ignorar archivos de blog e índices
        if 'blog' in str(md_file) or 'index.md' in str(md_file):
            continue

        if category_filter and category_filter.lower() not in str(md_file).lower():
            continue

        stats['total_files'] += 1
        fields = extract_frontmatter(md_file)

        if not fields:
            stats['files_without_frontmatter'] += 1
            stats['issues'].append({
                'file': md_file,
                'issue': 'Sin frontmatter',
                'severity': 'high'
            })
            continue

        if 'error' in fields:
            stats['issues'].append({
                'file': md_file,
                'issue': f'Error parseando frontmatter: {fields["error"]}',
                'severity': 'high'
            })
            continue

        stats['files_with_frontmatter'] += 1

        # Validar campos
        missing_required, missing_recommended = validate_metadata_fields(fields)

        if missing_required:
            stats['missing_required'] += 1
            stats['issues'].append({
                'file': md_file,
                'issue': f'Campos requeridos faltantes: {", ".join(missing_required)}',
                'severity': 'high'
            })

        # Contar por categoría
        if 'category' in fields:
            stats['by_category'][fields['category']] += 1

        # Contar por dificultad
        if 'difficulty' in fields:
            stats['by_difficulty'][fields['difficulty']] += 1

        # Contar por status
        if 'status' in fields:
            stats['by_status'][fields['status']] += 1

        # Recopilar tiempos estimados
        if 'estimated_time' in fields:
            # Parsear tiempo (ej: "5 min", "2h 30min")
            time_str = fields['estimated_time']
            try:
                if 'h' in time_str:
                    # Horas
                    if ' ' in time_str:
                        hours, minutes_part = time_str.split('h ')
                        hours = int(hours)
                        minutes = int(minutes_part.replace('min', ''))
                    else:
                        hours = int(time_str.replace('h', ''))
                        minutes = 0
                    total_minutes = hours * 60 + minutes
                else:
                    # Solo minutos
                    total_minutes = int(time_str.replace('min', ''))
                stats['estimated_times'].append(total_minutes)
            except (ValueError, AttributeError):
                pass  # Ignorar errores de parsing

        # Verificar si metadata está completo
        if not missing_required and len(missing_recommended) <= 2:  # Máximo 2 campos recomendados faltantes
            stats['complete_metadata'] += 1

    return stats


def print_report(stats):
    """Imprime un reporte completo de estadísticas."""
    print("📊 REPORTE DE METADATOS DE DOCUMENTACIÓN")
    print("=" * 60)
    print(f"📁 Total de archivos analizados: {stats['total_files']}")
    print(f"📄 Con frontmatter: {stats['files_with_frontmatter']} ({stats['files_with_frontmatter']/stats['total_files']*100:.1f}%)")
    print(f"❌ Sin frontmatter: {stats['files_without_frontmatter']} ({stats['files_without_frontmatter']/stats['total_files']*100:.1f}%)")
    print(f"✅ Metadatos completos: {stats['complete_metadata']} ({stats['complete_metadata']/stats['files_with_frontmatter']*100:.1f}%)")
    print(f"⚠️  Con campos requeridos faltantes: {stats['missing_required']}")
    print()

    if stats['by_category']:
        print("📂 DISTRIBUCIÓN POR CATEGORÍA:")
        for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")
        print()

    if stats['by_difficulty']:
        print("🎯 DISTRIBUCIÓN POR DIFICULTAD:")
        difficulties = ['beginner', 'intermediate', 'advanced', 'expert']
        for difficulty in difficulties:
            count = stats['by_difficulty'].get(difficulty, 0)
            if count > 0:
                print(f"  {difficulty.title()}: {count}")
        print()

    if stats['by_status']:
        print("📋 DISTRIBUCIÓN POR ESTADO:")
        for status, count in sorted(stats['by_status'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {status.title()}: {count}")
        print()

    if stats['estimated_times']:
        avg_time = sum(stats['estimated_times']) / len(stats['estimated_times'])
        min_time = min(stats['estimated_times'])
        max_time = max(stats['estimated_times'])

        print("⏱️  ESTADÍSTICAS DE TIEMPO ESTIMADO:")
        print(f"  Promedio: {avg_time:.0f} minutos")
        print(f"  Mínimo: {min_time} minutos")
        print(f"  Máximo: {max_time} minutos")
        print()

    if stats['issues']:
        print("🚨 PROBLEMAS IDENTIFICADOS:")
        high_priority = [i for i in stats['issues'] if i['severity'] == 'high']
        medium_priority = [i for i in stats['issues'] if i['severity'] == 'medium']

        if high_priority:
            print("  🔴 ALTA PRIORIDAD:")
            for issue in high_priority[:5]:  # Mostrar solo primeros 5
                print(f"    {issue['file']}: {issue['issue']}")
            if len(high_priority) > 5:
                print(f"    ... y {len(high_priority) - 5} más")

        if medium_priority:
            print("  🟡 MEDIANA PRIORIDAD:")
            for issue in medium_priority[:3]:
                print(f"    {issue['file'].relative_to(Path.cwd())}: {issue['issue']}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Validar metadatos de documentación')
    parser.add_argument('--docs-path', type=str, default='docs/doc',
                        help='Ruta a la documentación (default: docs/doc)')
    parser.add_argument('--category', type=str,
                        help='Analizar solo archivos de una categoría específica')
    parser.add_argument('--report', action='store_true',
                        help='Generar reporte completo')

    args = parser.parse_args()

    print("🔍 Analizando metadatos de documentación...")
    print(f"   Ruta: {args.docs_path}")
    if args.category:
        print(f"   Categoría: {args.category}")
    print()

    stats = analyze_metadata(Path(args.docs_path), args.category)

    if args.report:
        print_report(stats)
    else:
        # Resumen rápido
        print("📊 RESUMEN RÁPIDO:")
        print(f"  Total archivos: {stats['total_files']}")
        print(f"  Con frontmatter: {stats['files_with_frontmatter']}")
        print(f"  Metadatos completos: {stats['complete_metadata']}")
        print(f"  Problemas: {len(stats['issues'])}")

        if stats['by_difficulty']:
            print("\n🎯 Por dificultad:")
            for diff, count in stats['by_difficulty'].items():
                print(f"  {diff}: {count}")

        if stats['issues']:
            print(f"\n🚨 {len(stats['issues'])} archivos con problemas")
            print("Ejecuta con --report para ver detalles")


if __name__ == '__main__':
    main()