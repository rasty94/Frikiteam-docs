"""Comprobaciones de scripts/publish_to_astro.py. Cada caso salió de un fallo real al comparar con el flujo anterior."""
import sys

sys.path.insert(0, 'scripts')
from publish_to_astro import convert_body, wp_slug, _inline_html  # noqa: E402

no_diagram = lambda code: None


def body(text, title='Título'):
    return convert_body(text, title, no_diagram)


def test_admonicion():
    out = body('!!! warning "Ojo"\n    Cuidado con esto.\n\n    - uno\n    - dos\n\nSiguiente párrafo.\n')
    assert '<div class="admonition warning">\n<p class="admonition-title">Ojo</p>\n\nCuidado con esto.' in out
    assert '- uno\n- dos\n\n</div>\n\nSiguiente párrafo.' in out


def test_blanco_tras_admonicion():
    # Sin la línea en blanco tras </div>, el HTML se traga la tabla, el diagrama o el bloque de código que sigue.
    for sig in ('| a | b |\n|---|---|\n| 1 | 2 |', '```bash\nls\n```'):
        assert '</div>\n\n' + sig.split('\n')[0] in body(f'!!! note "N"\n    texto\n\n{sig}\n')


def test_admonicion_sin_titulo_y_con_titulo_vacio():
    assert 'admonition-title">Tip<' in body('!!! tip\n    x\n')
    assert 'admonition-title' not in body('!!! tip ""\n    x\n')


def test_codigo_no_se_toca():
    code = '```python\n!!! note "no"\n## no es un título\n```\n'
    assert body(code) == code


def test_titulo_inicial_se_quita_siempre():
    assert body('# Otro título distinto\n\nTexto\n') == 'Texto\n'


def test_encabezados_con_id_sin_tildes_y_repetidos():
    out = body('## Qué instalar y para qué\n\n## Uso\n\n## Uso\n')
    assert '<h2 id="que-instalar-y-para-que">Qué instalar y para qué</h2>' in out
    assert '<h2 id="uso">Uso</h2>' in out and '<h2 id="uso_1">Uso</h2>' in out


def test_encabezado_numerado_no_es_lista():
    assert _inline_html('1. Actualizaciones y Parches') == '1. Actualizaciones y Parches'
    assert '<ol>' not in body('### 1. Actualizaciones\n')


def test_raw_de_jinja():
    assert body('{% raw %}\n```yaml\na: {{ b }}\n```\n{% endraw %}\n') == '```yaml\na: {{ b }}\n```\n'


def test_mermaid_con_y_sin_imagen():
    fence = '```mermaid\ngraph TD\n  A-->B\n```\n'
    assert body(fence) == fence  # sin imagen disponible el bloque queda como estaba
    assert convert_body(fence, 'T', lambda code: '/diagrams/x.png') == '![Diagrama: T](/diagrams/x.png)\n'
    # el texto alternativo es la sección en la que está el diagrama, también dentro de una admonición
    out = convert_body('## Arquitectura de Ceph\n\n' + fence + '\n!!! note "N"\n    ' + fence.replace('\n', '\n    ').rstrip() + '\n', 'T', lambda c: '/d.png')
    assert out.count('![Diagrama: Arquitectura de Ceph](/d.png)') == 2
    assert '![Diagrama de flujo](/d.png)' in convert_body('## Diagrama de flujo\n\n' + fence, 'T', lambda c: '/d.png')  # sin repetir la palabra


def test_valla_larga_con_otra_dentro():
    code = '````markdown\n```python\nx = 1\n```\n````\n'
    assert body(code) == code


def test_atributos_de_imagen():
    assert body('![Logo](a.png){width=50%}\n') == '<img src="a.png" alt="Logo" style="width:50%">\n'
    assert body('![Logo](a.png){ width="300" height=100 }\n') == '<img src="a.png" alt="Logo" style="width:300px;height:100px">\n'
    assert body('![Logo](a.png)\n') == '![Logo](a.png)\n'


def test_slug_como_wordpress():
    assert wp_slug('Docker - Contenedores') == 'docker-contenedores'
    assert wp_slug('Terraform &amp; OpenTofu - Infraestructura como Código') == 'terraform-opentofu-infraestructura-como-codigo'
    assert wp_slug('¿Qué es VLSM?') == 'que-es-vlsm'
    assert wp_slug('MTU/MSS Values') == 'mtu-mss-values' and wp_slug('LLaMA.cpp: Compilación') == 'llama-cpp-compilacion'


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for t in tests:
        t()
    print(f'{len(tests)} comprobaciones de publish_to_astro correctas')
