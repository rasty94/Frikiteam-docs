import os
import re
from datetime import datetime


def parse_front_matter(markdown_text: str) -> dict:
    # Expect front matter delimited by --- at the top
    if not markdown_text.startswith("---\n"):
        return {}
    end = markdown_text.find("\n---\n", 4)
    if end == -1:
        return {}
    header = markdown_text[4:end]
    meta = {}
    key_val_pattern = re.compile(r"^(\w+):\s*(.*)$")
    lines = header.splitlines()
    key = None
    for line in lines:
        if not line.strip():
            continue
        if line.strip().endswith(":"):
            key = line.strip()[:-1]
            meta[key] = []
            continue
        m = key_val_pattern.match(line)
        if m:
            key = m.group(1)
            meta[key] = m.group(2)
        else:
            if key and isinstance(meta.get(key), list):
                # list item, remove leading dash if any
                item = line.strip()
                if item.startswith("- "):
                    item = item[2:]
                meta[key].append(item)
    return meta


def define_env(env):
    def collect_posts_for_lang(lang: str, page_src_path: str):
        docs_dir = env.conf.get('docs_dir', 'docs')
        base_dir = os.path.join(docs_dir, *( [lang] if lang and lang != 'es' else [] ))
        posts_dir = os.path.join(base_dir, 'blog', 'posts')
        collected = []
        if not os.path.isdir(posts_dir):
            return collected
        for root, _dirs, files in os.walk(posts_dir):
            for fname in files:
                if not fname.endswith('.md'):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception:
                    continue
                meta = parse_front_matter(text)
                title = meta.get('title') or os.path.splitext(fname)[0]
                date_str = meta.get('date') or '1970-01-01'
                try:
                    date = datetime.fromisoformat(str(date_str))
                except Exception:
                    date = datetime(1970, 1, 1)
                categories = meta.get('categories') or []
                # Make link relative to the current page directory
                page_dir = os.path.dirname(page_src_path)
                page_dir_fs = os.path.join(docs_dir, page_dir)
                rel_path_from_page = os.path.relpath(path, page_dir_fs)
                link = rel_path_from_page.replace(os.sep, '/')
                collected.append({
                    'title': title,
                    'date': date,
                    'date_str': date.strftime('%Y-%m-%d'),
                    'categories': categories,
                    'link': link,
                })
        collected.sort(key=lambda p: p['date'], reverse=True)
        return collected

    @env.macro
    def blog_list(group_by_category=False):
        # Determine current language from the page path
        page = env.variables.get('page')
        src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
        lang = 'en' if src_path.startswith('en/') else 'es'
        posts = collect_posts_for_lang(lang, src_path)
        if not posts:
            return "_No hay entradas disponibles._" if lang == 'es' else "_No posts available._"

        if not group_by_category:
            lines = ["# Últimas entradas" if lang == 'es' else "# Latest posts"]
            for p in posts:
                lines.append(f"- [{p['title']}]({p['link']}) — {p['date_str']}")
            return "\n".join(lines)

        # Group by category
        category_to_posts = {}
        for p in posts:
            cats = p['categories'] if isinstance(p['categories'], list) else [p['categories']]
            if not cats:
                cats = ['General']
            for c in cats:
                category_to_posts.setdefault(c, []).append(p)

        lines = ["# Entradas por categoría" if lang == 'es' else "# Posts by category"]
        for category in sorted(category_to_posts.keys(), key=lambda s: s.lower()):
            lines.append(f"\n## {category}")
            for p in category_to_posts[category]:
                lines.append(f"- [{p['title']}]({p['link']}) — {p['date_str']}")
        return "\n".join(lines)

    @env.macro
    def blog_archive():
        page = env.variables.get('page')
        src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
        lang = 'en' if src_path.startswith('en/') else 'es'
        posts = collect_posts_for_lang(lang, src_path)
        if not posts:
            return "_No hay entradas disponibles._" if lang == 'es' else "_No posts available._"
        # Group by year and month
        archive = {}
        for p in posts:
            year = p['date'].year
            month = p['date'].strftime('%m')
            archive.setdefault(year, {}).setdefault(month, []).append(p)
        lines = ["# Archivo" if lang == 'es' else "# Archive"]
        for year in sorted(archive.keys(), reverse=True):
            lines.append(f"\n## {year}")
            for month in sorted(archive[year].keys(), reverse=True):
                month_title = {
                    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril', '05': 'Mayo', '06': 'Junio',
                    '07': 'Julio', '08': 'Agosto', '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
                }[month] if lang == 'es' else datetime.strptime(month, '%m').strftime('%B')
                lines.append(f"\n### {month_title}")
                for p in archive[year][month]:
                    lines.append(f"- [{p['title']}]({p['link']}) — {p['date_str']}")
        return "\n".join(lines)

    @env.macro
    def blog_categories():
        page = env.variables.get('page')
        src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
        lang = 'en' if src_path.startswith('en/') else 'es'
        posts = collect_posts_for_lang(lang, src_path)
        if not posts:
            return "_No hay entradas disponibles._" if lang == 'es' else "_No posts available._"
        category_to_posts = {}
        for p in posts:
            cats = p['categories'] if isinstance(p['categories'], list) else [p['categories']]
            if not cats:
                cats = ['General']
            for c in cats:
                category_to_posts.setdefault(c, []).append(p)
        lines = ["# Categorías" if lang == 'es' else "# Categories"]
        for category in sorted(category_to_posts.keys(), key=lambda s: s.lower()):
            lines.append(f"\n## {category}")
            for p in category_to_posts[category]:
                lines.append(f"- [{p['title']}]({p['link']}) — {p['date_str']}")
        return "\n".join(lines)

    @env.macro
    def sync_badge():
        page = env.variables.get('page')
        if not page:
            return ""
        # Get the front matter
        meta = getattr(page, 'meta', {})
        sync_date = meta.get('sync_date')
        if not sync_date:
            return ""
        # Determine language
        src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
        lang = 'en' if src_path.startswith('en/') else 'es'
        if lang == 'es':
            badge_text = f"Sincronizado: {sync_date}"
            return f'<span class="md-badge md-badge--secondary">{badge_text}</span>'
        else:
            badge_text = f"Synchronized: {sync_date}"
            return f'<span class="md-badge md-badge--secondary">{badge_text}</span>'



def on_post_page_macros(env):
    def inner(html, page, config, site_navigation=None, **kwargs):
        # Add sync badge if sync_date exists in front matter
        meta = getattr(page, 'meta', {})
        sync_date = meta.get('sync_date')
        if sync_date:
            src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
            lang = 'en' if src_path.startswith('en/') else 'es'
            if lang == 'es':
                badge = f'<p><span class="md-badge md-badge--secondary">Sincronizado: {sync_date}</span></p>'
            else:
                badge = f'<p><span class="md-badge md-badge--secondary">Synchronized: {sync_date}</span></p>'
            # Insert before the closing article tag
            if '</article>' in html:
                html = html.replace('</article>', f'{badge}</article>', 1)
            else:
                html += badge
        return html
    return inner


