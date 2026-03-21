# WhatsApp Guardian Bot

An open-source, self-hosted, privacy-first parental control bot. It connects to a WhatsApp account, uses any LLM (local Ollama, cloud OpenAI, Groq, or Google Gemini) to scan messages for concerning content, and alerts parents via Telegram.

## Features

- **Fully Containerized:** Runs with Docker / Podman
- **LLM Agnostic:** Use local Ollama, OpenAI, Groq, or Google Gemini
- **Privacy First:** No raw messages stored - analyzed in-memory only
- **Telegram Alerts:** Instant notifications for unsafe content
- **Configurable Failure Notifications:** Control when to be alerted about LLM issues

## Architecture

```
┌─────────────────┐     webhook      ┌─────────────────┐
│  WhatsApp       │ ──────────────►  │  Guardian Bot   │
│  (child device) │                  │  (Python/Flask) │
│                 │                  │                 │
│  WAHA Container │                  │  - LLM Analysis │
│  (whatsapp-web) │                  │  - Telegram API │
└─────────────────┘                  └────────┬────────┘
                                              │
                    ┌─────────────────────────┤
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │  LLM Endpoint │         │   Telegram    │
            │  (Ollama/etc) │         │   (Parent)    │
            └───────────────┘         └───────────────┘
```

The stack consists of two containers:
1. **WAHA** — WhatsApp HTTP API (headless client)
2. **Guardian Bot** — Python middleware that processes messages

## Quick Start

### 1. Set Up Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`, give it a name, and save the **Bot Token**
3. Start a chat with your new bot and send "hello"
4. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Find `"chat":{"id": 123456789}` — this is your **Chat ID**

### 2. Configure LLM Provider

| Provider | Env Vars Needed |
|----------|-----------------|
| **Ollama (local)** | `LLM_PROVIDER=ollama`, `LLM_BASE_URL=http://localhost:11434/v1` |
| **Ollama (remote)** | `LLM_PROVIDER=ollama`, `LLM_BASE_URL=<remote-url>`, `LLM_API_KEY=<key>` |
| **OpenAI** | `LLM_PROVIDER=openai`, `LLM_API_KEY=<key>` |
| **Groq** | `LLM_PROVIDER=groq`, `LLM_API_KEY=<key>` |
| **Google Gemini** | `LLM_PROVIDER=google`, `GOOGLE_API_KEY=<key>` |

### 3. Deploy with Docker Compose

Create `docker-compose.yml`:

```yaml
services:
  waha:
    image: devlikeapro/waha:latest
    container_name: guardian-waha
    restart: unless-stopped
    ports:
      - 3003:3000
    environment:
      - WHATSAPP_HOOK_URL=http://guardian-bot:5000/webhook
      - WHATSAPP_HOOK_EVENTS=message.any
      # --- WAHA Security Definitions ---
      - WAHA_DASHBOARD_USERNAME=admin
      - WAHA_DASHBOARD_PASSWORD=${WAHA_DASHBOARD_PASSWORD}
      - WHATSAPP_SWAGGER_USERNAME=admin
      - WHATSAPP_SWAGGER_PASSWORD=${WAHA_DASHBOARD_PASSWORD}
      - WAHA_API_KEY=${WAHA_API_KEY}
    volumes:
      - waha-data:/app/.waha
    healthcheck:
      test:
        - CMD-SHELL
        - "curl -s -f -H 'X-Api-Key: ${WAHA_API_KEY}' http://[::1]:3000/api/server/status || curl -s -f -H 'X-Api-Key: ${WAHA_API_KEY}' http://127.0.0.1:3000/api/server/status || exit 1"
      interval: 30s
      timeout: 10s
      retries: 3
  guardian-bot:
    image: ghcr.io/anatolyra/whatsapp-guardian-bot:latest
    container_name: guardian-bot
    restart: unless-stopped
    ports:
      - 5005:5000
    env_file:
      - .env
    depends_on:
      - waha
volumes:
  waha-data:
networks: {}
```

Create `.env`:

```env
# WAHA Security
WAHA_DASHBOARD_PASSWORD=<SECURE_PASSWORD>
WAHA_API_KEY=<YOUR_API_KEY>

# LLM Configuration
LLM_PROVIDER=ollama
LLM_BASE_URL=https://<LLM_URL_BASE>/api
LLM_MODEL_NAME=qwen2.5:3b
LLM_API_KEY=<YOUR_API_KEY>

# Telegram Configuration
TELEGRAM_BOT_TOKEN=<BOT_TOKEN>
TELEGRAM_CHAT_ID=<CHAT_ID>

# Failure Notification Settings
FAILURE_NOTIFY_ENABLED=true
FAILURE_NOTIFY_FIRST=true
FAILURE_NOTIFY_INTERVAL=3
```

Then run:

```bash
docker compose up -d
```

### 4. Link WhatsApp Account

1. Open `http://<YOUR_SERVER_IP>:3000/dashboard`
2. Navigate to Sessions tab
3. On the child's device: WhatsApp → Settings → Linked Devices → Link a Device
4. Scan the QR code from WAHA dashboard

The bot is now monitoring. Any message containing concerning content (bullying, explicit material, self-harm mentions, dangerous activities) will trigger a Telegram alert.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Provider: `ollama`, `openai`, `groq`, `google` |
| `LLM_BASE_URL` | Provider-specific | API endpoint URL |
| `LLM_API_KEY` | None | API key (required for OpenAI/Groq) |
| `LLM_MODEL_NAME` | Provider-specific | Model name |
| `GOOGLE_API_KEY` | None | Google API key (required for Gemini) |
| `TELEGRAM_BOT_TOKEN` | None | Telegram bot token |
| `TELEGRAM_CHAT_ID` | None | Telegram chat ID for alerts |
| `FAILURE_NOTIFY_ENABLED` | `true` | Enable failure notifications |
| `FAILURE_NOTIFY_FIRST` | `true` | Send notification on first failure |
| `FAILURE_NOTIFY_INTERVAL` | `3` | Send every N failures after first (0 = only first) |

### Provider Defaults

| Provider | Default Base URL | Default Model |
|----------|------------------|---------------|
| `ollama` | `http://localhost:11434/v1` | `llama3.2` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `groq` | `https://api.groq.com/openai/v1` | `llama-3.1-70b-versatile` |
| `google` | N/A | `gemini-3-flash-preview` |

## Development

### Run Locally

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
python guardian.py
```

### Run with Docker

```bash
docker build -t guardian-bot .
docker run -p 5000:5000 --env-file .env guardian-bot
```

## Security

- **No message storage** — Messages analyzed in-memory, never persisted
- **Container logs only** — Failures logged without message content
- **Env vars for secrets** — Telegram token, API keys via environment
- **No webhook authentication** — Assumes trusted network

## License

MIT License — see [LICENSE](LICENSE)
