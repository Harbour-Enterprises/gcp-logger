import sys
from unittest.mock import patch

import pytest
from google.cloud import logging as cloud_logging

from src.superlogs import SuperLogs, logger


@pytest.fixture
def superlogs_instance():
    with patch("google.cloud.logging.Client"), patch("google.cloud.storage.Client"):
        yield SuperLogs(environment="unittest", default_bucket="test-bucket")


def test_init(superlogs_instance):
    assert superlogs_instance.environment == "unittest"
    assert superlogs_instance.default_bucket == "test-bucket"
    assert superlogs_instance.gae_instance == "-"
    assert isinstance(superlogs_instance.client, cloud_logging.Client)
    assert isinstance(superlogs_instance.cloud_logger, cloud_logging.Logger)


def test_setup_logging_unittest(superlogs_instance):
    assert logger.level("ALERT").no == 70
    assert logger.level("EMERGENCY").no == 80

    # Check if the stdout handler is added for unittest environment
    handlers = logger._core.handlers
    assert any(handler.sink == sys.stdout for handler in handlers.values())


@pytest.mark.parametrize(
    "log_level,expected_severity",
    [
        ("TRACE", "DEBUG"),
        ("DEBUG", "DEBUG"),
        ("INFO", "INFO"),
        ("SUCCESS", "NOTICE"),
        ("WARNING", "WARNING"),
        ("ERROR", "ERROR"),
        ("CRITICAL", "CRITICAL"),
        ("ALERT", "ALERT"),
        ("EMERGENCY", "EMERGENCY"),
    ],
)
def test_google_cloud_log_sink(superlogs_instance, log_level, expected_severity):
    with patch.object(superlogs_instance.cloud_logger, "log_struct") as mock_log_struct:
        logger.log(log_level, "Test message")

        mock_log_struct.assert_called_once()
        args, kwargs = mock_log_struct.call_args
        assert kwargs["severity"] == expected_severity
        assert "Test message" in args[0]["message"]


def test_google_cloud_log_format():
    record = {
        "extra": {"instance_id": "test-instance", "trace_id": "trace-123", "span_id": "span-456"},
        "process": {"id": 1234},
        "thread": {"id": 5678},
        "level": {"name": "INFO"},
        "name": "test_logger",
        "function": "test_function",
        "line": 42,
        "message": "Test log message",
    }
    formatted_log = SuperLogs.google_cloud_log_format(record)
    assert (
        "test-instance | trace-123 | span-456 | 1234 | 5678 | INFO     | test_logger:test_function:42 - Test log message"
        in formatted_log
    )


def test_google_cloud_log_truncate():
    long_message = "a" * (SuperLogs.LOGGING_MAX_SIZE + 1000)
    gsutil_uri = "gs://test-bucket/test-log.txt"

    truncated_message = SuperLogs.google_cloud_log_truncate(long_message, gsutil_uri)

    assert len(truncated_message.encode("utf-8")) <= SuperLogs.LOGGING_MAX_SIZE
    assert "... [truncated]" in truncated_message
    assert gsutil_uri in truncated_message


@patch("google.cloud.storage.Client")
@patch("google.cloud.storage.Bucket")
@patch("google.cloud.storage.Blob")
def test_save_large_log_to_gcs(mock_blob, mock_bucket, mock_storage_client, superlogs_instance):
    mock_storage_client.return_value.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    log_message = "Test log message"
    result = superlogs_instance.save_large_log_to_gcs(
        log_message, "instance-1", "trace-123", "span-456", "1234", "5678"
    )

    assert result.startswith("gs://test-bucket/logs/")
    mock_blob.upload_from_string.assert_called_once_with(log_message)


def test_get_logger():
    assert SuperLogs.get_logger() == logger


def test_custom_log_levels():
    logger.alert("Test alert message")
    logger.emergency("Test emergency message")
    # These tests mainly ensure that the custom log levels don't raise exceptions
    # You might want to add more specific assertions based on your needs
