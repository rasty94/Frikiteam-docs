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

    @env.macro
    def document_metadata():
        page = env.variables.get('page')
        if not page:
            return ""
        
        meta = getattr(page, 'meta', {})
        src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
        lang = 'en' if src_path.startswith('en/') else 'es'
        
        # Collect metadata fields
        metadata_items = []
        
        # Difficulty badge
        difficulty = meta.get('difficulty')
        if difficulty:
            difficulty_colors = {
                'beginner': 'green',
                'intermediate': 'yellow', 
                'advanced': 'orange',
                'expert': 'red'
            }
            color = difficulty_colors.get(difficulty.lower(), 'grey')
            difficulty_labels = {
                'es': {'beginner': 'Principiante', 'intermediate': 'Intermedio', 'advanced': 'Avanzado', 'expert': 'Experto'},
                'en': {'beginner': 'Beginner', 'intermediate': 'Intermediate', 'advanced': 'Advanced', 'expert': 'Expert'}
            }
            label = difficulty_labels[lang].get(difficulty.lower(), difficulty.capitalize())
            metadata_items.append(f'<span class="md-badge md-badge--{color}">{label}</span>')
        
        # Estimated time
        estimated_time = meta.get('estimated_time')
        if estimated_time:
            time_labels = {'es': 'Tiempo estimado', 'en': 'Estimated time'}
            metadata_items.append(f'<span class="md-badge md-badge--secondary">{time_labels[lang]}: {estimated_time}</span>')
        
        # Category
        category = meta.get('category')
        if category:
            category_labels = {'es': 'Categoría', 'en': 'Category'}
            metadata_items.append(f'<span class="md-badge md-badge--primary">{category_labels[lang]}: {category}</span>')
        
        # Status
        status = meta.get('status')
        if status:
            status_colors = {
                'draft': 'grey',
                'review': 'yellow',
                'published': 'green',
                'archived': 'red'
            }
            color = status_colors.get(status.lower(), 'grey')
            status_labels = {
                'es': {'draft': 'Borrador', 'review': 'En revisión', 'published': 'Publicado', 'archived': 'Archivado'},
                'en': {'draft': 'Draft', 'review': 'In Review', 'published': 'Published', 'archived': 'Archived'}
            }
            label = status_labels[lang].get(status.lower(), status.capitalize())
            metadata_items.append(f'<span class="md-badge md-badge--{color}">{label}</span>')
        
        # Prerequisites
        prerequisites = meta.get('prerequisites')
        if prerequisites:
            if isinstance(prerequisites, list):
                prereq_text = ', '.join(prerequisites)
            else:
                prereq_text = str(prerequisites)
            prereq_labels = {'es': 'Prerrequisitos', 'en': 'Prerequisites'}
            metadata_items.append(f'<span class="md-badge md-badge--secondary" title="{prereq_labels[lang]}: {prereq_text}">💡 {prereq_labels[lang]}</span>')
        
        if metadata_items:
            return '<div class="document-metadata">' + ' '.join(metadata_items) + '</div>'
        return ""


