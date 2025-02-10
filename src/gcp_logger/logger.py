import logging
import os
from enum import Enum
from typing import Optional, Union

from .custom_logger import CustomLogger
from .handlers import CloudHandler, LocalDevHandler


class LogEnvironment(Enum):
    """Environment types for logger configuration.

    LOCAL: Local development environment with colored console output
    GCP: Google Cloud Platform environment with structured JSON logging
    TEST: Testing environment (similar to LOCAL but with specific test configurations)
    """

    LOCAL = "local"
    GCP = "gcp"
    TEST = "test"

    @classmethod
    def from_string(cls, value: str) -> "LogEnvironment":
        """Convert string to LogEnvironment, with flexible input handling.

        Args:
            value: String representation of environment

        Returns:
            LogEnvironment: Corresponding enum value

        Examples:
            >>> LogEnvironment.from_string("local")
            <LogEnvironment.LOCAL>
            >>> LogEnvironment.from_string("development")
            <LogEnvironment.LOCAL>
            >>> LogEnvironment.from_string("prod")
            <LogEnvironment.GCP>
        """
        value = value.lower().strip()

        # Map various common environment names to our enum values
        local_environments = {"local", "development", "dev", "localdev"}
        gcp_environments = {"gcp", "cloud", "prod", "production", "staging", "stage"}
        test_environments = {"test", "testing", "unittest"}

        if value in local_environments:
            return cls.LOCAL
        elif value in gcp_environments:
            return cls.GCP
        elif value in test_environments:
            return cls.TEST
        else:
            # Default to LOCAL for unknown environments
            return cls.LOCAL


class GCPLogger:
    """Main logger setup and configuration handler.

    This class provides a flexible logging setup that can switch between local development
    and Google Cloud Platform (GCP) logging configurations. The local development setup
    includes colored console output, while the GCP setup provides structured JSON logging.

    Args:
        environment: The logging environment to use. Can be:
            - A LogEnvironment enum value
            - A string that will be converted to a LogEnvironment
            - None (will check ENVIRONMENT env var, defaulting to LOCAL if not set)

    Environment Resolution Order:
        1. Explicitly passed environment argument
        2. ENVIRONMENT environment variable
        3. Default to LOCAL environment
    """

    def __init__(self, environment: Optional[Union[LogEnvironment, str]] = None):
        """Initialize logger setup."""
        # Convert string environment to enum if needed
        if isinstance(environment, str):
            environment = LogEnvironment.from_string(environment)
        elif environment is None:
            # Check environment variable, default to LOCAL if not set
            env_value = os.getenv("ENVIRONMENT", "local")
            environment = LogEnvironment.from_string(env_value)

        self.environment = environment
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
        """Configure logging system based on environment."""
        # Set custom logger class as default
        logging.setLoggerClass(CustomLogger)

        # Create logger instance
        logger = CustomLogger("gcp-logger")
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        logger.handlers.clear()

        # Create appropriate handler based on environment
        if self.environment in (LogEnvironment.LOCAL, LogEnvironment.TEST):
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
