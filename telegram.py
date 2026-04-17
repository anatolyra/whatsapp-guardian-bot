import requests
from typing import Optional, Dict

class TelegramSender:
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._session = requests.Session()

    def send_safety_alert(
        self,
        direction: str,
        sender_info: Dict[str, Optional[str]],
        timestamp: str,
        message: str,
        reason: str,
    ) -> bool:
        sender_line = self._format_sender_line(sender_info)
        group_line = self._format_group_line(sender_info)

        text = f"""🚨 *Guardian Alert* 🚨

*Direction:* {direction}
{sender_line}
{group_line}*Time:* {timestamp}
*Message:* {message}
*Reason:* {reason}"""

        return self._send_message(text)

    def _format_sender_line(self, sender_info: Dict[str, Optional[str]]) -> str:
        sender_name = sender_info.get("sender_name")
        sender_phone = sender_info.get("sender_phone", "unknown")

        if sender_name and sender_phone != "unknown":
            return f"*From:* {sender_name} ({sender_phone})"
        if sender_name:
            return f"*From:* {sender_name}"
        if sender_phone != "unknown":
            return f"*From:* {sender_phone}"
        return "*From:* private number"

    def _format_group_line(self, sender_info: Dict[str, Optional[str]]) -> str:
        group_name = sender_info.get("group_name")
        if group_name:
            return f"*Group:* {group_name}\n"
        return ""

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
                response = self._session.post(
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
