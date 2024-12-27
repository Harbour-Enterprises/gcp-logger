# conftest.py
import logging
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_logging():
    """Clean up logging configuration before and after each test."""
    root = logging.getLogger()
    root.handlers.clear()
    yield
    root.handlers.clear()
    logging.setLogRecordFactory(logging.LogRecord)


@pytest.fixture
def mock_cloud_client():
    """Mock Google Cloud Logging client."""
    with patch("google.cloud.logging.Client") as mock_client:
        mock_client.return_value.logger.return_value = MagicMock()
        yield mock_client


@pytest.fixture
def sample_log_record():
    """Create a minimal sample LogRecord."""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
        func="test_function",
    )
    record.trace_id = "-"
    record.span_id = "-"
    record.instance_id = "test-instance"
    return record
