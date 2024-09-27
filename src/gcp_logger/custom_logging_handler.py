# File: gcp_logger/custom_logging_handler.py

import logging
import os
from typing import Any, Dict

from google.cloud import logging as cloud_logging
from google.cloud.logging_v2._helpers import LogSeverity
from google.cloud.logging_v2.handlers import CloudLoggingHandler

from .async_uploader import AsyncUploader
from .internal_logger import internal_debug
from .levels import ALERT, EMERGENCY, NOTICE


class CustomCloudLoggingHandler(CloudLoggingHandler):
    MAX_LOG_SIZE = 255 * 1024  # 255KB

    CUSTOM_LOGGING_SEVERITY = {
        logging.DEBUG: LogSeverity.DEBUG,
        logging.INFO: LogSeverity.INFO,
        NOTICE: LogSeverity.NOTICE,
        logging.WARNING: LogSeverity.WARNING,
        logging.ERROR: LogSeverity.ERROR,
        logging.CRITICAL: LogSeverity.CRITICAL,
        ALERT: LogSeverity.ALERT,
        EMERGENCY: LogSeverity.EMERGENCY,
    }

    def __init__(
        self,
        client: cloud_logging.Client,
        default_bucket: str = None,
    ):
        """
        Initializes the CustomCloudLoggingHandler.

        Args:
            client (cloud_logging.Client): The Google Cloud Logging client.
            default_bucket (str, optional): The default GCS bucket for large logs.
        """
        internal_debug(f"Initializing CustomCloudLoggingHandler: client={client}, default_bucket={default_bucket}")
        try:
            super().__init__(client, name="gcp-logger")
            internal_debug("CloudLoggingHandler initialized successfully")
        except Exception as e:
            internal_debug(f"Error initializing CloudLoggingHandler: {str(e)}")
            raise

        self.default_bucket = default_bucket
        self.async_uploader = AsyncUploader(bucket_name=self.default_bucket) if self.default_bucket else None

    def emit(self, record: logging.LogRecord):
        """
        Emits a log record to Google Cloud Logging, handling large logs by uploading to GCS.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        internal_debug(f"Emitting log: level={record.levelno}, msg={record.getMessage()[:50]}...")

        try:
            self.add_custom_attributes(record)

            if self.is_large_log(record) and self.async_uploader:
                record = self.handle_large_log(record)

            internal_debug("Sending log record to Cloud Logging")
            message = self.format_log_message(record)

            # Ensure we have a valid labels dictionary
            labels = dict(self.resource.labels) if self.resource.labels else {}

            trace_id = getattr(record, "trace_id")
            span_id = getattr(record, "span_id")

            self.transport.send(
                record,
                message,
                resource=self.resource,
                labels=labels,
                trace=trace_id if trace_id != "-" else None,
                span_id=span_id if span_id != "-" else None,
            )
            internal_debug("Log record sent successfully")
        except Exception as e:
            internal_debug(f"Error in emit method: {str(e)}")

    def add_custom_attributes(self, record: logging.LogRecord):
        """
        Adds custom attributes to the log record.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        custom_fields = self.extract_custom_fields(record)
        for key, value in custom_fields.items():
            setattr(record, key, value)

    def get_severity(self, level: int) -> LogSeverity:
        """
        Maps a logging level to a Google Cloud LogSeverity.

        Args:
            level (int): The logging level.

        Returns:
            LogSeverity: The corresponding Google Cloud LogSeverity.
        """
        return self.CUSTOM_LOGGING_SEVERITY.get(level, LogSeverity.DEFAULT)

    def extract_custom_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Extracts custom fields from a logging.LogRecord.

        Args:
            record (logging.LogRecord): The log record to process.

        Returns:
            Dict[str, Any]: A dictionary of custom fields.
        """
        return {
            "instance_id": getattr(record, "instance_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
            "filename": os.path.basename(getattr(record, "custom_filename", record.filename)).split(".")[0],
            "funcName": getattr(record, "custom_func", record.funcName),
            "lineno": getattr(record, "custom_lineno", record.lineno),
            "process": record.process,
            "thread": record.thread,
            "levelname": record.levelname,
            "severity": self.get_severity(record.levelno),
        }

    def is_large_log(self, record: logging.LogRecord) -> bool:
        """
        Checks if a log record exceeds the maximum log size.

        Args:
            record (logging.LogRecord): The log record to check.

        Returns:
            bool: True if the log record is large, False otherwise.
        """
        message = self.format(record)
        return len(message.encode("utf-8")) > self.MAX_LOG_SIZE

    def handle_large_log(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Handles a large log record by uploading it to GCS and truncating the message.

        Args:
            record (logging.LogRecord): The large log record.

        Returns:
            logging.LogRecord: The updated log record with a truncated message.
        """
        internal_debug("Log size exceeds MAX_LOG_SIZE, attempting to upload to GCS")
        message = self.format_log_message(record)
        labels = dict(self.labels) if self.labels else {}
        gcs_uri = self.upload_large_log_to_gcs(message, labels)
        if gcs_uri:
            truncated_message = self.truncate_log_message(message, gcs_uri)
            record.msg = truncated_message
            internal_debug(f"Log truncated and uploaded to GCS: {gcs_uri}")
        else:
            internal_debug("Failed to upload large log to GCS")
        return record

    def upload_large_log_to_gcs(self, payload: str, labels: Dict[str, str]) -> str:
        """
        Uploads a large log message to GCS.

        Args:
            payload (str): The log message to upload.
            labels (Dict[str, str]): Labels associated with the log entry.

        Returns:
            str: The GCS URI of the uploaded log.
        """
        blob_name = self.generate_blob_name(labels)
        gcs_uri = f"gs://{self.default_bucket}/{blob_name}"
        self.async_uploader.upload_data(data=payload.encode("utf-8"), object_name=blob_name)
        return gcs_uri

    def generate_blob_name(self, labels: Dict[str, str]) -> str:
        """
        Generates a unique blob name for the log message.

        Args:
            labels (Dict[str, str]): Labels associated with the log entry.

        Returns:
            str: The generated blob name.
        """
        import time

        timestamp = int(time.time())
        parts = [str(timestamp)] + [str(labels.get(key, "")) for key in ["instance_id", "trace_id", "span_id"]]
        return f"logs/{'_'.join(filter(bool, parts))}.log"

    def truncate_log_message(self, message: str, gcs_uri: str) -> str:
        """
        Truncates the log message and appends a reference to the GCS URI.

        Args:
            message (str): The original log message.
            gcs_uri (str): The GCS URI where the full log is stored.

        Returns:
            str: The truncated log message with a reference.
        """
        truncation_notice = "... [truncated]"
        additional_text = f"\nMessage has been truncated. Full log at: {gcs_uri}"
        max_message_length = self.MAX_LOG_SIZE - len(truncation_notice) - len(additional_text)
        truncated_message = message[:max_message_length]
        return f"{truncated_message}{truncation_notice}{additional_text}"

    def format_log_message(self, record: logging.LogRecord) -> str:
        """
        Formats the log message according to the specified format.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message.
        """
        log_format = (
            "{instance_id} | {trace_id} | {span_id} | "
            "{process} | {thread} | "
            "{levelname:<8} | "
            "{filename}:{funcName}:{lineno} - "
            "{message}"
        )

        return log_format.format(**record.__dict__)

    def shutdown(self):
        """
        Shuts down the AsyncUploader gracefully.
        """
        if self.async_uploader:
            self.async_uploader.shutdown()
        super().shutdown()
