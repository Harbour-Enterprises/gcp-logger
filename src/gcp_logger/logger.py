import logging
import os
from typing import Optional

from .custom_logger import CustomLogger
from .handlers import CloudHandler, LocalDevHandler


class GCPLogger:
    """Main logger setup and configuration handler."""

    def __init__(self, environment: Optional[str] = None):
        """Initialize logger setup."""
        self.environment = environment or os.getenv("ENVIRONMENT", "localdev")
        self.gae_instance = os.getenv("GAE_INSTANCE", "-")[:10]
        self._default_attributes = {"trace_id": "-", "span_id": "-", "instance_id": self.gae_instance}
        self.original_factory = logging.getLogRecordFactory()
        self._setup_record_factory()
        self.logger = self._setup_logging()

    def _setup_record_factory(self):
        """Set up custom record factory with default values."""

        def record_factory(*args, **kwargs):
            record = self.original_factory(*args, **kwargs)
            for key, value in self._default_attributes.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)

    def update_log_record_factory(self, trace_id: str = "-", span_id: str = "-"):
        """Update log record factory with trace context."""
        self._default_attributes.update({"trace_id": trace_id, "span_id": span_id})
        self._setup_record_factory()

    def _setup_logging(self):
        """Configure logging system."""
        # Set custom logger class as default
        logging.setLoggerClass(CustomLogger)

        # Create logger instance
        logger = CustomLogger("gcp-logger")
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        logger.handlers.clear()

        # Create appropriate handler based on environment
        if self.environment in ["localdev", "unittest"]:
            handler = LocalDevHandler()
        else:
            handler = CloudHandler()

        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Add custom logging methods to logging module
        logging.notice = logger.notice
        logging.alert = logger.alert
        logging.emergency = logger.emergency

        return logger
