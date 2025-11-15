# Docker - Containers 

## Introduction to Docker

Docker is a container platform that allows packaging applications and their dependencies in lightweight and portable containers. This facilitates development, deployment and scaling of applications.

## 🚀 Start with Docker in 10 minutes

New to Docker? Start here:

- **[Official tutorial: Get started](https://docs.docker.com/get-started/)** - Your first container in minutes
- **[Play with Docker](https://labs.play-with-docker.com/)** - Free online interactive environment
- **[Docker Cheat Sheet](https://dockerlabs.collabnix.com/docker/cheatsheet/)** - Essential commands

## Fundamental concepts

### Containers
Containers are isolated environments that contain everything needed to run an application.

### Images
Images are read-only templates used to create containers.

### Dockerfile
A Dockerfile is a script containing instructions to build an image.

```dockerfile
# Example Dockerfile
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Basic commands

### Image management
```bash
# Build an image
docker build -t my-application .

# List images
docker images

# Remove an image
docker rmi my-application
```

### Container management
```bash
# Run a container
docker run -d -p 8080:80 my-application

# List containers
docker ps

# Stop a container
docker stop <container_id>

# Remove a container
docker rm <container_id>
```

## Docker Compose

Docker Compose allows defining and running multi-container applications.

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

## Use cases

- Local development
- Application deployment
- Microservices
- CI/CD pipelines

## Next steps

In the following sections we will explore:
- Image optimization
- Docker networks
- Volumes and persistence
- Container security
- Orchestration with Kubernetes

## Additional resources

### Official documentation
- **Official website:** [docker.com](https://www.docker.com/)
- **Documentation:** [docs.docker.com](https://docs.docker.com/)
- **GitHub:** [github.com/docker](https://github.com/docker)
- **Docker Hub:** [hub.docker.com](https://hub.docker.com/)

### Community
- **Reddit:** [r/docker](https://www.reddit.com/r/docker/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/docker](https://stackoverflow.com/questions/tagged/docker)
- **Official forums:** [forums.docker.com](https://forums.docker.com/)
