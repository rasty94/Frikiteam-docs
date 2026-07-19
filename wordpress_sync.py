import requests
import json
import os
import re
import html as html_lib
import hashlib
import tempfile
import subprocess
import sys
import mimetypes
import markdown
import pymdownx.superfences
import pymdownx.emoji
from datetime import datetime
import argparse
import glob

# Carga .env sin depender de python-dotenv: son cuatro líneas y evita añadir
# una dependencia al proyecto. Lo ya definido en el entorno tiene prioridad.
def cargar_env(ruta='.env'):
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    if not os.path.isfile(ruta):
        return
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, valor = linea.split('=', 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_env()

# constants.py es el método antiguo de guardar credenciales; se mantiene como
# respaldo para no romper instalaciones existentes, pero .env es lo preferente.
try:
    from constants import (WP_SITE_URL_DEFAULT, WP_USERNAME_DEFAULT,
                           WP_APP_PASSWORD_DEFAULT)
except ImportError:
    WP_SITE_URL_DEFAULT = WP_USERNAME_DEFAULT = WP_APP_PASSWORD_DEFAULT = None

# Configuración desde variables de entorno
wp_site_url = os.getenv('WP_SITE_URL', WP_SITE_URL_DEFAULT)
wp_username = os.getenv('WP_USERNAME', WP_USERNAME_DEFAULT)
wp_app_password = os.getenv('WP_APP_PASSWORD', WP_APP_PASSWORD_DEFAULT)

# Endpoint para crear un post
endpoint = f'{wp_site_url}/wp-json/wp/v2/posts'

# Extensiones alineadas con markdown_extensions de mkdocs.yml, para que el HTML
# publicado en WordPress conserve el mismo formato que la web (admonitions,
# mermaid, tablas, footnotes, mark, keys, emoji, magiclink...).
MD_EXTENSIONS = [
    'admonition', 'attr_list', 'def_list', 'footnotes', 'md_in_html',
    'sane_lists', 'tables', 'toc',
    'pymdownx.highlight', 'pymdownx.superfences', 'pymdownx.inlinehilite',
    'pymdownx.details', 'pymdownx.emoji', 'pymdownx.keys', 'pymdownx.mark',
    'pymdownx.tilde', 'pymdownx.magiclink', 'pymdownx.smartsymbols',
]
MD_EXTENSION_CONFIGS = {
    # noclasses=True incrusta los estilos de Pygments inline: el código sale
    # resaltado en WordPress sin necesidad de cargar un CSS de Pygments aparte.
    'pymdownx.highlight': {'use_pygments': True, 'noclasses': True},
    'pymdownx.superfences': {'custom_fences': [
        {'name': 'mermaid', 'class': 'mermaid',
         'format': pymdownx.superfences.fence_code_format}]},
    'pymdownx.emoji': {'emoji_index': pymdownx.emoji.twemoji,
                       'emoji_generator': pymdownx.emoji.to_svg},
}

# Función para convertir Markdown a HTML
def markdown_to_html(markdown_content):
    return markdown.markdown(
        markdown_content,
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXTENSION_CONFIGS,
    )


# Cache de imágenes ya subidas en esta ejecución: ruta local -> URL en WP.
_media_cache = {}


# Sube una imagen local a la biblioteca de medios de WordPress y devuelve su URL.
# Reutiliza medios existentes (por slug) para no duplicar en cada sync.
def upload_image_to_wp(local_path):
    if local_path in _media_cache:
        return _media_cache[local_path]

    filename = os.path.basename(local_path)
    slug = os.path.splitext(filename)[0]

    # ¿Ya existe en WP? Evita re-subir en syncs repetidos.
    try:
        existing = requests.get(
            f'{wp_site_url}/wp-json/wp/v2/media',
            auth=(wp_username, wp_app_password),
            params={'slug': slug},
        )
        if existing.status_code == 200 and existing.json():
            url = existing.json()[0]['source_url']
            _media_cache[local_path] = url
            return url
    except requests.RequestException as e:
        print(f'  Aviso: no se pudo consultar medios existentes ({e})')

    content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
    with open(local_path, 'rb') as f:
        data = f.read()

    resp = requests.post(
        f'{wp_site_url}/wp-json/wp/v2/media',
        auth=(wp_username, wp_app_password),
        headers={
            'Content-Type': content_type,
            'Content-Disposition': f'attachment; filename="{filename}"',
        },
        data=data,
    )
    if resp.status_code in (200, 201):
        url = resp.json()['source_url']
        _media_cache[local_path] = url
        print(f'  Imagen subida: {filename} -> {url}')
        return url

    print(f'  Error al subir imagen {filename}: {resp.status_code} - {resp.text[:120]}')
    return None


# Reescribe los src de <img> relativos (locales) apuntándolos a WordPress.
# base_dir es la carpeta del .md, para resolver rutas relativas.
def rewrite_image_srcs(html, base_dir):
    def replace(match):
        src = match.group('src')
        if src.startswith(('http://', 'https://', 'data:')):
            return match.group(0)
        local_path = os.path.normpath(os.path.join(base_dir, src))
        if not os.path.isfile(local_path):
            print(f'  Aviso: imagen no encontrada, se deja tal cual: {src}')
            return match.group(0)
        url = upload_image_to_wp(local_path)
        if not url:
            return match.group(0)
        return match.group(0).replace(f'src="{src}"', f'src="{url}"')

    return re.sub(r'<img[^>]*\bsrc="(?P<src>[^"]+)"[^>]*>', replace, html)


# Ruta al puppeteer-config.json junto a este script (para mmdc en CI/sandbox).
_PUPPETEER_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'puppeteer-config.json')


