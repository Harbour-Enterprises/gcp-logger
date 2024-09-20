# File: tests/test_context_aware_logger.py

import logging
from unittest.mock import ANY, MagicMock, call, patch

import pytest

from src.gcp_logger.context_aware_logger import ContextAwareLogger
from src.gcp_logger.levels import ALERT, EMERGENCY, NOTICE


@pytest.fixture
def context_aware_logger():
    """
    Fixture to create an instance of ContextAwareLogger.
    """
    return ContextAwareLogger("test_logger")


def test_context_aware_logger_custom_levels(context_aware_logger):
    """
    Test that the ContextAwareLogger correctly handles custom logging levels by
    calling the underlying _log method with appropriate level numbers and messages.
    """
    with patch.object(logging.Logger, "_log") as mock_log:
        context_aware_logger.notice("Notice message")
        context_aware_logger.alert("Alert message")
        context_aware_logger.emergency("Emergency message")

        # Define the expected calls including the 'stacklevel' argument
        expected_calls = [
            call(NOTICE, "Notice message", (), None, ANY, False, 1),
            call(ALERT, "Alert message", (), None, ANY, False, 1),
            call(EMERGENCY, "Emergency message", (), None, ANY, False, 1),
        ]

        # Assert that _log was called with the expected arguments in order
        mock_log.assert_has_calls(expected_calls, any_order=False)


def test_context_aware_logger_success(context_aware_logger):
    """
    Test that the ContextAwareLogger's success method correctly formats the message
    and calls the info method with the updated message.
    """
    with patch.object(logging.Logger, "info") as mock_info:
        context_aware_logger.success("Success message")

        # Ensure that info was called once with the correctly formatted message
        mock_info.assert_called_once_with("SUCCESS: Success message")
