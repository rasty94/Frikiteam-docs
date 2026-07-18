"""Comprobación mínima del formato Markdown->HTML de wordpress_sync.

Ejecutar: python test_wordpress_format.py
"""
from wordpress_sync import markdown_to_html, rewrite_image_srcs


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


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print(f'ok  {name}')
    print('todos los checks pasaron')
