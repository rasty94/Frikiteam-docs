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
                md_path = Path(docs_dir) / rel_path
                md_path = md_path.with_suffix('.md')
                
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
                                new_article = article_content.replace('>', f'>{metadata_html}', 1)
                                new_content = content.replace(article_content, new_article)
                                
                                with open(html_file, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                                print(f'Updated {html_file}')
        
        except Exception as e:
            print(f'Error processing {html_file}: {e}')