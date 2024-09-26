# File: gcp_logger/logger.py

import logging
import os
import sys
from typing import Optional
from uuid import uuid4

from google.cloud import logging as cloud_logging

from .colored_formatter import ColoredFormatter
from .context_aware_logger import ContextAwareLogger
from .custom_logging_handler import CustomCloudLoggingHandler
from .internal_logger import internal_debug, internal_logger
from .logger_adapter import GCPLoggerAdapter


class GCPLogger:
    """
    A logger class that sets up logging with custom handlers and formatters,
    supporting both local development and production environments.
    """

    def __init__(
        self,
        environment: str,
        default_bucket: str = None,
        logger_name: str = "gcp-logger",
        debug_logs: bool = False,
    ):
        """
        Initializes the GCPLogger.

        Args:
            environment (str): The deployment environment (e.g., 'production', 'localdev').
            default_bucket (str, optional): The default GCS bucket for large logs.
            logger_name (str, optional): The name of the logger.
        """
        # Configure the internal logger
        internal_logger.configure(debug_logs)

        internal_debug(
            f"Initializing GCPLogger with environment={environment}, logger_name={logger_name}, debug_logs={debug_logs}"
        )

        self.environment = environment
        self.default_bucket = default_bucket or os.getenv("GCP_DEFAULT_BUCKET")
        self.instance_id = self.get_instance_id()
        self.logger_name = logger_name
        self.debug_logs = debug_logs

        internal_debug(f"Setting up logger class: ContextAwareLogger")
        logging.setLoggerClass(ContextAwareLogger)
        self._logger = logging.getLogger(self.logger_name)
        logging.setLoggerClass(logging.Logger)

        internal_debug(f"Setting logger level to DEBUG")
        self._logger.setLevel(logging.DEBUG)

        internal_debug("Configuring handlers")
        self.configure_handlers()

        internal_debug("Setting up GCPLoggerAdapter")
        self.logger = GCPLoggerAdapter(
            self._logger,
            extra={"instance_id": self.instance_id, "trace_id": "-", "span_id": "-"},
        )

        internal_debug("GCPLogger initialization completed")

    @staticmethod
    def get_instance_id() -> str:
        """
        Retrieves the instance ID based on environment variables.

        Returns:
            str: The instance ID or '-' if not found.
        """
        if os.getenv("GAE_INSTANCE"):
            return os.getenv("GAE_INSTANCE")[:10]
        elif os.getenv("K_SERVICE"):
            return f"{os.getenv('K_SERVICE')}-{os.getenv('K_REVISION')}"[:9]
        elif os.getenv("FUNCTION_NAME"):
            return os.getenv("FUNCTION_NAME")[:10]
        else:
            internal_debug("Instance ID not found.")
            return "-"

    @staticmethod
    def get_trace_and_span_ids(trace_header: str = None):
        """
        Extracts trace_id and span_id from the X-Cloud-Trace-Context header.
        If the header is not provided, generates a UUID for trace_id.

        Args:
            trace_header (str, optional): The X-Cloud-Trace-Context header value.

        Returns:
            tuple: (trace_id, span_id)
        """
        if trace_header:
            try:
                trace_split = trace_header.split("/")
                span_split = trace_split[1].split(";")
                return trace_split[0], span_split[0]
            except IndexError:
                internal_debug(f"Invalid trace header format: {trace_header}")

        # If no valid trace_header, generate a UUID for trace_id
        return str(uuid4()), "-"


def configure_handlers(self):
    """
    Configures the appropriate logging handlers based on the environment.
    """
    internal_debug(f"Configuring handlers for environment: {self.environment}")

    # Remove existing handlers to prevent duplicate logs
    for handler in self._logger.handlers[:]:
        self._logger.removeHandler(handler)

    if self.environment in ["localdev", "unittest"]:
        internal_debug("Setting up console handler for localdev/unittest")
        formatter = ColoredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(console_handler)
        self._logger.propagate = False
    else:
        internal_debug("Setting up Custom Cloud Logging handler for production")
        try:
            client = cloud_logging.Client()
            cloud_handler = CustomCloudLoggingHandler(
                client,
                default_bucket=self.default_bucket,
                environment=self.environment,
            )
            cloud_handler.setLevel(logging.DEBUG)
            self._logger.addHandler(cloud_handler)
            self._logger.propagate = True
            internal_debug("Cloud Logging handler added successfully")
        except Exception as e:
            internal_debug(f"Error setting up Cloud Logging handler: {str(e)}")

    internal_debug(
        f"Logger configuration complete. Propagate: {self._logger.propagate}, Handlers: {len(self._logger.handlers)}"
    )

    @staticmethod
    def get_trace_context(trace_header: Optional[str] = None) -> tuple:
        """Default method to extract trace_id and span_id."""
        if trace_header:
            try:
                trace_split = trace_header.split("/")
                span_split = trace_split[1].split(";")
                return trace_split[0], span_split[0]
            except IndexError:
                internal_logger.debug(f"Invalid trace header format: {trace_header}")
        return str(uuid4().hex), "-"

    def update_trace_context(self, trace_header: Optional[str] = None):
        """Update the logger's trace context."""
        trace_id, span_id = self.get_trace_context(trace_header)
        self.logger.extra.update({"trace_id": trace_id, "span_id": span_id})

    def get_logger(self) -> logging.Logger:
        """
        Retrieves the configured logger.

        Returns:
            logging.Logger: The configured logger instance.
        """
        internal_debug("get_logger called")
        return self.logger

    def shutdown(self):
        """
        Shuts down all handlers gracefully.
        """
        for handler in self._logger.handlers:
            if hasattr(handler, "shutdown"):
                handler.shutdown()
