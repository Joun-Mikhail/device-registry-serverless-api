import logging

from src.repositories.device_repository import DeviceRepository
from src.utils.response import success, not_found, internal_error

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
    logger.info("GetDevice invoked for deviceId=%s", device_id)

    if not device_id:
        from src.utils.response import error
        return error("'deviceId' path parameter is required.")

    try:
        device = _get_repository().get(device_id)
        if device is None:
            return not_found("Device")
        return success(device.to_response())
    except Exception as exc:
        return internal_error(exc)
