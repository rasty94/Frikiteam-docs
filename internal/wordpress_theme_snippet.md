# Formato de los posts en WordPress

Desde la versión con render self-contained, `wordpress_sync.py` genera posts que
**no necesitan tocar el tema de WordPress**:

| Elemento | Cómo se resuelve |
| --- | --- |
| Código | Resaltado con estilos Pygments **inline** (`noclasses=True`) |
| Admonitions | `<div>` con **estilos inline** (cajas de colores) — ver `inline_admonition_styles` |
| Mermaid | Renderizado a **PNG con `mmdc`** y subido a la biblioteca de medios; se embebe como `<img>` |
| Imágenes locales | Subidas a medios de WP y `src` reescrito |

No hace falta pegar CSS ni JS en el tema. Todo llega dentro del `post_content`.

## Requisito para Mermaid

El render de diagramas usa **mermaid-cli** en la máquina que ejecuta el sync:

```bash
npm install -g @mermaid-js/mermaid-cli   # provee el comando `mmdc`
```

Si `mmdc` no está disponible, el diagrama se deja como bloque `<pre class="mermaid">`
(fallback) y el resto del post se publica igual. En ese caso, para dibujarlo en el
navegador harían falta estas líneas en el footer del tema:

```html
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true });
</script>
```

Pero con `mmdc` instalado **no es necesario**: los diagramas llegan ya como imagen.
