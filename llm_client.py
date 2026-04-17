import json
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from config import Config
import requests

class LLMClient(ABC):
    @abstractmethod
    def analyze(self, text: str) -> Tuple[bool, str]:
        pass

class OpenAICompatibleClient(LLMClient):
    SYSTEM_PROMPT = """You are a strict child safety moderator. Analyze the following message for:
1. Bullying or severe insults
2. Explicit/sexual content
3. Self-harm mentions
4. Dangerous illegal acts

Respond ONLY with valid JSON: {"unsafe": true/false, "reason": "short explanation"}.
If safe, return {"unsafe": false, "reason": "none"}."""

    def __init__(self, base_url: str, api_key: Optional[str], model: str, provider: str = "openai-compatible"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    def analyze(self, text: str) -> Tuple[bool, str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        response = self._session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)

        return result.get("unsafe", False), result.get("reason", "Unknown")

class GoogleClient(LLMClient):
    SYSTEM_PROMPT = """You are a strict child safety moderator. Analyze the following message for:
1. Bullying or severe insults
2. Explicit/sexual content
3. Self-harm mentions
4. Dangerous illegal acts

Respond ONLY with valid JSON: {"unsafe": true/false, "reason": "short explanation"}.
If safe, return {"unsafe": false, "reason": "none"}."""

    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        self.api_key = api_key
        self.model = model
        self.provider = "google"
        genai.configure(api_key=api_key)

    def analyze(self, text: str) -> Tuple[bool, str]:
        import google.generativeai as genai

        model = genai.GenerativeModel(
            self.model,
            system_instruction=self.SYSTEM_PROMPT,
        )

        response = model.generate_content(
            text,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        result = json.loads(response.text)
        return result.get("unsafe", False), result.get("reason", "Unknown")

def create_llm_client(config: Config) -> LLMClient:
    if config.provider == "google":
        if not config.api_key:
            raise ValueError("GOOGLE_API_KEY is required for Google provider")
        return GoogleClient(config.api_key, config.model)
    else:
        return OpenAICompatibleClient(config.base_url, config.api_key, config.model, config.provider)
