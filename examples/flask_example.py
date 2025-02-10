# examples/flask_example.py
from flask import Flask, jsonify, request

from gcp_logger import GCPLogger, LogEnvironment

# Initialize Flask app
app = Flask(__name__)

# Initialize logger
# For local development, you can use either the enum or string-based initialization
gcp_logger = GCPLogger(LogEnvironment.LOCAL)  # Using enum (recommended)
# Alternative string-based initialization:
# gcp_logger = GCPLogger("dev")  # Will also use LOCAL environment
logger = gcp_logger.logger


@app.before_request
def before_request():
    """Update trace context before each request."""
    trace_header = request.headers.get("X-Cloud-Trace-Context")

    if trace_header:
        # Update trace context for this request
        gcp_logger.update_log_record_factory(
            trace_id=trace_header.split("/")[0] if "/" in trace_header else "-",
            span_id=trace_header.split("/")[1].split(";")[0] if "/" in trace_header else "-",
        )


@app.after_request
def after_request(response):
    """Log response status after each request."""
    logger.info(f"Request completed with status: {response.status}")
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler with error logging."""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500


@app.route("/")
def root():
    """Root endpoint demonstrating basic logging."""
    logger.info("Processing request to root endpoint")
    return jsonify({"message": "Hello World"})


@app.route("/items/<int:item_id>")
def get_item(item_id):
    """Endpoint demonstrating structured logging with parameters."""
    logger.info(f"Processing request for item ID: {item_id}")

    try:
        # Simulate some processing
        if item_id == 0:
            raise ValueError("Item ID cannot be zero")

        logger.notice(f"Successfully retrieved item {item_id}")
        return jsonify({"item_id": item_id, "status": "success"})

    except ValueError as e:
        logger.warning(f"Invalid item request: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to process item {item_id}: {str(e)}", exc_info=True)
        raise


@app.route("/test-levels")
def test_log_levels():
    """Endpoint demonstrating different log levels."""
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.notice("This is a notice")
    logger.warning("This is a warning")
    logger.error("This is an error")
    logger.critical("This is a critical message")
    logger.alert("This is an alert")
    logger.emergency("This is an emergency")
    return jsonify({"message": "Logged all levels"})


if __name__ == "__main__":
    logger.info("Starting Flask application")
    app.run(host="0.0.0.0", port=8080, debug=True)