# Renderiza un diagrama Mermaid a PNG con mermaid-cli (mmdc). Cachea por hash del
# código: el mismo diagrama no se re-renderiza. Devuelve la ruta al PNG o None.
def render_mermaid_to_png(code):
    digest = hashlib.sha1(code.encode('utf-8')).hexdigest()[:12]
    tmp_dir = tempfile.gettempdir()
    png_path = os.path.join(tmp_dir, f'mermaid-{digest}.png')
    if os.path.exists(png_path):
        return png_path

    mmd_path = os.path.join(tmp_dir, f'mermaid-{digest}.mmd')
    with open(mmd_path, 'w', encoding='utf-8') as f:
        f.write(code)

    cmd = ['mmdc', '-i', mmd_path, '-o', png_path, '-b', 'transparent']
    if os.path.exists(_PUPPETEER_CONFIG):
        cmd += ['-p', _PUPPETEER_CONFIG]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=90)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        detail = getattr(e, 'stderr', b'')
        if isinstance(detail, bytes):
            detail = detail.decode('utf-8', 'replace')
        print(f'  Aviso: no se pudo renderizar Mermaid ({e}). {detail[:120]}')
        return None
    return png_path


# Sustituye los bloques <pre class="mermaid"> por imágenes PNG subidas a WordPress,
# para que los diagramas se vean sin cargar mermaid.js en el tema.
def render_and_embed_mermaid(html):
    pattern = re.compile(
        r'<pre class="mermaid"><code>(?P<code>.*?)</code></pre>', re.DOTALL)

    def replace(match):
        code = html_lib.unescape(match.group('code')).strip()
        png_path = render_mermaid_to_png(code)
        if not png_path:
            return match.group(0)  # dejar el bloque original como fallback
        url = upload_image_to_wp(png_path)
        if not url:
            return match.group(0)
        return (f'<figure class="mermaid-diagram" style="text-align:center">'
                f'<img src="{url}" alt="Diagrama Mermaid" '
                f'style="max-width:100%;height:auto"></figure>')

    return pattern.sub(replace, html)


# Colores por tipo de admonition (fondo, borde) para estilos inline.
_ADMONITION_COLORS = {
    'note': ('#f5f7ff', '#448aff'), 'info': ('#f5f7ff', '#448aff'),
    'tip': ('#f1faf3', '#00c853'), 'success': ('#f1faf3', '#00c853'),
    'warning': ('#fff6ec', '#ff9100'), 'caution': ('#fff6ec', '#ff9100'),
    'danger': ('#fff0f2', '#ff1744'), 'error': ('#fff0f2', '#ff1744'),
    'quote': ('#f6f6f6', '#9e9e9e'), 'abstract': ('#f6f6f6', '#9e9e9e'),
}


# Añade estilos inline a los <div class="admonition ..."> para que se vean como
# cajas de colores en WordPress sin depender del CSS del tema.
def inline_admonition_styles(html):
    def style_div(match):
        classes = match.group('classes').split()
        kind = next((c for c in classes if c in _ADMONITION_COLORS), 'note')
        bg, border = _ADMONITION_COLORS[kind]
        style = (f'background:{bg};border-left:.25rem solid {border};'
                 f'border-radius:.2rem;padding:.6rem 1rem;margin:1rem 0;overflow:auto')
        return f'<div class="{match.group("classes")}" style="{style}">'

    html = re.sub(r'<div class="(?P<classes>admonition[^"]*)">', style_div, html)
    html = html.replace(
        '<p class="admonition-title">',
        '<p class="admonition-title" style="font-weight:700;margin:0 0 .4rem">')
    return html


# --- Mejora de estilo "blog" con un LLM vía Ollama (local o Cloud) ------------

# Activado con --enhance. Requiere OLLAMA_MODEL; para Ollama Cloud, además
# OLLAMA_HOST=https://ollama.com y OLLAMA_API_KEY.
ENHANCE_BLOG = False

