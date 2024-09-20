# File: tests/test_internal_logger.py

from unittest.mock import patch

import pytest

from src.gcp_logger.internal_logger import InternalLogger, internal_debug


@pytest.fixture
def internal_logger():
    return InternalLogger.get_instance()


def test_internal_logger_singleton():
    logger1 = InternalLogger.get_instance()
    logger2 = InternalLogger.get_instance()
    assert logger1 is logger2


def test_internal_logger_configure(internal_logger):
    with patch.object(internal_logger.logger, "setLevel") as mock_set_level:
        internal_logger.configure(debug_internal=True)
        mock_set_level.assert_called_with(10)  # DEBUG level

        internal_logger.configure(debug_internal=False)
        mock_set_level.assert_called_with(20)  # INFO level


def test_internal_logger_debug(internal_logger):
    with patch.object(internal_logger.logger, "debug") as mock_debug:
        internal_logger.debug("Test debug message")
        mock_debug.assert_called_with("Test debug message")


def test_internal_debug():
    with patch("src.gcp_logger.internal_logger.internal_logger.debug") as mock_debug:
        internal_debug("Test debug message")
        mock_debug.assert_called_with("Test debug message")
