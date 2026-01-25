---
title: "Local Chatbots with LLMs"
description: "Building conversational chatbots using Ollama and LLaMA.cpp, with integration to Slack, Discord and Telegram"
date: 2026-01-25
tags: [ai, llm, chatbots, ollama, slack, discord, telegram]
difficulty: intermediate
estimated_time: "30 min"
category: ai
status: published
prerequisites: ["ollama_basics", "model_optimization"]
---

# Local Chatbots with LLMs

> **Reading time:** 30 minutes | **Difficulty:** Intermediate | **Category:** Artificial Intelligence

## Summary

Local chatbots allow you to create private conversational assistants that run entirely on your infrastructure. This guide covers building chatbots using Ollama and LLaMA.cpp, with integration to platforms like Slack, Discord and Telegram.

## 🎯 Why Local Chatbots

### Advantages over Cloud Solutions

- ✅ **Complete privacy:** Data never leaves your network
- ✅ **No usage costs:** Only initial hardware costs
- ✅ **Full customization:** Models fine-tuned for your domain
- ✅ **24/7 availability:** No API limits or downtime
- ✅ **Total control:** You decide what data to use for training

### Enterprise Use Cases

- **Internal technical support** for development teams
- **Documentation assistant** that knows your codebase
- **HR chatbot** for policy inquiries
- **Compliance assistant** for regulatory questions
- **Corporate tutor** for internal training

## 🏗️ Basic Architecture

### Main Components

```
User → Platform (Slack/Discord) → Webhook/API → LLM Server → Response
                                      ↓
                            Knowledge Base (Optional)
```

### Technology Stack

- **LLM Engine:** Ollama or LLaMA.cpp
- **API Layer:** FastAPI, Flask or Node.js
- **Message Queue:** Redis (optional for scalability)
- **Vector DB:** ChromaDB for RAG (optional)
- **Frontend:** Native integration with each platform

## 🚀 Basic Implementation with Ollama

### 1. Environment Setup

```bash
# Install dependencies
pip install fastapi uvicorn requests python-multipart

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download optimized model
ollama pull llama2:7b-chat-q4_0
```

### 2. Chatbot API

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
        # Build prompt with context
        prompt = f"""
        You are a helpful and friendly assistant. Respond clearly and concisely.

        Additional context: {request.context}

        User: {request.message}
        Assistant:"""

        # Call Ollama
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
            raise HTTPException(status_code=500, detail="LLM Error")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. Test Client

```python
import requests

def test_chatbot():
    response = requests.post("http://localhost:8000/chat", json={
        "message": "What is the capital of France?",
        "context": "Basic geography question"
    })

    if response.status_code == 200:
        print("🤖:", response.json()["response"])
    else:
        print("Error:", response.text)

if __name__ == "__main__":
    test_chatbot()
```

## 💬 Slack Integration

### Slack App Configuration

1. **Create App in Slack:**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Create new app → "From scratch"
   - Name it and select workspace

2. **Configure Permissions:**
   - OAuth & Permissions → Scopes:
     - `chat:write` (to send messages)
     - `im:history` (to read direct messages)
     - `mpim:history` (for groups)

3. **Configure Event Subscriptions:**
   - Enable Events → Subscribe to bot events:
     - `app_mention` (when bot is mentioned)
     - `message.im` (direct messages)

### Integration Code

```python
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
import os

# Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

client = WebClient(token=SLACK_BOT_TOKEN)

def process_message(event_data):
    """Process chatbot messages"""
    text = event_data["text"]
    channel = event_data["channel"]
    user = event_data["user"]

    # Remove bot mention
    if text.startswith("<@"):
        text = text.split("> ", 1)[1] if "> " in text else text.split(">")[1]

    # Call chatbot API
    try:
        response = requests.post("http://localhost:8000/chat", json={
            "message": text,
            "context": f"Slack user message: {user}"
        })

        if response.status_code == 200:
            bot_response = response.json()["response"]

            # Send response
            client.chat_postMessage(
                channel=channel,
                text=bot_response,
                thread_ts=event_data.get("thread_ts")  # Reply in thread if needed
            )
    except Exception as e:
        client.chat_postMessage(
            channel=channel,
            text=f"Sorry, I had an error: {str(e)}"
        )

# Event handler
def process_socket_mode_request(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        event = req.payload["event"]
        if event["type"] == "app_mention" or event["type"] == "message":
            if event.get("subtype") != "bot_message":  # Avoid loops
                process_message(event)
    req.acknowledge()

# Start client
socket_client = SocketModeClient(
    app_token=SLACK_APP_TOKEN,
    web_client=client
)

socket_client.socket_mode_request_listener = process_socket_mode_request
socket_client.connect()

print("🤖 Chatbot connected to Slack!")
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY slack_bot.py .

# Install Ollama CLI (optional, for management)
RUN curl -fsSL https://ollama.ai/install.sh | sh

CMD ["python", "slack_bot.py"]
```

## 🎮 Discord Integration

### Discord Bot Configuration

