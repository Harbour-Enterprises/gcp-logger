from superlogs import SuperLogs

# Initialize SuperLogs
superlogs = SuperLogs(environment="localdev", default_bucket="my-gcs-bucket")

# Get the logger instance
logger = superlogs.get_logger()

# Use the logger
logger.info("This is an info log")
logger.error("This is an error log")
logger.debug("This is a debug log")
logger.warning("This is a warning log")
logger.success("This is a success log")
logger.critical("This is a critical log")
logger.alert("This is an alert log")
logger.emergency("This is an emergency log")