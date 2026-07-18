---
title: "Chatbots Locales con LLMs"
description: "Construcción de chatbots conversacionales usando Ollama y LLaMA.cpp, con integración a Slack, Discord y Telegram"
date: 2026-01-25
tags: [ai, llm, chatbots, ollama, slack, discord, telegram]
difficulty: intermediate
estimated_time: "30 min"
category: Inteligencia Artificial
status: published
prerequisites: ["ollama_basics", "model_optimization"]
---

# Chatbots Locales con LLMs

> **Tiempo de lectura:** 30 minutos | **Dificultad:** Intermedia | **Categoría:** Inteligencia Artificial

## Resumen

Los chatbots locales permiten crear asistentes conversacionales privados que ejecutan completamente en tu infraestructura. Esta guía cubre la construcción de chatbots usando Ollama y LLaMA.cpp, con integración a plataformas como Slack, Discord y Telegram.

## 🎯 Por Qué Chatbots Locales

### Ventajas sobre Soluciones Cloud

- ✅ **Privacidad total:** Datos nunca salen de tu red
- ✅ **Sin costos por uso:** Solo costos de hardware inicial
- ✅ **Personalización completa:** Modelos fine-tuneados para tu dominio
- ✅ **Disponibilidad 24/7:** Sin límites de API o downtime
- ✅ **Control total:** Tú decides qué datos usar para entrenamiento

### Casos de Uso Empresariales

- **Soporte técnico interno** para equipos de desarrollo
- **Asistente de documentación** que conoce tu codebase
- **Chatbot de RRHH** para consultas de políticas
- **Asistente de compliance** para preguntas regulatorias
- **Tutor corporativo** para capacitación interna

## 🏗️ Arquitectura Básica

### Componentes Principales

```
Usuario → Plataforma (Slack/Discord) → Webhook/API → LLM Server → Respuesta
                                      ↓
                            Base de Conocimiento (Opcional)
```

### Stack Tecnológico

- **LLM Engine:** Ollama o LLaMA.cpp
- **API Layer:** FastAPI, Flask o Node.js
- **Message Queue:** Redis (opcional para escalabilidad)
- **Vector DB:** ChromaDB para RAG (opcional)
- **Frontend:** Integración nativa con cada plataforma

## 🚀 Implementación Básica con Ollama

### 1. Configuración del Entorno

```bash
# Instalar dependencias
pip install fastapi uvicorn requests python-multipart

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo optimizado
ollama pull llama2:7b-chat-q4_0
```

### 2. API del Chatbot

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json

app = FastAPI(title="Local Chatbot API")

class ChatRequest(BaseModel):
    message: str
    context: str = ""
    temperature: float = 0.7

OLLAMA_URL = "http://localhost:11434/api/generate"

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Construir prompt con contexto
        prompt = f"""
        Eres un asistente útil y amigable. Responde de manera clara y concisa.

        Contexto adicional: {request.context}

        Usuario: {request.message}
        Asistente:"""

        # Llamar a Ollama
        response = requests.post(OLLAMA_URL, json={
            "model": "llama2:7b-chat-q4_0",
            "prompt": prompt,
            "temperature": request.temperature,
            "stream": False
        })

        if response.status_code == 200:
            result = response.json()
            return {"response": result["response"].strip()}
        else:
            raise HTTPException(status_code=500, detail="Error en LLM")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. Cliente de Prueba

```python
import requests

def test_chatbot():
    response = requests.post("http://localhost:8000/chat", json={
        "message": "¿Cuál es la capital de Francia?",
        "context": "Pregunta sobre geografía básica"
    })

    if response.status_code == 200:
        print("🤖:", response.json()["response"])
    else:
        print("Error:", response.text)

if __name__ == "__main__":
    test_chatbot()
```

## 💬 Integración con Slack

### Configuración de Slack App

