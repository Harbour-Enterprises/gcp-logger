# test_custom_logger.py
import logging

import pytest

from gcp_logger.custom_logger import CustomLogger


@pytest.fixture
def custom_logger():
    """Create a CustomLogger instance."""
    return CustomLogger("test_logger")


def test_custom_logger_initialization(custom_logger):
    """Test basic logger initialization."""
    assert isinstance(custom_logger, CustomLogger)
    assert custom_logger.name == "test_logger"


def test_custom_log_levels():
    """Test custom log levels are properly registered."""
    assert hasattr(logging, "NOTICE")
    assert hasattr(logging, "ALERT")
    assert hasattr(logging, "EMERGENCY")
    assert logging.getLevelName(CustomLogger.NOTICE) == "NOTICE"
    assert logging.getLevelName(CustomLogger.ALERT) == "ALERT"
    assert logging.getLevelName(CustomLogger.EMERGENCY) == "EMERGENCY"
