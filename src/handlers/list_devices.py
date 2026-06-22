from repositories.device_repository import DeviceRepository
from utils.logging import log_invocation
from utils.pagination import decode_token, encode_token
from utils.response import error, success, internal_error
from validation.device_validator import validate_list_params

_repository = None


def _get_repository() -> DeviceRepository:
    global _repository
    if _repository is None:
        _repository = DeviceRepository()
    return _repository


@log_invocation("ListDevices")
def handler(event: dict, context) -> dict:
    query = event.get("queryStringParameters") or {}

    valid, message, params = validate_list_params(query)
    if not valid:
        return error(message)

    try:
        start_key = decode_token(params["next_token"])
    except ValueError as exc:
        return error(str(exc))

    try:
        # NOTE: Uses DynamoDB Scan when unfiltered — bounded per request by limit.
        # When type is given, queries the type-createdAt GSI instead. At scale,
        # replace the unfiltered Scan with a materialised index.
        devices, last_key = _get_repository().list_paginated(
            limit=params["limit"],
            start_key=start_key,
            device_type=params["type"],
        )
        body = {
            "items": [d.to_response() for d in devices],
            "count": len(devices),
        }
        next_token = encode_token(last_key)
        if next_token:
            body["nextToken"] = next_token
        return success(body)
    except Exception as exc:
        return internal_error(exc)
