import logging
import sys

from google.cloud import logging as cloud_logging

from .formatters import CloudFormatter


class CloudHandler(logging.StreamHandler):
    """Handler for Cloud Logging output."""

    def __init__(self):
        """Initialize Cloud Handler."""
        super().__init__(sys.stdout)
        self.setFormatter(CloudFormatter())
        self.setLevel(logging.DEBUG)  # Set default level to DEBUG
        try:
            self.client = cloud_logging.Client()
            self.cloud_logger = self.client.logger("gcp_logger")
        except Exception as e:
            print(f"Failed to initialize Cloud Logging client: {e}")

    def filter(self, record):
        """Filter records based on level."""
        return record.levelno >= self.level


class LocalDevHandler(logging.StreamHandler):
    """Color-coded handler for local development."""

    COLORS = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "NOTICE": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[31m",  # red
        "ALERT": "\033[35m",  # magenta
        "EMERGENCY": "\033[35m",  # magenta
        "RESET": "\033[0m",
    }

    def __init__(self):
        """Initialize local development handler."""
        super().__init__(sys.stdout)
        self.setFormatter(self._get_formatter())

    def _get_formatter(self):
        """Get development formatter."""
        return logging.Formatter(
            "%(asctime)s.%(msecs)03d | "
            "%(trace_id)s | %(process)d | %(thread)d | "
            "%(levelname)-8s | "
            "%(module)s:%(funcName)s:%(lineno)d - "
            "%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        """Format log record with color coding."""
        color = self.COLORS.get(record.levelname.strip(), self.COLORS["RESET"])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)
