from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from gcp_logger import GCPLogger

# Initialize GCPLogger
gcp_logger = GCPLogger(
    environment="localdev",
    default_bucket="my-gcs-bucket",
    debug_logs=True,  # Set to False in production
)
logger = gcp_logger.get_logger()

app = FastAPI()


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_header = request.headers.get("X-Cloud-Trace-Context")

        # Update trace context for this request
        gcp_logger.update_trace_context(trace_header)

        response = await call_next(request)
        return response


app.add_middleware(TraceMiddleware)


def nested_function(item_id: int):
    logger.info(f"Inside nested_function for item_id: {item_id}")
    return f"Processed item {item_id}"


async def async_nested_function(item_id: int):
    logger.info(f"Inside async_nested_function for item_id: {item_id}")
    return f"Async processed item {item_id}"


@app.get("/")
async def root(request: Request):
    logger.info("Handling root request")
    nested_result = nested_function(0)
    logger.info(f"Result from nested function: {nested_result}")
    return {"message": "Hello World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, request: Request):
    logger.info(f"Fetching item with id: {item_id}")
    nested_result = nested_function(item_id)
    logger.info(f"Result from nested function: {nested_result}")
    async_result = await async_nested_function(item_id)
    logger.info(f"Result from async nested function: {async_result}")
    return {"item_id": item_id, "nested_result": nested_result, "async_result": async_result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
