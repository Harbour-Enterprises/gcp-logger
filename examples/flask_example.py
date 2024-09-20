# File: examples/flask_example.py

from flask import Flask, jsonify, request

from gcp_logger import GCPLogger

# Initialize Flask app
app = Flask(__name__)

# Initialize GCPLogger
gcp_logger = GCPLogger(
    environment="localdev",
    default_bucket="my-gcs-bucket",
    debug_logs=True,  # Set to False in production
)
logger = gcp_logger.get_logger()


def nested_function(item_id: int):
    logger.info(f"Inside nested_function for item_id: {item_id}")
    return f"Processed item {item_id}"


@app.before_request
def before_request():
    gcp_logger.update_trace_context(request.headers.get("X-Cloud-Trace-Context"))


@app.route("/")
def root():
    logger.info("Handling root request")
    nested_result = nested_function(0)
    logger.info(f"Result from nested function: {nested_result}")
    return jsonify({"message": "Hello World"})


@app.route("/items/<int:item_id>")
def get_item(item_id):
    logger.info(f"Fetching item with id: {item_id}")
    nested_result = nested_function(item_id)
    logger.info(f"Result from nested function: {nested_result}")
    return jsonify({"item_id": item_id, "nested_result": nested_result})


@app.errorhandler(404)
def not_found(error):
    logger.warning(f"Invalid path: {request.path}")
    return jsonify({"error": "Not Found"}), 404


@app.after_request
def after_request(response):
    # Log the outgoing response
    logger.info(f"Sending response: {response.status}")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
