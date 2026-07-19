"""Comprobación mínima del formato Markdown->HTML de wordpress_sync.

Ejecutar: python test_wordpress_format.py
"""
import os
from wordpress_sync import (
    markdown_to_html, rewrite_image_srcs,
    render_mermaid_to_png, inline_admonition_styles,
    _strip_code_fence, enhance_markdown, _strip_html, _structure_lost,
    _protect_structure, _restore_structure,
)


def test_admonition_renders_as_div():
    html = markdown_to_html('!!! note "Aviso"\n    contenido')
    assert 'class="admonition' in html, html


def test_mermaid_becomes_mermaid_block():
    html = markdown_to_html('```mermaid\ngraph TD; A-->B;\n```')
    assert 'class="mermaid"' in html, html


def test_code_has_inline_styles():
    # noclasses -> estilos inline, self-contained en WordPress
    html = markdown_to_html('```python\nprint("hi")\n```')
    assert 'style=' in html and 'highlight' in html, html


def test_table_renders():
    html = markdown_to_html('| a | b |\n|---|---|\n| 1 | 2 |')
    assert '<table>' in html, html


def test_http_image_left_untouched():
    # URLs absolutas no se tocan (no hace red)
    html = '<img src="https://example.com/a.png">'
    assert rewrite_image_srcs(html, '.') == html


def test_missing_local_image_left_untouched():
    # imagen inexistente: se deja tal cual, sin subir (no hace red)
    html = '<img src="no_existe_12345.png">'
    assert rewrite_image_srcs(html, '.') == html


def test_admonition_gets_inline_styles():
    html = markdown_to_html('!!! warning "Ojo"\n    contenido')
    styled = inline_admonition_styles(html)
    assert 'style="background:#fff6ec' in styled, styled  # color de warning


def test_mermaid_renders_to_png():
    import shutil
    if not shutil.which('mmdc'):
        print('  (mmdc no disponible, se omite render de mermaid)')
        return
    png = render_mermaid_to_png('graph TD; A-->B;')
    assert png and os.path.isfile(png), png


def test_strip_code_fence():
    assert _strip_code_fence('```markdown\n# H\ntxt\n```') == '# H\ntxt'
    assert _strip_code_fence('# sin fence') == '# sin fence'


def test_enhance_without_model_returns_original():
    # sin OLLAMA_MODEL no toca la red y devuelve el original
    os.environ.pop('OLLAMA_MODEL', None)
    orig = '# Doc\ncontenido'
    assert enhance_markdown(orig) == orig


def test_protect_restore_es_identidad_en_docs_reales():
    # roundtrip sobre los documentos donde el modelo destrozó la estructura
    import glob
    for path in ['docs/doc/storage/kubernetes_csi.md',
                 'docs/doc/ai/llama_cpp.md',
                 'docs/doc/kubernetes/service_mesh.md']:
        orig = open(path, encoding='utf-8').read()
        protegido, bloques = _protect_structure(orig)
        assert bloques, f'{path}: no protegió nada'
        # el modelo no ve código ni admonitions
        assert '```' not in protegido, path
        assert not [l for l in protegido.split('\n') if l.lstrip().startswith('!!!')], path
        restaurado, faltan = _restore_structure(protegido, bloques)
        assert not faltan, path
        assert restaurado == orig, f'{path}: el roundtrip no es idéntico'


