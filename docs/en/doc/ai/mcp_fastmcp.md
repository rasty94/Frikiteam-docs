---
title: "MCP (Model Context Protocol) and FastMCP"
description: "Quick MCP guide: a protocol for sharing context between model clients and servers, with FastMCP as a lightweight implementation"
keywords: "mcp, model context protocol, fastmcp, llm, api, devops"
tags: [ai, llm, mcp, fastmcp, api]
updated: 2026-07-18
difficulty: intermediate
estimated_time: 5 min
category: Artificial Intelligence
status: published
last_reviewed: 2026-07-18
prerequisites:
  - "Basic understanding of LLMs"
  - "Basic Python or Node.js"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# MCP (Model Context Protocol) and FastMCP — quick guide

Summary
- What MCP is: a simple protocol that lets clients and *model-serving* backends share context, conversations and metadata in a standard way (requests/responses, streaming, health, session control).
- What FastMCP is: a lightweight, teaching-oriented implementation (the example used here) for standing up a minimal MCP server and connecting Python/Node.js clients.

Who this guide is for
- Infra/DevOps engineers who want to expose an LLM through an interoperable API.
- Developers who need a quick local server for testing and prototyping.

---

## 1 — The idea in a nutshell (2 minutes) 💡
- MCP defines a common set of endpoints and behaviours: health, open/close session, send context, request inference (without mandating any particular model).
- Implementations may use HTTP/JSON, SSE or WebSocket for streaming.

## 2 — Use cases
- RAG service: orchestrate context from the vector DB and request answers from the model.
- Multi-turn chat with context persisted server-side.
- Gateway for enforcing policies (caching, rate limiting, auditing) in front of the model.

## 3 — Minimal design (outline)
- Endpoints (recommended minimum):
  - GET /mcp/health → {status: "ok"}
  - POST /mcp/session → creates a session, returns session_id
  - POST /mcp/{session_id}/context → adds context (metadata, documents)
  - POST /mcp/{session_id}/prompt → {prompt, params} → returns {response, tokens, metadata}
  - (optional) /mcp/{session_id}/stream → streaming via SSE/WS

Payloads: plain JSON; include `client_id`, `api_key` (where applicable) and `trace_id` for observability.

## 4 — Quickstart: minimal server (FastMCP) — Python (copy/paste) ✅
Minimum requirements: Python 3.11+, virtualenv

Quick commands:
1. python -m venv .venv && source .venv/bin/activate
2. pip install fastapi[all] uvicorn httpx
3. Create `fastmcp.py` (snippet below) and run `uvicorn fastmcp:app --reload --port 8080`

Snippet (file `fastmcp.py`):

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
    # This is where you would plug in the real LLM; for simplicity we just echo
    resp = {
        "response": f"ECHO: {body.prompt}",
        "tokens": len(body.prompt.split()),
        "metadata": {"engine": "fastmcp-demo"}
    }
    SESSIONS[sid]["history"].append({"type": "user", "text": body.prompt})
    SESSIONS[sid]["history"].append({"type": "assistant", "text": resp["response"]})
    return resp

# Optional: WebSocket for streaming
@app.websocket('/mcp/{sid}/stream')
async def stream_ws(websocket: WebSocket, sid: str):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_json()
            prompt = msg.get('prompt', '')
            # Simulate chunked streaming
            for chunk in (prompt[i:i+8] for i in range(0, len(prompt), 8)):
                await websocket.send_json({"delta": chunk})
    finally:
        await websocket.close()
```

How to try it out (examples):

```bash
# Create a session
curl -sX POST http://localhost:8080/mcp/session | jq

# Send a prompt (replace <SESSION> with the id returned above)
curl -sX POST http://localhost:8080/mcp/<SESSION>/prompt \
  -d '{"prompt":"hello world"}' -H 'Content-Type: application/json' | jq

# Test streaming (WebSocket)
websocat -t ws://localhost:8080/mcp/<SESSION>/stream -n '{"prompt":"hello streaming"}'
```

---

## 5 — Python client (connecting to FastMCP)
Install: pip install httpx

```python
import httpx

base = "http://localhost:8080/mcp"
with httpx.Client() as c:
    sid = c.post(f"{base}/session").json()["session_id"]
    print('session', sid)
    r = c.post(f"{base}/{sid}/prompt", json={"prompt":"Explain MCP in one sentence"})
    print(r.json())
```

## 6 — Node.js client (quick example)
Install: npm init -y && npm i node-fetch@2

```js
const fetch = require('node-fetch');
(async ()=>{
  const base = 'http://localhost:8080/mcp';
  const sid = (await (await fetch(base + '/session',{method:'POST'})).json()).session_id;
  const resp = await (await fetch(`${base}/${sid}/prompt`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({prompt:'Summarise MCP'})})).json();
  console.log(resp);
})();
```

## 7 — Docker (optional)
Suggested Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY fastmcp.py .
RUN pip install fastapi uvicorn
CMD ["uvicorn","fastmcp:app","--host","0.0.0.0","--port","8080"]
```

## 8 — Best practices (production) ⚠️
- Always use TLS (terminated at NGINX/ALB or in a sidecar).
- Authentication: API keys or mTLS; validate `client_id` and scopes.
- Rate limiting and caching for frequent prompts.
- Observability: `trace_id`, metrics (latency, tokens), structured logs.
- Data protection: never store PII without consent, and encrypt it if persisted.

## 9 — Useful extensions
- Add SSE/WS to stream responses token by token.
- Implement cost controls (max_tokens, sampling) at the gateway level.
- Middleware that automatically injects context from a vector DB.

## 10 — Wiring it into a RAG pipeline (summary)
1. Retrieve the relevant docs from the vector DB.
2. Call `/mcp/{sid}/context` with those documents.
3. Call `/mcp/{sid}/prompt` asking for the synthesis.
4. Store the conversation and metrics for auditing.

---

## Resources and next steps
- Example in this repo: copy `fastmcp.py` and run it locally.
- For production: add authentication, TLS and deploy on k8s using `Deployment` + `Ingress`.

> Note: FastMCP in this guide is a teaching implementation. For a production gateway, integrate it with your model provider (OpenAI/Anthropic/llama-servers) or with a local runtime (vLLM, Ollama, etc.).

---

### Included files (example)
- `fastmcp.py` — demo server
- `Dockerfile` — minimal container
- `examples/` — Python/Node.js clients

If you'd like, I can: 1) add the example files to the repo and 2) show how to deploy it with Docker Compose or on Kubernetes (manifests). Which one first?
