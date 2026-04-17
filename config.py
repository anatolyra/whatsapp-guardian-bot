import os
from dataclasses import dataclass
from typing import Optional

PROVIDER_DEFAULTS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-70b-versatile",
    },
    "google": {
        "base_url": None,
        "model": "gemini-3-flash-preview",
    },
}

@dataclass
class Config:
    provider: str
    base_url: Optional[str]
    api_key: Optional[str]
    model: str

    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]

    failure_notify_enabled: bool
    failure_notify_first: bool
    failure_notify_interval: int

    language: str

    @classmethod
    def from_env(cls) -> "Config":
        provider = os.environ.get("LLM_PROVIDER", "ollama").lower()

        if provider not in PROVIDER_DEFAULTS:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

        defaults = PROVIDER_DEFAULTS[provider]

        return cls(
            provider=provider,
            base_url=os.environ.get("LLM_BASE_URL", defaults["base_url"]),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME", defaults["model"]),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
            failure_notify_enabled=os.environ.get("FAILURE_NOTIFY_ENABLED", "true").lower() == "true",
            failure_notify_first=os.environ.get("FAILURE_NOTIFY_FIRST", "true").lower() == "true",
            failure_notify_interval=int(os.environ.get("FAILURE_NOTIFY_INTERVAL", "3")),
            language=os.environ.get("ALERT_LANGUAGE", "en"),
        )
