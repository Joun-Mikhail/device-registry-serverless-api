import json

from repositories.device_repository import DeviceRepository
from utils.logging_config import configure_logger
from utils.response import error, success, not_found, internal_error
from validation.device_validator import validate_update_payload

logger = configure_logger(__name__)

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


def handler(event: dict, context) -> dict:
    request_id = getattr(context, "aws_request_id", "local")
    device_id = event.get("pathParameters", {}).get("deviceId")
    logger.info("UpdateDevice invoked request_id=%s deviceId=%s", request_id, device_id)

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error("Request body must be valid JSON.")

    valid, message = validate_update_payload(body)
    if not valid:
        return error(message)

    # Build an immutable copy so the caller's dict is never mutated.
    updates = dict(body)
    if "name" in updates and isinstance(updates["name"], str):
        updates["name"] = updates["name"].strip()

    try:
        updated = _get_repository().update(device_id, updates)
        if updated is None:
            return not_found("Device")
        return success(updated.to_response())
    except Exception as exc:
        return internal_error(exc)