1. **Create application:**
   - Go to [discord.com/developers](https://discord.com/developers/applications)
   - New Application → Name it

2. **Create Bot:**
   - Bot section → Add Bot
   - Copy TOKEN (keep it secure)

3. **Configure Intents:**
   - Privileged Gateway Intents:
     - Message Content Intent (to read messages)

4. **Invite to server:**
   - OAuth2 → URL Generator
   - Scopes: `bot`
   - Permissions: `Send Messages`, `Read Messages`

### Integration Code

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
    print(f'🤖 {bot.user} connected to Discord!')

@bot.event
async def on_message(message):
    # Avoid responding to own messages
    if message.author == bot.user:
        return

    # Respond to mentions or messages in specific channels
    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            try:
                # Call chatbot API
                response = requests.post(CHATBOT_API_URL, json={
                    "message": message.content,
                    "context": f"Discord user: {message.author.name}"
                }, timeout=30)

                if response.status_code == 200:
                    bot_response = response.json()["response"]

                    # Discord has 2000 character limit
                    if len(bot_response) > 2000:
                        bot_response = bot_response[:1997] + "..."

                    await message.reply(bot_response)
                else:
                    await message.reply("Sorry, I'm having technical issues.")

            except requests.exceptions.Timeout:
                await message.reply("The response is taking too long. Can you rephrase your question?")
            except Exception as e:
                await message.reply(f"Unexpected error: {str(e)}")

# Help command
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Local Assistant",
        description="I'm a chatbot that runs completely locally. Ask me anything!",
        color=0x00ff00
    )
    embed.add_field(
        name="How to use",
        value="Just mention me (@Bot) or send me a direct message",
        inline=False
    )
    await ctx.send(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))
```

## 📱 Telegram Integration

### Telegram Bot Configuration

1. **Create bot with BotFather:**
   ```
   /newbot
   Name: My Local Chatbot
   Username: my_local_chatbot_bot
   ```

2. **Get token:** Save the provided token

3. **Configure webhook (optional):**
   - For production, configure webhook instead of polling

### Integration Code

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

CHATBOT_API_URL = "http://localhost:8000/chat"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "🤖 Hello! I'm a chatbot that runs completely locally.\n\n"
        "Ask me anything and I'll help you as best I can."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
🤖 *Available commands:*

/start - Start conversation
/help - Show this help

*How to use:*
Just send me normal messages and I'll respond automatically.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user messages"""
    user_message = update.message.text
    user_name = update.effective_user.first_name

    # Show "typing..."
    await update.message.chat.send_action("typing")

    try:
        # Call chatbot API
        response = requests.post(CHATBOT_API_URL, json={
            "message": user_message,
            "context": f"Telegram user: {user_name}"
        }, timeout=30)

        if response.status_code == 200:
            bot_response = response.json()["response"]

            # Telegram has 4096 character limit
            if len(bot_response) > 4096:
                bot_response = bot_response[:4093] + "..."

            await update.message.reply_text(bot_response)
        else:
            await update.message.reply_text("Sorry, I'm having technical issues.")

    except requests.exceptions.Timeout:
        await update.message.reply_text("The response is taking too long. Can you rephrase your question?")
    except Exception as e:
        await update.message.reply_text(f"Unexpected error: {str(e)}")

def main():
    """Main function"""
    # Create application
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start bot
    print("🤖 Telegram chatbot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

## 🧠 Advanced Improvements

### 1. Conversational Memory

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

# Usage in chatbot
memory = ConversationMemory()

@app.post("/chat")
async def chat_with_memory(request: ChatRequest):
    memory.add_message("user", request.message)

    context = memory.get_context()
    prompt = f"{context}\nAssistant:"

    # ... rest of code ...

    memory.add_message("assistant", bot_response)
    return {"response": bot_response}
```

### 2. Knowledge Base Integration (RAG)

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

# Integration in chatbot
kb = KnowledgeBase()

# Add company documents
kb.add_document("The vacation policy is 25 days per year", {"category": "hr"})
kb.add_document("The main server is srv-prod-01", {"category": "infra"})

@app.post("/chat")
async def chat_with_kb(request: ChatRequest):
    # Search for relevant information
    relevant_docs = kb.search(request.message)

    context = "\n".join(relevant_docs) if relevant_docs else ""
    enhanced_context = f"{request.context}\nRelevant information:\n{context}"

    # ... use enhanced_context in prompt ...
```

### 3. Content Moderation

```python
def moderate_content(text: str) -> bool:
    """Check if content is appropriate"""
    forbidden_words = ["inappropriate", "spam", "offensive"]

    for word in forbidden_words:
        if word.lower() in text.lower():
            return False
    return True

@app.post("/chat")
async def moderated_chat(request: ChatRequest):
    if not moderate_content(request.message):
        return {"response": "Sorry, I can't respond to that type of content."}

    # ... continue with normal processing ...
```

## 📊 Monitoring and Metrics

### Basic Metrics

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

### Simple Dashboard

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

        # Update average
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

## 🚀 Production Deployment

### Complete Docker Compose

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

### Production Configuration

```bash
# Environment variables
export CHATBOT_ENV=production
export OLLAMA_URL=http://localhost:11434
export REDIS_URL=redis://localhost:6379
export LOG_LEVEL=INFO

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

## ⚠️ Security Considerations

### Best Practices

- ✅ **Validate inputs:** Sanitize all input messages
- ✅ **Rate limiting:** Limit requests per user/minute
- ✅ **Secure logging:** Don't log sensitive information
- ✅ **Updates:** Keep models and dependencies updated
- ✅ **Backup:** Regularly backup important conversations

### Firewall Configuration

```bash
# Only allow access from trusted networks
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw deny 8000

# For public APIs, use reverse proxy with SSL
sudo certbot --nginx -d chatbot.mydomain.com
```

## 🔗 Additional Resources

- [Ollama API Documentation](https://github.com/jmorganca/ollama/blob/main/docs/api.md)
- [Slack Bolt for Python](https://slack.dev/bolt-python/concepts)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## 📚 Next Steps

After implementing basic chatbots, consider:

1. **[Prompt Engineering](../prompt_engineering/)** - Techniques for better responses
2. **[Basic Fine-tuning](../fine_tuning_basics/)** - Customize models for your domain
3. **[LLM Monitoring](../llms_monitoring/)** - Metrics and observability

---

*Have you built any local chatbots? Share your experiences and challenges in the comments.*