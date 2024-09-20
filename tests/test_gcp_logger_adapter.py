# File: tests/test_gcp_logger_adapter.py

from unittest.mock import MagicMock, patch

import pytest

from src.gcp_logger import ALERT, EMERGENCY, NOTICE, GCPLoggerAdapter


@pytest.fixture
def logger_adapter():
    mock_logger = MagicMock()
    return GCPLoggerAdapter(mock_logger, extra={"instance_id": "test-instance"})


def test_logger_adapter_process(logger_adapter):
    msg, kwargs = logger_adapter.process("Test message", {})
    assert msg == "Test message"
    assert "extra" in kwargs
    assert kwargs["extra"]["instance_id"] == "test-instance"


def test_logger_adapter_custom_levels(logger_adapter):
    with patch.object(logger_adapter, "log") as mock_log:
        logger_adapter.notice("Notice message")
        mock_log.assert_called_with(NOTICE, "Notice message")

        logger_adapter.alert("Alert message")
        mock_log.assert_called_with(ALERT, "Alert message")

        logger_adapter.emergency("Emergency message")
        mock_log.assert_called_with(EMERGENCY, "Emergency message")


def test_logger_adapter_success(logger_adapter):
    with patch.object(logger_adapter, "info") as mock_info:
        logger_adapter.success("Success message")
        mock_info.assert_called_with("SUCCESS: Success message")
