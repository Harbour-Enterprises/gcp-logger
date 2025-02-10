from gcp_logger import GCPLogger, LogEnvironment

# Initialize logger with explicit environment
logger = GCPLogger(LogEnvironment.LOCAL).logger

# Example of using different log levels
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.notice("This is a notice")
logger.warning("This is a warning")
logger.error("This is an error")
logger.critical("This is a critical message")
logger.alert("This is an alert")
logger.emergency("This is an emergency")

# You can also initialize with string-based environment
production_logger = GCPLogger("prod").logger  # Will use GCP environment
development_logger = GCPLogger("dev").logger  # Will use LOCAL environment
