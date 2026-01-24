#!/bin/bash
# Script de validación de enlaces para MkDocs
# Uso: ./validate_links.sh [directorio_site]

set -e

SITE_DIR="${1:-site}"
LINKCHECKER_CONFIG="${2:---config=.linkcheckerrc}"

echo "🔍 Validando enlaces en $SITE_DIR..."

# Verificar que el directorio existe
if [ ! -d "$SITE_DIR" ]; then
    echo "❌ Error: Directorio $SITE_DIR no encontrado"
    echo "💡 Ejecuta 'mkdocs build' primero para generar el sitio"
    exit 1
fi

# Ejecutar linkchecker con configuración optimizada
echo "🚀 Ejecutando linkchecker..."
linkchecker \
    --config=.linkcheckerrc \
    --output=text \
    --verbose \
    "$SITE_DIR" 2>&1 | tee linkchecker_output.txt

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "✅ Todos los enlaces válidos"
    exit 0
else
    echo "❌ Se encontraron enlaces rotos"
    echo "📋 Revisa linkchecker_output.txt para detalles"
    exit 1
fi