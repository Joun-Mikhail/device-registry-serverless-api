import json
from src.utils.logging_config import configure_logger

logger = configure_logger(__name__)

# Standard response headers returned on every API call.
# Access-Control-Allow-Origin is set to * because this is a dev-only endpoint
# with no authentication layer. Restrict to a specific origin in production.
RESPONSE_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
}


def success(body: dict | list, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps(body),
    }


def error(message: str, status_code: int = 400) -> dict:
    return {
        "statusCode": status_code,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps({"error": message}),
    }


def not_found(resource: str = "Resource") -> dict:
    return error(f"{resource} not found.", status_code=404)


def internal_error(exc: Exception) -> dict:
    logger.exception("Unhandled exception: %s", exc)
    return error("An internal error occurred. Please try again later.", status_code=500)