1. **Crear App en Slack:**
   - Ir a [api.slack.com/apps](https://api.slack.com/apps)
   - Crear nueva app → "From scratch"
   - Dar nombre y seleccionar workspace

2. **Configurar Permissions:**
   - OAuth & Permissions → Scopes:
     - `chat:write` (para enviar mensajes)
     - `im:history` (para leer mensajes directos)
     - `mpim:history` (para grupos)

3. **Configurar Event Subscriptions:**
   - Enable Events → Subscribe to bot events:
     - `app_mention` (cuando mencionan al bot)
     - `message.im` (mensajes directos)

### Código de Integración

```python
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
import os

# Configuración
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

client = WebClient(token=SLACK_BOT_TOKEN)

def process_message(event_data):
    """Procesa mensajes del chatbot"""
    text = event_data["text"]
    channel = event_data["channel"]
    user = event_data["user"]

    # Remover mención del bot
    if text.startswith("<@"):
        text = text.split("> ", 1)[1] if "> " in text else text.split(">")[1]

    # Llamar a la API del chatbot
    try:
        response = requests.post("http://localhost:8000/chat", json={
            "message": text,
            "context": f"Mensaje de usuario Slack: {user}"
        })

        if response.status_code == 200:
            bot_response = response.json()["response"]

            # Enviar respuesta
            client.chat_postMessage(
                channel=channel,
                text=bot_response,
                thread_ts=event_data.get("thread_ts")  # Responder en thread si es necesario
            )
    except Exception as e:
        client.chat_postMessage(
            channel=channel,
            text=f"Lo siento, tuve un error: {str(e)}"
        )

# Handler para eventos
def process_socket_mode_request(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        event = req.payload["event"]
        if event["type"] == "app_mention" or event["type"] == "message":
            if event.get("subtype") != "bot_message":  # Evitar loops
                process_message(event)
    req.acknowledge()

# Iniciar cliente
socket_client = SocketModeClient(
    app_token=SLACK_APP_TOKEN,
    web_client=client
)

socket_client.socket_mode_request_listener = process_socket_mode_request
socket_client.connect()

print("🤖 Chatbot conectado a Slack!")
```

### Despliegue con Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY slack_bot.py .

# Instalar Ollama CLI (opcional, para gestión)
RUN curl -fsSL https://ollama.ai/install.sh | sh

CMD ["python", "slack_bot.py"]
```

## 🎮 Integración con Discord

### Configuración del Bot de Discord

1. **Crear aplicación:**
   - Ir a [discord.com/developers](https://discord.com/developers/applications)
   - New Application → Dar nombre

2. **Crear Bot:**
   - Bot section → Add Bot
   - Copiar TOKEN (guardarlo seguro)

3. **Configurar Intents:**
   - Privileged Gateway Intents:
     - Message Content Intent (para leer mensajes)

4. **Invitar al servidor:**
   - OAuth2 → URL Generator
   - Scopes: `bot`
   - Permissions: `Send Messages`, `Read Messages`

### Código de Integración

```python
import discord
from discord.ext import commands
import requests
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

CHATBOT_API_URL = "http://localhost:8000/chat"

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} conectado a Discord!')

@bot.event
async def on_message(message):
    # Evitar que responda a sus propios mensajes
    if message.author == bot.user:
        return

    # Responder menciones o mensajes en canales específicos
    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            try:
                # Llamar a la API del chatbot
                response = requests.post(CHATBOT_API_URL, json={
                    "message": message.content,
                    "context": f"Usuario Discord: {message.author.name}"
                }, timeout=30)

                if response.status_code == 200:
                    bot_response = response.json()["response"]

                    # Discord tiene límite de 2000 caracteres
                    if len(bot_response) > 2000:
                        bot_response = bot_response[:1997] + "..."

                    await message.reply(bot_response)
                else:
                    await message.reply("Lo siento, estoy teniendo problemas técnicos.")

            except requests.exceptions.Timeout:
                await message.reply("La respuesta está tardando demasiado. ¿Puedes reformular tu pregunta?")
            except Exception as e:
                await message.reply(f"Error inesperado: {str(e)}")

