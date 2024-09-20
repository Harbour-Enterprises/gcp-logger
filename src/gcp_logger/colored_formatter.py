# File: gcp_logger/formatter.py

import logging
import os
from functools import lru_cache
from typing import Dict

from .levels import ALERT, EMERGENCY, NOTICE

# Lazy import of colorama
colorama = None


class ColoredFormatter(logging.Formatter):
    """
    Formatter for local development that adds color to log outputs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color_codes = self._generate_color_codes()

    @staticmethod
    @lru_cache(maxsize=None)
    def _generate_color_codes() -> Dict[int, str]:
        global colorama
        if colorama is None:
            import colorama

            colorama.init(autoreset=True)

        return {
            logging.DEBUG: colorama.Fore.CYAN,
            logging.INFO: colorama.Fore.GREEN,
            NOTICE: colorama.Fore.BLUE,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Fore.RED + colorama.Style.BRIGHT,
            ALERT: colorama.Fore.YELLOW + colorama.Style.BRIGHT,
            EMERGENCY: colorama.Fore.RED + colorama.Style.BRIGHT,
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats the log record with colors.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message with ANSI color codes.
        """
        color_code = self.color_codes.get(record.levelno, self.color_codes[logging.DEBUG])
        reset = colorama.Style.RESET_ALL

        formatted_time = colorama.Fore.GREEN + self.formatTime(record, self.datefmt) + reset
        formatted_level = color_code + f"{record.levelname:<10}" + reset

        # Use the custom fields from record
        func = getattr(record, "custom_func", record.funcName)
        filename = os.path.basename(getattr(record, "custom_filename", record.filename)).split(".")[0]
        lineno = getattr(record, "custom_lineno", record.lineno)

        formatted_name = colorama.Fore.CYAN + f"{filename}:{func}:{lineno}" + reset
        formatted_message = color_code + record.getMessage() + reset

        # Access extra info from record.__dict__
        trace_id = record.__dict__.get("trace_id", "-")

        return (
            f"{formatted_time} | "
            f"{trace_id} | {record.process} | {record.thread} | "
            f"{formatted_level} | "
            f"{formatted_name} - "
            f"{formatted_message}"
        )
