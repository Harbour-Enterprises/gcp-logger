# File: tests/test_superlogs.py

from unittest.mock import MagicMock, patch

import pytest

from src.superlogs import SuperLogs, logger


@pytest.fixture
def mock_google_cloud():
    with patch("google.cloud.logging.Client") as mock_logging, patch("google.cloud.storage.Client") as mock_storage:
        mock_logging.return_value.logger.return_value = MagicMock()
        mock_storage.return_value.bucket.return_value.blob.return_value = MagicMock()
        yield mock_storage


@pytest.fixture
def superlogs_instance(mock_google_cloud):
    return SuperLogs(environment="unittest", default_bucket="test-bucket")


@pytest.mark.parametrize(
    "env_var, expected_id",
    [
        ({"GAE_INSTANCE": "gae-instance-123"}, "gae-instan"),
        ({"K_SERVICE": "run-service", "K_REVISION": "revision-123"}, "run-servi"),
        ({"FUNCTION_NAME": "cloud-function-name"}, "cloud-func"),
        ({}, "-"),
    ],
)
def test_get_instance_id(env_var, expected_id, mock_google_cloud):
    with patch.dict("os.environ", env_var, clear=True):
        superlogs = SuperLogs(environment="production", default_bucket="test-bucket")
        assert superlogs.instance_id == expected_id


def test_init(superlogs_instance):
    assert superlogs_instance is not None
    assert superlogs_instance.environment == "unittest"
    assert superlogs_instance.default_bucket == "test-bucket"
    assert superlogs_instance.instance_id == "-"  # Default value for non-cloud environments


@pytest.mark.parametrize("environment", ["localdev", "unittest", "production"])
def test_setup_logging(environment, mock_google_cloud):
    superlogs = SuperLogs(environment=environment, default_bucket="test-bucket")
    assert logger._core.handlers  # Check that handlers were added
    assert "ALERT" in logger._core.levels
    assert "EMERGENCY" in logger._core.levels


def test_save_large_log_to_gcs(mock_google_cloud, superlogs_instance):
    mock_blob = mock_google_cloud.return_value.bucket.return_value.blob.return_value

    result = superlogs_instance.save_large_log_to_gcs(
        "Large log message", "instance", "trace", "span", "process", "thread"
    )

    assert result.startswith("gs://test-bucket/logs/")
    mock_blob.upload_from_string.assert_called_once_with("Large log message")


def test_google_cloud_log_sink(superlogs_instance):
    mock_message = MagicMock()
    mock_message.record = {
        "level": {"name": "INFO"},
        "time": MagicMock(),
        "extra": {"instance_id": "test", "trace_id": "trace", "span_id": "span"},
        "process": {"id": 1},
        "thread": {"id": 1},
        "name": "test_logger",
        "function": "test_func",
        "line": 10,
        "message": "Test message",
    }

    superlogs_instance.google_cloud_log_sink(mock_message)

    superlogs_instance.cloud_logger.log_struct.assert_called_once()
    log_entry = superlogs_instance.cloud_logger.log_struct.call_args[0][0]
    assert log_entry["level"] == "INFO"
    assert "Test message" in log_entry["message"]


def test_custom_log_levels():
    assert "ALERT" in logger._core.levels
    assert "EMERGENCY" in logger._core.levels

    with patch.object(logger, "log") as mock_log:
        logger.alert("Test alert")
        mock_log.assert_called_with("ALERT", "Test alert")

        logger.emergency("Test emergency")
        mock_log.assert_called_with("EMERGENCY", "Test emergency")
