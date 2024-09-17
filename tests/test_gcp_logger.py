# File: tests/test_gcp_logger.py

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from src.gcp_logger import (
    ALERT,
    EMERGENCY,
    NOTICE,
    ConsoleColorFormatter,
    ContextAwareLogger,
    CustomCloudLoggingHandler,
    GCPLogger,
)


class TestHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def mock_google_cloud():
    with patch("google.cloud.logging.Client") as mock_logging, patch(
        "google.cloud.storage.Client"
    ) as mock_storage, patch("google.cloud.logging_v2.handlers.CloudLoggingHandler") as mock_cloud_handler:
        mock_logging_instance = MagicMock()
        mock_storage_instance = MagicMock()
        mock_cloud_handler_instance = MagicMock()
        mock_logging.return_value = mock_logging_instance
        mock_storage.return_value = mock_storage_instance
        mock_cloud_handler.return_value = mock_cloud_handler_instance
        yield mock_logging_instance, mock_storage_instance, mock_cloud_handler_instance


@pytest.fixture
def gcp_logger_instance(mock_google_cloud):
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}):
        return GCPLogger(environment="unittest", default_bucket="test-bucket")


@patch("google.cloud.logging.Client")
@patch("google.cloud.storage.Client")
def test_get_instance_id(mock_storage_client, mock_logging_client):
    with patch.dict(
        os.environ, {"GAE_INSTANCE": "gae-instance-123", "GOOGLE_CLOUD_PROJECT": "test-project"}, clear=True
    ):
        logger = GCPLogger(environment="production")
        assert logger.instance_id == "gae-instan"

    with patch.dict(
        os.environ,
        {"K_SERVICE": "run-service", "K_REVISION": "revision-123", "GOOGLE_CLOUD_PROJECT": "test-project"},
        clear=True,
    ):
        logger = GCPLogger(environment="production")
        assert logger.instance_id == "run-servi"

    with patch.dict(
        os.environ, {"FUNCTION_NAME": "cloud-function-name", "GOOGLE_CLOUD_PROJECT": "test-project"}, clear=True
    ):
        logger = GCPLogger(environment="production")
        assert logger.instance_id == "cloud-func"

    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=True):
        logger = GCPLogger(environment="production")
        assert logger.instance_id == "-"


def test_gcp_logger_initialization(gcp_logger_instance):
    assert gcp_logger_instance.environment == "unittest"
    assert gcp_logger_instance.default_bucket == "test-bucket"
    assert gcp_logger_instance.instance_id == "-"
    assert isinstance(gcp_logger_instance.logger, logging.LoggerAdapter)


@pytest.mark.parametrize("environment", ["localdev", "unittest", "production"])
def test_configure_handlers(environment, mock_google_cloud):
    logger = GCPLogger(environment=environment, default_bucket="test-bucket")
    assert logger.logger.logger.handlers

    if environment in ["localdev", "unittest"]:
        assert any(isinstance(h, logging.StreamHandler) for h in logger.logger.logger.handlers)
        assert any(isinstance(h.formatter, ConsoleColorFormatter) for h in logger.logger.logger.handlers)
    else:
        assert any(isinstance(h, CustomCloudLoggingHandler) for h in logger.logger.logger.handlers)


def test_console_color_formatter():
    formatter = ConsoleColorFormatter()
    record = logging.LogRecord("test_logger", logging.INFO, "test_file.py", 42, "Test message", (), None)
    record.trace_id = "test-trace"
    formatted = formatter.format(record)
    assert "INFO" in formatted
    assert "test_file:None:42" in formatted  # Updated this line
    assert "Test message" in formatted
    assert "test-trace" in formatted


def test_custom_cloud_logging_handler(mock_google_cloud):
    mock_logging, mock_storage, mock_cloud_handler = mock_google_cloud

    # Create a mock CloudLoggingHandler
    mock_cloud_handler_instance = MagicMock()
    mock_cloud_handler.return_value = mock_cloud_handler_instance

    # Set up the resource attribute
    mock_cloud_handler_instance.resource = MagicMock()
    mock_cloud_handler_instance.labels = {}
    mock_cloud_handler_instance.trace = None
    mock_cloud_handler_instance.span_id = None

    # Mock the background thread worker
    mock_worker = MagicMock()
    mock_worker.enqueue = MagicMock()

    # Create the CustomCloudLoggingHandler with the mock
    with patch("google.cloud.logging_v2.handlers.transports.background_thread._Worker", return_value=mock_worker):
        handler = CustomCloudLoggingHandler(mock_logging, default_bucket="test-bucket", environment="production")

    # Create a LogRecord and add all necessary attributes
    record = logging.LogRecord("test_logger", logging.INFO, "test_file.py", 42, "Test message", (), None)
    record._resource = MagicMock()
    record._labels = {}
    record._trace = None
    record._span_id = None
    record.trace = None
    record.span_id = None
    record._trace_sampled = None
    record._http_request = None
    record._source_location = None

    # Call emit
    handler.emit(record)

    # Verify that the worker's enqueue method was called
    mock_worker.enqueue.assert_called_once()

    # Verify that the custom attributes were added
    assert hasattr(record, "severity")
    assert record.severity == "INFO"
    assert hasattr(record, "instance_id")
    assert hasattr(record, "trace_id")
    assert hasattr(record, "span_id")
    assert hasattr(record, "environment")
    assert record.environment == "production"

    # Check if the message was formatted
    assert "test_file:None:42" in record.msg


