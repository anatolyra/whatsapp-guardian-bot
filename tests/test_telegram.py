import pytest
from unittest.mock import patch, MagicMock
from telegram import TelegramSender


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
*Status:* LLM service not responding. Messages are not being analyzed.

_Analysis will retry automatically._"""

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