# Servidores de inferencia por orden de prioridad, leídos de .env para no dejar
# ninguna URL de infraestructura en el código. Formato de INFERENCE_SERVERS:
#   url|modelo|clave_opcional ; url|modelo ; ...
# Una URL con /v1 habla el dialecto OpenAI (vLLM); el resto, el de Ollama.
def _parsear_servidores():
    servidores = []
    for entrada in os.getenv('INFERENCE_SERVERS', '').split(';'):
        partes = [p.strip() for p in entrada.split('|')]
        if len(partes) >= 2 and partes[0]:
            servidores.append({
                'url': partes[0].rstrip('/'),
                'modelo': partes[1],
                'clave': os.getenv(partes[2], partes[2]) if len(partes) > 2 and partes[2] else '',
            })
    return servidores


SERVIDORES = _parsear_servidores()

# Servidor elegido en esta ejecución (se resuelve una vez, no por documento).
_SIN_RESOLVER = object()
_SERVIDOR = _SIN_RESOLVER


# ¿Responde el servidor? Prueba el endpoint que corresponda a su dialecto.
def servidor_disponible(srv, timeout=8):
    es_openai = '/v1' in srv['url']
    url = f"{srv['url']}/models" if es_openai else f"{srv['url']}/api/tags"
    cabeceras = {'Authorization': f"Bearer {srv['clave']}"} if srv['clave'] else {}
    try:
        return requests.get(url, headers=cabeceras, timeout=timeout).status_code == 200
    except requests.RequestException:
        return False


# Recorre los servidores por prioridad. Si el primero (el potente) no responde,
# avisa y sigue; antes de caer al último (local) pregunta, porque ahí la carga
# la soporta la máquina del usuario.
def resolver_servidor(interactivo=True):
    if not SERVIDORES:
        print('  Aviso: INFERENCE_SERVERS no configurado en .env')
        return None

    for i, srv in enumerate(SERVIDORES):
        es_ultimo_local = 'localhost' in srv['url'] or '127.0.0.1' in srv['url']
        if not servidor_disponible(srv):
            print(f"  Aviso: {srv['url']} no responde.")
            continue
        if es_ultimo_local and i > 0 and interactivo and sys.stdin.isatty():
            if input('  ¿Ejecutar en local? (S/n): ').strip().lower() in ('n', 'no'):
                return None
        return srv

    print('  Ningún servidor de inferencia disponible; se publica sin reescribir.')
    return None


