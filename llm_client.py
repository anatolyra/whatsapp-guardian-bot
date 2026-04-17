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

    def __init__(self, base_url: str, api_key: Optional[str], model: str, provider: str = "openai-compatible", llm_instruction: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.system_prompt = f"{self.SYSTEM_PROMPT}\n\n{llm_instruction}" if llm_instruction else self.SYSTEM_PROMPT
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    def analyze(self, text: str) -> Tuple[bool, str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
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

    def __init__(self, api_key: str, model: str, llm_instruction: Optional[str] = None):
        from google import genai
        self.api_key = api_key
        self.model = model
        self.provider = "google"
        self.system_prompt = f"{self.SYSTEM_PROMPT}\n\n{llm_instruction}" if llm_instruction else self.SYSTEM_PROMPT
        self._client = genai.Client(api_key=api_key)

    def analyze(self, text: str) -> Tuple[bool, str]:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        result = json.loads(response.text)
        return result.get("unsafe", False), result.get("reason", "Unknown")

def create_llm_client(config: Config, llm_instruction: Optional[str] = None) -> LLMClient:
    if config.provider == "google":
        if not config.api_key:
            raise ValueError("LLM_API_KEY is required for Google provider")
        return GoogleClient(config.api_key, config.model, llm_instruction=llm_instruction)
    else:
        return OpenAICompatibleClient(config.base_url, config.api_key, config.model, config.provider, llm_instruction=llm_instruction)
