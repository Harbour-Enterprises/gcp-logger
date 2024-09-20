# File: gcp_logger/levels.py

import logging

# Define custom logging levels
NOTICE = 300
ALERT = 700
EMERGENCY = 800

# Add custom levels to the logging module
logging.addLevelName(NOTICE, "NOTICE")
logging.addLevelName(ALERT, "ALERT")
logging.addLevelName(EMERGENCY, "EMERGENCY")
