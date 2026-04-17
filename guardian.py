import hashlib
import logging
from collections import OrderedDict
from typing import Optional, Dict
from flask import Flask, request, jsonify
from datetime import datetime, timezone
from config import Config
from llm_client import create_llm_client
from failure_tracker import FailureTracker
from telegram import TelegramSender
from i18n import load_locale

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEEN_MESSAGES_MAX = 1000

app = Flask(__name__)

config = Config.from_env()
locale = load_locale(config.language)
llm_client = create_llm_client(config, llm_instruction=locale["llm_instruction"])
failure_tracker = FailureTracker(
    notify_first=config.failure_notify_first,
    notify_interval=config.failure_notify_interval,
)
telegram = TelegramSender(config.telegram_bot_token, config.telegram_chat_id, locale=locale) if config.telegram_bot_token and config.telegram_chat_id else None
_seen_messages: OrderedDict[str, None] = OrderedDict()


def extract_sender_info(payload: dict) -> Dict[str, Optional[str]]:
    data = payload.get("_data", {}) or {}
    from_id = payload.get("from", "") or ""
    to_id = payload.get("to", "") or ""

    is_group = from_id.endswith("@g.us") or to_id.endswith("@g.us")

    if is_group:
        group_jid = from_id if from_id.endswith("@g.us") else to_id
        group_name = group_jid.split("@")[0]
        sender_id = payload.get("participant")
    else:
        group_name = None
        sender_id = from_id

    sender_phone = _extract_phone(sender_id)

    notify_name = data.get("notifyName")
    push_name = data.get("pushName")

    if push_name and push_name != "~":
        sender_name = push_name
    elif notify_name and notify_name != "~":
        sender_name = notify_name
    else:
        sender_name = None

    return {
        "sender_name": sender_name,
        "sender_phone": sender_phone,
        "group_name": group_name,
        "is_group": is_group
    }


def _extract_phone(sender_id: Optional[str]) -> str:
    if not sender_id or sender_id == "unknown" or sender_id == "out@c.us":
        return "unknown"

    local_part, _, suffix = sender_id.partition("@")
    if not local_part:
        return "unknown"

    if suffix == "lid":
        return "unknown"

    return f"+{local_part}"


def _make_dedup_key(payload: dict) -> str:
    msg_id = payload.get("id", "")
    if msg_id:
        return msg_id

    sender = payload.get("from", "") or ""
    body = payload.get("body", "") or ""
    timestamp = payload.get("timestamp", "") or ""
    raw = f"{sender}:{body}:{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data or "payload" not in data:
        return jsonify({"status": "ignored"}), 200

    payload = data["payload"]
    payload_data = payload.get("_data", {}) or {}

    if payload_data.get("type") in ("e2e_notification", "notification_template"):
        return jsonify({"status": "ignored"}), 200

    dedup_key = _make_dedup_key(payload)
    if dedup_key in _seen_messages:
        logger.info(f"Duplicate message ignored: {dedup_key[:16]}...")
        return jsonify({"status": "duplicate"}), 200

    _seen_messages[dedup_key] = None
    while len(_seen_messages) > SEEN_MESSAGES_MAX:
        _seen_messages.popitem(last=False)

    message_text = payload.get("body", "")
    from_me = payload.get("fromMe", False)
    direction = "outgoing" if from_me else "incoming"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sender_info = extract_sender_info(payload)

    try:
        is_unsafe, reason = llm_client.analyze(message_text)

        if is_unsafe and telegram and config.failure_notify_enabled:
            telegram.send_safety_alert(
                direction=direction,
                sender_info=sender_info,
                timestamp=timestamp,
                message=message_text[:200],
                reason=reason,
            )

        failure_tracker.record_success()
        logger.info(f"Message analyzed: {direction} from {sender_info.get('sender_phone', 'unknown')}, verdict: {'unsafe' if is_unsafe else 'safe'}")

    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        count = failure_tracker.record_failure()

        if config.failure_notify_enabled and failure_tracker.should_notify() and telegram:
            telegram.send_failure_alert(
                timestamp=timestamp,
                failure_count=count,
            )

    return jsonify({"status": "processed"}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
