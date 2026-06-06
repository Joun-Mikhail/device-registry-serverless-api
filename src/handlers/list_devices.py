from repositories.device_repository import DeviceRepository
from utils.logging_config import configure_logger
from utils.response import success, internal_error

logger = configure_logger(__name__)

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


def handler(event: dict, context) -> dict:
    request_id = getattr(context, "aws_request_id", "local")
    logger.info("ListDevices invoked request_id=%s", request_id)

    try:
        # NOTE: Uses DynamoDB Scan — acceptable for dev datasets under ~1,000 items.
        # At scale, replace with a GSI on 'type' or 'status' + Query + pagination.
        devices = _get_repository().list_all()
        return success({"items": [d.to_response() for d in devices], "count": len(devices)})
    except Exception as exc:
        return internal_error(exc)