def test_gcp_logger_adapter_custom_levels(gcp_logger_instance):
    with patch.object(gcp_logger_instance.logger.logger, "log") as mock_log:
        gcp_logger_instance.logger.notice("Test notice")
        mock_log.assert_called_with(NOTICE, "Test notice", extra={"instance_id": "-", "trace_id": "-", "span_id": "-"})

        gcp_logger_instance.logger.alert("Test alert")
        mock_log.assert_called_with(ALERT, "Test alert", extra={"instance_id": "-", "trace_id": "-", "span_id": "-"})

        gcp_logger_instance.logger.emergency("Test emergency")
        mock_log.assert_called_with(
            EMERGENCY, "Test emergency", extra={"instance_id": "-", "trace_id": "-", "span_id": "-"}
        )

        gcp_logger_instance.logger.success("Test success")
        mock_log.assert_called_with(
            logging.INFO, "SUCCESS: Test success", extra={"instance_id": "-", "trace_id": "-", "span_id": "-"}
        )


def test_context_aware_logger():
    logging.setLoggerClass(ContextAwareLogger)
    logger = logging.getLogger("test_context_aware")

    # Remove any existing handlers and set the level to INFO
    logger.handlers = []
    logger.setLevel(logging.INFO)

    # Add our test handler
    test_handler = TestHandler()
    logger.addHandler(test_handler)

    # Log a message
    logger.info("Test message")

    # Check if a record was logged
    assert len(test_handler.records) == 1, "Expected one log record, but got {len(test_handler.records)}"

    # Get the log record
    record = test_handler.records[0]

    # Check for custom attributes
    assert hasattr(record, "custom_filename"), "Expected 'custom_filename' attribute, but it wasn't present"
    assert hasattr(record, "custom_lineno"), "Expected 'custom_lineno' attribute, but it wasn't present"
    assert hasattr(record, "custom_func"), "Expected 'custom_func' attribute, but it wasn't present"

    # Check the values of custom attributes
    assert record.custom_filename.endswith("test_gcp_logger.py"), f"Unexpected filename: {record.custom_filename}"
    assert isinstance(
        record.custom_lineno, int
    ), f"Expected lineno to be an integer, but got {type(record.custom_lineno)}"
    assert record.custom_func == "test_context_aware_logger", f"Unexpected function name: {record.custom_func}"

    # Check the log message
    assert record.msg == "Test message", f"Unexpected log message: {record.msg}"


def test_large_log_message_handling(mock_google_cloud):
    mock_logging, mock_storage, mock_cloud_handler = mock_google_cloud

    # Mock the background thread worker
    mock_worker = MagicMock()
    mock_worker.enqueue = MagicMock()

    # Create the CustomCloudLoggingHandler with the mock
    with patch("google.cloud.logging_v2.handlers.transports.background_thread._Worker", return_value=mock_worker):
        handler = CustomCloudLoggingHandler(mock_logging, default_bucket="test-bucket", environment="production")

    large_message = "A" * (handler.MAX_LOG_SIZE + 1000)
    record = logging.LogRecord("test_logger", logging.INFO, "test_file.py", 42, large_message, (), None)

    # Add necessary attributes to the LogRecord
    record._resource = MagicMock()
    record._labels = {}
    record._trace = None
    record._span_id = None
    record._trace_sampled = None
    record._http_request = None
    record._source_location = None

    with patch.object(handler, "upload_large_log_to_gcs", return_value="gs://test-bucket/logs/test.log"):
        handler.emit(record)

    # Verify that the worker's enqueue method was called
    mock_worker.enqueue.assert_called_once()

    # Get the args passed to enqueue
    call_args = mock_worker.enqueue.call_args[0]
    assert len(call_args) >= 2, "Expected at least 2 arguments passed to enqueue"

    # The second argument should be the formatted message
    formatted_message = call_args[1]

    assert len(formatted_message.encode("utf-8")) <= handler.MAX_LOG_SIZE, "Message exceeds maximum size"
    assert "Message has been truncated" in formatted_message
    assert "gs://test-bucket/logs/test.log" in formatted_message
