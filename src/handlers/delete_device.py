from repositories.device_repository import DeviceRepository
from utils.logging import log_invocation
from utils.response import error, success, not_found, internal_error

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
    except Exception as exc:
        return internal_error(exc)
