import json
import logging

from src.repositories.device_repository import DeviceRepository
from src.validation.device_validator import validate_update_payload
from src.utils.response import success, error, not_found, internal_error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


def handler(event: dict, context) -> dict:
    device_id = event.get("pathParameters", {}).get("deviceId")
    logger.info("UpdateDevice invoked for deviceId=%s", device_id)

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error("Request body must be valid JSON.")

    valid, message = validate_update_payload(body)
    if not valid:
        return error(message)

    # Strip whitespace from name if provided
    if "name" in body and isinstance(body["name"], str):
        body["name"] = body["name"].strip()

    try:
        updated = _get_repository().update(device_id, body)
        if updated is None:
            return not_found("Device")
        return success(updated.to_response())
    except Exception as exc:
        return internal_error(exc)
