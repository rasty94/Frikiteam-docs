import re


def define_env(env):
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