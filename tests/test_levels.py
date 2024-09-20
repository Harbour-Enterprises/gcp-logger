# File: tests/test_levels.py

import logging

import pytest

from src.gcp_logger.levels import ALERT, EMERGENCY, NOTICE


def test_custom_levels():
    """
    Test to ensure that custom logging levels are defined correctly.
    """
    assert NOTICE == 300, f"NOTICE level should be 300, got {NOTICE}"
    assert ALERT == 700, f"ALERT level should be 700, got {ALERT}"
    assert EMERGENCY == 800, f"EMERGENCY level should be 800, got {EMERGENCY}"


def test_level_names():
    """
    Test to ensure that logging module recognizes custom level names.
    """
    assert logging.getLevelName(NOTICE) == "NOTICE", f"Expected 'NOTICE', got '{logging.getLevelName(NOTICE)}'"
    assert logging.getLevelName(ALERT) == "ALERT", f"Expected 'ALERT', got '{logging.getLevelName(ALERT)}'"
    assert (
        logging.getLevelName(EMERGENCY) == "EMERGENCY"
    ), f"Expected 'EMERGENCY', got '{logging.getLevelName(EMERGENCY)}'"


@pytest.mark.parametrize(
    "level, message",
    [
        (NOTICE, "Notice message"),
        (ALERT, "Alert message"),
        (EMERGENCY, "Emergency message"),
    ],
)
def test_logging_with_custom_levels(caplog, level, message):
    """
    Parameterized test logging messages with custom levels using pytest's caplog fixture.
    Verifies that messages are logged correctly at NOTICE, ALERT, and EMERGENCY levels.
    """
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)  # Set to lowest level to capture all logs
    logger.propagate = True  # Ensure logs propagate to root and are captured by caplog
    logger.handlers = []  # Remove any existing handlers to prevent duplication

    with caplog.at_level(level, logger="test_logger"):
        logger.log(level, message)

    # Check if the message was captured
    assert any(message in record.message for record in caplog.records), f"{message} not captured for level {level}."
    caplog.clear()
