# test_logger.py
import logging
import os

import pytest

from gcp_logger import GCPLogger, LogEnvironment
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


def test_logger_initialization_with_enum():
    """Test GCPLogger initialization with LogEnvironment enum."""
    logger = GCPLogger(LogEnvironment.TEST)
    assert logger.environment == LogEnvironment.TEST
    assert isinstance(logger.logger, CustomLogger)
    assert logger.logger.level == logging.DEBUG


def test_logger_initialization_with_string():
    """Test GCPLogger initialization with string-based environment."""
    logger = GCPLogger(environment="unittest")
    assert logger.environment == LogEnvironment.TEST
    assert isinstance(logger.logger, CustomLogger)
    assert logger.logger.level == logging.DEBUG


def test_environment_string_mapping():
    """Test string to LogEnvironment mapping."""
    # Test LOCAL mappings
    assert GCPLogger("local").environment == LogEnvironment.LOCAL
    assert GCPLogger("dev").environment == LogEnvironment.LOCAL
    assert GCPLogger("development").environment == LogEnvironment.LOCAL
    assert GCPLogger("localdev").environment == LogEnvironment.LOCAL

    # Test GCP mappings
    assert GCPLogger("gcp").environment == LogEnvironment.GCP
    assert GCPLogger("prod").environment == LogEnvironment.GCP
    assert GCPLogger("production").environment == LogEnvironment.GCP
    assert GCPLogger("staging").environment == LogEnvironment.GCP

    # Test TEST mappings
    assert GCPLogger("test").environment == LogEnvironment.TEST
    assert GCPLogger("testing").environment == LogEnvironment.TEST
    assert GCPLogger("unittest").environment == LogEnvironment.TEST


def test_environment_case_insensitivity():
    """Test case-insensitive environment string handling."""
    assert GCPLogger("PROD").environment == LogEnvironment.GCP
    assert GCPLogger("Dev").environment == LogEnvironment.LOCAL
    assert GCPLogger("TEST").environment == LogEnvironment.TEST


def test_environment_whitespace_handling():
    """Test environment string whitespace handling."""
    assert GCPLogger(" prod ").environment == LogEnvironment.GCP
    assert GCPLogger("\tdev\n").environment == LogEnvironment.LOCAL


def test_environment_handler_selection(clean_logging):
    """Test handler selection based on environment."""
    # Test with enum
    local_logger = GCPLogger(LogEnvironment.LOCAL)
    local_handler = local_logger.logger.handlers[0]
    assert isinstance(local_handler, LocalDevHandler)

    logging.getLogger().handlers.clear()
    gcp_logger = GCPLogger(LogEnvironment.GCP)
    gcp_handler = gcp_logger.logger.handlers[0]
    assert isinstance(gcp_handler, CloudHandler)

    # Test with strings (backward compatibility)
    logging.getLogger().handlers.clear()
    dev_logger = GCPLogger("development")
    dev_handler = dev_logger.logger.handlers[0]
    assert isinstance(dev_handler, LocalDevHandler)

    logging.getLogger().handlers.clear()
    prod_logger = GCPLogger("production")
    prod_handler = prod_logger.logger.handlers[0]
    assert isinstance(prod_handler, CloudHandler)


def test_environment_variable_fallback(clean_logging):
    """Test environment variable fallback behavior."""
    # Test with environment variable
    os.environ["ENVIRONMENT"] = "production"
    env_logger = GCPLogger()
    assert env_logger.environment == LogEnvironment.GCP
    env_handler = env_logger.logger.handlers[0]
    assert isinstance(env_handler, CloudHandler)

    # Test default when no environment specified
    del os.environ["ENVIRONMENT"]
    default_logger = GCPLogger()
    assert default_logger.environment == LogEnvironment.LOCAL
    default_handler = default_logger.logger.handlers[0]
    assert isinstance(default_handler, LocalDevHandler)


def test_unknown_environment_handling():
    """Test handling of unknown environment strings."""
    # Unknown environments should default to LOCAL
    unknown_logger = GCPLogger("unknown_env")
    assert unknown_logger.environment == LogEnvironment.LOCAL
    assert isinstance(unknown_logger.logger.handlers[0], LocalDevHandler)


def test_none_environment_handling():
    """Test handling of None environment."""
    # None should trigger environment variable check
    none_logger = GCPLogger(None)
    assert none_logger.environment == LogEnvironment.LOCAL  # Assumes no ENVIRONMENT var set
    assert isinstance(none_logger.logger.handlers[0], LocalDevHandler)
