import pytest
from unittest.mock import patch, MagicMock
from telegram import TelegramSender
from i18n import load_locale


def test_send_safety_alert_with_sender_name():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": "John",
            "sender_phone": "+1234567890",
            "group_name": None,
            "is_group": False
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test message",
            reason="explicit content"
        )

    expected_text = """🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* John (+1234567890)
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Test message
*Reason:* explicit content"""

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text
    assert call_args[1]["json"]["parse_mode"] == "Markdown"


def test_send_safety_alert_without_sender_name():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": None,
            "sender_phone": "+1234567890",
            "group_name": None,
            "is_group": False
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test message",
            reason="explicit content"
        )

    expected_text = """🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* +1234567890
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Test message
*Reason:* explicit content"""

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text


def test_send_unsafe_alert_group_message():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": "Alice",
            "sender_phone": "+9876543210",
            "group_name": "Family Chat",
            "is_group": True
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test group message",
            reason="explicit content"
        )

    expected_text = """🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* Alice (+9876543210)
*Group:* Family Chat
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Test group message
*Reason:* explicit content"""

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text


def test_send_unsafe_alert_group_no_sender_name():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": None,
            "sender_phone": "+9876543210",
            "group_name": "Family Chat",
            "is_group": True
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test group message",
            reason="explicit content"
        )

    expected_text = """🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* +9876543210
*Group:* Family Chat
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Test group message
*Reason:* explicit content"""

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text


def test_send_failure_alert():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender.send_failure_alert(
            timestamp="2025-03-13 14:30:00 UTC",
            failure_count=4
        )

    expected_text = """⚠️ *Guardian - LLM Unavailable*

*Time:* 2025-03-13 14:30:00 UTC
*Failed analyses:* 4
*LLM service not responding. Messages are not being analyzed.*

_Analysis will retry automatically._"""

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text


def test_format_sender_line_name_and_phone():
    sender = TelegramSender("test-bot-token", "test-chat-id")
    result = sender._format_sender_line({
        "sender_name": "John",
        "sender_phone": "+1234567890",
        "group_name": None,
        "is_group": False
    })
    assert result == "*From:* John (+1234567890)"


def test_format_sender_line_name_unknown_phone():
    sender = TelegramSender("test-bot-token", "test-chat-id")
    result = sender._format_sender_line({
        "sender_name": "Orit Rabinovich",
        "sender_phone": "unknown",
        "group_name": None,
        "is_group": False
    })
    assert result == "*From:* Orit Rabinovich"


def test_format_sender_line_phone_only():
    sender = TelegramSender("test-bot-token", "test-chat-id")
    result = sender._format_sender_line({
        "sender_name": None,
        "sender_phone": "+1234567890",
        "group_name": None,
        "is_group": False
    })
    assert result == "*From:* +1234567890"


def test_format_sender_line_no_name_no_phone():
    sender = TelegramSender("test-bot-token", "test-chat-id")
    result = sender._format_sender_line({
        "sender_name": None,
        "sender_phone": "unknown",
        "group_name": None,
        "is_group": False
    })
    assert result == "*From:* private number"


def test_send_safety_alert_group_unknown_phone():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    with patch.object(sender._session, "post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        sender_info = {
            "sender_name": "Orit Rabinovich",
            "sender_phone": "unknown",
            "group_name": "Family Chat",
            "is_group": True
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test group message",
            reason="explicit content"
        )

    expected_text = """🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* Orit Rabinovich
*Group:* Family Chat
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Test group message
*Reason:* explicit content"""

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text


def test_send_message_retries():
    sender = TelegramSender("test-bot-token", "test-chat-id")

    with patch.object(sender._session, "post") as mock_post:
        mock_post.side_effect = [
            Exception("timeout"),
            Exception("timeout"),
            MagicMock(status_code=200),
        ]

        result = sender._send_message("test message")

    assert result is True
    assert mock_post.call_count == 3


def _get_english_locale():
    return load_locale("en")


def _get_hebrew_locale():
    return load_locale("he")


def test_send_safety_alert_with_english_locale():
    locale = _get_english_locale()
    sender = TelegramSender("test-bot-token", "test-chat-id", locale=locale)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": "John",
            "sender_phone": "+1234567890",
            "group_name": None,
            "is_group": False
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test message",
            reason="explicit content"
        )

    expected_text = """🚨 *Guardian Alert* 🚨

*Direction:* incoming
*From:* John (+1234567890)
*Time:* 2025-03-13 14:30:00 UTC
*Message:* Test message
*Reason:* explicit content"""

    call_args = mock_post.call_args
    assert call_args[1]["json"]["text"] == expected_text


def test_send_safety_alert_with_hebrew_locale():
    locale = _get_hebrew_locale()
    sender = TelegramSender("test-bot-token", "test-chat-id", locale=locale)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": "John",
            "sender_phone": "+1234567890",
            "group_name": None,
            "is_group": False
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test message",
            reason="explicit content"
        )

    call_args = mock_post.call_args
    text = call_args[1]["json"]["text"]
    assert text.startswith("\u200f")
    assert "התראת שומר" in text
    assert "מאת" in text


def test_send_failure_alert_with_hebrew_locale():
    locale = _get_hebrew_locale()
    sender = TelegramSender("test-bot-token", "test-chat-id", locale=locale)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender.send_failure_alert(
            timestamp="2025-03-13 14:30:00 UTC",
            failure_count=4
        )

    call_args = mock_post.call_args
    text = call_args[1]["json"]["text"]
    assert text.startswith("\u200f")
    assert "שומר - LLM לא זמין" in text


def test_format_sender_line_with_hebrew_locale():
    locale = _get_hebrew_locale()
    sender = TelegramSender("test-bot-token", "test-chat-id", locale=locale)
    result = sender._format_sender_line({
        "sender_name": "John",
        "sender_phone": "+1234567890",
        "group_name": None,
        "is_group": False
    })
    assert "מאת" in result


def test_format_sender_line_private_number_with_hebrew_locale():
    locale = _get_hebrew_locale()
    sender = TelegramSender("test-bot-token", "test-chat-id", locale=locale)
    result = sender._format_sender_line({
        "sender_name": None,
        "sender_phone": "unknown",
        "group_name": None,
        "is_group": False
    })
    assert "מספר פרטי" in result


def test_english_locale_no_rlm():
    locale = _get_english_locale()
    sender = TelegramSender("test-bot-token", "test-chat-id", locale=locale)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(sender._session, "post", return_value=mock_response) as mock_post:
        sender_info = {
            "sender_name": None,
            "sender_phone": "+1234567890",
            "group_name": None,
            "is_group": False
        }
        sender.send_safety_alert(
            direction="incoming",
            sender_info=sender_info,
            timestamp="2025-03-13 14:30:00 UTC",
            message="Test",
            reason="test"
        )

    call_args = mock_post.call_args
    text = call_args[1]["json"]["text"]
    assert not text.startswith("\u200f")
