#!/usr/bin/env python3
"""
Script de diagnóstico para problemas con diagramas Mermaid
"""

import os
import re
from pathlib import Path

def check_mermaid_config():
    """Verifica la configuración de Mermaid en mkdocs.yml"""
    print("🔍 Verificando configuración de Mermaid...")
    
    try:
        with open('mkdocs.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que pymdownx.superfences esté configurado
        if 'pymdownx.superfences' in content:
            print("✅ pymdownx.superfences encontrado")
            
            # Verificar configuración de Mermaid
            if 'custom_fences' in content and 'mermaid' in content:
                print("✅ Configuración de custom_fences para Mermaid encontrada")
            else:
                print("❌ Configuración de custom_fences para Mermaid NO encontrada")
        else:
            print("❌ pymdownx.superfences NO encontrado")
        
        # Verificar carga de JavaScript
        if 'mermaid.min.js' in content:
            print("✅ Carga de Mermaid JavaScript encontrada")
        else:
            print("❌ Carga de Mermaid JavaScript NO encontrada")
            
        # Verificar extra_javascript
        if 'extra_javascript' in content:
            print("✅ Sección extra_javascript encontrada")
        else:
            print("❌ Sección extra_javascript NO encontrada")
            
    except FileNotFoundError:
        print("❌ Archivo mkdocs.yml no encontrado")
    except Exception as e:
        print(f"❌ Error leyendo mkdocs.yml: {e}")

def check_mermaid_files():
    """Verifica archivos con diagramas Mermaid"""
    print("\n🔍 Verificando archivos con diagramas Mermaid...")
    
    docs_dir = Path("docs")
    mermaid_files = []
    
    for md_file in docs_dir.rglob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if '```mermaid' in content:
                mermaid_blocks = re.findall(r'```mermaid\s*\n(.*?)\n```', content, re.DOTALL)
                mermaid_files.append({
                    'file': md_file,
                    'blocks': len(mermaid_blocks),
                    'content': mermaid_blocks
                })
        except Exception as e:
            print(f"❌ Error leyendo {md_file}: {e}")
    
    print(f"📊 Se encontraron {len(mermaid_files)} archivos con diagramas Mermaid:")
    
    for file_info in mermaid_files:
        print(f"   📄 {file_info['file']} ({file_info['blocks']} diagramas)")
        
        # Verificar sintaxis de cada diagrama
        for i, diagram in enumerate(file_info['content']):
            lines = diagram.strip().split('\n')
            if lines:
                first_line = lines[0].strip()
                print(f"      Diagrama {i+1}: {first_line[:50]}...")
                
                # Verificar tipos soportados
                supported_types = [
                    'flowchart', 'graph', 'sequenceDiagram', 'classDiagram',
                    'stateDiagram', 'stateDiagram-v2', 'erDiagram', 'gitgraph',
                    'gantt', 'pie', 'journey', 'quadrantChart', 'xyChart'
                ]
                
                if not any(first_line.startswith(t) for t in supported_types):
                    print(f"      ⚠️  Tipo no soportado: {first_line}")

def check_css_files():
    """Verifica archivos CSS"""
    print("\n🔍 Verificando archivos CSS...")
    
    css_file = Path("docs/stylesheets/extra.css")
    if css_file.exists():
        print("✅ Archivo extra.css encontrado")
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '.mermaid' in content:
            print("✅ Estilos Mermaid encontrados en extra.css")
        else:
            print("❌ Estilos Mermaid NO encontrados en extra.css")
    else:
        print("❌ Archivo extra.css NO encontrado")

def generate_test_html():
    """Genera un archivo HTML de prueba para verificar Mermaid"""
    print("\n🔍 Generando archivo HTML de prueba...")
    
    test_html = """<!DOCTYPE html>
<html>
<head>
    <title>Test Mermaid</title>
    <script src="https://unpkg.com/mermaid@10.9.4/dist/mermaid.min.js"></script>
</head>
<body>
    <h1>Test Mermaid</h1>
    
    <div class="mermaid">
flowchart TD
    A[Inicio] --> B[Proceso]
    B --> C[Fin]
    </div>
    
    <div class="mermaid">
sequenceDiagram
    A->>B: Hola
    B->>A: Hola de vuelta
    </div>
    
    <script>
        mermaid.initialize({startOnLoad: true});
    </script>
</body>
</html>"""
    
    with open('test_mermaid.html', 'w', encoding='utf-8') as f:
        f.write(test_html)
    
    print("✅ Archivo test_mermaid.html generado")
    print("   Puedes abrir este archivo en tu navegador para probar Mermaid directamente")

def main():
    print("🔧 Diagnóstico de Mermaid para Frikiteam Docs")
    print("=" * 50)
    
    check_mermaid_config()
    check_mermaid_files()
    check_css_files()
    generate_test_html()
    
    print("\n📋 Resumen de diagnóstico:")
    print("1. Verifica que mkdocs.yml tenga la configuración correcta")
    print("2. Asegúrate de que los diagramas usen sintaxis válida")
    print("3. Prueba el archivo test_mermaid.html en tu navegador")
    print("4. Revisa la consola del navegador para errores JavaScript")
    print("5. Verifica que Mermaid se cargue correctamente")

if __name__ == "__main__":
    main()
