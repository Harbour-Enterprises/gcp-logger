# File: tests/test_custom_cloud_logging_handler.py

import logging
from unittest.mock import MagicMock, patch

import pytest
from google.cloud import logging as cloud_logging

from src.gcp_logger.custom_logging_handler import CustomCloudLoggingHandler


@pytest.fixture
def mock_cloud_logging_client():
    """
    Fixture to create a mock of the Google Cloud Logging client.
    Adds the 'project' attribute to avoid AttributeError during handler initialization.
    """
    mock_client = MagicMock(spec=cloud_logging.Client)
    mock_client.project = "test-project"  # Mock the 'project' attribute
    return mock_client


@pytest.fixture
def custom_handler(mock_cloud_logging_client):
    """
    Fixture to initialize the CustomCloudLoggingHandler with the mocked client.
    """
    return CustomCloudLoggingHandler(
        mock_cloud_logging_client,
        default_bucket="test-bucket",
        environment="testing",  # Optional: Provide an environment if needed
    )


def test_custom_handler_initialization(custom_handler):
    """
    Test to verify that the CustomCloudLoggingHandler initializes correctly.
    Checks if the default bucket is set and AsyncUploader is initialized.
    """
    assert custom_handler.default_bucket == "test-bucket", "Default bucket not set correctly."
    assert custom_handler.async_uploader is not None, "AsyncUploader was not initialized."


def test_custom_handler_initialization_no_bucket(mock_cloud_logging_client):
    """
    Test to verify that AsyncUploader is not initialized when no default_bucket is provided.
    """
    handler = CustomCloudLoggingHandler(mock_cloud_logging_client, default_bucket=None, environment="testing")
    assert handler.default_bucket is None, "Default bucket should be None."
    assert handler.async_uploader is None, "AsyncUploader should not be initialized when no default_bucket is provided."


def test_custom_handler_emit_info(custom_handler):
    """
    Test the emit method for an INFO level log record.
    Verifies that the severity is set correctly and that emit calls the parent class's emit method.
    """
    with patch.object(CustomCloudLoggingHandler, "add_custom_attributes") as mock_add_attrs, patch.object(
        CustomCloudLoggingHandler, "format_log_message", return_value="Formatted message"
    ) as mock_format, patch.object(
        CustomCloudLoggingHandler, "upload_large_log_to_gcs", return_value=None
    ) as mock_upload, patch.object(
        cloud_logging.handlers.CloudLoggingHandler, "emit"
    ) as mock_parent_emit:

        record = MagicMock(spec=logging.LogRecord)
        record.levelno = logging.INFO
        record.getMessage.return_value = "Test message"

        custom_handler.emit(record)

        # Verify severity is set correctly
        assert record.severity == "INFO", "Severity was not set to 'INFO'."

        # Verify custom attributes are added
        mock_add_attrs.assert_called_once_with(record)

        # Verify the log message is formatted
        mock_format.assert_called_once_with(record)

        # Since the message is short, upload_large_log_to_gcs should not be called
        mock_upload.assert_not_called()

        # Verify that the parent emit method was called with the modified record
        mock_parent_emit.assert_called_once_with(record)


def test_custom_handler_emit_large_log(custom_handler):
    """
    Test the emit method for a log record that exceeds MAX_LOG_SIZE.
    Verifies that the log is uploaded to GCS and the message is truncated.
    """
    large_message = "A" * (CustomCloudLoggingHandler.MAX_LOG_SIZE + 1)
    gcs_uri = "gs://test-bucket/logs/large_log.log"

    with patch.object(CustomCloudLoggingHandler, "add_custom_attributes") as mock_add_attrs, patch.object(
        CustomCloudLoggingHandler, "format_log_message", return_value=large_message
    ) as mock_format, patch.object(
        CustomCloudLoggingHandler, "upload_large_log_to_gcs", return_value=gcs_uri
    ) as mock_upload, patch.object(
        cloud_logging.handlers.CloudLoggingHandler, "emit"
    ) as mock_parent_emit:

        record = MagicMock(spec=logging.LogRecord)
        record.levelno = logging.INFO
        record.getMessage.return_value = large_message

        custom_handler.emit(record)

        # Verify severity is set correctly
        assert record.severity == "INFO", "Severity was not set to 'INFO'."

        # Verify custom attributes are added
        mock_add_attrs.assert_called_once_with(record)

        # Verify the log message is formatted
        mock_format.assert_called_once_with(record)

        # Verify the large log is uploaded to GCS
        mock_upload.assert_called_once_with(large_message, record.__dict__)

        # Calculate expected truncated message
        truncation_notice = "... [truncated]\nMessage has been truncated. Full log at: " + gcs_uri
        max_truncated_length = CustomCloudLoggingHandler.MAX_LOG_SIZE - len(truncation_notice)
        truncated_message = large_message[:max_truncated_length]

        expected_truncated_message = f"{truncated_message}{truncation_notice}"

        # Verify that the record's message is truncated and includes the GCS URI
        assert record.msg == expected_truncated_message, "Log message was not truncated correctly."

        # Verify that the parent emit method was called with the modified record
        mock_parent_emit.assert_called_once_with(record)


