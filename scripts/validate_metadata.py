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
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import argparse


# Vocabulario cerrado de tags. Cualquier tag fuera de esta lista hace fallar
# `--strict`, para que la pagina de tags siga agrupando en vez de dispersarse.
# Para añadir uno nuevo: justificarlo con al menos 2-3 documentos que lo usen.
TAG_VOCABULARY = {
    # Areas
    'ai', 'llm', 'networking', 'cybersecurity', 'storage', 'monitoring', 'kubernetes',
    'docker', 'linux', 'devops', 'databases', 'backups', 'identity', 'programming',
    'virtualization', 'documentation',
    # Transversales
    'automation', 'performance', 'high-availability', 'troubleshooting', 'testing',
    'best-practices', 'observability', 'benchmarks', 'migration', 'compliance', 'api', 'cost',
    # Storage y virtualizacion
    'ceph', 'netapp', 'pure-storage', 'proxmox', 'openstack',
    # IaC y entrega continua
    'terraform', 'ansible', 'gitops', 'ci-cd', 'helm', 'argocd',
    # Monitorizacion
    'prometheus', 'grafana', 'loki', 'logs',
    # Seguridad
    'firewall', 'vpn', 'wireguard', 'zero-trust', 'encryption', 'hardening', 'pentesting',
    'forensics', 'secrets', 'rbac', 'supply-chain', 'vulnerability-scanning',
    'incident-response', 'siem', 'devsecops',
    # Contenedores
    'containers', 'podman', 'service-mesh', 'ebpf',
    # IA aplicada
    'vllm', 'ollama', 'rag', 'vector-db', 'fine-tuning', 'quantization',
    'prompt-engineering', 'mcp', 'gpu', 'inference', 'evaluation',
    # Sistema
    'vrouter', 'bash', 'systemd',
}


def validate_tags(fields):
    """Devuelve los tags del fichero que no estan en el vocabulario cerrado."""
    return sorted(t for t in fields.get('tags', []) if t not in TAG_VOCABULARY)


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


def analyze_metadata(docs_paths, category_filter=None):
    """Analiza metadatos de todos los archivos de los árboles indicados."""
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

    md_files = sorted(f for p in docs_paths for f in Path(p).rglob('*.md'))

    for md_file in md_files:
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


# Vocabulario cerrado de categorias, ES -> EN. La categoria se pinta como badge
# en la cabecera de cada pagina, asi que cada arbol usa su idioma y los gemelos
# ES/EN deben apuntar al mismo concepto.
CATEGORY_VOCABULARY = {
    'Redes': 'Networking',
    'Inteligencia Artificial': 'Artificial Intelligence',
    'Ciberseguridad': 'Cybersecurity',
    'Contenedores': 'Containers',
    'Almacenamiento': 'Storage',
    'DevOps': 'DevOps',
    'Linux': 'Linux',
    'Cloud Computing': 'Cloud Computing',
    'Monitoreo': 'Monitoring',
    'Gestión de Identidad': 'Identity Management',
    'Virtualización': 'Virtualization',
    'Bases de Datos': 'Databases',
    'Copias de Seguridad': 'Backups',
    'Desarrollo': 'Development',
    'General': 'General',
}


def check_categories(docs_paths):
    """Devuelve [(ruta, problema)] por categoria invalida o desparejada entre ES y EN."""
    problemas = []
    for docs_path in docs_paths:
        es_tree = 'docs/en/' not in str(docs_path)
        for md in sorted(Path(docs_path).rglob('*.md')):
            fields = extract_frontmatter(md)
            if not fields or 'category' not in fields:
                continue
            cat = str(fields['category']).strip()
            if es_tree:
                if cat not in CATEGORY_VOCABULARY:
                    problemas.append((str(md), f"categoría '{cat}' fuera del vocabulario"))
                    continue
                gemelo = Path(str(md).replace('docs/', 'docs/en/', 1))
                campos_en = extract_frontmatter(gemelo) if gemelo.exists() else None
                if campos_en and 'category' in campos_en:
                    cat_en = str(campos_en['category']).strip()
                    esperado = CATEGORY_VOCABULARY[cat]
                    if cat_en != esperado:
                        problemas.append((str(gemelo), f"categoría '{cat_en}' debería ser '{esperado}' (ES: '{cat}')"))
            elif cat not in CATEGORY_VOCABULARY.values():
                problemas.append((str(md), f"categoría '{cat}' fuera del vocabulario"))
    return problemas


