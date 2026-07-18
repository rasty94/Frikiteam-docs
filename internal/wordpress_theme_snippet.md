# Snippet para WordPress (pegar una sola vez)

Hace que los posts sincronizados con `wordpress_sync.py` se vean igual que la web:
admonitions como cajas de colores y diagramas Mermaid dibujados.

## 1. CSS de admonitions

**Apariencia → Personalizar → CSS adicional** y pega esto:

```css
/* Admonitions estilo Material (note, tip, warning, danger, info...) */
.admonition {
  border-left: .25rem solid #448aff;
  border-radius: .2rem;
  background: #f5f7ff;
  padding: .6rem 1rem;
  margin: 1rem 0;
  font-size: .95em;
  overflow: auto;
}
.admonition > .admonition-title {
  font-weight: 700;
  margin: 0 0 .4rem;
}
.admonition.tip,     .admonition.success   { border-left-color:#00c853; background:#f1faf3; }
.admonition.warning, .admonition.caution   { border-left-color:#ff9100; background:#fff6ec; }
.admonition.danger,  .admonition.error     { border-left-color:#ff1744; background:#fff0f2; }
.admonition.info,    .admonition.note      { border-left-color:#448aff; background:#f5f7ff; }
.admonition.quote,   .admonition.abstract  { border-left-color:#9e9e9e; background:#f6f6f6; }

/* Bloques colapsables (??? / details) */
details.admonition { padding: .4rem 1rem; }
details.admonition > summary { cursor: pointer; font-weight: 700; }
```

El resaltado de código NO necesita CSS: `wordpress_sync.py` incrusta los estilos
inline (`noclasses=True`), así que llega self-contained.

## 2. JS de Mermaid

Necesita cargar mermaid.js. La forma más simple sin plugins: **Apariencia →
Editor de temas → footer.php** (o un plugin de "insertar código en el footer") y
añade antes de `</body>`:

```html
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: false });
  // el script sincroniza los diagramas como <pre class="mermaid">
  const blocks = document.querySelectorAll('pre.mermaid');
  blocks.forEach(b => { b.textContent = b.querySelector('code')?.textContent || b.textContent; });
  mermaid.run({ nodes: blocks });
</script>
```

> Si usas un plugin de Mermaid para WordPress, quizá espere ```` ```mermaid ````
> en el contenido en vez de `<pre class="mermaid">`. En ese caso avísame y ajusto
> el `custom_fences` del script para que emita el formato que el plugin espera.
