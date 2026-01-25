---
title: "Ceph"
description: "Documentación sobre ceph"
tags: ['storage']
updated: 2026-01-25
difficulty: beginner
estimated_time: 3 min
category: Almacenamiento
status: published
last_reviewed: 2026-01-25
prerequisites: ["Ninguno"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

````markdown
---
title: "Ceph Storage Guide: Distributed Storage System Overview"
description: "Complete guide to Ceph, the distributed storage system. Learn about architecture, installation with cephadm, use cases, and resources for scalable and reliable data storage."
keywords: Ceph, distributed storage, OSD, MON, MGR, MDS, object storage, block storage, file system, cloud storage, big data, backup, recovery, cephadm, Reef
---

# Ceph

Ceph es un sistema de almacenamiento distribuido que proporciona un almacenamiento altamente escalable y fiable para grandes cantidades de datos. Está diseñado para ser auto-gestionado, auto-reparado y auto-optimizado, lo que lo hace ideal para entornos de almacenamiento en la nube y centros de datos.

![Ceph Logo](ceph_logo.png){width=50%}
## Características Principales

- **Escalabilidad**: Ceph puede escalar desde unos pocos nodos hasta miles de nodos, permitiendo un crecimiento sin interrupciones.
- **Fiabilidad**: Utiliza replicación y codificación de borrado para asegurar la integridad de los datos.
- **Auto-gestión**: Ceph se auto-repara y se auto-optimiza, reduciendo la necesidad de intervención manual.
- **Flexibilidad**: Soporta múltiples interfaces de almacenamiento, incluyendo bloques, objetos y sistemas de archivos.

## Arquitectura de Ceph

Ceph se compone de varios componentes clave:

- **Ceph Monitors (MON)**: Mantienen un mapa del clúster y aseguran la coherencia de los datos.
- **Ceph OSD Daemons (OSD)**: Almacenan los datos y manejan las operaciones de replicación y recuperación.
- **Ceph Manager Daemons (MGR)**: Proporcionan funcionalidades adicionales como la monitorización y la gestión del clúster.
- **Ceph Metadata Servers (MDS)**: Gestionan los metadatos del sistema de archivos CephFS.

![Arquitectura de Ceph](Estructura_Ceph.png){width=80%}

## Casos de Uso

- **Almacenamiento en la Nube**: Ceph es ideal para proveedores de servicios en la nube que necesitan un almacenamiento escalable y fiable.
- **Big Data**: Ceph puede manejar grandes volúmenes de datos, lo que lo hace adecuado para aplicaciones de Big Data.
- **Backup y Recuperación**: La replicación y la codificación de borrado de Ceph aseguran que los datos estén siempre disponibles y protegidos.

## Instalación Básica con cephadm (Versión Reef)

Para instalar Ceph versión Reef utilizando `cephadm`, se pueden seguir los siguientes pasos básicos:

1. **Preparar los nodos**: Asegurarse de que todos los nodos tengan las dependencias necesarias instaladas y que tengan acceso a internet.
2. **Instalar cephadm**: Descargar e instalar `cephadm` en el nodo inicial.
    ```bash
    curl --silent --remote-name https://raw.githubusercontent.com/ceph/ceph/reef/src/cephadm/cephadm
    chmod +x cephadm
    sudo ./cephadm install
    ```
3. **Desplegar el clúster**: Utilizar `cephadm` para desplegar el clúster.
    ```bash
    sudo cephadm bootstrap --mon-ip <IP_DEL_NODO_INICIAL>
    ```
4. **Agregar nodos adicionales**: Añadir más nodos al clúster.
    ```bash
    sudo ceph orch host add <NOMBRE_DEL_NODO> <IP_DEL_NODO>
    ```
5. **Configurar el clúster**: Configurar los monitores, OSDs y otros componentes necesarios utilizando `cephadm`.
    ```bash
    sudo ceph orch apply osd --all-available-devices
    ```
6. **Verificar la instalación**: Asegurarse de que el clúster esté funcionando correctamente.
    ```bash
    ceph -s
    ```


## Recursos adicionales

### Videos tutoriales

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;">
  <iframe src="https://www.youtube.com/embed/7HKy5qV9L8E" frameborder="0" allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe>
</div>

*Video: Introducción a Ceph - Sistema de almacenamiento distribuido*

### Documentación oficial
- **Sitio web oficial:** [ceph.io](https://ceph.io/)
- **Documentación:** [docs.ceph.com](https://docs.ceph.com/)
- **GitHub:** [github.com/ceph/ceph](https://github.com/ceph/ceph)
- **Wiki:** [wiki.ceph.com](https://wiki.ceph.com/)

### Comunidad
- **Reddit:** [r/ceph](https://www.reddit.com/r/ceph/)
- **Stack Overflow:** [stackoverflow.com/questions/tagged/ceph](https://stackoverflow.com/questions/tagged/ceph)
- **IRC:** #ceph en freenode

---

!!! tip "¿Buscas comandos rápidos?"
    Consulta nuestras **[Recetas rápidas](../recipes.md#ceph)** para comandos copy-paste comunes.

!!! warning "¿Problemas con Ceph?"
    Revisa nuestra **[sección de troubleshooting](../../troubleshooting.md)** para soluciones a errores comunes.

````