# def on_post_page_macros(env):
#     """Hook called after page macros are processed to inject metadata badges."""
#     print("HOOK CALLED: on_post_page_macros")  # Debug output
#     page = env.variables.get('page')
#     if not page:
#         print("HOOK: No page found")
#         return
#     
#     # Check if page has html attribute
#     if hasattr(page, 'html'):
#         print(f"HOOK: Page has html attribute with length: {len(page.html or '')}")
#         content = page.html or ""
#     else:
#         print("HOOK: Page does not have html attribute, using content")
#         content = page.content or ""
#     
#     print(f"HOOK: Processing page with content length: {len(content)}")
#     
#     # Get metadata
#     meta = getattr(page, 'meta', {})
#     src_path = getattr(getattr(page, 'file', None), 'src_path', '') or ''
#     lang = 'en' if src_path.startswith('en/') else 'es'
#     
#     # Collect metadata fields
#     metadata_items = []
#     
#     # Difficulty badge
#     difficulty = meta.get('difficulty')
#     if difficulty:
#         difficulty_colors = {
#             'beginner': 'green',
#             'intermediate': 'yellow', 
#             'advanced': 'orange',
#             'expert': 'red'
#         }
#         color = difficulty_colors.get(difficulty.lower(), 'grey')
#         difficulty_labels = {
#             'es': {'beginner': 'Principiante', 'intermediate': 'Intermedio', 'advanced': 'Avanzado', 'expert': 'Experto'},
#             'en': {'beginner': 'Beginner', 'intermediate': 'Intermediate', 'advanced': 'Advanced', 'expert': 'Expert'}
#         }
#         label = difficulty_labels[lang].get(difficulty.lower(), difficulty.capitalize())
#         metadata_items.append(f'<span class="md-badge md-badge--{color}">{label}</span>')
#     
#     # Estimated time
#     estimated_time = meta.get('estimated_time')
#     if estimated_time:
#         time_labels = {'es': 'Tiempo estimado', 'en': 'Estimated time'}
#         metadata_items.append(f'<span class="md-badge md-badge--secondary">{time_labels[lang]}: {estimated_time}</span>')
#     
#     # Category
#     category = meta.get('category')
#     if category:
#         category_labels = {'es': 'Categoría', 'en': 'Category'}
#         metadata_items.append(f'<span class="md-badge md-badge--primary">{category_labels[lang]}: {category}</span>')
#     
#     # Status
#     status = meta.get('status')
#     if status:
#         status_colors = {
#             'draft': 'grey',
#             'review': 'yellow',
#             'published': 'green',
#             'archived': 'red'
#         }
#         color = status_colors.get(status.lower(), 'grey')
#         status_labels = {
#             'es': {'draft': 'Borrador', 'review': 'En revisión', 'published': 'Publicado', 'archived': 'Archivado'},
#             'en': {'draft': 'Draft', 'review': 'In Review', 'published': 'Published', 'archived': 'Archived'}
#         }
#         label = status_labels[lang].get(status.lower(), status.capitalize())
#         metadata_items.append(f'<span class="md-badge md-badge--{color}">{label}</span>')
#     
#     # Prerequisites
#     prerequisites = meta.get('prerequisites')
#     if prerequisites:
#         if isinstance(prerequisites, list):
#             prereq_text = ', '.join(prerequisites)
#         else:
#             prereq_text = str(prerequisites)
#         prereq_labels = {'es': 'Prerrequisitos', 'en': 'Prerequisites'}
#         metadata_items.append(f'<span class="md-badge md-badge--secondary" title="{prereq_labels[lang]}: {prereq_text}">💡 {prereq_labels[lang]}</span>')
#     
#     # If we have metadata, inject it at the beginning of the content
#     if metadata_items:
#         metadata_html = '<div class="document-metadata">' + ' '.join(metadata_items) + '</div>'
#         print(f"HOOK: Injecting metadata: {metadata_html}")
#         new_content = metadata_html + '\n' + content
#         if hasattr(page, 'html'):
#             page.html = new_content
#             print(f"HOOK: Modified page.html, new length: {len(page.html)}")
#         else:
#            page.content = new_content
#            print(f"HOOK: Modified page.content, new length: {len(page.content)}")
#     else:
#         print("HOOK: No metadata to inject")


