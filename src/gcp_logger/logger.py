import logging
import os
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
    supporting both local development and production environments, with tracing capabilities.
    """

    def __init__(
        self,
        logger_name: str = "gcp-logger",
        logger_level: int = logging.DEBUG,
        default_bucket: str = None,
        is_localdev: bool = False,
        debug_logs: bool = False,
    ):
        """
        Initializes the GCPLogger.

        Args:
            logger_name (str, optional): The name of the logger.
            is_localdev (bool): Whether the environment is local development.
            default_bucket (str, optional): The default GCS bucket for large logs.
            debug (bool): Whether to enable debug logging.
        """
        internal_logger.configure(debug_logs)
        internal_debug(
            f"Initializing GCPLogger (localdev={is_localdev}), logger_name={logger_name}, debug_logs={debug_logs}"
        )

        self.logger_name = logger_name
        self.logger_level = logger_level
        self.default_bucket = default_bucket
        self.is_localdev = is_localdev
        self.debug_logs = debug_logs
        self.instance_id = self.get_instance_id()

        internal_debug(f"Setting up logger class: ContextAwareLogger")
        logging.setLoggerClass(ContextAwareLogger)
        self._logger = logging.getLogger(logger_name)

        self._logger.setLevel(logger_level)

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
        """Retrieves the instance ID based on environment variables."""
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
        internal_debug(f"Configuring handlers for is_localdev={self.is_localdev}")

        if not self.is_localdev:
            internal_debug("Setting up Cloud Logging handler for production")
            try:
                self.client = cloud_logging.Client()
                cloud_handler = CustomCloudLoggingHandler(self.client, default_bucket=self.default_bucket)
                self._logger.addHandler(cloud_handler)
                internal_debug("Cloud Logging handler added successfully")
            except Exception as e:
                internal_debug(f"Error setting up Cloud Logging handler: {str(e)}")
        else:
            internal_debug("Setting up stream handler")
            stream_handler = logging.StreamHandler()
            if self.is_localdev:
                local_formatter = ColoredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
                stream_handler.setFormatter(local_formatter)
            self._logger.addHandler(stream_handler)

        internal_debug(f"Logger configuration complete. Handlers: {len(self._logger.handlers)}")

    @staticmethod
    def get_trace_context(trace_header: Optional[str] = None) -> tuple:
        """Default method to extract trace_id and span_id."""
        if trace_header:
            try:
                trace_split = trace_header.split("/")
                span_split = trace_split[1].split(";")
                return trace_split[0], span_split[0]
            except IndexError:
                internal_debug(f"Invalid trace header format: {trace_header}")
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
