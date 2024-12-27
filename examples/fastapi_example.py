# examples/fastapi_example.py
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from gcp_logger import GCPLogger

# Initialize logger
gcp_logger = GCPLogger()
logger = gcp_logger.logger


class TraceMiddleware(BaseHTTPMiddleware):
    """Middleware to handle trace context for request tracking."""

    async def dispatch(self, request: Request, call_next):
        # Extract trace context from headers
        trace_header = request.headers.get("X-Cloud-Trace-Context")

        if trace_header:
            # Update trace context for this request
            gcp_logger.update_log_record_factory(
                trace_id=trace_header.split("/")[0] if "/" in trace_header else "-",
                span_id=trace_header.split("/")[1].split(";")[0] if "/" in trace_header else "-",
            )

        # Process the request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}", exc_info=True)
            raise


app = FastAPI()
app.add_middleware(TraceMiddleware)


@app.get("/")
async def root():
    """Root endpoint demonstrating basic logging."""
    logger.info("Processing request to root endpoint")
    return {"message": "Hello World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    """Endpoint demonstrating structured logging with parameters."""
    logger.info(f"Processing request for item ID: {item_id}")

    try:
        # Simulate some processing
        if item_id == 0:
            raise ValueError("Item ID cannot be zero")

        logger.notice(f"Successfully retrieved item {item_id}")
        return {"item_id": item_id, "status": "success"}

    except Exception as e:
        logger.error(f"Failed to process item {item_id}: {str(e)}", exc_info=True)
        raise


@app.get("/test-levels")
async def test_log_levels():
    """Endpoint demonstrating different log levels."""
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.notice("This is a notice")
    logger.warning("This is a warning")
    logger.error("This is an error")
    logger.critical("This is a critical message")
    logger.alert("This is an alert")
    logger.emergency("This is an emergency")
    return {"message": "Logged all levels"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI application")
    uvicorn.run(app, host="0.0.0.0", port=8000)
