# File: gcp_logger/custom_logging_handler.py

import logging
import os
import time
from typing import Union

from google.cloud import logging as cloud_logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler

from .async_uploader import AsyncUploader
from .internal_logger import internal_debug
from .levels import ALERT, EMERGENCY, NOTICE


class CustomCloudLoggingHandler(CloudLoggingHandler):
    MAX_LOG_SIZE = 255 * 1024  # 255KB

    CUSTOM_LOGGING_SEVERITY = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        NOTICE: "NOTICE",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
        ALERT: "ALERT",
        EMERGENCY: "EMERGENCY",
    }

    def __init__(
        self,
        client: cloud_logging.Client,
        default_bucket: str = None,
        environment: str = None,
    ):
        """
        Initializes the CustomCloudLoggingHandler.

        Args:
            client (cloud_logging.Client): The Google Cloud Logging client.
            default_bucket (str, optional): The default GCS bucket for large logs.
            environment (str, optional): The deployment environment (e.g., production).
        """
        internal_debug(
            f"Initializing CustomCloudLoggingHandler: client={client}, default_bucket={default_bucket}, environment={environment}"
        )
        try:
            super().__init__(client, name="gcp-logger")
            internal_debug("CloudLoggingHandler initialized successfully")
        except Exception as e:
            internal_debug(f"Error initializing CloudLoggingHandler: {str(e)}")
            raise

        self.default_bucket = default_bucket
        self.environment = environment
        self.async_uploader = None

        if self.default_bucket:
            try:
                self.async_uploader = AsyncUploader(bucket_name=self.default_bucket)
                internal_debug(f"AsyncUploader initialized with bucket {self.default_bucket}")
            except Exception as e:
                internal_debug(f"Error initializing AsyncUploader: {str(e)}")

    def emit(self, record: logging.LogRecord):
        """
        Emits a log record to Google Cloud Logging, handling large logs by uploading to GCS.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        internal_debug(f"Emitting log: level={record.levelno}, msg={record.getMessage()[:50]}...")

        try:
            record.severity = self.CUSTOM_LOGGING_SEVERITY.get(record.levelno, "DEFAULT")
            self.add_custom_attributes(record)
            message = self.format_log_message(record)

            if len(message.encode("utf-8")) > self.MAX_LOG_SIZE and self.async_uploader:
                internal_debug("Log size exceeds MAX_LOG_SIZE, attempting to upload to GCS")
                gcs_uri = self.upload_large_log_to_gcs(record.getMessage(), record.__dict__)
                if gcs_uri:
                    message = self.truncate_log_message(message, gcs_uri)
                    internal_debug(f"Log truncated and uploaded to GCS: {gcs_uri}")
                else:
                    internal_debug("Failed to upload large log to GCS")

            record.msg = message
            record.args = ()

            internal_debug("Calling super().emit")
            super().emit(record)
            internal_debug("super().emit completed successfully")
        except Exception as e:
            internal_debug(f"Error in emit method: {str(e)}")

    def add_custom_attributes(self, record: logging.LogRecord):
        """
        Adds custom attributes to the log record.

        Args:
            record (logging.LogRecord): The log record to modify.
        """
        internal_debug("Adding custom attributes to log record")
        record.instance_id = getattr(record, "instance_id", "-")
        record.trace_id = getattr(record, "trace_id", "-")
        record.span_id = getattr(record, "span_id", "-")
        record.environment = self.environment or "production"
        record.filename = os.path.basename(getattr(record, "custom_filename", record.filename)).split(".")[0]
        record.funcName = getattr(record, "custom_func", record.funcName)
        record.lineno = getattr(record, "custom_lineno", record.lineno)

    def format_log_message(self, record: logging.LogRecord) -> str:
        """
        Formats the log message.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message.
        """
        internal_debug("Formatting log message")
        log_format = (
            "{instance_id} | {trace_id} | {span_id} | "
            "{process} | {thread} | "
            "{levelname:<8} | "
            "{filename}:{funcName}:{lineno} - "
            "{message}"
        )

        record.message = record.getMessage()

        return log_format.format(**record.__dict__)

    def upload_large_log_to_gcs(self, log_message: str, record_dict: dict) -> Union[str, None]:
        """
        Uploads a large log message to GCS asynchronously.

        Args:
            log_message (str): The log message to upload.
            record_dict (dict): The dictionary representation of the log record.

        Returns:
            Union[str, None]: The GCS URI of the uploaded log or None if upload failed.
        """
        if not self.default_bucket or not self.async_uploader:
            internal_debug("Skipping upload to GCS: missing default_bucket or async_uploader")
            return None

        internal_debug(f"Uploading large log to GCS bucket: {self.default_bucket}")
        blob_name = self.get_blob_name(record_dict)
        gcs_uri = f"gs://{self.default_bucket}/{blob_name}"

        try:
            # Upload asynchronously using AsyncUploader
            self.async_uploader.upload_data(data=log_message.encode("utf-8"), object_name=blob_name)
            internal_debug(f"Scheduled upload for {blob_name}. GCS URI: {gcs_uri}")
            return gcs_uri
        except Exception as e:
            internal_debug(f"Error uploading to GCS: {str(e)}")
            return None

    def get_blob_name(self, record_dict: dict) -> str:
        """
        Generates a unique blob name for the log message.

        Args:
            record_dict (dict): The dictionary representation of the log record.

        Returns:
            str: The blob name for the log message.
        """
        internal_debug("Generating blob name for GCS upload")

        timestamp = int(time.time())

        parts = [
            (timestamp, None),  # timestamp is always included
            (record_dict.get("instance_id"), "instance_id"),
            (record_dict.get("trace_id"), "trace_id"),
            (record_dict.get("span_id"), "span_id"),
            (record_dict.get("process"), "process"),
            (record_dict.get("thread"), "thread"),
        ]

        # Filter out parts that are not available (i.e., None or "-")
        available_parts = [str(part) for part, _ in parts if part is not None and part != "-"]

        return "logs/" + "_".join(available_parts) + ".log"

    def truncate_log_message(self, log_message: str, gcs_uri: str) -> str:
        """
        Truncates the log message and appends a reference to the GCS URI.

        Args:
            log_message (str): The original log message.
            gcs_uri (str): The GCS URI where the full log is stored.

        Returns:
            str: The truncated log message with a reference.
        """
        internal_debug("Truncating log message")

        truncation_notice = "... [truncated]"
        additional_text = f"\nMessage has been truncated. Full log at: {gcs_uri}"

        max_message_length = (
            self.MAX_LOG_SIZE - len(truncation_notice.encode("utf-8")) - len(additional_text.encode("utf-8"))
        )
        truncated_message = log_message.encode("utf-8")[:max_message_length].decode("utf-8", errors="ignore")

        return f"{truncated_message}{truncation_notice}{additional_text}"

    def shutdown(self):
        """
        Shuts down the AsyncUploader gracefully.
        """
        internal_debug("Shutting down CustomCloudLoggingHandler")
        if self.async_uploader:
            try:
                self.async_uploader.shutdown()
                internal_debug("AsyncUploader shutdown complete")
            except Exception as e:
                internal_debug(f"Error during AsyncUploader shutdown: {str(e)}")
