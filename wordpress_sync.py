import requests
import json
import os
import markdown
from datetime import datetime
import argparse
import glob
from constants import WP_SITE_URL_DEFAULT, WP_USERNAME_DEFAULT, WP_APP_PASSWORD_DEFAULT

# Configuración desde variables de entorno
wp_site_url = os.getenv('WP_SITE_URL', WP_SITE_URL_DEFAULT)
wp_username = os.getenv('WP_USERNAME', WP_USERNAME_DEFAULT)
wp_app_password = os.getenv('WP_APP_PASSWORD', WP_APP_PASSWORD_DEFAULT)

# Endpoint para crear un post
endpoint = f'{wp_site_url}/wp-json/wp/v2/posts'

# Función para convertir Markdown a HTML
def markdown_to_html(markdown_content):
    return markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])

# Función para extraer metadatos del frontmatter
def extract_frontmatter(content):
    lines = content.split('\n')
    if lines[0] == '---':
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                end_idx = i
                break
        if end_idx > 0:
            frontmatter = '\n'.join(lines[1:end_idx])
            body = '\n'.join(lines[end_idx+1:])
            return frontmatter, body
    return '', content

# Función para parsear frontmatter (simple)
def parse_frontmatter(frontmatter):
    metadata = {}
    for line in frontmatter.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata

# Función para generar tags de WordPress desde metadatos
def generate_wp_tags(metadata):
    tags = []
    if 'tags' in metadata:
        # Parsear lista de tags
        tag_str = metadata['tags'].strip('[]')
        tags = [tag.strip().strip('"').strip("'") for tag in tag_str.split(',')]
    if 'keywords' in metadata:
        keyword_tags = [kw.strip() for kw in metadata['keywords'].split(',')]
        tags.extend(keyword_tags)
    return list(set(tags))  # Eliminar duplicados

# Función para crear post desde archivo Markdown
def create_post_from_md(file_path, status='draft'):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, body = extract_frontmatter(content)
    metadata = parse_frontmatter(frontmatter)

    # Convertir Markdown a HTML
    html_content = markdown_to_html(body)

    # Preparar datos del post
    post_data = {
        'title': metadata.get('title', os.path.basename(file_path)),
        'content': html_content,
        'status': status,
        'excerpt': metadata.get('description', ''),
        'tag_names': generate_wp_tags(metadata)
    }

    return post_data

