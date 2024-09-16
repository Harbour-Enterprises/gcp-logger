# File: tests/conftest.py

import logging

import pytest


@pytest.fixture(autouse=True)
def reset_gcp_logger():
    """
    Automatically reset the 'gcp_logger' logger before each test to prevent handler accumulation.
    """
    logger = logging.getLogger("gcp_logger")
    logger.handlers = []
    logger.propagate = False
    yield
    logger.handlers = []
