#!/usr/bin/env python3
"""Frikiteam-docs -> frikiteam-astro/src/content/posts (sustituye a wordpress_sync.py).

El Markdown de docs es la fuente del contenido; el .md del artículo en Astro es el registro
editorial: ahí viven la serie, la fecha de publicación y la URL. El script nunca las pisa en un
artículo que ya existe: solo refresca título, extracto, etiquetas, fecha de actualización y cuerpo.

    python scripts/publish_to_astro.py                 # informe, no escribe nada
    python scripts/publish_to_astro.py --write         # actualiza los existentes y crea los nuevos
    python scripts/publish_to_astro.py --out /tmp/gen  # escribe en otra carpeta (para comparar)
    python scripts/publish_to_astro.py --adopt         # una vez: añade `source:` a los artículos de WordPress

Un artículo nuevo necesita serie (la propone el mapa category -> serie, o `--serie ruta=serie`)
y recibe el siguiente hueco libre: un artículo cada 2 días a las 09:00 de Madrid.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown
import yaml
from markdown.extensions.toc import slugify, unique

DOCS_ROOT = Path(__file__).resolve().parent.parent
ASTRO_ROOT = DOCS_ROOT.parent / 'frikiteam-astro'

# Páginas de navegación o meta sin valor como artículo (las mismas que excluía wordpress_sync.py).
NO_ARTICULO = {f'docs/{n}.md' for n in ('about', 'privacy', 'glossary', 'quickstart', 'troubleshooting', 'tags')}

# `category` de docs -> serie. Solo las que lo son casi siempre; el resto exige elegirla.
CATEGORY_SERIE = {
    'Redes': 'networking', 'Inteligencia Artificial': 'ia-local', 'Ciberseguridad': 'devsecops',
    'Gestión de Identidad': 'devsecops', 'Almacenamiento': 'almacenamiento',
    'Copias de Seguridad': 'almacenamiento', 'DevOps': 'automatizacion', 'Monitoreo': 'observabilidad',
    'Virtualización': 'virtualizacion', 'Cloud Computing': 'virtualizacion', 'Desarrollo': 'desarrollo',
    'Bases de Datos': 'sistemas',
}  # Contenedores (contenedores o kubernetes), General y Linux: a mano

# Borradores a propósito: cidr_notation se funde con VLSM antes de publicarse (ver docs/servidor/CLAUDE.md).
EXCLUIR = {'docs/doc/networking/cidr_notation.md'}

MADRID = ZoneInfo('Europe/Madrid')
STEP_DAYS = 2

_RAW_LINE = re.compile(r'^[ \t]*\{%-?\s*(?:end)?raw\s*-?%\}[ \t]*\n?', re.M)
_RAW = re.compile(r'\{%-?\s*(?:end)?raw\s*-?%\}')
_FENCE = re.compile(r'^(\s*)(`{3,}|~{3,})(.*)$')
_ADMON = re.compile(r'^!!!\s+(\S+)(?:\s+"(.*)")?\s*$')
_HEAD = re.compile(r'^(#{2,4})\s+(.+?)\s*#*\s*$')


# ---------- conversión del cuerpo ----------

def _inline_html(text):
    # `### 1. Instalar` no es una lista: escapar el inicio para que el conversor no lo tome por una.
    text = re.sub(r'^(\d+)([.)])', r'\1\\\2', text)
    text = re.sub(r'^([-+*>])(\s)', r'\\\1\2', text)
    return re.sub(r'^<p>(.*)</p>$', r'\1', markdown.markdown(text), flags=re.S)


def _heading(level, text, ids):
    inner = _inline_html(text)
    plain = html.unescape(re.sub(r'<[^>]+>', '', inner))
    # Mismo identificador que daba python-markdown a WordPress: sin tildes y con `_1` si se repite.
    # Los índices del propio documento (`[x](#que-es)`) enlazan con él, y el de Astro conserva las tildes.
    return f'<h{level} id="{unique(slugify(plain, "-"), ids)}">{inner}</h{level}>'


def _alt(state):
    """Texto alternativo de un diagrama: la sección en la que está, que es lo que lo describe."""
    return f'Diagrama: {state["heading"]}' if state.get('heading') else 'Diagrama'


_IMG = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)\)(\{[^}]*\})?')


def _images(line, image):
    """Imágenes locales a public/img; y `{width=50%}` (attr_list de MkDocs), que Markdown a secas dejaría como texto."""
    def one(m):
        alt, src, attrs = m.group(1), image(m.group(2)), m.group(3)
        if not attrs:
            return f'![{alt}]({src})'
        css = [f'{k}:{v if v.endswith("%") or not v.isdigit() else v + "px"}'
               for k, v in re.findall(r'\b(width|height)\s*=\s*"?([\w.%]+)"?', attrs)]
        return f'<img src="{src}" alt="{html.escape(alt)}"' + (f' style="{";".join(css)}"' if css else '') + '>'
    return _IMG.sub(one, line)


def _blocks(lines, ids, diagram, image, state):
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            mark, info = fence.group(2), fence.group(3).strip()
            j = i + 1
            while j < n and not (re.match(rf'^\s*{re.escape(mark[0])}{{{len(mark)},}}\s*$', lines[j])):
                j += 1
            block = lines[i:j + 1]
            code = '\n'.join(block[1:-1]) if j < n else '\n'.join(block[1:])
            png = diagram(code) if info.split(' ')[0] == 'mermaid' else None
            out += [f'![{_alt(state)}]({png})'] if png else block
            i = j + 1
            continue
        adm = _ADMON.match(line)
        if adm:
            j = i + 1
            while j < n and (lines[j].strip() == '' or lines[j].startswith('    ')):
                j += 1
            body = lines[i + 1:j]
            while body and not body[-1].strip():
                body.pop()
            kind = adm.group(1)
            title = kind.capitalize() if adm.group(2) is None else adm.group(2)
            out += [f'<div class="admonition {kind}">']
            if title:
                out += [f'<p class="admonition-title">{html.escape(title, quote=False)}</p>']
            out += ['', *_blocks([b[4:] if b.startswith('    ') else '' for b in body], ids, diagram, image, state), '', '</div>', '']  # sin esa línea en blanco, el <div> se traga lo que sigue
            i = j
            continue
        head = _HEAD.match(line)
        if head:
            h = _heading(len(head.group(1)), head.group(2), ids)
            state['heading'] = html.unescape(re.sub(r'<[^>]+>', '', h))
            out += ['', h, '']
        else:
            out.append(_images(line, image))
        i += 1
    return out


def convert_body(text, title, diagram=lambda code: None, image=lambda src: src):
    text = _RAW.sub('', _RAW_LINE.sub('', text))
    text = re.sub(r'\A\s*# .+\n+', '', text)  # el título de la página: la plantilla de Astro pinta el suyo
    body = '\n'.join(_blocks(text.split('\n'), set(), diagram, image, {'heading': title}))
    return re.sub(r'\n{3,}', '\n\n', body).strip('\n') + '\n'


# ---------- metadatos ----------

def _plain(s):
    s = html.unescape(str(s)).replace('–', '-').replace('—', '-').replace('’', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip().lower()


def wp_slug(title):
    """sanitize_title de WordPress: sin tildes, `&` fuera, el resto de símbolos a guiones."""
    s = unicodedata.normalize('NFKD', html.unescape(title)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9\s-]', '', re.sub(r'[/.]', ' ', s.replace('&', ' ')))
    return re.sub(r'[\s-]+', '-', s).strip('-')


def split_frontmatter(text):
    m = re.match(r'---\n(.*?)\n---\n?', text, re.S)
    if not m:
        return {}, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return {}, text[m.end():]


def _iso(d):
    if isinstance(d, datetime):  # YAML lee `2026-09-27T07:00:00Z` como datetime
        d = d.astimezone(timezone.utc) if d.tzinfo else d
        return d.strftime('%Y-%m-%dT%H:%M:%SZ')
    return f'{d}T00:00:00Z' if d else None


def render_post(meta, body):
    """Frontmatter en el mismo formato que escribía export.mjs (cadenas JSON)."""
    j = lambda v: json.dumps('' if v is None else v, ensure_ascii=False)
    rows = [('title', j(meta['title']))]
    if meta.get('wpId'):
        rows.append(('wpId', str(meta['wpId'])))
    rows += [('source', j(meta['source'])), ('date', meta['date']), ('updated', meta['updated']),
             ('category', meta['category']), ('description', j(meta.get('description'))),
             ('image', j(meta.get('image'))), ('imageAlt', j(meta.get('imageAlt'))),
             ('tags', json.dumps(meta.get('tags') or [], ensure_ascii=False))]
    return '---\n' + '\n'.join(f'{k}: {v}' for k, v in rows) + '\n---\n\n' + body


# ---------- diagramas ----------

class Diagrams:
    """mermaid -> PNG en public/diagrams/. Mismo nombre que subía el pipeline a WordPress (sha1 del código),
    así que los ya generados se reutilizan en vez de volver a renderizarlos."""

    def __init__(self, astro, render=True):
        self.dir, self.astro, self.render, self.missing = astro / 'public' / 'diagrams', astro, render, []

    def __call__(self, code):
        code = code.strip()
        name = f'mermaid-{hashlib.sha1(code.encode("utf-8")).hexdigest()[:12]}.png'
        target = self.dir / name
        if not target.exists():
            legacy = next((self.astro / 'public' / 'wp-content' / 'uploads').rglob(name), None)
            self.dir.mkdir(parents=True, exist_ok=True)
            if legacy:
                shutil.copy(legacy, target)
            elif self.render:
                src = target.with_suffix('.mmd')
                src.write_text(code, encoding='utf-8')
                cmd = ['mmdc', '-i', str(src), '-o', str(target), '-b', 'transparent']
                if (DOCS_ROOT / 'puppeteer-config.json').exists():
                    cmd += ['-p', str(DOCS_ROOT / 'puppeteer-config.json')]
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=90)
                except (subprocess.SubprocessError, FileNotFoundError) as e:
                    self.missing.append(name)
                    print(f'  Aviso: no se pudo renderizar {name}: {e}', file=sys.stderr)
                finally:
                    src.unlink(missing_ok=True)
            else:
                self.missing.append(name)
        return f'/diagrams/{name}' if target.exists() else None  # sin imagen, el bloque mermaid queda como está


class Images:
    """Imágenes locales del Markdown -> public/img/<slug>/ (las remotas y las absolutas se dejan)."""

    def __init__(self, astro, slug, source):
        self.astro, self.slug, self.base = astro, slug, (DOCS_ROOT / source).parent

    def __call__(self, src):
        if re.match(r'(https?:|data:|/)', src):
            return src
        path = (self.base / src.split('#')[0]).resolve()
        if not path.is_file():
            print(f'  Aviso: imagen no encontrada en {self.slug}: {src}', file=sys.stderr)
            return src
        target = self.astro / 'public' / 'img' / self.slug / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
        return f'/img/{self.slug}/{path.name}'


# ---------- el sitio ----------

def candidates():
    """Páginas de docs que son artículo, con su frontmatter y cuerpo."""
    for p in sorted((DOCS_ROOT / 'docs').rglob('*.md')):
        rel = p.relative_to(DOCS_ROOT).as_posix()
        if rel.startswith('docs/en/') or p.name == 'index.md' or rel in NO_ARTICULO or rel in EXCLUIR:
            continue
        meta, body = split_frontmatter(p.read_text(encoding='utf-8'))
        if meta.get('draft'):
            continue
        if not meta.get('title'):
            print(f'  SALTADA {rel}: sin título o frontmatter ilegible (¿un `:` sin comillas?)', file=sys.stderr)
            continue
        yield rel, meta, body


def load_posts(astro):
    posts = {}
    for p in sorted((astro / 'src' / 'content' / 'posts').glob('*.md')):
        meta, _ = split_frontmatter(p.read_text(encoding='utf-8'))
        posts[p.stem] = dict(meta, _file=p, date=_iso(meta.get('date')), updated=_iso(meta.get('updated')))
    return posts


def next_slot(posts, extra=0):
    last = max(datetime.fromisoformat(m['date'].replace('Z', '+00:00')) for m in posts.values()).astimezone(MADRID)
    day = (last + timedelta(days=STEP_DAYS * (extra + 1))).date()
    return datetime(day.year, day.month, day.day, 9, 0, tzinfo=MADRID).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def adopt(astro):
    """Añade `source:` a los artículos que vinieron de WordPress, usando el estado del pipeline antiguo."""
    state = json.loads((DOCS_ROOT / '.wp_sync_state.json').read_text())
    by_id = {v['post_id']: k for k, v in state.items()}
    n = 0
    for slug, m in load_posts(astro).items():
        src = by_id.get(m.get('wpId'))
        if src and not m.get('source') and (DOCS_ROOT / src).exists():
            f = m['_file']
            f.write_text(f.read_text(encoding='utf-8').replace('\nwpId:', f'\nsource: {json.dumps(src)}\nwpId:', 1), encoding='utf-8')
            n += 1
    print(f'{n} artículos con `source` añadido')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--astro', type=Path, default=ASTRO_ROOT)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--adopt', action='store_true')
    ap.add_argument('--serie', action='append', default=[], metavar='RUTA=SERIE')
    ap.add_argument('--no-render', action='store_true', help='no ejecutar mmdc (los diagramas nuevos quedan sin imagen)')
    a = ap.parse_args()
    if a.adopt:
        return adopt(a.astro)

    posts = load_posts(a.astro)
    by_source = {m['source']: s for s, m in posts.items() if m.get('source')}
    if not by_source:
        sys.exit('Ningún artículo tiene `source`. Lanza antes --adopt.')
    series = dict(s.split('=', 1) for s in a.serie)
    diagrams = Diagrams(a.astro, render=not a.no_render)
    outdir = a.out or a.astro / 'src' / 'content' / 'posts'
    upd, new, blocked, seen = [], [], [], set()

    for rel, meta, body in candidates():
        slug = by_source.get(rel)
        seen.add(rel)
        if slug:
            old = posts[slug]
            title = old['title'] if _plain(old['title']) == _plain(meta['title']) else meta['title']
            m = dict(old, title=title, source=rel, updated=_iso(meta.get('updated')) or old['updated'],
                     description=meta.get('description') or old.get('description'), tags=meta.get('tags') or [])
            upd.append((slug, m, body))
            continue
        serie = series.get(rel) or CATEGORY_SERIE.get(meta.get('category'))
        if not serie:
            blocked.append((rel, meta.get('category')))
            continue
        slug = wp_slug(meta['title'])
        card = f'/wp-content/uploads/2026/09/frikiteam-serie-{serie}-1200x630.png'
        name = next((c['name'] for c in json.loads((a.astro / 'src/data/categories.json').read_text()) if c['slug'] == serie), serie)
        has_card = (a.astro / 'public' / card.lstrip('/')).exists()  # la serie `desarrollo` aún no tiene tarjeta
        m = dict(title=meta['title'], source=rel, date=next_slot(posts, len(new)), updated=_iso(meta.get('updated')),
                 category=serie, description=meta.get('description'), tags=meta.get('tags') or [],
                 image=card if has_card else '', imageAlt=f'Serie {name} — Frikiteam' if has_card else '')
        new.append((slug, m, body, rel))

    orphans = [s for s, m in posts.items() if not m.get('source')]
    gone = [s for s, m in posts.items() if m.get('source') and m['source'] not in seen]
    print(f'actualizar {len(upd)} · nuevos {len(new)} · sin serie {len(blocked)} · sin fuente en docs {len(orphans)} · fuente desaparecida {len(gone)}')
    for slug, m, _, rel in new:
        print(f'  NUEVO {rel} → {m["category"]}/{slug}, sale el {m["date"][:10]}')
    for rel, cat in blocked:
        print(f'  SIN SERIE {rel} (category: {cat}) → usa --serie {rel}=<serie>')
    for s in gone:
        print(f'  FUENTE DESAPARECIDA {s} ← {posts[s]["source"]}')
    if not (a.write or a.out):
        return
    outdir.mkdir(parents=True, exist_ok=True)
    for slug, m, b, *_ in upd + new:
        body = convert_body(b, m['title'], diagrams, Images(a.astro, slug, m['source']))
        (outdir / f'{slug}.md').write_text(render_post(m, body), encoding='utf-8')
    print(f'escritos {len(upd) + len(new)} artículos en {outdir}; diagramas sin imagen: {len(diagrams.missing)}')


if __name__ == '__main__':
    main()
