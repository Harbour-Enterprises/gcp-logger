# 💾 GCPLogger

Version: 1.1.1

GCPLogger is a Python package that provides seamless integration with Google Cloud Logging, offering enhanced logging capabilities for both cloud and local development environments.

## Features

- **Native Google Cloud Logging Integration**: Direct integration with Google Cloud's logging service
- **Environment-Aware**: Flexible environment configuration with enum-based setup
- **Enhanced Log Levels**: Additional severity levels like NOTICE, ALERT, and EMERGENCY
- **Trace Context Support**: Built-in handling of Trace ID and Span ID for request tracking
- **Instance ID Integration**: Automatic capture of instance IDs in cloud environments
- **Structured Logging**: JSON-formatted logs with standardized fields
- **Developer-Friendly**: Colorized console output for local development
- **Large Message Handling**: Automatic truncation of oversized log messages
- **Exception Tracking**: Enhanced error reporting with stack traces
- **Framework Integration**: Ready-to-use middleware for FastAPI and Flask

## Installation

```bash
pip install gcp-logger
```

## Usage

### Basic Usage

```python
from gcp_logger import GCPLogger, LogEnvironment

# Initialize logger with explicit environment (recommended)
logger = GCPLogger(LogEnvironment.LOCAL).logger

# Or use string-based initialization
dev_logger = GCPLogger("dev").logger     # Maps to LOCAL environment
prod_logger = GCPLogger("prod").logger    # Maps to GCP environment

# Use various log levels
logger.debug("Debug message")
logger.info("Info message")
logger.notice("Notice message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
logger.alert("Alert message")
logger.emergency("Emergency message")
```

### Environment Configuration

GCPLogger supports multiple ways to configure the logging environment:

```python
from gcp_logger import GCPLogger, LogEnvironment

# 1. Using LogEnvironment enum (recommended)
logger = GCPLogger(LogEnvironment.LOCAL).logger    # Local development
logger = GCPLogger(LogEnvironment.GCP).logger      # Google Cloud Platform
logger = GCPLogger(LogEnvironment.TEST).logger     # Testing environment

# 2. Using string-based configuration
logger = GCPLogger("dev").logger          # Maps to LOCAL
logger = GCPLogger("development").logger  # Maps to LOCAL
logger = GCPLogger("prod").logger         # Maps to GCP
logger = GCPLogger("production").logger   # Maps to GCP
logger = GCPLogger("staging").logger      # Maps to GCP
logger = GCPLogger("test").logger         # Maps to TEST

# 3. Using environment variable
# ENVIRONMENT=production python your_script.py
logger = GCPLogger().logger  # Will use environment variable or default to LOCAL
```

The environment determines the logging behavior:
- **LOCAL/TEST**: Colorized console output for development
- **GCP**: Structured JSON logging for Google Cloud Platform

### Framework Integration

#### FastAPI Example:

```python
from fastapi import FastAPI
from gcp_logger import GCPLogger, LogEnvironment
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()
gcp_logger = GCPLogger(LogEnvironment.LOCAL)  # For development
# gcp_logger = GCPLogger(LogEnvironment.GCP)  # For production
logger = gcp_logger.logger

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_header = request.headers.get("X-Cloud-Trace-Context")
        if trace_header:
            gcp_logger.update_log_record_factory(
                trace_id=trace_header.split("/")[0],
                span_id=trace_header.split("/")[1].split(";")[0]
            )
        return await call_next(request)

app.add_middleware(TraceMiddleware)
```

#### Flask Example:

```python
from flask import Flask, request
from gcp_logger import GCPLogger, LogEnvironment

app = Flask(__name__)
gcp_logger = GCPLogger(LogEnvironment.LOCAL)  # For development
# gcp_logger = GCPLogger("prod")              # For production (string-based)
logger = gcp_logger.logger

@app.before_request
def before_request():
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    if trace_header:
        gcp_logger.update_log_record_factory(
            trace_id=trace_header.split("/")[0],
            span_id=trace_header.split("/")[1].split(";")[0]
        )
```

## Comparison with Other Logging Libraries

GCPLogger combines the best features of popular Python logging libraries with native Google Cloud Platform integration. Here's how it compares to other logging solutions:

| Feature                   | GCP Logger | Loguru | FastLogging | stdlib logging |
|---------------------------|------------|--------|-------------|----------------|
| GCP Integration           | ✅         | ❌     | ❌          | ❌             |
| Custom Log Levels         | ✅         | ✅     | ❌          | ✅             |
| Colorized Console Output  | ✅         | ✅     | ❌          | ❌             |
| Structured Logging        | ✅         | ✅     | ✅          | ❌             |
| Async Support             | ✅         | ✅     | ✅          | ❌             |
| Instance ID Capture       | ✅         | ❌     | ❌          | ❌             |
| Trace/Span ID Support     | ✅         | ❌     | ❌          | ❌             |
| Large Message Handling    | ✅         | ❌     | ❌          | ❌             |
| Performance (High Volume) | Good       | Good   | Excellent   | Fair           |
| Memory Usage             | Low        | Low    | Very Low    | Low            |
| Ease of Use              | High       | High   | Medium      | Medium         |
| Cloud-Native Design      | ✅         | ❌     | ❌          | ❌             |

### Key Advantages of GCP Logger

1. **Native GCP Integration**: Seamlessly works with Google Cloud Logging and other GCP services
2. **Cloud-Native Features**: Automatic capture of Instance ID, support for Trace and Span IDs
3. **Flexible Log Levels**: Includes custom levels like NOTICE, ALERT, and EMERGENCY
4. **Development-Friendly**: Offers colorized console output for improved readability during local development
5. **Balanced Performance**: Maintains good performance in both normal and high-volume scenarios
6. **Comprehensive Solution**: Combines the best features of popular logging libraries with GCP-specific enhancements

## Key Features

### Environment-Based Configuration

GCPLogger automatically detects and configures itself based on the environment:

- **Cloud Environment**: Uses structured JSON logging format compatible with Google Cloud Logging
- **Local Development**: Provides colorized console output for better readability

### Custom Log Levels

In addition to standard log levels, GCPLogger provides:

- **NOTICE**: For normal but significant events
- **ALERT**: For situations requiring immediate attention
- **EMERGENCY**: For system-wide catastrophic failures

### Trace Context Support

Automatically captures and includes trace context in logs when running in Google Cloud environments:

- Trace ID for request tracing
- Span ID for operation tracking
- Instance ID for container/VM identification

### Structured Logging

All logs are automatically structured with:

- Timestamp
- Severity level
- Source location (file, line, function)
- Trace context (when available)
- Error reporting information (for exceptions)

## Development

To set up the development environment:

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -r requirements-test.txt
   ```
3. Run tests:
   ```bash
   pytest tests
   ```

### Running Performance Tests

```bash
pytest tests -v -m performance
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
