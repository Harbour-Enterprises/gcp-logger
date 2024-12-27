# test_handlers.py
import logging
import sys

from gcp_logger.formatters import CloudFormatter
from gcp_logger.handlers import CloudHandler, LocalDevHandler


def test_handler_initialization(mock_cloud_client):
    """Test basic handler initialization."""
    cloud_handler = CloudHandler()
    local_handler = LocalDevHandler()

    assert isinstance(cloud_handler.formatter, CloudFormatter)
    assert isinstance(local_handler.formatter, logging.Formatter)
    assert cloud_handler.stream == sys.stdout
    assert local_handler.stream == sys.stdout