def check_drafts(docs_paths):
    """Devuelve [(ruta, problema)] cuando una gemela es borrador y la otra no.

    `draft: true` excluye la página del sitio (ver `hooks/drafts.py`). Si solo lo
    lleva uno de los dos idiomas, se publica media página y nadie se entera.
    """
    problemas = []
    for docs_path in docs_paths:
        if 'docs/en/' in str(docs_path).replace('\\', '/'):
            continue
        for md in sorted(Path(docs_path).rglob('*.md')):
            gemelo = Path(str(md).replace('docs/', 'docs/en/', 1))
            if not gemelo.exists():
                continue
            es_borrador = str((extract_frontmatter(md) or {}).get('draft', '')).lower() == 'true'
            en_borrador = str((extract_frontmatter(gemelo) or {}).get('draft', '')).lower() == 'true'
            if es_borrador != en_borrador:
                cual = 'ES' if es_borrador else 'EN'
                otro = 'EN' if es_borrador else 'ES'
                problemas.append((str(md), f"solo la versión {cual} es borrador; la {otro} se publicaría igual"))
    return problemas


# Campos que, si la ES los declara, la EN debe declarar también. `prerequisites`
# se pinta como badge (macros.py) y `description` alimenta el <meta> de la pagina:
# una EN sin el suyo hereda el del sitio, que esta en espanol.
CAMPOS_ESPEJO = ('prerequisites', 'last_reviewed', 'description', 'keywords')


def check_en_fields(docs_paths):
    """Devuelve [(ruta_en, campos_que_faltan)] para gemelas EN con menos metadatos que su ES."""
    problemas = []
    for docs_path in docs_paths:
        if 'docs/en/' in str(docs_path).replace('\\', '/'):
            continue
        for md in sorted(Path(docs_path).rglob('*.md')):
            gemelo = Path(str(md).replace('docs/', 'docs/en/', 1))
            if not gemelo.exists():
                continue
            es, en = extract_frontmatter(md), extract_frontmatter(gemelo)
            if not es or not en:
                continue
            faltan = [c for c in CAMPOS_ESPEJO if c in es and c not in en]
            if faltan:
                problemas.append((str(gemelo), faltan))
    return problemas


def check_twin_parity(docs_paths):
    """Devuelve [(ruta_en, motivo)] cuando tags, updated o last_reviewed difieren entre gemelas.

    El CLAUDE.md del proyecto exige los mismos tags en ambos idiomas y las mismas
    fechas. check_sync.py solo detecta la ES mas nueva que la EN, no el caso
    contrario ni los tags: el 2026-10-11 habia 44 fechas y 6 tags desparejados.
    """
    problemas = []
    for docs_path in docs_paths:
        if 'docs/en/' in str(docs_path).replace('\\', '/'):
            continue
        for md in sorted(Path(docs_path).rglob('*.md')):
            gemelo = Path(str(md).replace('docs/', 'docs/en/', 1))
            if not gemelo.exists():
                continue
            es, en = extract_frontmatter(md), extract_frontmatter(gemelo)
            if not es or not en:
                continue
            if 'tags' in es and 'tags' in en and sorted(map(str, es['tags'] or [])) != sorted(map(str, en['tags'] or [])):
                problemas.append((str(gemelo), f"tags {en['tags']} distintos de la ES {es['tags']}"))
            for campo in ('updated', 'last_reviewed'):
                if campo in es and campo in en and str(es[campo]) != str(en[campo]):
                    problemas.append((str(gemelo), f"{campo} {en[campo]} distinto de la ES {es[campo]}"))
    return problemas


