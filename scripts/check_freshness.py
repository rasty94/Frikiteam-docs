#!/usr/bin/env python3
"""
Script para detectar archivos de documentación que no han sido actualizados recientemente.
Útil para identificar contenido potencialmente obsoleto.

Uso:
    python scripts/check_freshness.py [--days 90]
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import argparse


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


def find_stale_docs(docs_path, days_threshold=90):
    """Encuentra documentos que no han sido actualizados en X días."""
    stale_docs = []
    no_date_docs = []
    
    # Buscar todos los archivos .md en docs/doc/
    for md_file in Path(docs_path).rglob('*.md'):
        # Ignorar archivos de índice y blog
        if 'blog' in str(md_file) or 'index.md' in str(md_file):
            continue
            
        updated_date = extract_updated_date(md_file)
        
        if updated_date is None:
            no_date_docs.append(md_file)
        else:
            days_old = (datetime.now() - updated_date).days
            if days_old > days_threshold:
                stale_docs.append((md_file, days_old, updated_date))
    
    return stale_docs, no_date_docs


def main():
    parser = argparse.ArgumentParser(description='Detectar documentación obsoleta')
    parser.add_argument('--days', type=int, default=90, 
                        help='Días sin actualizar para considerar obsoleto (default: 90)')
    parser.add_argument('--docs-path', type=str, default='docs/doc',
                        help='Ruta a la documentación (default: docs/doc)')
    args = parser.parse_args()
    
    print(f"🔍 Buscando documentos sin actualizar en más de {args.days} días...\n")
    
    stale_docs, no_date_docs = find_stale_docs(args.docs_path, args.days)
    
    if stale_docs:
        print(f"⚠️  DOCUMENTOS OBSOLETOS ({len(stale_docs)}):")
        print("=" * 80)
        stale_docs.sort(key=lambda x: x[1], reverse=True)
        for doc, days, updated in stale_docs:
            print(f"  📄 {doc.relative_to('docs/doc')}")
            print(f"     Última actualización: {updated.strftime('%Y-%m-%d')} ({days} días)")
            print()
    else:
        print("✅ No hay documentos obsoletos.")
    
    if no_date_docs:
        print(f"\n📝 DOCUMENTOS SIN FECHA 'updated' ({len(no_date_docs)}):")
        print("=" * 80)
        for doc in no_date_docs[:10]:  # Mostrar solo primeros 10
            print(f"  📄 {doc.relative_to('docs/doc')}")
        if len(no_date_docs) > 10:
            print(f"  ... y {len(no_date_docs) - 10} más")
    
    print("\n" + "=" * 80)
    print(f"📊 Resumen:")
    print(f"  - Obsoletos (>{args.days} días): {len(stale_docs)}")
    print(f"  - Sin fecha: {len(no_date_docs)}")
    print(f"  - Total revisados: {len(stale_docs) + len(no_date_docs)}")


if __name__ == '__main__':
    main()
