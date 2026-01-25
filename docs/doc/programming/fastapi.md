---
title: "FastAPI"
description: "Documentación sobre fastapi"
tags: ['documentation']
updated: 2026-01-25
difficulty: advanced
estimated_time: 1 min
category: Desarrollo
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# FastAPI

FastAPI es un framework web moderno y rápido (de alto rendimiento) para construir APIs con Python 3.8+ basado en las sugerencias de tipo estándar de Python.

## Ventajas Clave

- **Rápido**: Muy alto rendimiento, a la par con **NodeJS** y **Go** (gracias a Starlette y Pydantic). Uno de los frameworks de Python más rápidos disponibles.
- **Rápido de programar**: Aumenta la velocidad de desarrollo de funciones entre un 200% y un 300%.
- **Menos errores**: Reduce los errores inducidos por el desarrollador en aproximadamente un 40%.
- **Intuitivo**: Gran soporte de editores (autocompletado, etc.) y menos tiempo leyendo documentación.
- **Fácil**: Diseñado para ser fácil de usar y aprender. Menos tiempo leyendo documentación.
- **Corto**: Minimiza la duplicación de código. Múltiples funciones de cada declaración de parámetro.
- **Robusto**: Obtén código listo para producción. Con documentación interactiva automática.
- **Basado en estándares**: Basado en (y totalmente compatible con) los estándares abiertos para APIs: OpenAPI y JSON Schema.

## Ejemplo Básico

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

## Enlaces de Interés

- [Documentación oficial](https://fastapi.tiangolo.com/)
- [GitHub de FastAPI](https://github.com/tiangolo/fastapi)
