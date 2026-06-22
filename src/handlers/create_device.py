import json

from models.device import Device
from repositories.device_repository import DeviceRepository, DeviceAlreadyExistsError
from utils.logging import log_invocation
from utils.response import success, error, conflict, internal_error
from validation.device_validator import validate_create_payload

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


@log_invocation("CreateDevice")
def handler(event: dict, context) -> dict:
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
    except DeviceAlreadyExistsError:
        return conflict("A device with this ID already exists.")
    except Exception as exc:
        return internal_error(exc)
