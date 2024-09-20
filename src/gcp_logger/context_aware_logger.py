# File: gcp_logger/context_aware_logger.py

import inspect
import logging


class ContextAwareLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        """
        Overrides the _log method to inject additional context into log records.

        Args:
            level (int): The log level.
            msg (str): The log message.
            args (tuple): Arguments for the log message.
            exc_info (bool, Exception, tuple): Exception information.
            extra (dict): Additional context.
            stack_info (bool): Stack information flag.
            stacklevel (int): Stack level for caller information.
        """
        # Find the first frame outside of the logging module and gcp_logger package
        frame = inspect.currentframe()
        while frame and (
            frame.f_code.co_filename.endswith("logging/__init__.py") or "gcp_logger" in frame.f_code.co_filename
        ):
            frame = frame.f_back

        if frame:
            extra = extra or {}
            extra.update(
                {
                    "custom_filename": frame.f_code.co_filename,
                    "custom_lineno": frame.f_lineno,
                    "custom_func": frame.f_code.co_name,
                }
            )

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)

    def notice(self, msg, *args, **kwargs):
        """
        Logs a message with NOTICE level.

        Args:
            msg (str): The log message.
        """
        self.log(logging.NOTICE, msg, *args, **kwargs)

    def alert(self, msg, *args, **kwargs):
        """
        Logs a message with ALERT level.

        Args:
            msg (str): The log message.
        """
        self.log(logging.ALERT, msg, *args, **kwargs)

    def emergency(self, msg, *args, **kwargs):
        """
        Logs a message with EMERGENCY level.

        Args:
            msg (str): The log message.
        """
        self.log(logging.EMERGENCY, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        """
        Logs a message with SUCCESS indication.

        Args:
            msg (str): The log message.
        """
        self.info(f"SUCCESS: {msg}", *args, **kwargs)
