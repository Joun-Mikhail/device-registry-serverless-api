from repositories.device_repository import DeviceRepository
from utils.logging import log_invocation
from utils.response import error, internal_error, not_found, success

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


@log_invocation("GetDevice")
def handler(event: dict, context) -> dict:
    # API Gateway sends pathParameters as null (not omitted) when a route matches
    # with no path values, so `.get(k, {})` is not enough — the default only
    # applies when the key is absent. Same `or {}` idiom as queryStringParameters.
    device_id = (event.get("pathParameters") or {}).get("deviceId")

    if not device_id:
        return error("'deviceId' path parameter is required.")

    try:
        device = _get_repository().get(device_id)
        if device is None:
            return not_found("Device")
        return success(device.to_response())
    # Boundary handler: converts any unexpected error into a 500 so stack traces
    # are logged but never reach the caller (README → Security → Error isolation).
    except Exception as exc:  # noqa: BLE001
        return internal_error(exc)
