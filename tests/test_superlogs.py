import unittest
from unittest.mock import patch

from src.superlogs import SuperLogs


class TestSuperLogs(unittest.TestCase):
    def setUp(self):
        self.superlogs = SuperLogs(environment="unittest", default_bucket="test-bucket")

    @patch("superlogs.cloud_logging.Client")
    def test_init(self, mock_client):
        self.assertIsNotNone(self.superlogs)
        mock_client.assert_called_once()

    def test_google_cloud_log_format(self):
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
        self.assertIn("test | trace | span", formatted)
        self.assertIn("INFO", formatted)
        self.assertIn("Test message", formatted)

    # Add more tests for other methods...


if __name__ == "__main__":
    unittest.main()