# Función para actualizar TODO.md con posts publicados
def update_todo_md(published_posts):
    todo_file = 'TODO.md'
    if not os.path.exists(todo_file):
        return

    with open(todo_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar sección de progreso o añadirla
    if '## Progreso de Publicación' not in content:
        content += '\n## Progreso de Publicación\n\n'

    for post in published_posts:
        entry = f'- {post["title"]} - Publicado el {datetime.now().strftime("%Y-%m-%d")}\n'
        if entry not in content:
            content = content.replace('## Progreso de Publicación\n\n', f'## Progreso de Publicación\n\n{entry}')

    with open(todo_file, 'w', encoding='utf-8') as f:
        f.write(content)

# Función para publicar post
def publish_post(post_data):
    headers = {
        'Content-Type': 'application/json'
    }

    # Verificar autenticación
    auth_check = requests.get(f'{wp_site_url}/wp-json/wp/v2/users/me', auth=(wp_username, wp_app_password))
    if auth_check.status_code != 200:
        print(f'Error de autenticación: {auth_check.status_code} - {auth_check.text}')
        return False

    print("Autenticación exitosa.")

    # Crear post
    response = requests.post(endpoint, auth=(wp_username, wp_app_password), headers=headers, data=json.dumps(post_data))

    if response.status_code == 201:
        print(f'Post "{post_data["title"]}" creado exitosamente como {post_data["status"]}.')
        return True
    else:
        print(f'Error: {response.status_code} - {response.text}')
        return False

# Función para actualizar post existente
def update_post(post_id, post_data):
    headers = {
        'Content-Type': 'application/json',
        'X-HTTP-Method-Override': 'PUT'
    }

    url = f'{endpoint}/{post_id}'
    response = requests.post(url, auth=(wp_username, wp_app_password), headers=headers, data=json.dumps(post_data))

    if response.status_code == 200:
        print(f'Post actualizado exitosamente.')
        return True
    else:
        print(f'Error al actualizar: {response.status_code} - {response.text}')
        return False

# Función para sincronizar todos los posts existentes
def sync_all_posts(status_new='draft'):
    # Verificar autenticación
    auth_check = requests.get(f'{wp_site_url}/wp-json/wp/v2/users/me', auth=(wp_username, wp_app_password))
    if auth_check.status_code != 200:
        print(f'Error de autenticación: {auth_check.status_code} - {auth_check.text}')
        return

    print("Autenticación exitosa.")

    # Obtener todos los posts
    response = requests.get(endpoint, auth=(wp_username, wp_app_password), params={'per_page': 100})
    if response.status_code != 200:
        print(f'Error al obtener posts: {response.status_code} - {response.text}')
        return

    posts = response.json()
    print(f'Encontrados {len(posts)} posts en WordPress.')

    # Obtener todos los tags
    tags_response = requests.get(f'{wp_site_url}/wp-json/wp/v2/tags', auth=(wp_username, wp_app_password), params={'per_page': 100})
    if tags_response.status_code != 200:
        print(f'Error al obtener tags: {tags_response.status_code} - {tags_response.text}')
        return

    tags = tags_response.json()
    tag_dict = {tag['name']: tag['id'] for tag in tags}
    print(f'Encontrados {len(tags)} tags en WordPress.')

    # Crear diccionario de títulos a archivos MD
    md_files = list_md_files()
    md_dict = {}
    for f in md_files:
        title = get_md_title(f)
        md_dict[title] = f

    updated_posts = []
    for post in posts:
        title = post['title']['rendered']
        if title in md_dict:
            file_path = md_dict[title]
            print(f'Procesando post: {title} ({file_path})')
            post_data = create_post_from_md(file_path, post['status'])  # Mantener status actual
            html_content = post_data['content']
            current_content = post['content']['rendered']
            current_excerpt = post.get('excerpt', {}).get('rendered', '')
            current_title = title
            current_tag_ids = post.get('tags', [])

            tag_names = post_data.get('tag_names', [])
            tag_ids = [tag_dict[name] for name in tag_names if name in tag_dict]
            missing_tags = [name for name in tag_names if name not in tag_dict]
            if missing_tags:
                print(f'Tags no encontrados en WP (se omitirán): {missing_tags}')

            # Verificar si hay cambios
            changed = False
            update_data = {}

            if html_content.strip() != current_content.strip():
                update_data['content'] = html_content
                changed = True

            if post_data['title'] != current_title:
                update_data['title'] = post_data['title']
                changed = True

            if post_data.get('excerpt', '') != current_excerpt:
                update_data['excerpt'] = post_data.get('excerpt', '')
                changed = True

            if set(tag_ids) != set(current_tag_ids):
                update_data['tags'] = tag_ids
                changed = True

            if changed:
                if update_post(post['id'], update_data):
                    updated_posts.append(post_data)
                    print(f'Actualizado: {title}')
                else:
                    print(f'Error al actualizar: {title}')
            else:
                print(f'No cambios necesarios: {title}')
        else:
            print(f'No encontrado archivo MD para: {title}')

    # Crear nuevos posts para MD sin post correspondiente
    existing_titles = {post['title']['rendered'] for post in posts}
    for title, file_path in md_dict.items():
        if title not in existing_titles:
            print(f'Creando nuevo post: {title} ({file_path})')
            post_data = create_post_from_md(file_path, status_new)  # Usar status_new
            tag_names = post_data.get('tag_names', [])
            tag_ids = [tag_dict[name] for name in tag_names if name in tag_dict]
            post_data['tags'] = tag_ids
            if publish_post(post_data):
                updated_posts.append(post_data)
                print(f'Creado: {title}')
            else:
                print(f'Error al crear: {title}')

    if updated_posts:
        update_todo_md(updated_posts)
        print(f"\nProcesados {len(updated_posts)} posts (actualizados o creados). TODO.md actualizado.")
    else:
        print("\nNo se procesó ningún post.")

# Función para listar archivos MD
def list_md_files(base_path='docs'):
    md_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    return sorted(md_files)

# Función para obtener título de un archivo MD
def get_md_title(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        frontmatter, _ = extract_frontmatter(content)
        metadata = parse_frontmatter(frontmatter)
        return metadata.get('title', os.path.basename(file_path))
    except:
        return os.path.basename(file_path)

# Función interactiva para seleccionar archivos
def interactive_mode():
    md_files = list_md_files()
    if not md_files:
        print("No se encontraron archivos .md en docs/")
        return

    # Opción de búsqueda
    search_query = input("Buscar por palabra clave en título o nombre de archivo (opcional, presiona Enter para ver todos): ").strip().lower()
    if search_query:
        filtered_files = []
        for f in md_files:
            title = get_md_title(f).lower()
            filename = os.path.basename(f).lower()
            if search_query in title or search_query in filename:
                filtered_files.append(f)
        md_files = filtered_files
        if not md_files:
            print(f"No se encontraron archivos que contengan '{search_query}' en título o nombre.")
            return

    print("Archivos Markdown disponibles:")
    for i, file in enumerate(md_files, 1):
        title = get_md_title(file)
        print(f"{i}. {title} ({file})")

    selections = input("Selecciona números separados por coma (ej: 1,3,5) o 'all' para todos: ").strip()
    if selections.lower() == 'all':
        selected_files = md_files
    else:
        indices = [int(x.strip()) - 1 for x in selections.split(',') if x.strip().isdigit()]
        selected_files = [md_files[i] for i in indices if 0 <= i < len(md_files)]

    if not selected_files:
        print("No se seleccionaron archivos válidos.")
        return

    status = input("Estado del post (draft/publish) [draft]: ").strip().lower() or 'draft'
    if status not in ['draft', 'publish']:
        status = 'draft'

    published_posts = []
    for file_path in selected_files:
        print(f"\nProcesando {file_path}...")
        post_data = create_post_from_md(file_path, status)
        if publish_post(post_data):
            published_posts.append(post_data)

    if published_posts:
        update_todo_md(published_posts)
        print("\nTODO.md actualizado con posts publicados.")

# CLI
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sincronizar documentación Markdown a WordPress')
    parser.add_argument('--file', help='Archivo Markdown específico a sincronizar')
    parser.add_argument('--status', choices=['draft', 'publish'], default='draft', help='Estado del post')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo para seleccionar archivos')
    parser.add_argument('--all', action='store_true', help='Sincronizar todos los posts existentes con archivos Markdown')
    parser.add_argument('--publish', action='store_true', help='Publicar nuevos posts en lugar de dejarlos como draft (solo para --all)')

    args = parser.parse_args()

    if args.all:
        status_new = 'publish' if args.publish else 'draft'
        sync_all_posts(status_new)
    elif args.interactive:
        interactive_mode()
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Archivo no encontrado: {args.file}")
        else:
            post_data = create_post_from_md(args.file, args.status)
            if publish_post(post_data):
                update_todo_md([post_data])
                print("TODO.md actualizado.")
    else:
        print("Usa --file para especificar un archivo, --interactive para modo interactivo o --all para sincronizar todos.")