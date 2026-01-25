#!/usr/bin/env python3
"""
Script para expandir metadatos en archivos de documentación.

Añade campos avanzados como:
- difficulty: Nivel de dificultad (beginner, intermediate, advanced, expert)
- estimated_time: Tiempo estimado de lectura/completado
- reviewers: Lista de revisores
- last_reviewed: Fecha de última revisión
- prerequisites: Requisitos previos
- category: Categoría principal
- status: Estado del documento
- contributors: Contribuidores principales

Uso:
    python scripts/expand_metadata.py [--dry-run] [--category CATEGORY]
"""

import os
import re
from datetime import datetime
from pathlib import Path
import argparse


def infer_difficulty_from_content(content, file_path):
    """Infere dificultad basada en contenido y ruta."""
    path_str = str(file_path).lower()

    # Palabras clave que indican dificultad
    beginner_keywords = ['introducción', 'primeros pasos', 'básico', 'fundamentos', 'instalación', 'quickstart']
    intermediate_keywords = ['avanzado', 'configuración', 'optimización', 'troubleshooting', 'integración']
    advanced_keywords = ['arquitectura', 'escalado', 'producción', 'enterprise', 'cluster', 'distribuido']
    expert_keywords = ['debugging', 'performance tuning', 'security hardening', 'disaster recovery']

    content_lower = content.lower()

    # Contar ocurrencias de palabras clave
    beginner_count = sum(1 for kw in beginner_keywords if kw in content_lower)
    intermediate_count = sum(1 for kw in intermediate_keywords if kw in content_lower)
    advanced_count = sum(1 for kw in advanced_keywords if kw in content_lower)
    expert_count = sum(1 for kw in expert_keywords if kw in content_lower)

    # Inferir por ruta
    if 'quickstart' in path_str or 'base' in path_str or 'fundamentals' in path_str:
        return 'beginner'
    elif 'advanced' in path_str or 'troubleshooting' in path_str or 'security' in path_str:
        return 'intermediate'
    elif 'enterprise' in path_str or 'production' in path_str or 'cluster' in path_str:
        return 'advanced'
    elif 'tuning' in path_str or 'optimization' in path_str:
        return 'expert'

    # Por conteo de palabras clave
    max_count = max(beginner_count, intermediate_count, advanced_count, expert_count)
    if max_count == 0:
        return 'intermediate'  # default

    if expert_count == max_count:
        return 'expert'
    elif advanced_count == max_count:
        return 'advanced'
    elif intermediate_count == max_count:
        return 'intermediate'
    else:
        return 'beginner'


def infer_estimated_time(content):
    """Estima tiempo de lectura basado en longitud del contenido."""
    word_count = len(content.split())

    # Aproximadamente 200 palabras por minuto de lectura
    minutes = max(1, round(word_count / 200))

    if minutes <= 5:
        return f"{minutes} min"
    elif minutes <= 30:
        return f"{minutes} min"
    else:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}min"


def infer_category(file_path):
    """Infere categoría basada en la ruta del archivo."""
    path_parts = str(file_path).split('/')

    category_map = {
        'ai': 'Inteligencia Artificial',
        'cybersecurity': 'Ciberseguridad',
        'networking': 'Redes',
        'storage': 'Almacenamiento',
        'docker': 'Contenedores',
        'kubernetes': 'Orquestación',
        'terraform': 'Infraestructura como Código',
        'ansible': 'Automatización',
        'monitoring': 'Monitoreo',
        'backups': 'Copias de Seguridad',
        'linux': 'Sistema Operativo',
        'programming': 'Desarrollo',
        'cicd': 'CI/CD',
        'haproxy': 'Load Balancing',
        'proxmox': 'Virtualización',
        'openstack': 'Cloud Computing',
        'databases': 'Bases de Datos',
        'identity': 'Gestión de Identidad'
    }

    for part in path_parts:
        if part in category_map:
            return category_map[part]

    return 'General'


def infer_prerequisites(file_path, difficulty):
    """Infere prerrequisitos basados en ruta y dificultad."""
    path_str = str(file_path).lower()
    prereqs = []

    # Prerrequisitos básicos
    if difficulty in ['intermediate', 'advanced', 'expert']:
        prereqs.append('Conocimientos básicos de DevOps')

    # Prerrequisitos específicos por tecnología
    if 'kubernetes' in path_str:
        prereqs.append('Docker básico')
    elif 'terraform' in path_str:
        prereqs.append('Conceptos de cloud')
    elif 'ansible' in path_str:
        prereqs.append('SSH y Linux básico')
    elif 'networking' in path_str:
        prereqs.append('Fundamentos de redes')
    elif 'ai' in path_str:
        prereqs.append('Python básico')
    elif 'cybersecurity' in path_str:
        prereqs.append('Linux intermedio')

    if not prereqs:
        prereqs.append('Ninguno')

    return prereqs


