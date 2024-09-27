# File: gcp_logger/internal_logger.py

import sys
from datetime import datetime
from functools import wraps


class InternalLogger:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.is_debug_enabled = False

    def configure(self, debug: bool):
        self.is_debug_enabled = debug

    def debug(self, msg, *args, **kwargs):
        if self.is_debug_enabled:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            formatted_msg = msg.format(*args, **kwargs) if args or kwargs else msg
            print(f"[{timestamp}] GCPLogger Internal: {formatted_msg}", file=sys.stderr, flush=True)


internal_logger = InternalLogger.get_instance()


def internal_debug(msg, *args, **kwargs):
    internal_logger.debug(msg, *args, **kwargs)


def debug_only(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.debug_logs:
            return func(self, *args, **kwargs)

    return wrapper
