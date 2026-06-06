import json
import logging

from src.models.device import Device
from src.repositories.device_repository import DeviceRepository
from src.validation.device_validator import validate_create_payload
from src.utils.response import success, error, internal_error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


def handler(event: dict, context) -> dict:
    logger.info("CreateDevice invoked")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error("Request body must be valid JSON.")

    valid, message = validate_create_payload(body)
    if not valid:
        return error(message)

    device = Device(
        name=body["name"].strip(),
        type=body["type"],
        status=body.get("status", "active"),
        location=body.get("location"),
        metadata=body.get("metadata"),
    )

    try:
        created = _get_repository().create(device)
        return success(created.to_response(), status_code=201)
    except Exception as exc:
        return internal_error(exc)
