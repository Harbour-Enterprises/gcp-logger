# File: gcp_logger/__init__.py

import logging
import os
import sys
import time
from functools import lru_cache
from typing import Dict, Union

from google.cloud import logging as cloud_logging
from google.cloud import storage

# Lazy import of colorama
colorama = None

# Define custom logging levels
NOTICE = 25
ALERT = 70
EMERGENCY = 80

# Add custom levels
logging.addLevelName(NOTICE, "NOTICE")
logging.addLevelName(ALERT, "ALERT")
logging.addLevelName(EMERGENCY, "EMERGENCY")


class ColorizedFormatter(logging.Formatter):
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

    def format(self, record):
        color_code = self.color_codes.get(record.levelno, self.color_codes[logging.DEBUG])
        reset = colorama.Style.RESET_ALL

        formatted_time = colorama.Fore.GREEN + self.formatTime(record, self.datefmt) + reset
        formatted_level = color_code + f"{record.levelname:<8}" + reset

        # Use the custom fields if available, otherwise fall back to the standard ones
        func = getattr(record, "custom_func", record.funcName)
        filename = getattr(record, "custom_filename", record.filename)
        lineno = getattr(record, "custom_lineno", record.lineno)

        formatted_name = colorama.Fore.CYAN + f"{record.name}:{func}:{lineno}" + reset
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


class CustomLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

    def _log_with_location(self, level, msg, *args, **kwargs):
        # Get caller's frame
        frame = sys._getframe(2)
        # Create a new dict for extra to avoid modifying the existing one
        new_extra = {
            "custom_func": frame.f_code.co_name,
            "custom_filename": frame.f_code.co_filename,
            "custom_lineno": frame.f_lineno,
        }
        if "extra" in kwargs:
            kwargs["extra"].update(new_extra)
        else:
            kwargs["extra"] = new_extra
        self.log(level, msg, *args, **kwargs)

    def notice(self, msg, *args, **kwargs):
        self._log_with_location(NOTICE, msg, *args, **kwargs)

    def alert(self, msg, *args, **kwargs):
        self._log_with_location(ALERT, msg, *args, **kwargs)

    def emergency(self, msg, *args, **kwargs):
        self._log_with_location(EMERGENCY, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        self._log_with_location(logging.INFO, f"SUCCESS: {msg}", *args, **kwargs)


class GCPLogger:
    PYTHON_LEVEL_TO_GCP_SEVERITY = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        NOTICE: "NOTICE",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
        ALERT: "ALERT",
        logging.FATAL: "EMERGENCY",
    }

    LOGGING_MAX_SIZE = 255 * 1024  # 256KB max size for log messages in Google Cloud Logging

    def __init__(self, environment: str, default_bucket: str = None):
        self.environment = environment
        self.default_bucket = default_bucket or os.getenv("GCP_DEFAULT_BUCKET")
        self.instance_id = self._get_instance_id()

        # Initialize Google Cloud clients
        self.client = cloud_logging.Client()
        self.cloud_logger = self.client.logger("gcp_logger")

        self.logger = logging.getLogger("gcp_logger")
        self.logger.setLevel(logging.DEBUG)  # Ensure we capture all log levels
        self.logger.propagate = False  # Prevent double logging
        self.setup_logging()

        # Wrap logger with CustomLoggerAdapter after setup
        self.logger = CustomLoggerAdapter(
            self.logger, extra={"instance_id": self.instance_id, "trace_id": "-", "span_id": "-"}
        )

        print(f"Logger initialized with level: {self.logger.logger.level}")
        print(f"Logger handlers: {self.logger.logger.handlers}")

    def _get_instance_id(self):
        # Check for App Engine
        if os.getenv("GAE_INSTANCE"):
            return os.getenv("GAE_INSTANCE")[:10]

        # Check for Cloud Run
        elif os.getenv("K_SERVICE"):
            return f"{os.getenv('K_SERVICE')}-{os.getenv('K_REVISION')}"[:9]

        # Check for Cloud Functions
        elif os.getenv("FUNCTION_NAME"):
            return os.getenv("FUNCTION_NAME")[:10]

        # Default case
        else:
            return "-"

    def setup_logging(self):
        self.logger.setLevel(logging.DEBUG)  # Set to lowest level to capture all logs

        if self.environment in ["localdev", "unittest"]:
            formatter = ColorizedFormatter(datefmt="%Y-%m-%d %H:%M:%S.%f")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        else:
            gcp_handler = cloud_logging.handlers.CloudLoggingHandler(self.client)
            self.logger.addHandler(gcp_handler)

    def get_logger(self):
        return self.logger

    def log(self, level: int, message: str, **kwargs):
        extra = {
            "instance_id": self.instance_id,
            "trace_id": kwargs.get("trace_id", "-"),
            "span_id": kwargs.get("span_id", "-"),
        }

        if len(message.encode("utf-8")) > self.LOGGING_MAX_SIZE:
            gsutil_uri = self.save_large_log_to_gcs(message, **extra)
            message = self.google_cloud_log_truncate(message, gsutil_uri)

        if self.environment in ["localdev", "unittest"]:
            self.logger.log(level, message, extra=extra)
        else:
            self.google_cloud_log_sink(level, message, extra)

    @staticmethod
    def google_cloud_log_format(record: dict) -> str:
        custom_format = (
            "{instance_id} | {trace_id} | {span_id} | "
            "{process_id} | {thread_id} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        )

        formatted_record = {
            "instance_id": record["extra"].get("instance_id", "-"),
            "trace_id": record["extra"].get("trace_id", "-"),
            "span_id": record["extra"].get("span_id", "-"),
            "process_id": record["process"].id,
            "thread_id": record["thread"].id,
            "level": record["level"].name,
            "name": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        return custom_format.format(**formatted_record)

    def google_cloud_log_truncate(self, log_message: str, gsutil_uri: str | None) -> str:
        truncation_notice = "... [truncated]"
        additional_text_template = "\nMessage has been truncated, please check: {gsutil_uri} for full log message"

        truncation_notice_length = len(truncation_notice.encode("utf-8"))
        gsutil_uri_length = len(gsutil_uri.encode("utf-8")) if gsutil_uri else 0
        additional_text_length = len(additional_text_template.encode("utf-8")) - len("{gsutil_uri}") + gsutil_uri_length
        max_message_length = self.LOGGING_MAX_SIZE - truncation_notice_length - additional_text_length

        truncated_message = log_message.encode("utf-8")[:max_message_length].decode("utf-8", errors="ignore")

        if gsutil_uri:
            truncated_message = f"{truncated_message}{truncation_notice}\nMessage has been truncated, please check: {gsutil_uri} for full log message"
        else:
            truncated_message = f"{truncated_message}{truncation_notice}"

        return truncated_message

    def save_large_log_to_gcs(self, log_message: str, **kwargs) -> Union[str, None]:
        storage_client = storage.Client()
        storage_bucket = storage_client.bucket(self.default_bucket)
        timestamp = int(time.time())

        parts = [timestamp, kwargs.get("instance_id", "-"), kwargs.get("trace_id", "-"), kwargs.get("span_id", "-")]
        blob_name = "logs/" + "_".join(map(str, parts)) + ".log"
        blob = storage_bucket.blob(blob_name)

        try:
            blob.upload_from_string(log_message)
            return f"gs://{self.default_bucket}/{blob_name}"
        except Exception as e:
            self.logger.error(f"Failed to upload log to GCS: {e}")
            return None

    def google_cloud_log_sink(self, level: int, message: str, extra: dict):
        severity = self.PYTHON_LEVEL_TO_GCP_SEVERITY.get(level, "DEFAULT")

        log_entry = {
            "message": message,
            "severity": severity,
            "extra": extra,
        }

        # Add additional context that might be useful for GCP logging
        log_entry["labels"] = {
            "instance_id": extra.get("instance_id", "-"),
            "environment": self.environment,
        }

        if extra.get("trace_id") != "-":
            log_entry["trace"] = extra["trace_id"]
        if extra.get("span_id") != "-":
            log_entry["span_id"] = extra["span_id"]

        self.cloud_logger.log_struct(log_entry)