# Comando de ayuda
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Asistente Local",
        description="Soy un chatbot que funciona completamente local. ¡Pregúntame lo que sea!",
        color=0x00ff00
    )
    embed.add_field(
        name="Cómo usar",
        value="Solo mencióname (@Bot) o envíame un mensaje directo",
        inline=False
    )
    await ctx.send(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))
```

## 📱 Integración con Telegram

### Configuración del Bot de Telegram

1. **Crear bot con BotFather:**
   ```
   /newbot
   Nombre: Mi Chatbot Local
   Username: mi_chatbot_local_bot
   ```

2. **Obtener token:** Guardar el token proporcionado

3. **Configurar webhook (opcional):**
   - Para producción, configurar webhook en lugar de polling

### Código de Integración

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

CHATBOT_API_URL = "http://localhost:8000/chat"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida"""
    await update.message.reply_text(
        "🤖 ¡Hola! Soy un chatbot que funciona completamente local.\n\n"
        "Pregúntame lo que sea y te ayudaré lo mejor posible."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ayuda"""
    help_text = """
🤖 *Comandos disponibles:*

/start - Iniciar conversación
/help - Mostrar esta ayuda

*Cómo usar:*
Solo envíame mensajes normales y te responderé automáticamente.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesar mensajes del usuario"""
    user_message = update.message.text
    user_name = update.effective_user.first_name

    # Mostrar "escribiendo..."
    await update.message.chat.send_action("typing")

    try:
        # Llamar a la API del chatbot
        response = requests.post(CHATBOT_API_URL, json={
            "message": user_message,
            "context": f"Usuario Telegram: {user_name}"
        }, timeout=30)

        if response.status_code == 200:
            bot_response = response.json()["response"]

            # Telegram tiene límite de 4096 caracteres
            if len(bot_response) > 4096:
                bot_response = bot_response[:4093] + "..."

            await update.message.reply_text(bot_response)
        else:
            await update.message.reply_text("Lo siento, estoy teniendo problemas técnicos.")

    except requests.exceptions.Timeout:
        await update.message.reply_text("La respuesta está tardando demasiado. ¿Puedes reformular tu pregunta?")
    except Exception as e:
        await update.message.reply_text(f"Error inesperado: {str(e)}")

def main():
    """Función principal"""
    # Crear aplicación
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Iniciar bot
    print("🤖 Chatbot de Telegram iniciado!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

## 🧠 Mejoras Avanzadas

### 1. Memoria Conversacional

```python
class ConversationMemory:
    def __init__(self, max_messages=10):
        self.messages = []
        self.max_messages = max_messages

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_context(self) -> str:
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.messages])

# Uso en el chatbot
memory = ConversationMemory()

@app.post("/chat")
async def chat_with_memory(request: ChatRequest):
    memory.add_message("user", request.message)

    context = memory.get_context()
    prompt = f"{context}\nAssistant:"

    # ... resto del código ...

    memory.add_message("assistant", bot_response)
    return {"response": bot_response}
```

### 2. Integración con Base de Conocimiento (RAG)

```python
import chromadb
from sentence_transformers import SentenceTransformer

