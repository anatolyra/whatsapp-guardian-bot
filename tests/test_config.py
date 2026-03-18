import os
import pytest
from unittest.mock import patch

def test_default_provider_is_ollama():
    with patch.dict(os.environ, {}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.provider == "ollama"

def test_provider_from_env():
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.provider == "openai"

def test_ollama_defaults():
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.base_url == "http://localhost:11434/v1"
        assert config.model == "llama3.2"

def test_google_defaults():
    with patch.dict(os.environ, {"LLM_PROVIDER": "google"}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.base_url is None
        assert config.model == "gemini-3-flash-preview"

def test_failure_notify_defaults():
    with patch.dict(os.environ, {}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.failure_notify_enabled is True
        assert config.failure_notify_first is True
        assert config.failure_notify_interval == 3

def test_failure_notify_disabled():
    with patch.dict(os.environ, {"FAILURE_NOTIFY_ENABLED": "false"}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.failure_notify_enabled is False

def test_failure_notify_interval_zero():
    with patch.dict(os.environ, {"FAILURE_NOTIFY_INTERVAL": "0"}, clear=True):
        from config import Config
        config = Config.from_env()
        assert config.failure_notify_interval == 0

def test_unknown_provider_raises():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}, clear=True):
        from config import Config
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            Config.from_env()
