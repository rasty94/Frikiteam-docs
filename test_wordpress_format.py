"""Comprobación mínima del formato Markdown->HTML de wordpress_sync.

Ejecutar: python test_wordpress_format.py
"""
import os
from wordpress_sync import (
    markdown_to_html, rewrite_image_srcs,
    render_mermaid_to_png, inline_admonition_styles,
    _strip_code_fence, enhance_markdown, _strip_html,
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
