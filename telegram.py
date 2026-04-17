import requests
from typing import Optional, Dict

BOT_NAME = "Guardian Bot"

_ENGLISH_LOCALE = {
    "language": "en",
    "native_name": "English",
    "direction": "ltr",
    "safety_alert": {
        "title": "Alert",
        "direction": "Direction",
        "from": "From",
        "group": "Group",
        "time": "Time",
        "message": "Message",
        "reason": "Reason",
        "from_private": "private number",
    },
    "failure_alert": {
        "title": "LLM Unavailable",
        "time": "Time",
        "failed_analyses": "Failed analyses",
        "status": "LLM service not responding. Messages are not being analyzed.",
        "retry_note": "_Analysis will retry automatically._",
    },
    "llm_instruction": "Respond in English. All reason text must be written in English.",
}


class TelegramSender:
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str, locale: Optional[Dict] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.locale = locale or _ENGLISH_LOCALE
        self._session = requests.Session()

    def send_safety_alert(
        self,
        direction: str,
        sender_info: Dict[str, Optional[str]],
        timestamp: str,
        message: str,
        reason: str,
    ) -> bool:
        sa = self.locale["safety_alert"]
        sender_line = self._format_sender_line(sender_info)
        group_line = self._format_group_line(sender_info)

        text = f"""🤖 *{BOT_NAME}*

🚨 *{sa['title']}* 🚨

*{sa['direction']}:* {direction}
{sender_line}
{group_line}*{sa['time']}:* {timestamp}
*{sa['message']}:* {message}
*{sa['reason']}:* {reason}"""

        if self.locale.get("direction") == "rtl":
            text = "\u200f" + text

        return self._send_message(text)

    def _format_sender_line(self, sender_info: Dict[str, Optional[str]]) -> str:
        sa = self.locale["safety_alert"]
        sender_name = sender_info.get("sender_name")
        sender_phone = sender_info.get("sender_phone", "unknown")

        if sender_name and sender_phone != "unknown":
            return f"*{sa['from']}:* {sender_name} ({sender_phone})"
        if sender_name:
            return f"*{sa['from']}:* {sender_name}"
        if sender_phone != "unknown":
            return f"*{sa['from']}:* {sender_phone}"
        return f"*{sa['from']}:* {sa['from_private']}"

    def _format_group_line(self, sender_info: Dict[str, Optional[str]]) -> str:
        sa = self.locale["safety_alert"]
        group_name = sender_info.get("group_name")
        if group_name:
            return f"*{sa['group']}:* {group_name}\n"
        return ""

    def send_failure_alert(
        self,
        timestamp: str,
        failure_count: int,
    ) -> bool:
        fa = self.locale["failure_alert"]
        text = f"""🤖 *{BOT_NAME}*

⚠️ *{fa['title']}*

*{fa['time']}:* {timestamp}
*{fa['failed_analyses']}:* {failure_count}
*{fa['status']}*

{fa['retry_note']}"""

        if self.locale.get("direction") == "rtl":
            text = "\u200f" + text

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