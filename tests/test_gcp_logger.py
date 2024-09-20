# File: tests/test_gcp_logger.py

from unittest.mock import patch

import pytest

from src.gcp_logger import GCPLogger, GCPLoggerAdapter
from src.gcp_logger.custom_logging_handler import CustomCloudLoggingHandler


@pytest.fixture
def gcp_logger():
    return GCPLogger(environment="unittest", logger_name="test_logger")


def test_gcp_logger_initialization(gcp_logger):
    assert isinstance(gcp_logger.logger, GCPLoggerAdapter)
    assert gcp_logger.environment == "unittest"
    assert gcp_logger.logger_name == "test_logger"


def test_get_instance_id():
    with patch.dict("os.environ", {"GAE_INSTANCE": "test-instance"}):
        assert GCPLogger.get_instance_id() == "test-insta"

    with patch.dict("os.environ", {"K_SERVICE": "test-service", "K_REVISION": "rev1"}):
        assert GCPLogger.get_instance_id() == "test-serv"

    with patch.dict("os.environ", {"FUNCTION_NAME": "test-function"}):
        assert GCPLogger.get_instance_id() == "test-funct"

    with patch.dict("os.environ", clear=True):
        assert GCPLogger.get_instance_id() == "-"


def test_get_trace_and_span_ids():
    trace_header = "105445aa7843bc8bf206b12000100000/1;o=1"
    trace_id, span_id = GCPLogger.get_trace_and_span_ids(trace_header)
    assert trace_id == "105445aa7843bc8bf206b12000100000"
    assert span_id == "1"

    trace_id, span_id = GCPLogger.get_trace_and_span_ids()
    assert len(trace_id) == 36  # UUID4 length
    assert span_id == "-"


def test_update_trace_context(gcp_logger):
    trace_header = "105445aa7843bc8bf206b12000100000/1;o=1"
    gcp_logger.update_trace_context(trace_header)
    assert gcp_logger.logger.extra["trace_id"] == "105445aa7843bc8bf206b12000100000"
    assert gcp_logger.logger.extra["span_id"] == "1"


@patch("google.cloud.logging.Client")
def test_configure_handlers_production(mock_client, gcp_logger):
    gcp_logger.environment = "production"
    gcp_logger.configure_handlers()
    assert len(gcp_logger._logger.handlers) == 1
    assert isinstance(gcp_logger._logger.handlers[0], CustomCloudLoggingHandler)
