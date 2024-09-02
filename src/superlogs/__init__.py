# File: superlogs/__init__.py

import os
import sys
import time
from typing import Union

from google.cloud import logging as cloud_logging
from google.cloud import storage
from loguru import logger


class SuperLogs:
    LOGURU_LEVEL_TO_GCP_SEVERITY = {
        "TRACE": "DEBUG",
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "SUCCESS": "NOTICE",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
        "ALERT": "ALERT",
        "EMERGENCY": "EMERGENCY",
    }

    LOGGING_MAX_SIZE = 255 * 1024  # 256KB max size for log messages in Google Cloud Logging

    def __init__(self, environment: str, default_bucket: str = None):
        self.environment = environment
        self.default_bucket = default_bucket or os.getenv("GCP_DEFAULT_BUCKET")
        self.gae_instance = os.getenv("GAE_INSTANCE", "-")[:10]

        # Initialize Google Cloud clients
        self.client = cloud_logging.Client()
        self.cloud_logger = self.client.logger("superlogs_logger")

        self.setup_logging()

    def setup_logging(self):
        # Remove all existing handlers to avoid duplicate logs
        logger.remove()

        # Add custom log levels
        logger.level("ALERT", no=70, color="<yellow>")
        logger.level("EMERGENCY", no=80, color="<red>")

        if self.environment in ["localdev", "unittest"]:
            custom_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "{extra[trace_id]} | {process.id} | {thread.id} | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            )
            logger.add(sys.stdout, format=custom_format, level="TRACE", colorize=True, backtrace=True, diagnose=True)
            logger.configure(extra={"trace_id": "-"})
        else:
            logger.add(self.google_cloud_log_sink, level="DEBUG", colorize=False)
            logger.configure(extra={"instance_id": self.gae_instance, "trace_id": "-", "span_id": "-"})

    @staticmethod
    def google_cloud_log_format(record: dict) -> str:
        custom_format = (
            "{extra[instance_id]} | {extra[trace_id]} | {extra[span_id]} | "
            "{process.id} | {thread.id} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        )
        return custom_format.format(**record)

    @classmethod
    def google_cloud_log_truncate(cls, log_message: str, gsutil_uri: str | None) -> str:
        truncation_notice = "... [truncated]"
        additional_text_template = "\nMessage has been truncated, please check: {gsutil_uri} for full log message"

        truncation_notice_length = len(truncation_notice.encode("utf-8"))
        gsutil_uri_length = len(gsutil_uri.encode("utf-8")) if gsutil_uri else 0
        additional_text_length = len(additional_text_template.encode("utf-8")) - len("{gsutil_uri}") + gsutil_uri_length
        max_message_length = cls.LOGGING_MAX_SIZE - truncation_notice_length - additional_text_length

        truncated_message = log_message.encode("utf-8")[:max_message_length].decode("utf-8", errors="ignore")

        if gsutil_uri:
            truncated_message = f"{truncated_message}{truncation_notice}\nMessage has been truncated, please check: {gsutil_uri} for full log message"
        else:
            truncated_message = f"{truncated_message}{truncation_notice}"

        return truncated_message

    def save_large_log_to_gcs(
        self, log_message: str, instance_id: str, trace_id: str, span_id: str, process_id: str, thread_id: str
    ) -> Union[str, None]:
        storage_client = storage.Client()
        storage_bucket = storage_client.bucket(self.default_bucket)
        timestamp = int(time.time())

        parts = [timestamp, process_id, thread_id]
        if instance_id != "-":
            parts.insert(1, instance_id)
        if trace_id != "-":
            parts.insert(2, trace_id)
        if span_id != "-":
            parts.insert(3, span_id)

        blob_name = "logs/" + "_".join(map(str, parts)) + ".log"
        blob = storage_bucket.blob(blob_name)

        try:
            blob.upload_from_string(log_message)
            return f"gs://{self.default_bucket}/{blob_name}"
        except Exception as e:
            logger.error(f"Failed to upload log to GCS: {e}")
            return None

    def google_cloud_log_sink(self, message):
        record = message.record
        log_level = record["level"].name
        severity = self.LOGURU_LEVEL_TO_GCP_SEVERITY.get(log_level, "DEFAULT")
        log_message = self.google_cloud_log_format(record)
        instance_id = record["extra"].get("instance_id", "-")
        trace_id = record["extra"].get("trace_id", "-")
        span_id = record["extra"].get("span_id", "-")
        process_id = record["process"].id
        thread_id = record["thread"].id

        if len(log_message.encode("utf-8")) > self.LOGGING_MAX_SIZE:
            gsutil_uri = self.save_large_log_to_gcs(log_message, instance_id, trace_id, span_id, process_id, thread_id)
            log_message = self.google_cloud_log_truncate(log_message, gsutil_uri)

        self.cloud_logger.log_struct(
            {
                "message": log_message,
                "level": log_level,
                "time": record["time"].isoformat(),
                "instance_id": instance_id,
                "trace_id": trace_id,
                "span_id": span_id,
            },
            severity=severity,
        )

    @staticmethod
    def get_logger():
        return logger


logger.alert = lambda message, *args, **kwargs: logger.log("ALERT", message, *args, **kwargs)
logger.emergency = lambda message, *args, **kwargs: logger.log("EMERGENCY", message, *args, **kwargs)
