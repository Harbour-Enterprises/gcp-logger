# 💾 GCPLogger

Version: 0.1.3

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
| Memory Usage              | Low        | Low    | Very Low    | Low            |
| Ease of Use               | High       | High   | Medium      | Medium         |
| Cloud-Native Design       | ✅         | ❌     | ❌          | ❌             |

### Key Advantages of GCP Logger

1. **Native GCP Integration**: Seamlessly works with Google Cloud Logging and other GCP services.
2. **Cloud-Native Features**: Automatic capture of Instance ID, support for Trace and Span IDs.
3. **Flexible Log Levels**: Includes custom levels like NOTICE, ALERT, and EMERGENCY.
4. **Large Message Handling**: Efficiently manages oversized log messages via Google Cloud Storage.
5. **Development-Friendly**: Offers colorized console output for improved readability during local development.
6. **Balanced Performance**: Maintains good performance in both normal and high-volume scenarios.
7. **Comprehensive Logging Solution**: Combines the best features of popular logging libraries with GCP-specific enhancements.

## Development

To set up the development environment:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest tests`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
