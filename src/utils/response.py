import json
import logging

logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Content-Type": "application/json",
}


def success(body: dict | list, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def error(message: str, status_code: int = 400) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps({"error": message}),
    }


def not_found(resource: str = "Resource") -> dict:
    return error(f"{resource} not found.", status_code=404)


def internal_error(exc: Exception) -> dict:
    logger.exception("Unhandled exception: %s", exc)
    return error("An internal error occurred. Please try again later.", status_code=500)