# Una sola llamada de chat, hablando el dialecto que toque.
def chat_inferencia(srv, system_prompt, user_content, timeout=600):
    es_openai = '/v1' in srv['url']
    cabeceras = {'Content-Type': 'application/json'}
    if srv['clave']:
        cabeceras['Authorization'] = f"Bearer {srv['clave']}"
    mensajes = [{'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content}]

    if es_openai:
        url = f"{srv['url']}/chat/completions"
        payload = {'model': srv['modelo'], 'messages': mensajes, 'max_tokens': 32000}
    else:
        url = f"{srv['url']}/api/chat"
        payload = {'model': srv['modelo'], 'messages': mensajes, 'stream': False}

    resp = requests.post(url, headers=cabeceras, json=payload, timeout=timeout)
    resp.raise_for_status()
    datos = resp.json()
    if es_openai:
        return datos['choices'][0]['message']['content'].strip()
    return datos.get('message', {}).get('content', '').strip()

# Solo se reescribe la introducción: pedirle el documento entero a un modelo
# local pequeño falla siempre (gemma4:e4b-mlx perdía estructura en el 100% de
# los casos, incluso ocultándosela tras marcadores). La intro es donde está el
# tono y no tiene estructura que perder.
# Corchetes sueltos: el modelo escribe "[llama.cpp]" sin URL y queda como texto
# literal en la web.
def _colgantes(texto):
    return len(re.findall(r'\[[^\]]+\](?!\()', texto))


# Intento ambicioso: documento entero. Solo lo logran los modelos potentes; la
# validación posterior decide si se acepta.
_DOC_SYSTEM_PROMPT = (
    "Eres un editor técnico. Reescribe el siguiente documento Markdown para que "
    "se lea como un buen artículo de blog: introducción que enganche, transiciones "
    "naturales entre secciones y un cierre breve. REGLAS ESTRICTAS: "
    "1) Conserva LITERALMENTE todo bloque de código, comando, salida de terminal, "
    "diagrama ```mermaid```, enlace, imagen y tabla. "
    "2) No inventes datos técnicos ni cambies versiones, comandos o parámetros. "
    "3) Mantén TODOS los encabezados y su jerarquía exacta. "
    "4) No añadas frontmatter YAML. "
    "5) Responde SOLO con el Markdown resultante, sin comentarios."
)

_BLOG_SYSTEM_PROMPT = (
    "Eres un editor técnico. Reescribe la introducción de este artículo para que "
    "enganche desde la primera frase, en el tono del autor. REGLAS ESTRICTAS: "
    "1) No añadas encabezados, listas, tablas, código ni frontmatter. "
    "2) Conserva los enlaces Markdown tal cual. "
    "3) No inventes datos técnicos ni cambies versiones, comandos o parámetros. "
    "4) Mantén una longitud similar a la original. "
    "5) Responde SOLO con el párrafo reescrito, sin comentarios ni explicaciones."
)


# Saca de la vista del modelo todo lo que no debe tocar (bloques de código,
# admonitions y tablas) sustituyéndolo por marcadores. Así no puede alterarlo:
# gemma4:e4b-mlx perdía estructura en el 100% de los documentos aunque el prompt
# se lo prohibiera. Devuelve (texto_con_marcadores, bloques).
def _protect_structure(md):
    lines = md.split('\n')
    out, blocks = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith('```'):          # bloque de código o mermaid
            chunk = [line]
            i += 1
            while i < len(lines):
                chunk.append(lines[i])
                cerrado = lines[i].lstrip().startswith('```')
                i += 1
                if cerrado:
                    break
        elif re.match(r'^\s*(?:!!!|\?\?\?)\s', line):  # admonition + cuerpo indentado
            chunk = [line]
            i += 1
            while i < len(lines) and (lines[i].startswith((' ', '\t')) or not lines[i].strip()):
                if not lines[i].strip():
                    siguiente = lines[i + 1] if i + 1 < len(lines) else ''
                    if siguiente and not siguiente.startswith((' ', '\t')):
                        break
                chunk.append(lines[i])
                i += 1
        elif line.startswith('|'):                    # tabla
            chunk = [line]
            i += 1
            while i < len(lines) and lines[i].startswith('|'):
                chunk.append(lines[i])
                i += 1
        elif re.match(r'^#{1,6} ', line):             # encabezado
            # ponytail: se protegen en vez de dejar que el modelo los reescriba;
            # gemma4:e4b-mlx se comía 7 de ellos por documento. Si algún día se
            # usa un modelo fiable, quitar esta rama para que mejore los títulos.
            chunk = [line]
            i += 1
        else:
            out.append(line)
            i += 1
            continue
        blocks.append('\n'.join(chunk))
        out.append(f'⟦{len(blocks) - 1}⟧')
    return '\n'.join(out), blocks


# Devuelve los bloques originales a su sitio. Si el modelo se comió algún
# marcador, lo indica para poder descartar la reescritura.
def _restore_structure(md, blocks):
    faltan = [i for i in range(len(blocks)) if f'⟦{i}⟧' not in md]
    for i, bloque in enumerate(blocks):
        md = md.replace(f'⟦{i}⟧', bloque)
    return md, faltan


# Comprueba que la reescritura no haya perdido elementos estructurales.
# Un modelo pequeño puede absorber admonitions o bloques de código en la prosa
# pese a que el prompt lo prohíba; publicar eso sería perder contenido.
# Devuelve una descripción de lo perdido, o None si está todo.
def _structure_lost(original, rewritten):
    checks = (
        ('bloques de código', lambda t: t.count('```')),
        ('admonitions', lambda t: len(re.findall(r'^\s*(?:!!!|\?\?\?) ', t, re.M))),
        ('encabezados', lambda t: len(re.findall(r'^#{1,6} ', t, re.M))),
        ('tablas', lambda t: len(re.findall(r'^\|', t, re.M))),
    )
    perdidos = []
    for nombre, contar in checks:
        antes, despues = contar(original), contar(rewritten)
        if despues < antes:
            perdidos.append(f'{antes - despues} {nombre}')
    return ', '.join(perdidos) if perdidos else None


# Quita fences ```markdown ... ``` con que el modelo a veces envuelve su salida.
def _strip_code_fence(text):
    text = re.sub(r'^\s*```(?:markdown|md)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)
    return text.strip()


# Convierte HTML a texto plano legible (para usar posts existentes como ejemplo
# de estilo, no como contenido a copiar).
def _strip_html(html):
    text = re.sub(r'(?is)<(script|style).*?</\1>', '', html)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_lib.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


# Cache de los posts de referencia (se piden una vez por ejecución).
_style_refs_cache = None


# Obtiene los últimos posts publicados en WordPress como muestra del tono del
# autor, para que el modelo escriba parecido. Devuelve lista de textos planos.
def get_style_references(count=6, max_chars=1200):
    global _style_refs_cache
    if _style_refs_cache is not None:
        return _style_refs_cache

    refs = []
    try:
        resp = requests.get(
            endpoint,
            auth=(wp_username, wp_app_password),
            params={'status': 'publish', 'per_page': count,
                    'orderby': 'date', 'order': 'desc'},
        )
        resp.raise_for_status()
        for post in resp.json():
            body = _strip_html(post.get('content', {}).get('rendered', ''))
            if len(body) > 200:  # ignorar posts casi vacíos
                refs.append(body[:max_chars])
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f'  Aviso: no se pudieron obtener posts de referencia ({e})')

    _style_refs_cache = refs
    if refs:
        print(f'  Usando {len(refs)} post(s) publicados como referencia de estilo')
    return refs


# Reescribe el cuerpo Markdown con Ollama. Ante cualquier fallo devuelve el
# original para no bloquear la publicación.
def enhance_markdown(md_text):
    global _SERVIDOR
    if _SERVIDOR is _SIN_RESOLVER:
        _SERVIDOR = resolver_servidor()
    if not _SERVIDOR:
        return md_text
    srv = _SERVIDOR

    refs = get_style_references()
    estilo = ''
    if refs:
        estilo = ("\n\nA continuación tienes ejemplos REALES de artículos del autor. "
                  "Imita su tono, voz y ritmo (longitud de frases, cercanía, tipo de "
                  "introducciones y cierres, uso de segunda persona) SIN copiar su "
                  "contenido ni su tema:\n\n" + "\n\n--- EJEMPLO ---\n\n".join(refs))

    # Intento 1: documento completo. Solo los modelos potentes lo consiguen; la
    # validación decide, no la fe en el modelo.
    try:
        salida = chat_inferencia(srv, _DOC_SYSTEM_PROMPT + estilo, md_text)
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f'  Aviso: inferencia no disponible ({str(e)[:70]}); se publica el original')
        return md_text

    if salida:
        completo = _strip_code_fence(salida)
        perdido = _structure_lost(md_text, completo)
        if not perdido and _colgantes(completo) <= _colgantes(md_text):
            print(f"  Documento reescrito con {srv['modelo']}")
            return completo
        print(f'  Aviso: reescritura completa descartada ({perdido or "enlaces malformados"}); '
              f'se prueba solo la introducción')

    # Intento 2: solo la prosa introductoria, donde no hay estructura que romper
    h1 = re.match(r'\s*#\s[^\n]*\n', md_text)
    cabecera = h1.group(0) if h1 else ''
    cuerpo = md_text[h1.end():] if h1 else md_text
    corte = re.search(r'^(?:#{1,6} |```|\s*(?:!!!|\?\?\?) |\|)', cuerpo, re.M)
    intro = cuerpo[:corte.start()] if corte else cuerpo
    resto = cuerpo[corte.start():] if corte else ''
    if len(intro.strip()) < 80:
        print('  Aviso: sin introducción que reescribir; se publica tal cual')
        return md_text

    try:
        nueva = _strip_code_fence(chat_inferencia(srv, _BLOG_SYSTEM_PROMPT + estilo, intro))
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f'  Aviso: inferencia no disponible ({str(e)[:70]}); se publica el original')
        return md_text
    if not nueva:
        return md_text

    if _colgantes(nueva) > _colgantes(intro):
        print('  Aviso: la reescritura dejó enlaces Markdown malformados; se publica el original')
        return md_text
    perdido = _structure_lost(intro, nueva) or _structure_lost(nueva, intro)
    if perdido:
        print(f'  Aviso: la introducción alteró la estructura ({perdido}); se publica el original')
        return md_text

    print(f"  Introducción reescrita con {srv['modelo']}")
    reescrito = cabecera + nueva.strip() + '\n'
    return reescrito + '\n' + resto if resto else reescrito


