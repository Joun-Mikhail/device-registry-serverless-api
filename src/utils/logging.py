"""Structured JSON logging for Lambda handlers.

Every log line is a single JSON object so CloudWatch Logs Insights can query it
by field. The `log_invocation` decorator emits one record per request with the
fields ops teams care about: timestamp, level, requestId, operation, method,
path, status, latencyMs, and userAgent.
"""
import functools
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Standard LogRecord attributes — anything else attached to a record is treated
# as a structured "extra" field and merged into the JSON payload.
_STD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    """Render each LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that emits JSON to stdout, configured from LOG_LEVEL.

    Idempotent: repeated calls for the same name reuse the single handler.
    """
    logger = logging.getLogger(name)
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def _request_fields(event: dict, context, operation: str, status, latency_ms: float) -> dict:
    http = (event or {}).get("requestContext", {}).get("http", {})
    return {
        "operation": operation,
        "requestId": getattr(context, "aws_request_id", "local"),
        "method": http.get("method") or (event or {}).get("httpMethod"),
        "path": http.get("path") or (event or {}).get("rawPath"),
        "status": status,
        "latencyMs": latency_ms,
        "userAgent": http.get("userAgent"),
    }


def log_invocation(operation: str):
    """Decorator: emit one structured JSON log line per Lambda invocation.

    Wraps a `handler(event, context)` function, times it, and logs the request
    with its result status and latency. Re-raises on unhandled exceptions after
    logging them at ERROR with a 500 status.
    """
    def decorator(handler):
        logger = get_logger(handler.__module__)

        @functools.wraps(handler)
        def wrapper(event, context):
            start = time.monotonic()
            try:
                response = handler(event, context)
            except Exception:
                latency_ms = round((time.monotonic() - start) * 1000, 2)
                logger.exception(
                    "request failed",
                    extra=_request_fields(event, context, operation, 500, latency_ms),
                )
                raise
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            status = response.get("statusCode") if isinstance(response, dict) else None
            logger.info(
                "request",
                extra=_request_fields(event, context, operation, status, latency_ms),
            )
            return response

        return wrapper

    return decorator
