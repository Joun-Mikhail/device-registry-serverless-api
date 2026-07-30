import json

from repositories.device_repository import get_repository
from utils.logging import log_invocation
from utils.response import VALIDATION_FALLBACK, error, internal_error, not_found, success
from validation.device_validator import validate_update_payload


@log_invocation("UpdateDevice")
def handler(event: dict, context) -> dict:
    # API Gateway sends pathParameters as null (not omitted) when a route matches
    # with no path values, so `.get(k, {})` is not enough — the default only
    # applies when the key is absent. Same `or {}` idiom as queryStringParameters.
    device_id = (event.get("pathParameters") or {}).get("deviceId")

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error("Request body must be valid JSON.")

    valid, message = validate_update_payload(body)
    if not valid:
        return error(message or VALIDATION_FALLBACK)

    # Build an immutable copy so the caller's dict is never mutated.
    updates = dict(body)
    if "name" in updates and isinstance(updates["name"], str):
        updates["name"] = updates["name"].strip()

    try:
        updated = get_repository().update(device_id, updates)
        if updated is None:
            return not_found("Device")
        return success(updated.to_response())
    # Boundary handler: converts any unexpected error into a 500 so stack traces
    # are logged but never reach the caller (README → Security → Error isolation).
    except Exception as exc:  # noqa: BLE001
        return internal_error(exc)
