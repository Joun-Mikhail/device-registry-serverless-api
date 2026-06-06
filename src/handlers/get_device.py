from src.repositories.device_repository import DeviceRepository
from src.utils.logging_config import configure_logger
from src.utils.response import error, success, not_found, internal_error

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
    logger.info("GetDevice invoked request_id=%s deviceId=%s", request_id, device_id)

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        device = _get_repository().get(device_id)
        if device is None:
            return not_found("Device")
        return success(device.to_response())
    except Exception as exc:
        return internal_error(exc)
