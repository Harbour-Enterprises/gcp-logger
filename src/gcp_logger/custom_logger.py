import inspect
import logging
import os
from typing import Any


class CustomLogger(logging.Logger):
    """Extended Logger with additional logging levels."""

    # Custom log levels
    NOTICE = 300
    ALERT = 700
    EMERGENCY = 800

    # Level mapping for proper severity handling
    LEVEL_TO_SEVERITY = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        NOTICE: "NOTICE",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
        ALERT: "ALERT",
        EMERGENCY: "EMERGENCY",
    }

    def __init__(self, name: str):
        """Initialize custom logger."""
        super().__init__(name)
        self._add_custom_levels()

    def _add_custom_levels(self):
        """Register custom log levels."""
        # Define custom levels at module level
        if not hasattr(logging, "NOTICE"):
            logging.NOTICE = self.NOTICE
        if not hasattr(logging, "ALERT"):
            logging.ALERT = self.ALERT
        if not hasattr(logging, "EMERGENCY"):
            logging.EMERGENCY = self.EMERGENCY

        # Register level names
        logging.addLevelName(self.NOTICE, "NOTICE")
        logging.addLevelName(self.ALERT, "ALERT")
        logging.addLevelName(self.EMERGENCY, "EMERGENCY")

    def _log_with_caller(self, level: int, msg: str, *args: Any, **kwargs: Any):
        """Log with correct caller information."""
        frame = inspect.currentframe()
        caller_frame = frame.f_back.f_back
        filename = os.path.basename(caller_frame.f_code.co_filename)
        func_name = caller_frame.f_code.co_name
        lineno = caller_frame.f_lineno

        if "%" not in msg and not any(c in msg for c in "{}"):
            args = ()

        record = self.makeRecord(
            self.name,
            level,
            filename,
            lineno,
            msg,
            args,
            None,
            func_name,
            kwargs,
        )
        record.levelname = self.LEVEL_TO_SEVERITY.get(level, "UNKNOWN")
        self.handle(record)

    def notice(self, msg: str, *args: Any, **kwargs: Any):
        """Log a NOTICE level message."""
        self._log_with_caller(self.NOTICE, msg, *args, **kwargs)

    def alert(self, msg: str, *args: Any, **kwargs: Any):
        """Log an ALERT level message."""
        self._log_with_caller(self.ALERT, msg, *args, **kwargs)

    def emergency(self, msg: str, *args: Any, **kwargs: Any):
        """Log an EMERGENCY level message."""
        self._log_with_caller(self.EMERGENCY, msg, *args, **kwargs)
