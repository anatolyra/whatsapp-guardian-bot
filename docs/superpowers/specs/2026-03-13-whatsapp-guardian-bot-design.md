# WhatsApp Guardian Bot Design Spec

**Goal:** Self-hosted WhatsApp parental control bot that scans incoming/outgoing messages via local or cloud LLM and alerts parents via Telegram.

**Architecture:** Two-container stack — WAHA (WhatsApp HTTP API) receives messages and sends webhooks to guardian-bot (Python Flask). Guardian analyzes messages with LLM, logs to SQLite, and sends Telegram alerts for unsafe content.

**Tech Stack:** Python 3.11, Flask, SQLite, requests, google-generativeai (optional)

---

## Components

| Component | Responsibility |
|-----------|----------------|
| `config.py` | Env var loading, provider detection, defaults, validation |
| `llm_client.py` | Unified LLM interface (OpenAI-compatible API + Google Gemini SDK) |
| `audit_log.py` | SQLite audit log with size/retention caps |
| `guardian.py` | Flask webhook server, message routing, Telegram alerts |
| `Dockerfile` | Container build |
| `.github/workflows/docker-publish.yml` | CI/CD pipeline to GHCR |
| `docker-compose.yml` | Example deployment (in `examples/`) |
| `README.md` | Documentation |

---

## Architecture Diagram

```
┌─────────────────┐     webhook      ┌─────────────────┐
│  WhatsApp       │ ──────────────► │  Guardian Bot   │
│  (child device) │                  │  (Python/Flask) │
│                 │                  │                 │
│  WAHA Container │                  │  - LLM Analysis│
│  (whatsapp-web) │                  │  - Audit Log   │
└─────────────────┘                  │  - Telegram API│
                                     └────────┬────────┘
                                              │
                    ┌─────────────────────────┤
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │  LLM Endpoint │         │   Telegram    │
            │  (Ollama/etc) │         │   (Parent)    │
            └───────────────┘         └───────────────┘
```

---

## LLM Providers

| Provider | Auth Method | Config Env Vars |
|----------|-------------|-----------------|
| **Ollama (local/remote)** | Optional API key | `LLM_PROVIDER=ollama`, `LLM_BASE_URL`, `LLM_API_KEY` (optional), `LLM_MODEL_NAME` |
| **OpenAI** | API key | `LLM_PROVIDER=openai`, `LLM_API_KEY`, `LLM_MODEL_NAME` |
| **Groq** | API key | `LLM_PROVIDER=groq`, `LLM_API_KEY`, `LLM_MODEL_NAME` |
| **Google Gemini** | API key | `LLM_PROVIDER=google`, `GOOGLE_API_KEY`, `LLM_MODEL_NAME` |

### Provider Defaults

| Provider | Default Base URL | Default Model |
|----------|------------------|---------------|
| `ollama` | `http://localhost:11434/v1` | `llama3.2` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `groq` | `https://api.groq.com/openai/v1` | `llama-3.1-70b-versatile` |
| `google` | N/A (uses SDK) | `gemini-3-flash-preview` |

---

## Configuration

### Environment Variables

```python
# Required: Choose provider
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")  # "ollama" | "openai" | "groq" | "google"

# OpenAI-compatible providers (Ollama, OpenAI, Groq)
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")      # Provider-specific default
LLM_API_KEY = os.environ.get("LLM_API_KEY")        # Required for OpenAI/Groq, optional for Ollama
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME")  # Provider-specific default

# Google Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")  # Required when LLM_PROVIDER=google

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Audit Log
AUDIT_DB_PATH = os.environ.get("AUDIT_DB_PATH", "/app/data/audit.db")
AUDIT_MAX_SIZE_MB = os.environ.get("AUDIT_MAX_SIZE_MB", 500)
AUDIT_RETENTION_DAYS = os.environ.get("AUDIT_RETENTION_DAYS", 30)
```

---

## Audit Log Schema

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    direction TEXT NOT NULL,           -- 'incoming' | 'outgoing'
    sender TEXT NOT NULL,
    message_text TEXT NOT NULL,
    llm_verdict TEXT NOT NULL,         -- 'safe' | 'unsafe' | 'llm_failure'
    llm_reason TEXT,
    telegram_sent BOOLEAN DEFAULT FALSE,
    failure_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_verdict ON audit_log(llm_verdict);
