from repositories.device_repository import DeviceRepository
from utils.logging import log_invocation
from utils.response import error, internal_error, not_found, success

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


@log_invocation("DeleteDevice")
def handler(event: dict, context) -> dict:
    device_id = event.get("pathParameters", {}).get("deviceId")

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        deleted = _get_repository().delete(device_id)
        if not deleted:
            return not_found("Device")
        return success({"message": f"Device '{device_id}' deleted successfully."})
    # Boundary handler: converts any unexpected error into a 500 so stack traces
    # are logged but never reach the caller (README → Security → Error isolation).
    except Exception as exc:  # noqa: BLE001
        return internal_error(exc)
