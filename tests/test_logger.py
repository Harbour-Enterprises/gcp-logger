# test_logger.py
import logging

import pytest

from gcp_logger import GCPLogger
from gcp_logger.custom_logger import CustomLogger
from gcp_logger.handlers import CloudHandler, LocalDevHandler


@pytest.fixture
def clean_logging():
    """Ensure clean logging state before and after each test."""
    root = logging.getLogger()
    root.handlers.clear()
    yield
    root.handlers.clear()
    logging.setLoggerClass(logging.Logger)


def test_logger_initialization():
    """Test GCPLogger initialization."""
    logger = GCPLogger(environment="unittest")
    assert logger.environment == "unittest"
    assert isinstance(logger.logger, CustomLogger)
    assert logger.logger.level == logging.DEBUG


def test_environment_handler_selection(clean_logging):
    """Test handler selection based on environment."""
    # Test development environment
    dev_logger = GCPLogger(environment="localdev")
    dev_handler = dev_logger.logger.handlers[0]

    # Test production environment
    logging.getLogger().handlers.clear()
    prod_logger = GCPLogger(environment="production")
    prod_handler = prod_logger.logger.handlers[0]

    # Verify handler types
    assert isinstance(dev_handler, LocalDevHandler), f"Expected LocalDevHandler but got {type(dev_handler)}"
    assert isinstance(prod_handler, CloudHandler), f"Expected CloudHandler but got {type(prod_handler)}"
