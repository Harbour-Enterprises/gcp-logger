# File: tests/test_gcp_logger_performance.py

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.gcp_logger import GCPLogger


@pytest.fixture
def gcp_logger_benchmark():
    with patch("google.cloud.logging.Client") as mock_logging_client, patch(
        "google.cloud.storage.Client"
    ) as mock_storage_client, patch("google.cloud.logging.handlers.CloudLoggingHandler") as mock_cloud_handler:

        # Mock the logging client and its methods
        mock_logging_instance = MagicMock()
        mock_logging_client.return_value = mock_logging_instance
        mock_logging_instance.logger.return_value = MagicMock()

        # Mock the storage client and its methods
        mock_storage_instance = MagicMock()
        mock_storage_client.return_value = mock_storage_instance
        mock_storage_instance.bucket.return_value = MagicMock()
        mock_storage_instance.bucket.return_value.blob.return_value = MagicMock()

        # Mock the CloudLoggingHandler
        mock_cloud_handler_instance = MagicMock()
        mock_cloud_handler.return_value = mock_cloud_handler_instance

        # Initialize GCPLogger in a local environment to use StreamHandler
        logger = GCPLogger(environment="localdev", default_bucket="test-bucket")
        return logger


@pytest.mark.performance
def test_logging_performance(benchmark, gcp_logger_benchmark):
    """
    Benchmark the performance of logging a single message.
    """

    logger = gcp_logger_benchmark

    # Define the logging action
    def log_action():
        logger.log(logging.INFO, "Performance test log message", trace_id="test-trace", span_id="test-span")

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
            logger.log(
                logging.DEBUG, f"Bulk performance test log message {i}", trace_id=f"trace-{i}", span_id=f"span-{i}"
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
            logger.log(logging.INFO, f"Concurrent log message {i}", trace_id=f"trace-{i}", span_id=f"span-{i}")

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