# Función para extraer metadatos del frontmatter
def extract_frontmatter(content):
    lines = content.split('\n')
    if lines[0] == '---':
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                end_idx = i
                break
        if end_idx > 0:
            frontmatter = '\n'.join(lines[1:end_idx])
            body = '\n'.join(lines[end_idx+1:])
            return frontmatter, body
    return '', content

# Función para parsear frontmatter (simple)
def parse_frontmatter(frontmatter):
    metadata = {}
    for line in frontmatter.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata

# Función para generar tags de WordPress desde metadatos
def generate_wp_tags(metadata):
    tags = []
    if 'tags' in metadata:
        # Parsear lista de tags
        tag_str = metadata['tags'].strip('[]')
        tags = [tag.strip().strip('"').strip("'") for tag in tag_str.split(',')]
    if 'keywords' in metadata:
        keyword_tags = [kw.strip() for kw in metadata['keywords'].split(',')]
        tags.extend(keyword_tags)
    return list(set(tags))  # Eliminar duplicados

# Función para crear post desde archivo Markdown
def create_post_from_md(file_path, status='draft'):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, body = extract_frontmatter(content)
    metadata = parse_frontmatter(frontmatter)

    # Opcional: reescribir el cuerpo con Ollama para darle tono "blog"
    if ENHANCE_BLOG:
        body = enhance_markdown(body)

    # Convertir Markdown a HTML
    html_content = markdown_to_html(body)

    # Subir imágenes locales a WordPress y reescribir sus rutas (relativas al .md)
    html_content = rewrite_image_srcs(html_content, os.path.dirname(file_path))

    # Renderizar diagramas Mermaid a PNG y embeberlos (self-contained, sin JS)
    html_content = render_and_embed_mermaid(html_content)

    # Estilos inline en admonitions para que se vean como cajas sin CSS del tema
    html_content = inline_admonition_styles(html_content)

    # Preparar datos del post
    post_data = {
        'title': metadata.get('title', os.path.basename(file_path)),
        'content': html_content,
        'status': status,
        'excerpt': metadata.get('description', ''),
        'tag_names': generate_wp_tags(metadata)
    }

    return post_data

