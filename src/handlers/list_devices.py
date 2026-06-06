import logging

from src.repositories.device_repository import DeviceRepository
from src.utils.response import success, internal_error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


def handler(event: dict, context) -> dict:
    logger.info("ListDevices invoked")

    try:
        devices = _get_repository().list_all()
        return success({"items": [d.to_response() for d in devices], "count": len(devices)})
    except Exception as exc:
        return internal_error(exc)
