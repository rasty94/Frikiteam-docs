# FastAPI

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on Python's standard type hints.

## Key Advantages

- **Fast**: Very high performance, on par with **NodeJS** and **Go** (thanks to Starlette and Pydantic). One of the fastest Python frameworks available.
- **Fast to code**: Increase the speed of developing features by 200% to 300%.
- **Fewer bugs**: Reduce human-induced errors by about 40%.
- **Intuitive**: Great editor support (autocomplete, etc.) and less time reading documentation.
- **Easy**: Designed to be easy to use and learn. Less time reading documentation.
- **Short**: Minimize code duplication. Multiple features from each parameter declaration.
- **Robust**: Get production-ready code. With automatic interactive documentation.
- **Standards-based**: Based on (and fully compatible with) the open standards for APIs: OpenAPI and JSON Schema.

## Basic Example

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

## Links of Interest

- [Official Documentation](https://fastapi.tiangolo.com/)
- [FastAPI GitHub](https://github.com/tiangolo/fastapi)