# Función para actualizar TODO.md con posts publicados
def update_todo_md(published_posts):
    todo_file = 'TODO.md'
    if not os.path.exists(todo_file):
        return

    with open(todo_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar sección de progreso o añadirla
    if '## Progreso de Publicación' not in content:
        content += '\n## Progreso de Publicación\n\n'

    for post in published_posts:
        # Distinguir borrador de publicado: registrar "Publicado" un draft
        # induce a error al releer el histórico meses después.
        estado = 'Publicado' if post.get('status') == 'publish' else 'Borrador creado'
        entry = f'- {post["title"]} - {estado} el {datetime.now().strftime("%Y-%m-%d")}\n'
        if entry not in content:
            content = content.replace('## Progreso de Publicación\n\n', f'## Progreso de Publicación\n\n{entry}')

    with open(todo_file, 'w', encoding='utf-8') as f:
        f.write(content)

# Función para publicar post
def publish_post(post_data):
    headers = {
        'Content-Type': 'application/json'
    }

    # Verificar autenticación
    auth_check = requests.get(f'{wp_site_url}/wp-json/wp/v2/users/me', auth=(wp_username, wp_app_password))
    if auth_check.status_code != 200:
        print(f'Error de autenticación: {auth_check.status_code} - {auth_check.text}')
        return False

    print("Autenticación exitosa.")

    # Crear post
    response = requests.post(endpoint, auth=(wp_username, wp_app_password), headers=headers, data=json.dumps(post_data))

    if response.status_code == 201:
        print(f'Post "{post_data["title"]}" creado exitosamente como {post_data["status"]}.')
        return True
    else:
        print(f'Error: {response.status_code} - {response.text}')
        return False

# Busca un post existente por título exacto (en cualquier estado) y devuelve su
# id, o None. Evita que --file cree un duplicado de algo ya sincronizado.
def find_post_by_title(title):
    try:
        resp = requests.get(
            endpoint,
            auth=(wp_username, wp_app_password),
            params={'search': title, 'per_page': 20,
                    'status': 'publish,draft,pending,private'},
        )
        resp.raise_for_status()
        for post in resp.json():
            if post['title']['rendered'].strip() == title.strip():
                return post['id']
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f'  Aviso: no se pudo buscar el post existente ({e})')
    return None


# Función para actualizar post existente
def update_post(post_id, post_data):
    headers = {
        'Content-Type': 'application/json',
        'X-HTTP-Method-Override': 'PUT'
    }

    url = f'{endpoint}/{post_id}'
    response = requests.post(url, auth=(wp_username, wp_app_password), headers=headers, data=json.dumps(post_data))

    if response.status_code == 200:
        print(f'Post actualizado exitosamente.')
        return True
    else:
        print(f'Error al actualizar: {response.status_code} - {response.text}')
        return False

