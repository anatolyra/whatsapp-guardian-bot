import pytest
from unittest.mock import patch, MagicMock

def test_webhook_incoming_message(client):
    with patch("guardian.llm_client") as mock_llm, \
         patch("guardian.telegram") as mock_telegram, \
         patch("guardian.failure_tracker") as mock_tracker:

        mock_llm.analyze.return_value = (False, "none")

        response = client.post("/webhook", json={
            "event": "message.any",
            "payload": {
                "from": "+1234567890",
                "body": "Hello friend!",
                "fromMe": False,
                "timestamp": 1710337200
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
                "from": "+1234567890",
                "body": "Bad message",
                "fromMe": False,
                "timestamp": 1710337200
            }
        })

        assert response.status_code == 200
        mock_telegram.send_unsafe_alert.assert_called_once()

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
                "from": "+1234567890",
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
