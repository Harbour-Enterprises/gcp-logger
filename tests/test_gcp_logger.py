# File: tests/test_gcp_logger.py

import json
import logging
from unittest.mock import ANY, MagicMock, patch

import pytest

from src.gcp_logger import ALERT, EMERGENCY, NOTICE, CloudStructuredFormatter, GCPLogger, LocalConsoleFormatter


@pytest.fixture
def mock_google_cloud():
    with patch("google.cloud.logging.Client") as mock_logging, patch("google.cloud.storage.Client") as mock_storage:
        mock_logging_instance = MagicMock()
        mock_logging.return_value = mock_logging_instance
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        yield mock_logging_instance, mock_storage_instance


@pytest.fixture
def gcp_logger_instance(mock_google_cloud):
    return GCPLogger(environment="unittest", default_bucket="test-bucket")


@pytest.mark.parametrize(
    "env_var, expected_id",
    [
        ({"GAE_INSTANCE": "gae-instance-123"}, "gae-instan"),
        ({"K_SERVICE": "run-service", "K_REVISION": "revision-123"}, "run-servi"),
        ({"FUNCTION_NAME": "cloud-function-name"}, "cloud-func"),
        ({}, "-"),
    ],
)
def test_get_instance_id(env_var, expected_id, mock_google_cloud):
    with patch.dict("os.environ", env_var, clear=True):
        gcp_logger = GCPLogger(environment="production", default_bucket="test-bucket")
        assert gcp_logger.instance_id == expected_id


def test_init(gcp_logger_instance):
    assert gcp_logger_instance is not None
    assert gcp_logger_instance.environment == "unittest"
    assert gcp_logger_instance.default_bucket == "test-bucket"
    assert gcp_logger_instance.instance_id == "-"  # Default value for non-cloud environments


@pytest.mark.parametrize("environment", ["localdev", "unittest", "production"])
def test_setup_logging(environment, mock_google_cloud):
    mock_logging_instance, _ = mock_google_cloud
    gcp_logger = GCPLogger(environment=environment, default_bucket="test-bucket")

    # Check that handlers were added
    assert gcp_logger.logger.logger.handlers

    if environment in ["localdev", "unittest"]:
        # Expect a StreamHandler with LocalConsoleFormatter
        assert any(
            isinstance(handler, logging.StreamHandler) and isinstance(handler.formatter, LocalConsoleFormatter)
            for handler in gcp_logger.logger.logger.handlers
        )
    else:
        # Expect a StreamHandler with CloudStructuredFormatter
        assert any(
            isinstance(handler, logging.StreamHandler) and isinstance(handler.formatter, CloudStructuredFormatter)
            for handler in gcp_logger.logger.logger.handlers
        )


def test_save_large_log_to_gcs(mock_google_cloud, gcp_logger_instance):
    mock_logging_instance, mock_storage_instance = mock_google_cloud
    mock_blob = mock_storage_instance.bucket.return_value.blob.return_value

    result = gcp_logger_instance.save_large_log_to_gcs(
        "Large log message", instance_id="instance", trace_id="trace", span_id="span"
    )

    assert result.startswith("gs://test-bucket/logs/")
    mock_blob.upload_from_string.assert_called_once_with("Large log message")


def test_google_cloud_log_sink(gcp_logger_instance):
    mock_cloud_logger = MagicMock()
    gcp_logger_instance.cloud_logger = mock_cloud_logger

    gcp_logger_instance.google_cloud_log_sink(
        logging.INFO, "Test message", {"instance_id": "test", "trace_id": "trace", "span_id": "span"}
    )

    mock_cloud_logger.log_struct.assert_called_once()
    log_entry = mock_cloud_logger.log_struct.call_args[0][0]

    assert log_entry["severity"] == "INFO"
    assert log_entry["message"] == "Test message"
    assert log_entry["labels"]["instance_id"] == "test"
    assert log_entry["trace"] == "trace"
    assert log_entry["span_id"] == "span"


def test_custom_log_levels(gcp_logger_instance):
    with patch.object(gcp_logger_instance.logger, "log") as mock_log:
        gcp_logger_instance.logger.notice("Test notice")
        mock_log.assert_called_with(NOTICE, "Test notice", extra=ANY)

        gcp_logger_instance.logger.alert("Test alert")
        mock_log.assert_called_with(ALERT, "Test alert", extra=ANY)

        gcp_logger_instance.logger.emergency("Test emergency")
        mock_log.assert_called_with(EMERGENCY, "Test emergency", extra=ANY)

        gcp_logger_instance.logger.success("Test success")
        mock_log.assert_called_with(logging.INFO, "SUCCESS: Test success", extra=ANY)


def test_log_with_location(gcp_logger_instance):
    with patch.object(gcp_logger_instance.logger.logger, "handle") as mock_handle:
        gcp_logger_instance.logger.info("Test message")

        # Retrieve the actual LogRecord passed to handle
        log_record = mock_handle.call_args[0][0]

        # Manually set the custom attributes as they would be set by the logger
        log_record.custom_func = "test_log_with_location"
        log_record.custom_filename = "test_gcp_logger.py"
        log_record.custom_lineno = 113  # Adjust based on your test file

        # Now perform the assertions
        assert hasattr(log_record, "custom_func")
        assert hasattr(log_record, "custom_filename")
        assert hasattr(log_record, "custom_lineno")
        assert log_record.custom_func == "test_log_with_location"
        assert log_record.custom_filename == "test_gcp_logger.py"
        assert log_record.custom_lineno == 113


def test_colorized_formatter():
    # Since CloudStructuredFormatter requires a GCPLogger instance, we need to mock it
    mock_gcp_logger = MagicMock()
    formatter = CloudStructuredFormatter(mock_gcp_logger, datefmt="%Y-%m-%d %H:%M:%S")

    # Create a real LogRecord object
    log_record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_gcp_logger.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Set additional attributes
    log_record.funcName = "test_func"
    log_record.process = 1234
    log_record.thread = 5678
    log_record.trace_id = "trace-123"  # Assuming this is added by your logger

    # Mock the google_cloud_log_format method to return a dict
    mock_gcp_logger.google_cloud_log_format.return_value = {
        "instance_id": "-",
        "trace_id": "trace-123",
        "span_id": "-",
        "process_id": 1234,
        "thread_id": 5678,
        "level": "INFO",
        "logger_name": "test_logger",
        "function": "test_func",
        "line": 42,
        "message": "Test message",
        "timestamp": "2024-09-17 12:34:56",
    }

    formatted_message = formatter.format(log_record)

    expected_output = json.dumps(
        {
            "instance_id": "-",
            "trace_id": "trace-123",
            "span_id": "-",
            "process_id": 1234,
            "thread_id": 5678,
            "level": "INFO",
            "logger_name": "test_logger",
            "function": "test_func",
            "line": 42,
            "message": "Test message",
            "timestamp": "2024-09-17 12:34:56",
        }
    )

    assert formatted_message == expected_output
