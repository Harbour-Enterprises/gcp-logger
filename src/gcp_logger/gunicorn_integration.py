# File: gcp_logger/gunicorn_integration.py

import logging

from .custom_logging_handler import CustomCloudLoggingHandler

try:
    from gunicorn import glogging
except ImportError:
    raise ImportError(
        "Gunicorn is not installed. Please install gcp-logger with Gunicorn support: pip install gcp-logger[gunicorn]"
    )


class GunicornLogger(glogging.Logger):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.gcp_handler = None

    def setup(self, cfg):
        super().setup(cfg)

        # Get the existing GCPLogger handler
        self.gcp_handler = next((h for h in logging.root.handlers if isinstance(h, CustomCloudLoggingHandler)), None)

        if self.gcp_handler:
            # Replace Gunicorn's error_log and access_log handlers with GCPLogger's handler
            self.error_log.handlers = [self.gcp_handler]
            self.access_log.handlers = [self.gcp_handler]
        else:
            # Fallback to default Gunicorn logging if CustomCloudLoggingHandler is not found
            self.error_log.warning("GCPLogger handler not found, using default Gunicorn logging")

    def atoms(self, resp, req, environ, request_time):
        atoms = super().atoms(resp, req, environ, request_time)
        # Add or update GCP-specific attributes
        atoms.update(
            {
                "trace_id": getattr(req, "trace_id", "-"),
                "span_id": getattr(req, "span_id", "-"),
            }
        )
        return atoms

    def access(self, resp, req, environ, request_time):
        if self.gcp_handler:
            message = self.atoms_wrapper(resp, req, environ, request_time)
            self.gcp_handler.emit(
                self.gcp_handler.makeRecord("gunicorn.access", logging.INFO, "", 0, message, (), None)
            )
        else:
            super().access(resp, req, environ, request_time)


def get_gunicorn_logger_class():
    return GunicornLogger
