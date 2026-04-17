import os
from typing import Dict
import yaml

LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

REQUIRED_KEYS = [
    "language",
    "native_name",
    "direction",
    "safety_alert.title",
    "safety_alert.direction",
    "safety_alert.from",
    "safety_alert.group",
    "safety_alert.time",
    "safety_alert.message",
    "safety_alert.reason",
    "safety_alert.from_private",
    "failure_alert.title",
    "failure_alert.time",
    "failure_alert.failed_analyses",
    "failure_alert.status",
    "failure_alert.retry_note",
    "llm_instruction",
]


def _load_yaml(code: str) -> Dict:
    path = os.path.join(LOCALES_DIR, f"{code}.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_locale(locale: Dict, code: str) -> None:
    missing = []
    for key in REQUIRED_KEYS:
        parts = key.split(".")
        obj = locale
        try:
            for part in parts:
                obj = obj[part]
        except (KeyError, TypeError):
            missing.append(key)

    if missing:
        raise ValueError(
            f"Locale '{code}' is missing keys: {', '.join(missing)}"
        )


def load_locale(code: str, _skip_existence_check: bool = False) -> Dict:
    if not _skip_existence_check:
        available = get_available_languages()
        if code not in available:
            raise ValueError(
                f"Unknown language code: {code}. Available: {', '.join(sorted(available))}"
            )

    locale = _load_yaml(code)
    _validate_locale(locale, code)
    return locale


def get_available_languages() -> list:
    if not os.path.isdir(LOCALES_DIR):
        return []
    return sorted(
        f[:-5] for f in os.listdir(LOCALES_DIR) if f.endswith(".yaml")
    )