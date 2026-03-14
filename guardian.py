import os
import logging
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

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data or "payload" not in data:
        return jsonify({"status": "ignored"}), 200

    payload = data["payload"]
    sender = payload.get("from", "unknown")
    message_text = payload.get("body", "")
    from_me = payload.get("fromMe", False)
    direction = "outgoing" if from_me else "incoming"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        is_unsafe, reason = llm_client.analyze(message_text)

        if is_unsafe and telegram and config.failure_notify_enabled:
            telegram.send_unsafe_alert(
                direction=direction,
                sender=sender,
                timestamp=timestamp,
                message=message_text[:200],
                reason=reason,
            )

        failure_tracker.record_success()
        logger.info(f"Message analyzed: {direction} from {sender}, verdict: {'unsafe' if is_unsafe else 'safe'}")

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
