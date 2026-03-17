# 💀 ThanatosAgent: The Guardian of Search

Thanatos is a stoic, AI-powered price monitoring assistant inspired by *Persona 3*. It serves a single purpose: to provide definitive price data, eliminate user indecision, and monitor market shifts with inevitable precision.

## 🚀 Key Features
- **Bilingual Intelligence**: Full support for English and Portuguese, targeting both US and Brazilian markets.
- **Hybrid Search Engine**: Combines semantic embeddings (vector search) with full-text indexing for superior product retrieval.
- **Price Watchdog**: Proactive price monitoring with automated Telegram notifications when targets are hit.
- **Stoic Persona**: Stoic, mysterious, and data-driven interactions that adapt to user repetition.

---

## 🛠️ Local Execution Guide

Follow these steps to deploy Thanatos in your local environment.

### 1. Prerequisites
- **Python**: Managed via [uv](https://github.com/astral-sh/uv).
- **Docker**: Required for the database and vector extensions.
- **Ngrok**: For exposing your local server to Telegram Webhooks.
- **Database**: PostgreSQL with `pgvector` and `pg_trgm` extensions.

### 2. Installation
First, install `uv` if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone the repository and sync dependencies:
```bash
uv sync
```

### 3. Environment Configuration
Copy the template and fill in your credentials:
```bash
cp .env-example .env
```
Ensure you provide:
- `TOKEN_TELEGRAM`: Your BotFather token.
- `GROK_API_KEY` or `GEMINI_API_KEY`: For the LLM reasoning.
- `SERPER_API_KEY`: For web search capabilities.
- `NGROK_URL`: Your public HTTPS tunnel URL.

### 4. Infrastructure (Docker)
Start the database and required services:
```bash
docker-compose up -d
```
*Note: The database initialization scripts will automatically set up `pgvector` and the required schemas.*

### 5. Webhook Setup (Ngrok)
Expose your local FastAPI server (port 8080):
```bash
ngrok http 8080
```
Then, update the `NGROK_URL` in your `.env` file with the generated HTTPS address (e.g., `https://random-id.ngrok-free.app`).

### 6. Launching the Agent
Run the application using `uv`:
```bash
uv run main.py
```

---

## 📖 Usage Examples

Interact with Thanatos via Telegram:
- **Search**: "Find me an iPhone 15 Pro" or "Preço do MacBook M3".
- **Analysis**: "Is this price good?" (after a search result).
- **Watchdog**: "Monitor this URL and alert me if it hits $900".
- **Cleanup**: Send `/clean` to wipe the agent's current memory.

---
*Mude seu destino. Change your destiny.*