def expand_frontmatter(file_path, dry_run=False):
    """Expande el frontmatter con campos adicionales."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificar si tiene frontmatter
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return False, "No tiene frontmatter"

        frontmatter = frontmatter_match.group(1)
        original_frontmatter = frontmatter

        # Parsear campos existentes
        existing_fields = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                existing_fields[key.strip()] = value.strip()

        # Campos a añadir/modificar
        updates = {}

        # Difficulty
        if 'difficulty' not in existing_fields:
            updates['difficulty'] = infer_difficulty_from_content(content, file_path)

        # Estimated time
        if 'estimated_time' not in existing_fields:
            updates['estimated_time'] = infer_estimated_time(content)

        # Category
        if 'category' not in existing_fields:
            updates['category'] = infer_category(file_path)

        # Status (si no existe)
        if 'status' not in existing_fields:
            updates['status'] = 'published'

        # Last reviewed (igual a updated inicialmente)
        if 'last_reviewed' not in existing_fields and 'updated' in existing_fields:
            updates['last_reviewed'] = existing_fields['updated']

        # Prerequisites
        if 'prerequisites' not in existing_fields:
            prereqs = infer_prerequisites(file_path, updates.get('difficulty', 'intermediate'))
            updates['prerequisites'] = prereqs

        # Reviewers (placeholder)
        if 'reviewers' not in existing_fields:
            updates['reviewers'] = ['@rasty94']

        # Contributors (placeholder)
        if 'contributors' not in existing_fields:
            updates['contributors'] = ['@rasty94']

        # Si no hay cambios, retornar
        if not updates:
            return False, "Ya tiene todos los campos expandidos"

        # Construir nuevo frontmatter
        new_frontmatter_lines = []
        for line in frontmatter.split('\n'):
            if line.strip() and not line.startswith('#'):
                new_frontmatter_lines.append(line)
            elif line.strip() == '':
                continue

        # Añadir campos nuevos al final
        for key, value in updates.items():
            if isinstance(value, list):
                # Para listas, usar formato YAML
                if len(value) == 1:
                    new_frontmatter_lines.append(f"{key}: [{', '.join(f'\"{v}\"' for v in value)}]")
                else:
                    new_frontmatter_lines.append(f"{key}:")
                    for item in value:
                        new_frontmatter_lines.append(f"  - \"{item}\"")
            else:
                new_frontmatter_lines.append(f"{key}: {value}")

        new_frontmatter = '\n'.join(new_frontmatter_lines)
        new_content = content.replace(frontmatter_match.group(0), f"---\n{new_frontmatter}\n---")

        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        added_fields = list(updates.keys())
        return True, f"Campos añadidos: {', '.join(added_fields)}"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description='Expandir metadatos en archivos de documentación')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostrar cambios sin aplicarlos')
    parser.add_argument('--docs-path', type=str, default='docs/doc',
                        help='Ruta a la documentación (default: docs/doc)')
    parser.add_argument('--category', type=str,
                        help='Procesar solo archivos de una categoría específica')
    parser.add_argument('--max-files', type=int, default=None,
                        help='Máximo número de archivos a procesar')

    args = parser.parse_args()

    docs_path = Path(args.docs_path)

    print("🔍 Expandiendo metadatos en archivos de documentación...")
    print(f"   Ruta: {docs_path}")
    print(f"   Modo dry-run: {'Sí' if args.dry_run else 'No'}")
    if args.category:
        print(f"   Categoría: {args.category}")
    print()

    # Buscar archivos
    all_files = []
    for md_file in docs_path.rglob('*.md'):
        # Ignorar archivos de blog e índices
        if 'blog' in str(md_file) or 'index.md' in str(md_file):
            continue

        # Filtrar por categoría si se especifica
        if args.category:
            if args.category.lower() not in str(md_file).lower():
                continue

        all_files.append(md_file)

    if not all_files:
        print("No se encontraron archivos para procesar.")
        return

    if args.max_files:
        all_files = all_files[:args.max_files]

    print(f"📝 Procesando {len(all_files)} archivos...")
    print()

    processed = 0
    errors = 0

    for file_path in all_files:
        success, message = expand_frontmatter(file_path, args.dry_run)

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
    print(f"  - Total: {len(all_files)}")

    if args.dry_run:
        print("\n💡 Ejecuta sin --dry-run para aplicar los cambios")

    # Mostrar campos añadidos
    print("\n📋 CAMPOS EXPANDIDOS:")
    print("  - difficulty: Nivel de dificultad (beginner/intermediate/advanced/expert)")
    print("  - estimated_time: Tiempo estimado de lectura/completado")
    print("  - category: Categoría principal del documento")
    print("  - status: Estado del documento (published/draft/review)")
    print("  - last_reviewed: Fecha de última revisión")
    print("  - prerequisites: Lista de requisitos previos")
    print("  - reviewers: Lista de revisores")
    print("  - contributors: Lista de contribuidores principales")


if __name__ == '__main__':
    main()