def on_post_build(env):
    import re
    from pathlib import Path
    
    site_dir = env.conf.get('site_dir', 'site')
    docs_dir = env.conf.get('docs_dir', 'docs')
    
    for html_file in Path(site_dir).rglob('*.html'):
        if html_file.name in ['404.html', 'search.html']:
            continue
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            article_pattern = r'(<article[^>]*class=\"[^\"]*md-content[^\"]*\"[^>]*>.*?</article>)'
            match = re.search(article_pattern, content, re.DOTALL)
            
            if match:
                article_content = match.group(1)
                rel_path = html_file.relative_to(site_dir)
                lang = 'en' if str(rel_path).startswith('en/') else 'es'
                
                # Convert HTML path to markdown path
                if rel_path.name == 'index.html':
                    # For index.html, try the parent directory name + .md
                    potential_md = Path(docs_dir) / rel_path.parent / f"{rel_path.parent.name}.md"
                    if potential_md.exists():
                        md_path = potential_md
                    else:
                        # Try without the directory name (for cases like databases/index.html -> databases.md)
                        potential_md = Path(docs_dir) / rel_path.parent.with_suffix('.md')
                        if potential_md.exists():
                            md_path = potential_md
                        else:
                            md_path = potential_md  # Use the first attempt as fallback
                else:
                    # For other HTML files, just change extension
                    md_path = Path(docs_dir) / rel_path.with_suffix('.md')
                
                if md_path.exists():
                    # Simple metadata extraction
                    with open(md_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    
                    if md_content.startswith('---'):
                        end = md_content.find('\n---\n', 4)
                        if end != -1:
                            header = md_content[4:end]
                            meta = {}
                            for line in header.splitlines():
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    meta[key.strip()] = value.strip()
                            
                            metadata_items = []
                            
                            difficulty = meta.get('difficulty')
                            if difficulty:
                                colors = {'beginner': 'green', 'intermediate': 'yellow', 'advanced': 'orange', 'expert': 'red'}
                                color = colors.get(difficulty.lower(), 'grey')
                                labels = {'es': {'beginner': 'Principiante', 'intermediate': 'Intermedio', 'advanced': 'Avanzado', 'expert': 'Experto'}, 'en': {'beginner': 'Beginner', 'intermediate': 'Intermediate', 'advanced': 'Advanced', 'expert': 'Expert'}}
                                label = labels[lang].get(difficulty.lower(), difficulty.capitalize())
                                metadata_items.append(f'<span class="md-badge md-badge--{color}">{label}</span>')
                            
                            estimated_time = meta.get('estimated_time')
                            if estimated_time:
                                time_labels = {'es': 'Tiempo estimado', 'en': 'Estimated time'}
                                metadata_items.append(f'<span class="md-badge md-badge--secondary">{time_labels[lang]}: {estimated_time}</span>')
                            
                            category = meta.get('category')
                            if category:
                                category_labels = {'es': 'Categoría', 'en': 'Category'}
                                metadata_items.append(f'<span class="md-badge md-badge--primary">{category_labels[lang]}: {category}</span>')
                            
                            status = meta.get('status')
                            if status:
                                status_colors = {'draft': 'grey', 'review': 'yellow', 'published': 'green', 'archived': 'red'}
                                color = status_colors.get(status.lower(), 'grey')
                                status_labels = {'es': {'draft': 'Borrador', 'review': 'En revisión', 'published': 'Publicado', 'archived': 'Archivado'}, 'en': {'draft': 'Draft', 'review': 'In Review', 'published': 'Published', 'archived': 'Archived'}}
                                label = status_labels[lang].get(status.lower(), status.capitalize())
                                metadata_items.append(f'<span class="md-badge md-badge--{color}">{label}</span>')
                            
                            prerequisites = meta.get('prerequisites')
                            if prerequisites:
                                prereq_labels = {'es': 'Prerrequisitos', 'en': 'Prerequisites'}
                                metadata_items.append(f'<span class="md-badge md-badge--secondary" title="{prereq_labels[lang]}: {prerequisites}">💡 {prereq_labels[lang]}</span>')
                            
                            if metadata_items:
                                metadata_html = '<div class="document-metadata">' + ' '.join(metadata_items) + '</div>'
                                
                                # Only inject if not already present
                                if '<div class="document-metadata">' not in article_content:
                                    new_article = article_content.replace('>', f'>{metadata_html}', 1)
                                    new_content = content.replace(article_content, new_article)
                                    with open(html_file, 'w', encoding='utf-8') as f:
                                        f.write(new_content)
        
        except Exception as e:
            pass