# Función para sincronizar todos los posts existentes
def sync_all_posts(status_new='draft'):
    # Verificar autenticación
    auth_check = requests.get(f'{wp_site_url}/wp-json/wp/v2/users/me', auth=(wp_username, wp_app_password))
    if auth_check.status_code != 200:
        print(f'Error de autenticación: {auth_check.status_code} - {auth_check.text}')
        return

    print("Autenticación exitosa.")

    # Obtener todos los posts
    response = requests.get(endpoint, auth=(wp_username, wp_app_password), params={'per_page': 100})
    if response.status_code != 200:
        print(f'Error al obtener posts: {response.status_code} - {response.text}')
        return

    posts = response.json()
    print(f'Encontrados {len(posts)} posts en WordPress.')

    # Obtener todos los tags
    tags_response = requests.get(f'{wp_site_url}/wp-json/wp/v2/tags', auth=(wp_username, wp_app_password), params={'per_page': 100})
    if tags_response.status_code != 200:
        print(f'Error al obtener tags: {tags_response.status_code} - {tags_response.text}')
        return

    tags = tags_response.json()
    tag_dict = {tag['name']: tag['id'] for tag in tags}
    print(f'Encontrados {len(tags)} tags en WordPress.')

    # Crear diccionario de títulos a archivos MD
    md_files = list_md_files()
    md_dict = {}
    for f in md_files:
        title = get_md_title(f)
        md_dict[title] = f

    updated_posts = []
    for post in posts:
        title = post['title']['rendered']
        if title in md_dict:
            file_path = md_dict[title]
            print(f'Procesando post: {title} ({file_path})')
            post_data = create_post_from_md(file_path, post['status'])  # Mantener status actual
            html_content = post_data['content']
            current_content = post['content']['rendered']
            current_excerpt = post.get('excerpt', {}).get('rendered', '')
            current_title = title
            current_tag_ids = post.get('tags', [])

            tag_names = post_data.get('tag_names', [])
            tag_ids = [tag_dict[name] for name in tag_names if name in tag_dict]
            missing_tags = [name for name in tag_names if name not in tag_dict]
            if missing_tags:
                print(f'Tags no encontrados en WP (se omitirán): {missing_tags}')

            # Verificar si hay cambios
            changed = False
            update_data = {}

            if html_content.strip() != current_content.strip():
                update_data['content'] = html_content
                changed = True

            if post_data['title'] != current_title:
                update_data['title'] = post_data['title']
                changed = True

            if post_data.get('excerpt', '') != current_excerpt:
                update_data['excerpt'] = post_data.get('excerpt', '')
                changed = True

            if set(tag_ids) != set(current_tag_ids):
                update_data['tags'] = tag_ids
                changed = True

            if changed:
                if update_post(post['id'], update_data):
                    updated_posts.append(post_data)
                    print(f'Actualizado: {title}')
                else:
                    print(f'Error al actualizar: {title}')
            else:
                print(f'No cambios necesarios: {title}')
        else:
            print(f'No encontrado archivo MD para: {title}')

    # Crear nuevos posts para MD sin post correspondiente
    existing_titles = {post['title']['rendered'] for post in posts}
    for title, file_path in md_dict.items():
        if title not in existing_titles:
            print(f'Creando nuevo post: {title} ({file_path})')
            post_data = create_post_from_md(file_path, status_new)  # Usar status_new
            tag_names = post_data.get('tag_names', [])
            tag_ids = [tag_dict[name] for name in tag_names if name in tag_dict]
            post_data['tags'] = tag_ids
            if publish_post(post_data):
                updated_posts.append(post_data)
                print(f'Creado: {title}')
            else:
                print(f'Error al crear: {title}')

    if updated_posts:
        update_todo_md(updated_posts)
        print(f"\nProcesados {len(updated_posts)} posts (actualizados o creados). TODO.md actualizado.")
    else:
        print("\nNo se procesó ningún post.")

# Función para listar archivos MD
def list_md_files(base_path='docs'):
    md_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    return sorted(md_files)

