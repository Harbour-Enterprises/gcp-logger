# File: examples/basic_example.py

import time

from gcp_logger.logger import GCPLogger


def main():
    """
    Demonstrates the usage of GCPLogger for logging within an application,
    including handling large log messages that exceed the maximum log size.
    """
    # Initialize GCPLogger
    gcp_logger = GCPLogger(
        environment="localdev",
        default_bucket="my-gcs-bucket",
        debug_logs=True,  # Set to False in production
    )
    logger = gcp_logger.get_logger()

    try:
        # Simulate application logging
        for i in range(1, 101):
            logger.debug(f"Debugging item {i}")
            logger.info(f"Processing item {i}")
            if i % 10 == 0:
                logger.notice(f"Notice at item {i}")
            if i % 15 == 0:
                logger.warning(f"Warning at item {i}")
            if i % 20 == 0:
                logger.error(f"Error at item {i}")
            if i % 25 == 0:
                logger.critical(f"Critical issue at item {i}")
            if i % 30 == 0:
                logger.alert(f"Alert! Issue at item {i}")
            if i % 35 == 0:
                logger.emergency(f"Emergency! Critical issue at item {i}")
            if i % 40 == 0:
                logger.success(f"Successfully processed item {i}")

            # Introduce a large log message at i == 50
            if i == 50:
                large_message = "A" * (256 * 1024 + 1)  # 256KB + 1 byte to exceed the limit
                logger.info(f"Logging a large message:\n{large_message}")

            time.sleep(0.05)  # Simulate work

    finally:
        # Ensure graceful shutdown
        gcp_logger.shutdown()
        print("Logger has been shut down gracefully.")


if __name__ == "__main__":
    main()
