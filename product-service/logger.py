"""Structured logging configuration for Product Service.

Logs are written both to stdout (for `docker compose logs`) and to a
dedicated file under logs/ so that Promtail can tail it and ship it to Loki.
Each log line is emitted as a single JSON object, which makes it trivially
parsable by Loki/Grafana (structured logging).
"""
import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def setup_logger(service_name: str, log_file: str) -> logging.Logger:
    """Creates a logger that writes structured JSON logs to stdout and a file.

    Args:
        service_name: name used as a "service" field in every log line.
        log_file: path (relative to the container workdir) of the log file,
            e.g. "logs/product.log". The parent directory is created if
            needed so the file exists as soon as the container starts, which
            lets Promtail pick it up immediately.
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid attaching duplicate handlers if setup_logger is called twice
    # (e.g. under the Flask reloader).
    if logger.handlers:
        return logger

    formatter = JsonFormatter(service_name)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