def check_vocabulary(docs_paths):
    """Recorre los arboles y devuelve [(ruta, tags_invalidos)] de los ficheros infractores."""
    offenders = []
    for docs_path in docs_paths:
        for md in sorted(Path(docs_path).rglob('*.md')):
            fields = extract_frontmatter(md)
            if not fields:
                continue
            bad = validate_tags(fields)
            if bad:
                offenders.append((str(md), bad))
    return offenders


def main():
    parser = argparse.ArgumentParser(description='Validar metadatos de documentación')
    parser.add_argument('--docs-path', type=str, nargs='+',
                        default=['docs/doc', 'docs/en/doc'],
                        help='Rutas a la documentación (default: ambos árboles, ES y EN)')
    parser.add_argument('--category', type=str,
                        help='Analizar solo archivos de una categoría específica')
    parser.add_argument('--report', action='store_true',
                        help='Generar reporte completo')
    parser.add_argument('--strict', action='store_true',
                        help='Salir con codigo 1 si hay tags fuera del vocabulario')

    args = parser.parse_args()

    print("🔍 Analizando metadatos de documentación...")
    print(f"   Rutas: {', '.join(args.docs_path)}")
    if args.category:
        print(f"   Categoría: {args.category}")
    print()

    stats = analyze_metadata(args.docs_path, args.category)

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

    if args.strict:
        fallo = False

        offenders = check_vocabulary(args.docs_path)
        if offenders:
            fallo = True
            print(f"\n❌ {len(offenders)} archivos con tags fuera del vocabulario:")
            for path, bad in offenders:
                print(f"  {path}: {', '.join(bad)}")
            print(f"   Vocabulario permitido: {len(TAG_VOCABULARY)} tags en TAG_VOCABULARY")
        else:
            print("\n✅ Todos los tags pertenecen al vocabulario")

        problemas = check_categories(args.docs_path)
        if problemas:
            fallo = True
            print(f"\n❌ {len(problemas)} archivos con problemas de categoría:")
            for path, motivo in problemas:
                print(f"  {path}: {motivo}")
            print(f"   Vocabulario permitido: {len(CATEGORY_VOCABULARY)} categorías en CATEGORY_VOCABULARY")
        else:
            print("✅ Todas las categorías son válidas y coinciden entre ES y EN")

        borradores = check_drafts(args.docs_path)
        if borradores:
            fallo = True
            print(f"\n❌ {len(borradores)} páginas con estado de borrador desparejado:")
            for path, motivo in borradores:
                print(f"  {path}: {motivo}")
            print("   `draft: true` excluye la página del sitio (hooks/drafts.py);"
                  " debe declararse en los dos idiomas o en ninguno.")
        else:
            print("✅ El estado de borrador coincide entre ES y EN")

        huecos = check_en_fields(args.docs_path)
        if huecos:
            fallo = True
            print(f"\n❌ {len(huecos)} páginas EN con menos metadatos que su gemela ES:")
            for path, campos in huecos:
                print(f"  {path}: falta {', '.join(campos)}")
            print(f"   Campos espejo: {', '.join(CAMPOS_ESPEJO)}. Traducir desde la ES.")
        else:
            print("✅ Las gemelas EN declaran los mismos campos espejo que su ES")

        paridad = check_twin_parity(args.docs_path)
        if paridad:
            fallo = True
            print(f"\n❌ {len(paridad)} diferencias de tags o fechas entre gemelas:")
            for path, motivo in paridad:
                print(f"  {path}: {motivo}")
            print("   Tags, updated y last_reviewed deben ser iguales en ES y EN.")
        else:
            print("✅ Tags y fechas coinciden entre ES y EN")

        if fallo:
            print("\nAmbos vocabularios se definen en scripts/validate_metadata.py")
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)