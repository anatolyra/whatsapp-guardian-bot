import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from llm_client import create_llm_client, LLMClient, OpenAICompatibleClient, GoogleClient

def test_create_ollama_client():
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
        from config import Config
        config = Config.from_env()
        client = create_llm_client(config)
        assert client.provider == "ollama"
        assert client.base_url == "http://localhost:11434/v1"

def test_create_google_client():
    client = GoogleClient(api_key="test-key", model="gemini-3-flash-preview")
    assert client.provider == "google"

def test_create_google_client_missing_api_key():
    with patch.dict(os.environ, {"LLM_PROVIDER": "google"}, clear=True):
        from config import Config
        config = Config.from_env()
        with pytest.raises(ValueError, match="LLM_API_KEY is required"):
            create_llm_client(config)

def test_google_analyze_safe():
    with patch.dict(os.environ, {"LLM_PROVIDER": "google", "LLM_API_KEY": "test-key"}, clear=True):
        from config import Config
        config = Config.from_env()

        mock_response = MagicMock()
        mock_response.text = '{"unsafe": false, "reason": "none"}'

        client = create_llm_client(config)
        client._client = MagicMock()
        client._client.models.generate_content.return_value = mock_response

        is_unsafe, reason = client.analyze("Hello friend!")

    assert is_unsafe is False
    assert reason == "none"

def test_google_analyze_unsafe():
    with patch.dict(os.environ, {"LLM_PROVIDER": "google", "LLM_API_KEY": "test-key"}, clear=True):
        from config import Config
        config = Config.from_env()

        mock_response = MagicMock()
        mock_response.text = '{"unsafe": true, "reason": "explicit content"}'

        client = create_llm_client(config)
        client._client = MagicMock()
        client._client.models.generate_content.return_value = mock_response

        is_unsafe, reason = client.analyze("Bad message")

    assert is_unsafe is True
    assert reason == "explicit content"

def test_openai_analyze_safe():
    from config import Config
    config = Config.from_env()
    client = create_llm_client(config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"unsafe": false, "reason": "none"}'}}]
    }

    with patch.object(client._session, "post", return_value=mock_response):
        is_unsafe, reason = client.analyze("Hello friend!")

    assert is_unsafe is False
    assert reason == "none"

def test_openai_analyze_unsafe():
    from config import Config
    config = Config.from_env()
    client = create_llm_client(config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"unsafe": true, "reason": "explicit content"}'}}]
    }

    with patch.object(client._session, "post", return_value=mock_response):
        is_unsafe, reason = client.analyze("Bad message")

    assert is_unsafe is True
    assert reason == "explicit content"

def test_openai_analyze_timeout():
    from config import Config
    config = Config.from_env()
    client = create_llm_client(config)

    with patch.object(client._session, "post", side_effect=requests.Timeout()):
        with pytest.raises(requests.Timeout):
            client.analyze("Hello")