class KnowledgeBase:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("company_docs")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

    def add_document(self, text: str, metadata: dict = None):
        embedding = self.encoder.encode(text)
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata] if metadata else None,
            ids=[str(hash(text))]
        )

    def search(self, query: str, top_k=3):
        query_embedding = self.encoder.encode(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return results['documents'][0] if results['documents'] else []

# Integración en el chatbot
kb = KnowledgeBase()

# Agregar documentos de la empresa
kb.add_document("La política de vacaciones es de 25 días al año", {"category": "rrhh"})
kb.add_document("El servidor principal es srv-prod-01", {"category": "infra"})

@app.post("/chat")
async def chat_with_kb(request: ChatRequest):
    # Buscar información relevante
    relevant_docs = kb.search(request.message)

    context = "\n".join(relevant_docs) if relevant_docs else ""
    enhanced_context = f"{request.context}\nInformación relevante:\n{context}"

    # ... usar enhanced_context en el prompt ...
```

### 3. Moderación de Contenido

```python
def moderate_content(text: str) -> bool:
    """Verificar si el contenido es apropiado"""
    forbidden_words = ["inapropiate", "spam", "offensive"]

    for word in forbidden_words:
        if word.lower() in text.lower():
            return False
    return True

@app.post("/chat")
async def moderated_chat(request: ChatRequest):
    if not moderate_content(request.message):
        return {"response": "Lo siento, no puedo responder a ese tipo de contenido."}

    # ... continuar con procesamiento normal ...
```

## 📊 Monitoreo y Métricas

### Métricas Básicas

```python
from fastapi import Request, Response
from time import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()

    response = await call_next(request)

    process_time = time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}s"
    )

    return response
```

### Dashboard Simple

```python
from collections import defaultdict
import datetime

class ChatbotMetrics:
    def __init__(self):
        self.requests_today = 0
        self.errors_today = 0
        self.avg_response_time = 0
        self.daily_stats = defaultdict(int)

    def record_request(self, response_time: float, success: bool = True):
        self.requests_today += 1
        if not success:
            self.errors_today += 1

        # Actualizar promedio
        self.avg_response_time = (
            (self.avg_response_time * (self.requests_today - 1)) + response_time
        ) / self.requests_today

    def get_stats(self):
        return {
            "requests_today": self.requests_today,
            "errors_today": self.errors_today,
            "success_rate": (self.requests_today - self.errors_today) / max(self.requests_today, 1),
            "avg_response_time": self.avg_response_time
        }

metrics = ChatbotMetrics()

@app.get("/metrics")
async def get_metrics():
    return metrics.get_stats()
```

## 🚀 Despliegue en Producción

### Docker Compose Completo

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  chatbot-api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - ollama
    environment:
      - OLLAMA_URL=http://ollama:11434
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  ollama_data:
```

### Configuración de Producción

```bash
# Variables de entorno
export CHATBOT_ENV=production
export OLLAMA_URL=http://localhost:11434
export REDIS_URL=redis://localhost:6379
export LOG_LEVEL=INFO

# Ejecutar con Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

## ⚠️ Consideraciones de Seguridad

### Mejores Prácticas

- ✅ **Validar inputs:** Sanitizar todos los mensajes de entrada
- ✅ **Rate limiting:** Limitar requests por usuario/minuto
- ✅ **Logging seguro:** No loggear información sensible
- ✅ **Actualizaciones:** Mantener modelos y dependencias actualizadas
- ✅ **Backup:** Hacer backup regular de conversaciones importantes

### Configuración de Firewall

```bash
# Solo permitir acceso desde redes confiables
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw deny 8000

# Para APIs públicas, usar reverse proxy con SSL
sudo certbot --nginx -d chatbot.midominio.com
```

## 🔗 Recursos Adicionales

- [Ollama API Documentation](https://github.com/jmorganca/ollama/blob/main/docs/api.md)
- [Slack Bolt for Python](https://slack.dev/bolt-python/concepts)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## 📚 Próximos Pasos

Después de implementar chatbots básicos, considera:

1. **[Prompt Engineering](prompt_engineering.md)** - Técnicas para mejores respuestas
2. **[Fine-tuning Básico](fine_tuning_basico.md)** - Personalizar modelos para tu dominio
3. **[Monitoreo de LLMs](model_evaluation.md)** - Métricas y observabilidad

---

*¿Has construido algún chatbot local? Comparte tus experiencias y desafíos en los comentarios.*