from src.repositories.device_repository import DeviceRepository
from src.utils.logging_config import configure_logger
from src.utils.response import success, internal_error

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
        # NOTE: list_all() uses DynamoDB Scan, which reads every item in the table.
        # This is acceptable for a development dataset of < 1,000 items.
        # At production scale, replace with a GSI + Query to avoid full-table reads.
        # See docs/architecture.md for the proposed GSI design.
        devices = _get_repository().list_all()
        return success({"items": [d.to_response() for d in devices], "count": len(devices)})
    except Exception as exc:
        return internal_error(exc)
