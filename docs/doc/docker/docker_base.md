---
title: Docker - Contenedores
description: Guía básica de Docker para principiantes, incluyendo conceptos fundamentales y comandos básicos.
keywords: docker, contenedores, imágenes, dockerfile, comandos
tags: [docker, contenedores, base, virtualización]
---

---
title: Docker - Contenedores
description: Guía básica de Docker para principiantes, incluyendo conceptos fundamentales y comandos básicos.
keywords: docker, contenedores, imágenes, dockerfile, comandos
tags: [docker, contenedores, base, virtualización]
---

## Introducción a Docker

Docker es una plataforma de contenedores que permite empaquetar aplicaciones y sus dependencias en contenedores ligeros y portables. Esto facilita el desarrollo, despliegue y escalado de aplicaciones.

## 🚀 Iniciar con Docker en 10 minutos

¿Nuevo en Docker? Comienza aquí:

- **[Tutorial oficial: Get started](https://docs.docker.com/get-started/)** - Tu primer contenedor en minutos
- **[Play with Docker](https://labs.play-with-docker.com/)** - Entorno interactivo online gratuito
- **[Docker Cheat Sheet](https://dockerlabs.collabnix.com/docker/cheatsheet/)** - Comandos esenciales

## Conceptos fundamentales

### Contenedores
Los contenedores son entornos aislados que contienen todo lo necesario para ejecutar una aplicación.

### Imágenes
Las imágenes son plantillas de solo lectura que se utilizan para crear contenedores.

### Dockerfile
Un Dockerfile es un script que contiene instrucciones para construir una imagen.

```dockerfile
# Dockerfile de ejemplo
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Comandos básicos

### Gestión de imágenes
```bash
# Construir una imagen
docker build -t mi-aplicacion .

# Listar imágenes
docker images

# Eliminar una imagen
docker rmi mi-aplicacion
```

### Gestión de contenedores
```bash
# Ejecutar un contenedor
docker run -d -p 8080:80 mi-aplicacion

# Listar contenedores
docker ps

# Detener un contenedor
docker stop <container_id>

# Eliminar un contenedor
docker rm <container_id>
```

## Docker Compose

Docker Compose permite definir y ejecutar aplicaciones multi-contenedor.

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8080:80"
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
```

## Casos de uso

- Desarrollo local
- Despliegue de aplicaciones
- Microservicios
- CI/CD pipelines

## Próximos pasos

En las siguientes secciones exploraremos:
- Optimización de imágenes
- Redes de Docker
- Volúmenes y persistencia
- Seguridad en contenedores
- Orquestación con Kubernetes

## Recursos adicionales

### Videos tutoriales

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;">
  <iframe src="https://www.youtube.com/embed/fqMOX6JJhGo" frameborder="0" allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe>
</div>

*Video: Introducción completa a Docker en español (Docker Fundamentals)*

### Documentación oficial
- **Sitio web oficial:** [docker.com](https://www.docker.com/)
- **Documentación:** [docs.docker.com](https://docs.docker.com/)
- **GitHub:** [github.com/docker](https://github.com/docker)
- **Docker Hub:** [hub.docker.com](https://hub.docker.com/)

### Comunidad
- **Reddit:** [r/docker](https://www.reddit.com/r/docker/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/docker](https://stackoverflow.com/questions/tagged/docker)
- **Foros oficiales:** [forums.docker.com](https://forums.docker.com/)

---

!!! tip "¿Buscas comandos rápidos?"
    Consulta nuestras **[Recetas rápidas](../recipes.md#docker)** para comandos copy-paste comunes.

!!! warning "¿Problemas con Docker?"
    Revisa nuestra **[sección de troubleshooting](../troubleshooting.md)** para soluciones a errores comunes.