def test_enhance_rechaza_enlace_malformado(monkeypatch=None):
    # caso real: gemma4 escribió "[llama.cpp]" sin URL en la reescritura
    import wordpress_sync as w
    orig = ('# T\n\nMira [llama.cpp](https://x.dev) si quieres entender cómo funciona '
            'la inferencia local por debajo, sin depender de servicios externos ni '
            'de APIs de pago para tus pruebas.\n\n## Sec\n\ntexto\n')
    reescrito = ('Mira [llama.cpp] si quieres entender cómo funciona la inferencia '
                 'local por debajo, sin depender de nada externo en tus pruebas.')
    class _Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': reescrito}}
    post_real, refs_real, srv_real = w.requests.post, w.get_style_references, w._SERVIDOR
    w.requests.post = lambda *a, **k: _Resp()
    w.get_style_references = lambda *a, **k: []
    # servidor falso de dialecto Ollama, acorde con lo que devuelve el mock
    w._SERVIDOR = {'url': 'http://fake:11434', 'modelo': 'test', 'clave': ''}
    try:
        assert w.enhance_markdown(orig) == orig  # descartada, se publica el original
    finally:
        w.requests.post, w.get_style_references, w._SERVIDOR = post_real, refs_real, srv_real


def test_intro_detectada_dentro_de_la_primera_seccion():
    # dos documentos reales cuya prosa vive dentro de "## Introducción" /
    # "## El problema" en vez de suelta tras el título; antes se daban por
    # "sin introducción" y se publicaban sin mejorar
    import re as _re
    from wordpress_sync import extract_frontmatter
    for path in ['docs/doc/docker/docker_runtime_security.md',
                 'docs/doc/cybersecurity/secrets_gitops.md']:
        _, md = extract_frontmatter(open(path, encoding='utf-8').read())
        cuerpo = md
        for patron in (r'\s*#\s[^\n]*\n', r'\s*#{2,6}\s[^\n]*\n'):
            salto = _re.match(patron, cuerpo)
            if salto:
                cuerpo = cuerpo[salto.end():]
        corte = _re.search(r'^(?:#{1,6} |```|\s*(?:!!!|\?\?\?) |\|)', cuerpo, _re.M)
        intro = (cuerpo[:corte.start()] if corte else cuerpo).strip()
        assert len(intro) >= 80, f'{path}: intro no detectada ({len(intro)} chars)'


def test_restore_detecta_marcador_borrado():
    orig = 'Texto\n\n```bash\nls\n```\n\nfin\n'
    protegido, bloques = _protect_structure(orig)
    _, faltan = _restore_structure(protegido.replace('⟦0⟧', ''), bloques)
    assert faltan == [0], faltan


def test_structure_lost_detecta_admonition_perdido():
    # caso real: gemma4:e4b-mlx absorbió 6 admonitions en la prosa
    orig = '## T\n\n!!! note "Aviso"\n    ojo\n\n```bash\nls\n```\n'
    mala = '## T\n\nUn texto cualquiera.\n\n```bash\nls\n```\n'
    perdido = _structure_lost(orig, mala)
    assert perdido and 'admonitions' in perdido, perdido


def test_structure_lost_acepta_reescritura_fiel():
    orig = '## T\n\n!!! note "Aviso"\n    ojo\n\n```bash\nls\n```\n'
    buena = '## Titulo mejor\n\n!!! note "Aviso"\n    ojo con esto\n\n```bash\nls\n```\n'
    assert _structure_lost(orig, buena) is None


def test_strip_html_removes_tags_and_scripts():
    h = '<p>Hola <b>mundo</b></p><script>alert(1)</script>'
    out = _strip_html(h)
    assert 'alert' not in out and 'Hola mundo' in out, out


def test_todo_log_distingue_borrador_de_publicado():
    # el histórico no debe decir "Publicado" cuando es un borrador
    import tempfile, os as _os, shutil
    from wordpress_sync import update_todo_md
    tmp = tempfile.mkdtemp()
    cwd = _os.getcwd()
    try:
        _os.chdir(tmp)
        with open('TODO.md', 'w', encoding='utf-8') as f:
            f.write('# T\n\n## Progreso de Publicación\n\n')
        update_todo_md([{'title': 'Doc A', 'status': 'draft'},
                        {'title': 'Doc B', 'status': 'publish'}])
        out = open('TODO.md', encoding='utf-8').read()
        assert 'Doc A - Borrador creado el' in out, out
        assert 'Doc B - Publicado el' in out, out
    finally:
        _os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print(f'ok  {name}')
    print('todos los checks pasaron')
