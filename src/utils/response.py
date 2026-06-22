import json
from typing import Optional
from utils.logging_config import configure_logger

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

# Error codes are stable identifiers clients can branch on (the message is for humans).
CODE_VALIDATION = "VALIDATION_ERROR"
CODE_NOT_FOUND = "NOT_FOUND"
CODE_CONFLICT = "CONFLICT"
CODE_INTERNAL = "INTERNAL_ERROR"


def success(body: dict | list, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps(body),
    }


def error(
    message: str,
    status_code: int = 400,
    code: str = CODE_VALIDATION,
    details: Optional[dict] = None,
) -> dict:
    """Return a standardized error envelope: {"error": {code, message, details?}}."""
    err: dict = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {
        "statusCode": status_code,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps({"error": err}),
    }


def not_found(resource: str = "Resource") -> dict:
    return error(f"{resource} not found.", status_code=404, code=CODE_NOT_FOUND)


def conflict(message: str) -> dict:
    return error(message, status_code=409, code=CODE_CONFLICT)


def internal_error(exc: Exception) -> dict:
    logger.exception("Unhandled exception: %s", exc)
    return error(
        "An internal error occurred. Please try again later.",
        status_code=500,
        code=CODE_INTERNAL,
    )
