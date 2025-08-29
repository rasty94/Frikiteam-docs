#!/usr/bin/env python3
"""
Script para verificar que los diagramas Mermaid se rendericen correctamente
"""

import os
import re
from pathlib import Path

def find_mermaid_diagrams():
    """Busca archivos Markdown que contengan diagramas Mermaid"""
    docs_dir = Path("docs")
    mermaid_files = []
    
    for md_file in docs_dir.rglob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '```mermaid' in content:
                mermaid_files.append({
                    'file': md_file,
                    'diagrams': len(re.findall(r'```mermaid\s*\n(.*?)\n```', content, re.DOTALL))
                })
    
    return mermaid_files

def check_mermaid_syntax():
    """Verifica la sintaxis básica de los diagramas Mermaid"""
    docs_dir = Path("docs")
    errors = []
    
    for md_file in docs_dir.rglob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Buscar bloques de código Mermaid
        mermaid_blocks = re.findall(r'```mermaid\s*\n(.*?)\n```', content, re.DOTALL)
        
        for i, diagram in enumerate(mermaid_blocks):
            # Verificar sintaxis básica
            if not diagram.strip():
                errors.append(f"Diagrama vacío en {md_file}:{i+1}")
                continue
                
            # Verificar tipos de diagrama soportados
            diagram_type = diagram.strip().split('\n')[0].strip()
            supported_types = [
                'flowchart', 'graph', 'sequenceDiagram', 'classDiagram',
                'stateDiagram', 'stateDiagram-v2', 'erDiagram', 'gitgraph',
                'gantt', 'pie', 'journey', 'quadrantChart', 'xyChart'
            ]
            
            if not any(diagram_type.startswith(t) for t in supported_types):
                errors.append(f"Tipo de diagrama no soportado en {md_file}:{i+1} - {diagram_type}")
    
    return errors

def main():
    print("🔍 Verificando diagramas Mermaid...")
    print("=" * 50)
    
    # Buscar archivos con diagramas
    mermaid_files = find_mermaid_diagrams()
    
    if not mermaid_files:
        print("❌ No se encontraron diagramas Mermaid en la documentación")
        return
    
    print(f"✅ Se encontraron {len(mermaid_files)} archivos con diagramas Mermaid:")
    for file_info in mermaid_files:
        print(f"   📄 {file_info['file']} ({file_info['diagrams']} diagramas)")
    
    print("\n🔍 Verificando sintaxis...")
    
    # Verificar sintaxis
    errors = check_mermaid_syntax()
    
    if errors:
        print("❌ Se encontraron errores de sintaxis:")
        for error in errors:
            print(f"   ⚠️  {error}")
    else:
        print("✅ No se encontraron errores de sintaxis")
    
    print("\n📋 Resumen:")
    print(f"   - Archivos con diagramas: {len(mermaid_files)}")
    total_diagrams = sum(f['diagrams'] for f in mermaid_files)
    print(f"   - Total de diagramas: {total_diagrams}")
    print(f"   - Errores encontrados: {len(errors)}")
    
    if errors:
        print("\n💡 Sugerencias:")
        print("   - Revisa la sintaxis de los diagramas marcados")
        print("   - Asegúrate de que los tipos de diagrama sean soportados")
        print("   - Verifica que no haya bloques de diagrama vacíos")
    else:
        print("\n🎉 ¡Todos los diagramas parecen estar correctos!")
        print("   Puedes ejecutar 'mkdocs serve' para verificar la renderización visual")

if __name__ == "__main__":
    main()
