# File: tests/test_superlogs.py

from unittest.mock import MagicMock, patch

import pytest

from src.superlogs import SuperLogs, logger


@pytest.fixture
def superlogs_instance():
    with patch("google.cloud.logging.Client"), patch("google.cloud.storage.Client"):
        yield SuperLogs(environment="unittest", default_bucket="test-bucket")


@pytest.fixture
def mock_cloud_logging():
    with patch("google.cloud.logging.Client") as mock_client:
        mock_logger = MagicMock()
        mock_client.return_value.logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_storage():
    with patch("google.cloud.storage.Client") as mock_client:
        mock_bucket = MagicMock()
        mock_client.return_value.bucket.return_value = mock_bucket
        yield mock_bucket


def test_init(superlogs_instance):
    assert superlogs_instance is not None
    assert superlogs_instance.environment == "unittest"
    assert superlogs_instance.default_bucket == "test-bucket"


def test_google_cloud_log_format():
    record = {
        "extra": {"instance_id": "test", "trace_id": "trace", "span_id": "span"},
        "process": {"id": 1},
        "thread": {"id": 1},
        "level": {"name": "INFO"},
        "name": "test_logger",
        "function": "test_func",
        "line": 10,
        "message": "Test message",
    }
    formatted = SuperLogs.google_cloud_log_format(record)
    assert "test | trace | span" in formatted
    assert "INFO" in formatted
    assert "Test message" in formatted


def test_google_cloud_log_truncate():
    long_message = "a" * 300 * 1024  # 300KB message
    truncated = SuperLogs.google_cloud_log_truncate(long_message, "gs://test-bucket/test-blob")
    assert len(truncated.encode("utf-8")) <= SuperLogs.LOGGING_MAX_SIZE
    assert "[truncated]" in truncated
    assert "gs://test-bucket/test-blob" in truncated


@pytest.mark.parametrize("environment", ["localdev", "unittest", "production"])
def test_setup_logging(environment):
    with patch("google.cloud.logging.Client"), patch("google.cloud.storage.Client"):
        superlogs = SuperLogs(environment=environment, default_bucket="test-bucket")
        assert logger._core.handlers  # Check that handlers were added
        assert "ALERT" in logger._core.levels
        assert "EMERGENCY" in logger._core.levels


def test_save_large_log_to_gcs(superlogs_instance, mock_storage):
    mock_blob = MagicMock()
    mock_storage.blob.return_value = mock_blob

    result = superlogs_instance.save_large_log_to_gcs(
        "Large log message", "instance", "trace", "span", "process", "thread"
    )

    assert result.startswith("gs://test-bucket/logs/")
    mock_blob.upload_from_string.assert_called_once()


def test_google_cloud_log_sink(superlogs_instance, mock_cloud_logging):
    mock_message = MagicMock()
    mock_message.record = {
        "level": {"name": "INFO"},
        "time": MagicMock(),
        "extra": {"instance_id": "test", "trace_id": "trace", "span_id": "span"},
        "process": {"id": 1},
        "thread": {"id": 1},
        "name": "test_logger",
        "function": "test_func",
        "line": 10,
        "message": "Test message",
    }

    # Replace the cloud_logger in the superlogs_instance with our mock
    superlogs_instance.cloud_logger = mock_cloud_logging

    superlogs_instance.google_cloud_log_sink(mock_message)

    mock_cloud_logging.log_struct.assert_called_once()
    log_entry = mock_cloud_logging.log_struct.call_args[0][0]
    assert log_entry["level"] == "INFO"
    assert "Test message" in log_entry["message"]


def test_custom_log_levels():
    assert "ALERT" in logger._core.levels
    assert "EMERGENCY" in logger._core.levels

    with patch.object(logger, "log") as mock_log:
        logger.alert("Test alert")
        mock_log.assert_called_with("ALERT", "Test alert")

        logger.emergency("Test emergency")
        mock_log.assert_called_with("EMERGENCY", "Test emergency")
