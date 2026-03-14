import requests
from typing import Optional

class TelegramSender:
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_unsafe_alert(
        self,
        direction: str,
        sender: str,
        timestamp: str,
        message: str,
        reason: str,
    ) -> bool:
        text = f"""🚨 *Guardian Alert* 🚨

*Direction:* {direction}
*From:* {sender}
*Time:* {timestamp}
*Message:* {message}
*Reason:* {reason}"""

        return self._send_message(text)

    def send_failure_alert(
        self,
        timestamp: str,
        failure_count: int,
    ) -> bool:
        text = f"""⚠️ *Guardian - LLM Unavailable*

*Time:* {timestamp}
*Failed analyses:* {failure_count}
*Status:* LLM service not responding. Messages are not being analyzed.

_Analysis will retry automatically._"""

        return self._send_message(text)

    def _send_message(self, text: str) -> bool:
        url = self.API_URL.format(token=self.bot_token)

        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                    timeout=10,
                )
                response.raise_for_status()
                return True
            except Exception:
                if attempt == 2:
                    return False
                continue

        return False
