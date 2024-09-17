# File: tests/test_gcp_logger_performance.py

from unittest.mock import MagicMock, patch

import pytest

from src.gcp_logger import ALERT, EMERGENCY, NOTICE, GCPLogger


@pytest.fixture
def gcp_logger_benchmark():
    with patch("google.cloud.logging.Client") as mock_logging_client, patch(
        "google.cloud.storage.Client"
    ) as mock_storage_client, patch("src.gcp_logger.CustomCloudLoggingHandler") as mock_cloud_handler:

        # Mock the logging client
        mock_logging_client.return_value = MagicMock()

        # Mock the storage client
        mock_storage_client.return_value = MagicMock()
        mock_storage_client.return_value.bucket.return_value = MagicMock()
        mock_storage_client.return_value.bucket.return_value.blob.return_value = MagicMock()

        # Mock the CustomCloudLoggingHandler
        mock_cloud_handler.return_value = MagicMock()

        # Initialize GCPLogger in a local environment
        logger = GCPLogger(environment="localdev", default_bucket="test-bucket")
        return logger.get_logger()


@pytest.mark.performance
def test_logging_performance(benchmark, gcp_logger_benchmark):
    """
    Benchmark the performance of logging a single message.
    """
    logger = gcp_logger_benchmark

    # Define the logging action
    def log_action():
        logger.info("Performance test log message", extra={"trace_id": "test-trace", "span_id": "test-span"})

    # Benchmark the logging action
    benchmark(log_action)


@pytest.mark.performance
def test_bulk_logging_performance(benchmark, gcp_logger_benchmark):
    """
    Benchmark the performance of logging multiple messages.
    """
    logger = gcp_logger_benchmark
    num_messages = 1000

    # Define the bulk logging action
    def bulk_log_action():
        for i in range(num_messages):
            logger.debug(
                f"Bulk performance test log message {i}", extra={"trace_id": f"trace-{i}", "span_id": f"span-{i}"}
            )

    # Benchmark the bulk logging action
    benchmark(bulk_log_action)


@pytest.mark.performance
def test_concurrent_logging_performance(benchmark, gcp_logger_benchmark):
    """
    Benchmark the performance of logging from multiple threads concurrently.
    """
    import threading

    logger = gcp_logger_benchmark
    num_threads = 10
    logs_per_thread = 1000

    def thread_logging():
        for i in range(logs_per_thread):
            logger.info(f"Concurrent log message {i}", extra={"trace_id": f"trace-{i}", "span_id": f"span-{i}"})

    def concurrent_log_action():
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=thread_logging)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

    # Benchmark the concurrent logging action
    benchmark(concurrent_log_action)


@pytest.mark.performance
def test_custom_levels_performance(benchmark, gcp_logger_benchmark):
    """
    Benchmark the performance of logging with custom log levels.
    """
    logger = gcp_logger_benchmark

    def custom_log_action():
        logger.log(NOTICE, "Notice level test message")
        logger.log(ALERT, "Alert level test message")
        logger.log(EMERGENCY, "Emergency level test message")
        logger.success("Success test message")

    # Benchmark the custom logging action
    benchmark(custom_log_action)