```

### Retention & Cleanup

- Max size: 500MB (configurable via `AUDIT_MAX_SIZE_MB`)
- Retention: 30 days (configurable via `AUDIT_RETENTION_DAYS`)
- Cleanup runs on startup and after every 100 messages processed
- Cleanup purges oldest records until under size limit and past retention period

---

## Data Flow

1. WAHA receives WhatsApp message → sends POST to `http://guardian-bot:5000/webhook`
2. Guardian extracts sender, direction (incoming/outgoing), message text
3. Guardian logs message to SQLite audit log
4. Guardian calls LLM for safety analysis
5. If LLM returns `unsafe: true`, send detailed Telegram alert
6. If LLM fails/timeout, log failure, send Telegram failure alert (1st + every 3rd failure)
7. Periodic cleanup of audit log based on retention/size caps

---

## LLM Analysis

### System Prompt

```
You are a strict child safety moderator. Analyze the following message for:
1. Bullying or severe insults
2. Explicit/sexual content
3. Self-harm mentions
4. Dangerous illegal acts

Respond ONLY with valid JSON: {"unsafe": true/false, "reason": "short explanation"}.
If safe, return {"unsafe": false, "reason": "none"}.
```

### Response Format

```json
{
  "unsafe": true,
  "reason": "Contains explicit sexual content"
}
```

### Timeout

- 30-second timeout for LLM requests
- On timeout, treat as `llm_failure`

---

## Telegram Alerts

### Unsafe Content Alert Format

```
🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* +1234567890
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Hello there!
*Reason:* Contains explicit sexual content
```

### LLM Failure Alert Format

```
⚠️ *Guardian - LLM Unavailable*

*Time:* 2025-03-13 14:30:00 UTC
*Failed analyses:* 4
*Status:* LLM service not responding. Messages are being logged but not analyzed.

_Analysis will retry automatically._
```

### Failure Notification Strategy

- First LLM failure: Send Telegram alert
- Subsequent failures: No alert
- Every 3rd failure after the first: Send Telegram alert (3rd, 6th, 9th, etc.)
- Alert includes current failure count
- **No raw message text included in failure alerts**

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM timeout/failure | Log to SQLite, send Telegram failure alert (1st + every 3rd) |
| LLM returns invalid JSON | Log error, treat as safe (no alert) |
| Telegram API fails | Retry 3x with exponential backoff (1s, 2s, 4s), then log and give up |
| SQLite full (500MB) | Purge oldest records until under limit |
| Rate limit (many messages) | Process sequentially (no queue for MVP) |

---

## Webhook Contract

### Request from WAHA

```json
{
  "event": "message.any",
  "payload": {
    "from": "+1234567890",
    "body": "Hello, how are you?",
    "fromMe": false,
    "timestamp": 1710337200
  }
}
```

### Fields

- `from`: Sender phone number
- `body`: Message text content
- `fromMe`: `true` for outgoing, `false` for incoming
- `timestamp`: Unix timestamp

### Response

```json
{
  "status": "processed"
}
```

---

## File Structure

```
whatsapp-guardian-bot/
├── .github/
│   └── workflows/
│       └── docker-publish.yml    # CI/CD to GHCR
├── config.py                     # Env var loading & validation
├── llm_client.py                 # Unified LLM interface
├── audit_log.py                  # SQLite audit log
├── guardian.py                   # Main Flask app
├── requirements.txt              # Python deps
├── Dockerfile                    # Container build
├── examples/
│   └── docker-compose.yml        # Example deployment
└── README.md                     # Documentation
```

---

## Security Considerations

1. **No webhook authentication** — Assumes trusted network (homelab)
2. **Env vars for secrets** — Telegram token, API keys via environment
3. **No message storage for failures** — Only logged in SQLite, not sent in Telegram
4. **SQLite local only** — Database not exposed to network

---

## Dependencies

### requirements.txt

```
flask>=3.0.0
requests>=2.31.0
google-generativeai>=0.8.0
```

Note: `google-generativeai` is installed but only used when `LLM_PROVIDER=google`.

---

## Testing Strategy

### Unit Tests

- `test_config.py`: Provider detection, defaults, validation
- `test_llm_client.py`: Mock LLM responses, timeout handling, invalid JSON
- `test_audit_log.py`: Insert, cleanup, retention, size limits
- `test_guardian.py`: Webhook handling, message routing, Telegram alerts

### Integration Tests

- Full webhook flow with mocked LLM and Telegram
- LLM failure scenario
- Telegram failure scenario

---

## Future Considerations (Out of Scope)

- Webhook authentication (shared secret or HMAC)
- Message queuing for high-volume scenarios
- Admin dashboard for audit log viewing
- Multi-child/multi-parent support
- Action buttons on Telegram alerts