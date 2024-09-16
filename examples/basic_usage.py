from gcp_logger import GCPLogger

# Initialize GCPLogger
gcp_logger = GCPLogger(environment="localdev", default_bucket="my-gcs-bucket")

# Get the logger instance
logger = gcp_logger.get_logger()

# Use the logger with all levels from lowest to highest
logger.debug("This is a debug log")
logger.info("This is an info log")
logger.notice("This is a notice log")
logger.warning("This is a warning log")
logger.error("This is an error log")
logger.critical("This is a critical log")
logger.alert("This is an alert log")
logger.emergency("This is an emergency log")
logger.success("This is a success log")
