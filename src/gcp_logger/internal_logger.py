# File: gcp_logger/internal_logger.py

import logging
import sys


class InternalLogger:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger("gcp_logger.internal")
        self.logger.setLevel(logging.INFO)
        self.handler = None

    def configure(self, debug_internal: bool):
        if self.handler:
            self.logger.removeHandler(self.handler)

        self.handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("GCPLogger Internal: %(message)s")
        self.handler.setFormatter(formatter)
        self.handler.setLevel(logging.DEBUG if debug_internal else logging.INFO)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG if debug_internal else logging.INFO)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)


internal_logger = InternalLogger.get_instance()


def internal_debug(msg, *args, **kwargs):
    internal_logger.debug(msg, *args, **kwargs)
