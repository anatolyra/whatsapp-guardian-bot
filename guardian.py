import logging
from typing import Optional, Dict
from flask import Flask, request, jsonify
from datetime import datetime, timezone
from config import Config
from llm_client import create_llm_client
from failure_tracker import FailureTracker
from telegram import TelegramSender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

config = Config.from_env()
llm_client = create_llm_client(config)
failure_tracker = FailureTracker(
    notify_first=config.failure_notify_first,
    notify_interval=config.failure_notify_interval,
)
telegram = TelegramSender(config.telegram_bot_token, config.telegram_chat_id) if config.telegram_bot_token and config.telegram_chat_id else None


def extract_sender_info(payload: dict) -> Dict[str, Optional[str]]:
    """
    Extract sender information from WAHA webhook payload.

    Args:
        payload: The webhook payload dict from WAHA

    Returns:
        Dict with sender_name, sender_phone, group_name, and is_group fields
    """
    data = payload.get("_data", {}) or {}
    from_id = payload.get("from", "") or ""

    is_group = from_id.endswith("@g.us")
    sender_id = payload.get("participant") if is_group else from_id
    sender_phone = _extract_phone(sender_id)

    push_name = data.get("pushName")
    notify_name = data.get("notify")

    if push_name and push_name != "~":
        sender_name = push_name
    elif notify_name and notify_name != "~":
        sender_name = notify_name
    else:
        sender_name = None

    group_name = None
    if is_group:
        metadata = data.get("metadata", {}) or {}
        group_name = metadata.get("subject") or data.get("subject")

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


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data or "payload" not in data:
        return jsonify({"status": "ignored"}), 200

    payload = data["payload"]
    
    logger.info(f"DEBUG: Full webhook payload: {payload}")
    logger.info(f"DEBUG: payload['_data']: {payload.get('_data', {})}")
    
    message_text = payload.get("body", "")
    from_me = payload.get("fromMe", False)
    direction = "outgoing" if from_me else "incoming"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sender_info = extract_sender_info(payload)
    
    logger.info(f"DEBUG: Extracted sender_info: {sender_info}")

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
