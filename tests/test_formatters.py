# test_formatters.py
import json

from gcp_logger.formatters import CloudFormatter


def test_basic_format(sample_log_record):
    """Test basic log formatting."""
    formatter = CloudFormatter()
    formatted = formatter.format(sample_log_record)
    data = json.loads(formatted)

    assert "severity" in data
    assert "message" in data
    assert "timestamp" in data
    assert "logging.googleapis.com/sourceLocation" in data
