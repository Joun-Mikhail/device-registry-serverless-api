from repositories.device_repository import DeviceRepository
from utils.logging_config import configure_logger
from utils.response import error, success, not_found, internal_error

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
    logger.info("DeleteDevice invoked request_id=%s deviceId=%s", request_id, device_id)

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        deleted = _get_repository().delete(device_id)
        if not deleted:
            return not_found("Device")
        return success({"message": f"Device '{device_id}' deleted successfully."})
    except Exception as exc:
        return internal_error(exc)
