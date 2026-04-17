import pytest
from unittest.mock import patch
from i18n import load_locale, get_available_languages, REQUIRED_KEYS


def test_load_locale_english():
    locale = load_locale("en")
    assert locale["language"] == "en"
    assert locale["direction"] == "ltr"
    assert locale["safety_alert"]["title"] == "Alert"
    assert locale["llm_instruction"] is not None


def test_load_locale_hebrew():
    locale = load_locale("he")
    assert locale["language"] == "he"
    assert locale["direction"] == "rtl"
    assert locale["safety_alert"]["title"] == "התראה"


def test_load_locale_russian():
    locale = load_locale("ru")
    assert locale["language"] == "ru"
    assert locale["direction"] == "ltr"
    assert locale["safety_alert"]["title"] == "Оповещение"


def test_load_locale_unknown_raises():
    with pytest.raises(ValueError, match="Unknown language code: fr"):
        load_locale("fr")


def test_get_available_languages():
    languages = get_available_languages()
    assert "en" in languages
    assert "he" in languages
    assert "ru" in languages


def test_load_locale_validates_required_keys():
    with patch("i18n._load_yaml") as mock_yaml:
        mock_yaml.return_value = {
            "language": "xx",
            "native_name": "Test",
            "direction": "ltr",
            "safety_alert": {
                "title": "T",
            },
            "failure_alert": {},
        }
        with pytest.raises(ValueError, match=r"is missing keys"):
            load_locale("xx", _skip_existence_check=True)


def test_load_locale_all_required_keys_present():
    locale = load_locale("en")
    for key in REQUIRED_KEYS:
        parts = key.split(".")
        obj = locale
        for part in parts:
            assert part in obj, f"Missing required key: {key}"
            obj = obj[part]