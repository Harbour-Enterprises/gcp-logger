# 💾 GCPLogger

Version: 0.0.8

GCPLogger is a Python package that provides a flexible and powerful logging solution, integrating with Google Cloud Logging and supporting various environments.

## Features

- Easy integration with Google Cloud Logging
- Full support for GCP Logging severities
- Support for local development and production environments
- Automatic handling of large log messages via Google Cloud Storage
- Custom log levels (ALERT, EMERGENCY)
- Colorized console output for local development
- Automatic capture of Instance ID for AppEngine, Cloud Run, and Cloud Functions services
- Support for Trace ID and Span ID when running in Google Cloud environments

## Installation

```bash
pip install gcp-logger
```

## Usage

Basic usage:

```python
from gcp_logger import GCPLogger

# Initialize GCPLogger
gcp_logger = GCPLogger(environment="production", default_bucket="my-gcs-bucket")

# Get the logger instance
logger = gcp_logger.get_logger()

# Use the logger
logger.info("This is an info log")
logger.error("This is an error log")
```

For more examples, see the `examples/` directory.

## Development

To set up the development environment:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest tests`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.