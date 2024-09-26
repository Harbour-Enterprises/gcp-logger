# File: gcp_logger/logger_adapter.py

import logging

from .internal_logger import internal_debug
from .levels import ALERT, EMERGENCY, NOTICE


class GCPLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        """
        Processes the log message and injects additional contextual information.

        Args:
            msg (str): The log message.
            kwargs (dict): The keyword arguments for the log record.

        Returns:
            tuple: The modified log message and keyword arguments.
        """
        internal_debug(f"Processing log message: {msg}")
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

    def log(self, level, msg, *args, **kwargs):
        internal_debug(f"Logging message: level={level}, msg={msg}")
        super().log(level, msg, *args, **kwargs)

    def notice(self, msg, *args, **kwargs):
        """
        Logs a message with NOTICE level.

        Args:
            msg (str): The log message.
        """
        self.log(NOTICE, msg, *args, **kwargs)

    def alert(self, msg, *args, **kwargs):
        """
        Logs a message with ALERT level.

        Args:
            msg (str): The log message.
        """
        self.log(ALERT, msg, *args, **kwargs)

    def emergency(self, msg, *args, **kwargs):
        """
        Logs a message with EMERGENCY level.

        Args:
            msg (str): The log message.
        """
        self.log(EMERGENCY, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        """
        Logs a message with SUCCESS indication.

        Args:
            msg (str): The log message.
        """
        self.info(f"SUCCESS: {msg}", *args, **kwargs)
