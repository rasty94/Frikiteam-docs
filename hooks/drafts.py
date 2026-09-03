"""Excluye del sitio las páginas con `draft: true` en el frontmatter.

MkDocs no sabe leer el frontmatter para decidir qué publica: `exclude_docs` y
`draft_docs` trabajan con rutas, no con metadatos. Sin este hook, `draft: true`
era decorativo y la página se publicaba igual, que es justo lo contrario de lo
que espera quien la marca.

Se hacen dos cosas, y las dos hacen falta:

1. `on_config` poda las entradas del `nav` que apuntan a un borrador. Si solo se
   quitara el fichero, MkDocs avisaría de que el `nav` referencia algo que no
   existe y `--strict` convertiría ese aviso en error.
2. `on_files` retira los ficheros para que no se rendericen.

El árbol EN vive bajo `docs/en/`, así que sus páginas se marcan igual y por
separado. Que una gemela sea borrador y la otra no es un despiste: lo detecta
`scripts/validate_metadata.py --strict`.
"""

import logging
import re
from pathlib import Path

from mkdocs.structure.files import Files

log = logging.getLogger('mkdocs.hooks.drafts')

FRONTMATTER = re.compile(r'^---\n(.*?\n)---', re.DOTALL)
DRAFT = re.compile(r'^draft:\s*true\s*$', re.IGNORECASE | re.MULTILINE)


def es_borrador(ruta):
    """True si el frontmatter del fichero declara `draft: true`."""
    try:
        with open(ruta, encoding='utf-8') as fh:
            cabecera = fh.read(4096)
    except OSError:
        return False
    bloque = FRONTMATTER.match(cabecera)
    return bool(bloque and DRAFT.search(bloque.group(1)))


def podar_nav(nav, borradores):
    """Devuelve el nav sin las entradas que apunten a un borrador."""
    if isinstance(nav, str):
        return None if nav in borradores else nav
    if isinstance(nav, list):
        limpio = [x for x in (podar_nav(i, borradores) for i in nav) if x is not None]
        return limpio or None
    if isinstance(nav, dict):
        limpio = {}
        for titulo, valor in nav.items():
            podado = podar_nav(valor, borradores)
            if podado is not None:
                limpio[titulo] = podado
        return limpio or None
    return nav


def on_config(config):
    docs_dir = Path(config['docs_dir'])
    borradores = {
        md.relative_to(docs_dir).as_posix()
        for md in docs_dir.rglob('*.md')
        if es_borrador(md)
    }
    config['borradores_excluidos'] = borradores

    if borradores:
        for ruta in sorted(borradores):
            log.info("Borrador excluido del sitio: %s", ruta)
        if config.get('nav'):
            config['nav'] = podar_nav(config['nav'], borradores) or []
    return config


def on_files(files, config):
    borradores = config.get('borradores_excluidos') or set()
    if not borradores:
        return files
    return Files([f for f in files if f.src_uri not in borradores])