def test_custom_handler_emit_without_async_uploader(custom_handler, mock_cloud_logging_client):
    """
    Test the emit method when AsyncUploader is not initialized (no default_bucket).
    Ensures that large logs are not uploaded to GCS.
    """
    # Create a handler without a default_bucket
    handler = CustomCloudLoggingHandler(mock_cloud_logging_client, default_bucket=None, environment="testing")

    large_message = "A" * (CustomCloudLoggingHandler.MAX_LOG_SIZE + 1)

    with patch.object(handler, "add_custom_attributes") as mock_add_attrs, patch.object(
        handler, "format_log_message", return_value=large_message
    ) as mock_format, patch.object(handler, "upload_large_log_to_gcs") as mock_upload, patch.object(
        cloud_logging.handlers.CloudLoggingHandler, "emit"
    ) as mock_parent_emit:

        record = MagicMock(spec=logging.LogRecord)
        record.levelno = logging.INFO
        record.getMessage.return_value = large_message

        handler.emit(record)

        # Verify severity is set correctly
        assert record.severity == "INFO", "Severity was not set to 'INFO'."

        # Verify custom attributes are added
        mock_add_attrs.assert_called_once_with(record)

        # Verify the log message is formatted
        mock_format.assert_called_once_with(record)

        # Since AsyncUploader is not initialized, upload_large_log_to_gcs should not be called
        mock_upload.assert_not_called()

        # Verify that the record's message is still the large message (not truncated)
        assert record.msg == large_message, "Log message should not be truncated when AsyncUploader is not initialized."

        # Verify that the parent emit method was called with the modified record
        mock_parent_emit.assert_called_once_with(record)


def test_custom_handler_shutdown(custom_handler):
    """
    Test the shutdown method to ensure that AsyncUploader is shut down gracefully.
    """
    with patch.object(custom_handler.async_uploader, "shutdown") as mock_shutdown:
        custom_handler.shutdown()
        mock_shutdown.assert_called_once()


def test_custom_handler_add_custom_attributes(custom_handler):
    """
    Test the add_custom_attributes method to ensure that custom attributes are added to the log record.
    """
    record = MagicMock(spec=logging.LogRecord)
    record.filename = "test_file.py"
    record.funcName = "test_function"
    record.lineno = 42

    # Set initial attributes that might be missing
    del record.instance_id
    del record.trace_id
    del record.span_id
    del record.custom_filename
    del record.custom_func
    del record.custom_lineno

    custom_handler.environment = "testing"

    custom_handler.add_custom_attributes(record)

    # Verify that custom attributes are set correctly
    assert record.instance_id == "-", "instance_id should default to '-'."
    assert record.trace_id == "-", "trace_id should default to '-'."
    assert record.span_id == "-", "span_id should default to '-'."
    assert record.environment == "testing", "environment should be set to 'testing'."
    assert record.filename == "test_file", "filename should be stripped and without extension."
    assert record.funcName == "test_function", "funcName should be set correctly."
    assert record.lineno == 42, "lineno should be set correctly."


def test_custom_handler_format_log_message(custom_handler):
    """
    Test the format_log_message method to ensure that the log message is formatted correctly.
    """
    record = MagicMock(spec=logging.LogRecord)
    record.instance_id = "i-1234567890abcdef0"
    record.trace_id = "trace-123"
    record.span_id = "span-456"
    record.process = 1234
    record.thread = 5678
    record.levelno = logging.INFO
    record.levelname = "INFO"
    record.filename = "test_file"
    record.funcName = "test_function"
    record.lineno = 42
    record.getMessage.return_value = "Test log message."

    formatted_message = custom_handler.format_log_message(record)

    expected_format = (
        f"{record.instance_id} | {record.trace_id} | {record.span_id} | "
        f"{record.process} | {record.thread} | "
        f"{record.levelname:<8} | "
        f"{record.filename}:{record.funcName}:{record.lineno} - "
        f"{record.getMessage.return_value}"
    )

    assert formatted_message == expected_format, "Log message was not formatted correctly."


# def test_custom_handler_upload_large_log_to_gcs(custom_handler):
#     """
#     Test the upload_large_log_to_gcs method to ensure that large logs are uploaded correctly.
#     """
#     with patch.object(custom_handler.async_uploader, "upload_data") as mock_upload_data:
#         log_message = "A" * 300000  # Example large log message
#         record_dict = {
#             "instance_id": "i-1234567890abcdef0",
#             "trace_id": "trace-123",
#             "span_id": "span-456",
#             "process": 1234,
#             "thread": 5678,
#         }

#         gcs_uri = custom_handler.upload_large_log_to_gcs(log_message, record_dict)

#         # Verify that upload_data was called with correct parameters
#         mock_upload_data.assert_called_once_with(
#             data=log_message.encode("utf-8"), object_name="logs/1234_5678_trace-123_span-456_i-1234567890abcdef0.log"
#         )

#         # Verify that the GCS URI is returned correctly
#         expected_gcs_uri = f"gs://test-bucket/logs/1234_5678_trace-123_span-456_i-1234567890abcdef0.log"
#         assert gcs_uri == expected_gcs_uri, "GCS URI was not constructed correctly."
