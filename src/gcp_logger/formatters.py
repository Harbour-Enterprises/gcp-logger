import json
import logging
import os
from typing import Dict


class CloudFormatter(logging.Formatter):
    """JSON formatter for Cloud Logging with message truncation."""

    LOGGING_MAX_SIZE = 60 * 1024  # 60KB max size
    TRUNCATION_NOTICE = "... [truncated]"

    def __init__(self):
        """Initialize formatter."""
        format_string = (
            "%(instance_id)s | %(trace_id)s | %(span_id)s | "
            "%(process)d | %(thread)d | "
            "%(levelname)-8s | "
            "%(module)s:%(funcName)s:%(lineno)d - "
            "%(message)s"
        )
        super().__init__(fmt=format_string)

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with truncation."""
        try:
            record.message = record.getMessage()

            # Handle message truncation
            message_bytes = record.message.encode("utf-8")
            if len(message_bytes) > self.LOGGING_MAX_SIZE:
                record.message = self._truncate_message(record.message)

            # Create log structure
            log_struct = self._create_base_log_structure(record)
            log_struct["message"] = self.formatMessage(record)

            return json.dumps(log_struct)
        except Exception as e:
            return json.dumps(
                {
                    "severity": "ERROR",
                    "message": f"Error formatting log: {str(e)}",
                    "original_severity": record.levelname,
                }
            )

    def _create_base_log_structure(self, record: logging.LogRecord) -> Dict:
        """Create base log structure."""
        # Handle trace context
        span_id = getattr(record, "span_id", None)
        if span_id == "-":
            span_id = None

        trace_id = getattr(record, "trace_id", None)
        if trace_id == "-":
            trace_id = None

        # Basic structure
        log_struct = {
            "severity": record.levelname,
            "timestamp": self.formatTime(record, self.datefmt),
            "logging.googleapis.com/sourceLocation": {
                "file": record.filename,
                "line": str(record.lineno),
                "function": record.funcName,
            },
        }

        # Add trace context if available
        project_id = os.getenv("GCP_PROJECT_ID")
        if trace_id and project_id:
            log_struct["logging.googleapis.com/trace"] = f"projects/{project_id}/traces/{trace_id}"
        if span_id:
            log_struct["logging.googleapis.com/spanId"] = span_id

        # Add error info
        if record.exc_info:
            log_struct["exception"] = self.formatException(record.exc_info)
            log_struct["@type"] = "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"

        return log_struct

    def _truncate_message(self, message: str) -> str:
        """Truncate message to fit within max size."""
        notice_bytes = len(self.TRUNCATION_NOTICE.encode("utf-8"))
        message_space = self.LOGGING_MAX_SIZE - notice_bytes
        truncated = message.encode("utf-8")[:message_space]
        decoded = truncated.decode("utf-8", errors="ignore")
        return f"{decoded}{self.TRUNCATION_NOTICE}"
