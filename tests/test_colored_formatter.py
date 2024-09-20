# File: tests/test_colored_formatter.py

import logging

import pytest

from src.gcp_logger import ColoredFormatter


@pytest.fixture
def colored_formatter():
    return ColoredFormatter()


def test_colored_formatter_initialization(colored_formatter):
    assert colored_formatter.color_codes is not None


def test_colored_formatter_format(colored_formatter):
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=1, msg="Test message", args=(), exc_info=None
    )
    formatted = colored_formatter.format(record)
    assert "Test message" in formatted
    assert "\033[" in formatted  # Check for ANSI color codes