# Función para obtener título de un archivo MD
def get_md_title(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        frontmatter, _ = extract_frontmatter(content)
        metadata = parse_frontmatter(frontmatter)
        return metadata.get('title', os.path.basename(file_path))
    except Exception:
        return os.path.basename(file_path)

# Lista los modelos instalados en un servidor Ollama (para elegir en interactivo).
def list_ollama_models(host, api_key=None):
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    try:
        resp = requests.get(f'{host.rstrip("/")}/api/tags', headers=headers, timeout=5)
        resp.raise_for_status()
        return [m['name'] for m in resp.json().get('models', [])]
    except (requests.RequestException, ValueError, KeyError):
        return []


# Pregunta al usuario si quiere mejora "blog" con IA y con qué backend (local o
# cloud). Configura ENHANCE_BLOG y las variables OLLAMA_* en consecuencia.
def prompt_enhance_config():
    global ENHANCE_BLOG
    answer = input("\n¿Aplicar estilo 'blog' con IA antes de publicar? (s/N): ").strip().lower()
    if answer not in ('s', 'si', 'sí', 'y', 'yes'):
        ENHANCE_BLOG = False
        return

    backend = input("  Backend IA - [1] Ollama local  [2] Ollama Cloud  [1]: ").strip() or '1'

    if backend == '2':
        os.environ['OLLAMA_HOST'] = 'https://ollama.com'
        api_key = input("  OLLAMA_API_KEY (Enter para usar la del entorno): ").strip()
        if api_key:
            os.environ['OLLAMA_API_KEY'] = api_key
        elif not os.getenv('OLLAMA_API_KEY'):
            print("  ⚠️ No hay API key; Ollama Cloud fallará y se publicará el original.")
        default_model = os.getenv('OLLAMA_MODEL', 'gpt-oss:120b')
        model = input(f"  Modelo cloud [{default_model}]: ").strip() or default_model
    else:
        host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        if host.startswith('https://ollama.com'):
            host = 'http://localhost:11434'
        os.environ['OLLAMA_HOST'] = host
        os.environ.pop('OLLAMA_API_KEY', None)  # local no usa key
        models = list_ollama_models(host)
        if models:
            print("  Modelos locales disponibles:")
            for i, m in enumerate(models, 1):
                print(f"    {i}. {m}")
            choice = input(f"  Elige número o escribe el nombre [{models[0]}]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(models):
                model = models[int(choice) - 1]
            else:
                model = choice or models[0]
        else:
            print(f"  (No pude listar modelos en {host}; escribe el nombre manualmente)")
            model = input(f"  Modelo [{os.getenv('OLLAMA_MODEL', 'llama3.1')}]: ").strip() \
                or os.getenv('OLLAMA_MODEL', 'llama3.1')

    os.environ['OLLAMA_MODEL'] = model
    ENHANCE_BLOG = True
    print(f"  ✓ Estilo blog ACTIVADO — host={os.environ['OLLAMA_HOST']}  modelo={model}")


# Función interactiva para seleccionar archivos
def interactive_mode():
    md_files = list_md_files()
    if not md_files:
        print("No se encontraron archivos .md en docs/")
        return

    # Opción de búsqueda
    search_query = input("Buscar por palabra clave en título o nombre de archivo (opcional, presiona Enter para ver todos): ").strip().lower()
    if search_query:
        filtered_files = []
        for f in md_files:
            title = get_md_title(f).lower()
            filename = os.path.basename(f).lower()
            if search_query in title or search_query in filename:
                filtered_files.append(f)
        md_files = filtered_files
        if not md_files:
            print(f"No se encontraron archivos que contengan '{search_query}' en título o nombre.")
            return

    print("Archivos Markdown disponibles:")
    for i, file in enumerate(md_files, 1):
        title = get_md_title(file)
        print(f"{i}. {title} ({file})")

    selections = input("Selecciona números separados por coma (ej: 1,3,5) o 'all' para todos: ").strip()
    if selections.lower() == 'all':
        selected_files = md_files
    else:
        indices = [int(x.strip()) - 1 for x in selections.split(',') if x.strip().isdigit()]
        selected_files = [md_files[i] for i in indices if 0 <= i < len(md_files)]

    if not selected_files:
        print("No se seleccionaron archivos válidos.")
        return

    status = input("Estado del post (draft/publish) [draft]: ").strip().lower() or 'draft'
    if status not in ['draft', 'publish']:
        status = 'draft'

    # Preguntar por la mejora "blog" con IA (local/cloud/modelo)
    prompt_enhance_config()

    published_posts = []
    for file_path in selected_files:
        print(f"\nProcesando {file_path}...")
        post_data = create_post_from_md(file_path, status)
        if publish_post(post_data):
            published_posts.append(post_data)

    if published_posts:
        update_todo_md(published_posts)
        print("\nTODO.md actualizado con posts publicados.")

# CLI
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sincronizar documentación Markdown a WordPress')
    parser.add_argument('--file', help='Archivo Markdown específico a sincronizar')
    parser.add_argument('--status', choices=['draft', 'publish'], default='draft', help='Estado del post')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo para seleccionar archivos')
    parser.add_argument('--all', action='store_true', help='Sincronizar todos los posts existentes con archivos Markdown')
    parser.add_argument('--publish', action='store_true', help='Publicar nuevos posts en lugar de dejarlos como draft (solo para --all)')
    parser.add_argument('--enhance', action='store_true', help='Reescribir el cuerpo con Ollama para darle tono blog (usa OLLAMA_MODEL/OLLAMA_HOST/OLLAMA_API_KEY)')

    args = parser.parse_args()

    ENHANCE_BLOG = args.enhance
    if ENHANCE_BLOG:
        print(f"Mejora 'blog' con Ollama ACTIVADA (modelo: {os.getenv('OLLAMA_MODEL', 'no definido')})")

    if args.all:
        status_new = 'publish' if args.publish else 'draft'
        sync_all_posts(status_new)
    elif args.interactive:
        interactive_mode()
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Archivo no encontrado: {args.file}")
        else:
            post_data = create_post_from_md(args.file, args.status)
            # Si ya existe un post con ese título, actualizarlo en vez de
            # crear un duplicado.
            existing_id = find_post_by_title(post_data['title'])
            if existing_id:
                print(f"Ya existe un post con ese título (id {existing_id}): se actualiza.")
                ok = update_post(existing_id, post_data)
            else:
                ok = publish_post(post_data)
            if ok:
                update_todo_md([post_data])
                print("TODO.md actualizado.")
    else:
        print("Usa --file para especificar un archivo, --interactive para modo interactivo o --all para sincronizar todos.")