# File: gcp_logger/__init__.py

import logging
import os
import sys
import time
from datetime import datetime, timezone
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


class ConsoleColorFormatter(logging.Formatter):
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


class GCPLogFormatter(logging.Formatter):
    """
    Formatter for Google Cloud environments that structures and sends log records to GCP.
    """

    SEVERITY_MAPPING = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        NOTICE: "NOTICE",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
        ALERT: "ALERT",
        logging.FATAL: "EMERGENCY",
    }

    MAX_LOG_SIZE = 255 * 1024  # 256KB max size for log messages in Google Cloud Logging

    def __init__(self, environment, default_bucket, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environment = environment
        self.default_bucket = default_bucket
        self.gcp_logging_client = cloud_logging.Client()
        self.gcp_logger = self.gcp_logging_client.logger("gcp_logger")
        self.gcp_storage_client = storage.Client()

    def format(self, record):
        formatted_message = self.format_log_message(record)
        if len(formatted_message.encode("utf-8")) > self.MAX_LOG_SIZE:
            gcs_uri = self.upload_large_log_to_gcs(formatted_message, record.__dict__)
            formatted_message = self.truncate_log_message(formatted_message, gcs_uri)
        self.send_log_to_gcp(record, formatted_message)

    def format_log_message(self, record):
        log_format = (
            "{instance_id} | {trace_id} | {span_id} | "
            "{process_id} | {thread_id} | "
            "{severity:<8} | "
            "{logger_name}:{function}:{line} - "
            "{message}"
        )

        extra = getattr(record, "extra", {})
        return log_format.format(
            instance_id=extra.get("instance_id", "-"),
            trace_id=extra.get("trace_id", "-"),
            span_id=extra.get("span_id", "-"),
            process_id=record.process,
            thread_id=record.thread,
            severity=record.levelname,
            logger_name=record.name,
            function=record.funcName,
            line=record.lineno,
            message=record.getMessage(),
        )

    def send_log_to_gcp(self, record, formatted_message):
        severity = self.SEVERITY_MAPPING.get(record.levelno, "DEFAULT")

        log_entry = {
            "message": formatted_message,
            "severity": severity,
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "instance_id": getattr(record, "instance_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
            "labels": {
                "instance_id": getattr(record, "instance_id", "-"),
                "environment": self.environment,
            },
        }

        self.gcp_logger.log_struct(log_entry, severity=severity)

    def upload_large_log_to_gcs(self, log_message: str, record_dict: dict) -> Union[str, None]:
        storage_bucket = self.gcp_storage_client.bucket(self.default_bucket)
        timestamp = int(time.time())

        parts = [
            timestamp,
            record_dict.get("instance_id", "-"),
            record_dict.get("trace_id", "-"),
            record_dict.get("span_id", "-"),
        ]
        blob_name = "logs/" + "_".join(map(str, parts)) + ".log"
        blob = storage_bucket.blob(blob_name)

        try:
            blob.upload_from_string(log_message)
            return f"gs://{self.default_bucket}/{blob_name}"
        except Exception as e:
            print(f"Failed to upload log to GCS: {e}")  # Using print as we can't use the logger here
            return None

    def truncate_log_message(self, log_message: str, gcs_uri: str | None) -> str:
        truncation_notice = "... [truncated]"
        additional_text_template = "\nMessage has been truncated, please check: {gcs_uri} for full log message"

        truncation_notice_length = len(truncation_notice.encode("utf-8"))
        gcs_uri_length = len(gcs_uri.encode("utf-8")) if gcs_uri else 0
        additional_text_length = len(additional_text_template.encode("utf-8")) - len("{gcs_uri}") + gcs_uri_length
        max_message_length = self.MAX_LOG_SIZE - truncation_notice_length - additional_text_length

        truncated_message = log_message.encode("utf-8")[:max_message_length].decode("utf-8", errors="ignore")

        if gcs_uri:
            truncated_message = f"{truncated_message}{truncation_notice}\nMessage has been truncated, please check: {gcs_uri} for full log message"
        else:
            truncated_message = f"{truncated_message}{truncation_notice}"

        return truncated_message


class ContextAwareLogger(logging.LoggerAdapter):
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
    def __init__(self, environment: str, default_bucket: str = None, logger_name: str = "gcp_logger"):
        self.environment = environment
        self.default_bucket = default_bucket or os.getenv("GCP_DEFAULT_BUCKET")
        self.instance_id = self.get_instance_id()
        self.logger_name = logger_name

        self.base_logger = logging.getLogger(self.logger_name)
        self.base_logger.setLevel(logging.DEBUG)
        self.base_logger.propagate = False
        self.configure_handlers()

        self.logger = ContextAwareLogger(
            self.base_logger, extra={"instance_id": self.instance_id, "trace_id": "-", "span_id": "-"}
        )

        print(f"Logger initialized with level: {self.logger.logger.level}")
        print(f"Logger handlers: {self.logger.logger.handlers}")

    def get_instance_id(self):
        if os.getenv("GAE_INSTANCE"):
            return os.getenv("GAE_INSTANCE")[:10]
        elif os.getenv("K_SERVICE"):
            return f"{os.getenv('K_SERVICE')}-{os.getenv('K_REVISION')}"[:9]
        elif os.getenv("FUNCTION_NAME"):
            return os.getenv("FUNCTION_NAME")[:10]
        else:
            return "-"

    def configure_handlers(self):
        self.base_logger.setLevel(logging.DEBUG)

        for handler in self.base_logger.handlers[:]:
            self.base_logger.removeHandler(handler)

        if self.environment in ["localdev", "unittest"]:
            formatter = ConsoleColorFormatter(datefmt="%Y-%m-%d %H:%M:%S")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.base_logger.addHandler(console_handler)
        else:
            formatter = GCPLogFormatter(
                environment=self.environment, default_bucket=self.default_bucket, datefmt="%Y-%m-%d %H:%M:%S"
            )
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            self.base_logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger
