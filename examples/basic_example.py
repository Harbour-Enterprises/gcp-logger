from gcp_logger import GCPLogger

# Basic usage
logger = GCPLogger().logger
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.notice("This is a notice")
logger.warning("This is a warning")
logger.error("This is an error")
logger.critical("This is a critical message")
logger.alert("This is an alert")
logger.emergency("This is an emergency")
