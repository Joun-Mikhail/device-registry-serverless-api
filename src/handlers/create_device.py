import json

from src.models.device import Device
from src.repositories.device_repository import DeviceRepository
from src.utils.logging_config import configure_logger
from src.utils.response import success, error, internal_error
from src.validation.device_validator import validate_create_payload

logger = configure_logger(__name__)

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


def handler(event: dict, context) -> dict:
    request_id = getattr(context, "aws_request_id", "local")
    logger.info("CreateDevice invoked request_id=%s", request_id)

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
