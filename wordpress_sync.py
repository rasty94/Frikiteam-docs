import requests
import json
import os
import markdown
from datetime import datetime
import argparse
import glob

# Configuración desde variables de entorno
wp_site_url = os.getenv('WP_SITE_URL', 'https://frikiteam.es')
wp_username = os.getenv('WP_USERNAME', 'antonio')
wp_app_password = os.getenv('WP_APP_PASSWORD', 'jP4SKqPfR0btF9XUIUB7JMt7')

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
        # 'tags': generate_wp_tags(metadata)  # Removido: WordPress espera IDs de tags, no nombres
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

    args = parser.parse_args()

    if args.interactive:
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
        print("Usa --file para especificar un archivo o --interactive para modo interactivo.")