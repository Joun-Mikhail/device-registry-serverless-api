import json

from models.device import DEFAULT_STATUS, Device
from repositories.device_repository import DeviceAlreadyExistsError, get_repository
from utils.logging import log_invocation
from utils.response import conflict, error, internal_error, success
from validation.device_validator import validate_create_payload


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
        status=body.get("status", DEFAULT_STATUS),
        location=body.get("location"),
        metadata=body.get("metadata"),
    )

    try:
        created = get_repository().create(device)
        return success(created.to_response(), status_code=201)
    except DeviceAlreadyExistsError:
        return conflict("A device with this ID already exists.")
    # Boundary handler: converts any unexpected error into a 500 so stack traces
    # are logged but never reach the caller (README → Security → Error isolation).
    except Exception as exc:  # noqa: BLE001
        return internal_error(exc)
