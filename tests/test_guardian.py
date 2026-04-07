import pytest
from unittest.mock import patch, MagicMock


def test_extract_sender_info_direct_with_name():
    from guardian import extract_sender_info

    payload = {
        "from": "1234567890@c.us",
        "body": "Hello!",
        "_data": {
            "pushName": "John",
            "notify": "John"
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] == "John"
    assert result["sender_phone"] == "+1234567890"
    assert result["group_name"] is None
    assert result["is_group"] is False


def test_extract_sender_info_direct_no_name():
    from guardian import extract_sender_info

    payload = {
        "from": "1234567890@c.us",
        "body": "Hello!",
        "_data": {
            "pushName": "~"
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] is None
    assert result["sender_phone"] == "+1234567890"
    assert result["group_name"] is None
    assert result["is_group"] is False


def test_extract_sender_info_group_with_names():
    from guardian import extract_sender_info

    payload = {
        "from": "123456789@g.us",
        "participant": "9876543210@c.us",
        "body": "Hello group!",
        "_data": {
            "pushName": "Alice",
            "metadata": {
                "subject": "Family Chat"
            }
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] == "Alice"
    assert result["sender_phone"] == "+9876543210"
    assert result["group_name"] == "Family Chat"
    assert result["is_group"] is True


def test_extract_sender_info_group_no_names():
    from guardian import extract_sender_info

    payload = {
        "from": "123456789@g.us",
        "participant": "9876543210@c.us",
        "body": "Hello group!",
        "_data": {}
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] is None
    assert result["sender_phone"] == "+9876543210"
    assert result["group_name"] is None
    assert result["is_group"] is True


def test_extract_sender_info_missing_data():
    from guardian import extract_sender_info

    payload = {
        "from": "1234567890@c.us",
        "body": "Hello!"
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] is None
    assert result["sender_phone"] == "+1234567890"
    assert result["group_name"] is None
    assert result["is_group"] is False


def test_extract_sender_info_notify_fallback():
    from guardian import extract_sender_info

    payload = {
        "from": "1234567890@c.us",
        "body": "Hello!",
        "_data": {
            "pushName": "~",
            "notify": "Jane"
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] == "Jane"


def test_extract_sender_info_lid_format():
    from guardian import extract_sender_info

    payload = {
        "from": "1234567890@lid",
        "body": "Hello!",
        "_data": {
            "pushName": "John"
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] == "John"
    assert result["sender_phone"] == "+1234567890"


def test_extract_sender_info_empty_from():
    from guardian import extract_sender_info

    payload = {
        "from": "",
        "body": "Hello!",
        "_data": {}
    }

    result = extract_sender_info(payload)

    assert result["sender_phone"] == "unknown"
    assert result["sender_name"] is None


def test_extract_sender_info_none_from():
    from guardian import extract_sender_info

    payload = {
        "from": None,
        "body": "Hello!",
        "_data": {}
    }

    result = extract_sender_info(payload)

    assert result["sender_phone"] == "unknown"
    assert result["sender_name"] is None


def test_extract_sender_info_group_subject_fallback():
    from guardian import extract_sender_info

    payload = {
        "from": "123456789@g.us",
        "participant": "9876543210@c.us",
        "body": "Hello group!",
        "_data": {
            "pushName": "Alice",
            "subject": "Work Group"
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] == "Alice"
    assert result["sender_phone"] == "+9876543210"
    assert result["group_name"] == "Work Group"


def test_extract_sender_info_group_without_participant():
    from guardian import extract_sender_info

    payload = {
        "from": "123456789@g.us",
        "body": "Hello group!",
        "_data": {
            "subject": "Family Chat"
        }
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] is None
    assert result["sender_phone"] == "unknown"
    assert result["group_name"] == "Family Chat"


def test_extract_sender_info_none_data():
    from guardian import extract_sender_info

    payload = {
        "from": "1234567890@c.us",
        "body": "Hello!",
        "_data": None
    }

    result = extract_sender_info(payload)

    assert result["sender_name"] is None
    assert result["sender_phone"] == "+1234567890"


def test_webhook_incoming_message(client):
    with patch("guardian.llm_client") as mock_llm, \
         patch("guardian.telegram") as mock_telegram, \
         patch("guardian.failure_tracker") as mock_tracker:

        mock_llm.analyze.return_value = (False, "none")

        response = client.post("/webhook", json={
            "event": "message.any",
            "payload": {
                "from": "1234567890@c.us",
                "body": "Hello friend!",
                "fromMe": False,
                "timestamp": 1710337200,
                "_data": {
                    "pushName": "John"
                }
            }
        })

        assert response.status_code == 200
        assert response.json["status"] == "processed"
        mock_tracker.record_success.assert_called_once()


def test_webhook_unsafe_message_sends_telegram(client):
    with patch("guardian.llm_client") as mock_llm, \
         patch("guardian.telegram") as mock_telegram, \
         patch("guardian.failure_tracker") as mock_tracker:

        mock_llm.analyze.return_value = (True, "explicit content")

        response = client.post("/webhook", json={
            "event": "message.any",
            "payload": {
                "from": "1234567890@c.us",
                "body": "Bad message",
                "fromMe": False,
                "timestamp": 1710337200,
                "_data": {
                    "pushName": "John"
                }
            }
        })

        assert response.status_code == 200
        mock_telegram.send_safety_alert.assert_called_once()
        
        call_args = mock_telegram.send_safety_alert.call_args
        sender_info = call_args[1]["sender_info"]
        assert sender_info["sender_name"] == "John"
        assert sender_info["sender_phone"] == "+1234567890"


def test_webhook_llm_failure_sends_alert_on_first(client):
    with patch("guardian.llm_client") as mock_llm, \
         patch("guardian.telegram") as mock_telegram, \
         patch("guardian.failure_tracker") as mock_tracker, \
         patch("guardian.config") as mock_config:

        mock_llm.analyze.side_effect = Exception("LLM timeout")
        mock_tracker.should_notify.return_value = True
        mock_tracker.record_failure.return_value = 1
        mock_config.failure_notify_enabled = True

        response = client.post("/webhook", json={
            "event": "message.any",
            "payload": {
                "from": "1234567890@c.us",
                "body": "Hello",
                "fromMe": False,
                "timestamp": 1710337200
            }
        })

        assert response.status_code == 200
        mock_tracker.record_failure.assert_called_once()
        mock_telegram.send_failure_alert.assert_called_once()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"
