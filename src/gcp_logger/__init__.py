# File: gcp_logger/__init__.py

import inspect
import logging
import os
import sys
import time
from functools import lru_cache
from typing import Dict, Union

from google.cloud import logging as cloud_logging
from google.cloud import storage
from google.cloud.logging_v2.handlers import CloudLoggingHandler

# Lazy import of colorama
colorama = None

# Define custom logging levels
NOTICE = 300
ALERT = 700
EMERGENCY = 800

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


class CustomCloudLoggingHandler(CloudLoggingHandler):
    MAX_LOG_SIZE = 255 * 1024  # 256KB

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

    def __init__(self, client, default_bucket=None, environment=None):
        super().__init__(client, name="gcp-logger")
        self.default_bucket = default_bucket
        self.environment = environment
        self.gcp_storage_client = storage.Client() if default_bucket else None

    def emit(self, record):
        # 1. Set the severity first
        record.severity = self.CUSTOM_LOGGING_SEVERITY.get(record.levelno, "DEFAULT")

        # 2. Add custom attributes to the record
        self.add_custom_attributes(record)

        # 3. Format the message
        message = self.format_log_message(record)

        if len(message.encode("utf-8")) > self.MAX_LOG_SIZE:
            # Upload the full message to GCS
            gcs_uri = self.upload_large_log_to_gcs(message, record.__dict__)
            # Truncate the message and include the GCS URI
            message = self.truncate_log_message(message, gcs_uri)
            record.msg = message
            record.args = ()

        # Update the record's message to the formatted message
        record.msg = message
        record.args = ()

        # 4. Proceed with the standard CloudLoggingHandler emit
        super().emit(record)

    def add_custom_attributes(self, record):
        record.instance_id = getattr(record, "instance_id", "-")
        record.trace_id = getattr(record, "trace_id", "-")
        record.span_id = getattr(record, "span_id", "-")
        record.environment = self.environment or "production"
        record.filename = os.path.basename(getattr(record, "custom_filename", record.filename)).split(".")[0]
        record.funcName = getattr(record, "custom_func", record.funcName)
        record.lineno = getattr(record, "custom_lineno", record.lineno)

    def format_log_message(self, record):
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
        if not self.gcp_storage_client or not self.default_bucket:
            return None

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
            logging.error(f"Failed to upload log to GCS: {e}")
            return None

    def truncate_log_message(self, log_message: str, gcs_uri: str) -> str:
        truncation_notice = "... [truncated]"
        additional_text = f"\nMessage has been truncated. Full log at: {gcs_uri}"

        max_message_length = (
            self.MAX_LOG_SIZE - len(truncation_notice.encode("utf-8")) - len(additional_text.encode("utf-8"))
        )
        truncated_message = log_message.encode("utf-8")[:max_message_length].decode("utf-8", errors="ignore")

        return f"{truncated_message}{truncation_notice}{additional_text}"


class ContextAwareLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        # Find the first frame outside of the logging module
        frame = inspect.currentframe()
        while frame and (
            frame.f_code.co_filename.endswith("logging/__init__.py")
            or frame.f_code.co_filename.endswith("gcp_logger/__init__.py")
        ):
            frame = frame.f_back

        if frame:
            extra = extra or {}
            extra.update(
                {
                    "custom_filename": frame.f_code.co_filename,
                    "custom_lineno": frame.f_lineno,
                    "custom_func": frame.f_code.co_name,
                }
            )

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)

    def notice(self, msg, *args, **kwargs):
        self.log(NOTICE, msg, *args, **kwargs)

    def alert(self, msg, *args, **kwargs):
        self.log(ALERT, msg, *args, **kwargs)

    def emergency(self, msg, *args, **kwargs):
        self.log(EMERGENCY, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        self.info(f"SUCCESS: {msg}", *args, **kwargs)


class GCPLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

    def notice(self, msg, *args, **kwargs):
        self.log(NOTICE, msg, *args, **kwargs)

    def alert(self, msg, *args, **kwargs):
        self.log(ALERT, msg, *args, **kwargs)

    def emergency(self, msg, *args, **kwargs):
        self.log(EMERGENCY, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        self.info(f"SUCCESS: {msg}", *args, **kwargs)


class GCPLogger:
    def __init__(self, environment: str, default_bucket: str = None, logger_name: str = "cloud_logger"):
        self.environment = environment
        self.default_bucket = default_bucket or os.getenv("GCP_DEFAULT_BUCKET")
        self.instance_id = self.get_instance_id()
        self.logger_name = logger_name

        # Use our custom CallerInfoLogger class
        logging.setLoggerClass(ContextAwareLogger)
        self.logger = logging.getLogger(self.logger_name)
        logging.setLoggerClass(logging.Logger)  # Reset to default Logger class

        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.configure_handlers()

        # Use CloudLoggerAdapter
        self.logger = GCPLoggerAdapter(
            self.logger, extra={"instance_id": self.instance_id, "trace_id": "-", "span_id": "-"}
        )

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
        self.logger.setLevel(logging.DEBUG)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        if self.environment in ["localdev", "unittest"]:
            formatter = ConsoleColorFormatter(datefmt="%Y-%m-%d %H:%M:%S")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        else:
            # Use the Custom Cloud Logging handler
            client = cloud_logging.Client()
            cloud_handler = CustomCloudLoggingHandler(
                client, default_bucket=self.default_bucket, environment=self.environment
            )
            self.logger.addHandler(cloud_handler)

    def get_logger(self):
        return self.logger
