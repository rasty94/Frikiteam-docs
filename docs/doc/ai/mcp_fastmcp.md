# MCP (Model Context Protocol) y FastMCP — guía rápida

Resumen
- Qué es MCP: un protocolo simple para que clientes y *model-serving* compartan contexto, conversaciones y metadatos de forma estándar (requests/responses, streaming, health, control de sesión).
- Qué es FastMCP: implementación didáctica y ligera (ejemplo aquí) para montar un servidor MCP mínimo y conectar clientes Python/Node.js.

Para quién es esta guía
- Ingenieros de infra/DevOps que quieren exponer un LLM mediante una API interoperable.
- Desarrolladores que necesitan un servidor local rápido para pruebas y prototipos.

---

## 1 — Concepto rápido (2 minutos) 💡
- MCP define endpoints y comportamientos comunes: health, open/close session, enviar contexto, pedir inferencia (sin imponer un modelo concreto).
- Implementaciones pueden soportar HTTP/JSON, SSE o WebSocket para streaming.

## 2 — Casos de uso
- Servicio de RAG: orquestar contexto del vector DB y pedir respuestas al modelo.
- Chat multi-turn con persistencia de contexto en el servidor.
- Puerta de enlace para aplicar políticas (caching, rate-limit, auditing) delante del modelo.

## 3 — Diseño mínimo (esquema)
- Endpoints (mínimo recomendable):
  - GET /mcp/health → {status: "ok"}
  - POST /mcp/session → crea sesión, devuelve session_id
  - POST /mcp/{session_id}/context → añade contexto (metadatos, documentos)
  - POST /mcp/{session_id}/prompt → {prompt, params} → devuelve {response, tokens, metadata}
  - (opcional) /mcp/{session_id}/stream → streaming via SSE/WS

Payloads: JSON simple; incluir `client_id`, `api_key` (si aplica) y `trace_id` para observabilidad.

## 4 — Quickstart: servidor minimal (FastMCP) — Python (copy/paste) ✅
Requisitos mínimos: Python 3.11+, virtualenv

Comandos rápidos:
1. python -m venv .venv && source .venv/bin/activate
2. pip install fastapi[all] uvicorn httpx
3. Crear `fastmcp.py` (siguiente snippet) y ejecutar `uvicorn fastmcp:app --reload --port 8080`

Snippet (archivo `fastmcp.py`):

```python
from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()
SESSIONS = {}

class Prompt(BaseModel):
    prompt: str
    params: dict | None = None

@app.get('/mcp/health')
async def health():
    return {"status": "ok"}

@app.post('/mcp/session')
async def create_session():
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {"history": []}
    return {"session_id": sid}

@app.post('/mcp/{sid}/context')
async def add_context(sid: str, payload: dict):
    if sid not in SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")
    SESSIONS[sid]["history"].append({"type": "context", **payload})
    return {"ok": True}

@app.post('/mcp/{sid}/prompt')
async def prompt(sid: str, body: Prompt):
    if sid not in SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")
    # Aquí integrarías el LLM real; por simplicidad devolvemos eco
    resp = {
        "response": f"ECO: {body.prompt}",
        "tokens": len(body.prompt.split()),
        "metadata": {"engine": "fastmcp-demo"}
    }
    SESSIONS[sid]["history"].append({"type": "user", "text": body.prompt})
    SESSIONS[sid]["history"].append({"type": "assistant", "text": resp["response"]})
    return resp

# Opcional: WebSocket para streaming
@app.websocket('/mcp/{sid}/stream')
async def stream_ws(websocket: WebSocket, sid: str):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_json()
            prompt = msg.get('prompt', '')
            # Simular streaming por trozos
            for chunk in (prompt[i:i+8] for i in range(0, len(prompt), 8)):
                await websocket.send_json({"delta": chunk})
    finally:
        await websocket.close()
```

Cómo probarlo (ejemplos):
- Crear sesión:
  curl -sX POST http://localhost:8080/mcp/session | jq
- Enviar prompt:
  curl -sX POST http://localhost:8080/mcp/<SESSION>/prompt -d '{"prompt":"hola mundo"}' -H 'Content-Type: application/json' | jq
- Probar streaming (WebSocket):
  websocat -t ws://localhost:8080/mcp/<SESSION>/stream -n '{"prompt":"hola streaming"}'

---

## 5 — Cliente Python (conectar a FastMCP)
Instalar: pip install httpx

```python
import httpx

base = "http://localhost:8080/mcp"
with httpx.Client() as c:
    sid = c.post(f"{base}/session").json()["session_id"]
    print('session', sid)
    r = c.post(f"{base}/{sid}/prompt", json={"prompt":"Explica MCP en 1 frase"})
    print(r.json())
```

## 6 — Cliente Node.js (ejemplo rápido)
Instalar: npm init -y && npm i node-fetch@2

```js
const fetch = require('node-fetch');
(async ()=>{
  const base = 'http://localhost:8080/mcp';
  const sid = (await (await fetch(base + '/session',{method:'POST'})).json()).session_id;
  const resp = await (await fetch(`${base}/${sid}/prompt`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({prompt:'Resume MCP'})})).json();
  console.log(resp);
})();
```

## 7 — Docker (opcional)
Dockerfile sugerido:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY fastmcp.py .
RUN pip install fastapi uvicorn
CMD ["uvicorn","fastmcp:app","--host","0.0.0.0","--port","8080"]
```

## 8 — Buenas prácticas (producción) ⚠️
- Siempre TLS (terminación en NGINX/ALB o sidecar).
- Autenticación: API keys o mTLS; validar `client_id` y scopes.
- Rate-limiting y caching de prompts frecuentes.
- Observabilidad: `trace_id`, métricas (latencia, tokens), logs structured.
- Protección de datos: no almacenar PII sin consentimiento y cifrar si se persiste.

## 9 — Extensiones útiles
- Añadir SSE/WS para streaming de respuestas token-a-token.
- Implementar control de costes (max_tokens, sampling) a nivel de gateway.
- Middleware para inyección automática de contexto desde vector DB.

## 10 — Cómo conectar desde un pipeline RAG (resumen)
1. Recupera docs relevantes desde vector DB.
2. Llama a `/mcp/{sid}/context` con esos documentos.
3. Llama a `/mcp/{sid}/prompt` pidiendo la síntesis.
4. Guarda la conversación y métricas para auditoría.

---

## Recursos y siguientes pasos
- Ejemplo en este repo: copia `fastmcp.py` y pruébalo localmente.
- Para producción: implementar autenticación, TLS y despliegue en k8s usando `Deployment` + `Ingress`.

> Nota: FastMCP en esta guía es una implementación didáctica. Para un gateway en producción, integra con tu proveedor de modelos (OpenAI/Anthropic/llama-servers) o con un runtime local (vLLM, Ollama, etc.).

---

### Archivos incluidos (ejemplo)
- `fastmcp.py` — servidor demo
- `Dockerfile` — contenedor mínimo
- `examples/` — clientes Python/Node.js

Si quieres, puedo: 1) añadir los archivos de ejemplo al repo y 2) mostrar cómo desplegarlo en Docker Compose o en Kubernetes (manifiestos). ¿Cuál prefieres primero?