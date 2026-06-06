from typing import Tuple, Optional
from src.models.device import VALID_TYPES, VALID_STATUSES


MAX_NAME_LENGTH = 100
MAX_LOCATION_LENGTH = 200


def validate_create_payload(body: dict) -> Tuple[bool, Optional[str]]:
    """Validate request body for device creation."""
    if not isinstance(body, dict):
        return False, "Request body must be a JSON object."

    name = body.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return False, "'name' is required and must be a non-empty string."
    if len(name) > MAX_NAME_LENGTH:
        return False, f"'name' must not exceed {MAX_NAME_LENGTH} characters."

    device_type = body.get("type")
    if not device_type or not isinstance(device_type, str):
        return False, f"'type' is required. Valid values: {sorted(VALID_TYPES)}."
    if device_type not in VALID_TYPES:
        return False, f"'type' must be one of: {sorted(VALID_TYPES)}."

    status = body.get("status", "active")
    if status not in VALID_STATUSES:
        return False, f"'status' must be one of: {sorted(VALID_STATUSES)}."

    location = body.get("location")
    if location is not None:
        if not isinstance(location, str):
            return False, "'location' must be a string."
        if len(location) > MAX_LOCATION_LENGTH:
            return False, f"'location' must not exceed {MAX_LOCATION_LENGTH} characters."

    metadata = body.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        return False, "'metadata' must be a JSON object."

    return True, None


def validate_update_payload(body: dict) -> Tuple[bool, Optional[str]]:
    """Validate request body for device update. All fields are optional."""
    if not isinstance(body, dict):
        return False, "Request body must be a JSON object."

    if not body:
        return False, "At least one field must be provided for update."

    allowed_fields = {"name", "type", "status", "location", "metadata"}
    unknown = set(body.keys()) - allowed_fields
    if unknown:
        return False, f"Unknown fields: {sorted(unknown)}. Allowed: {sorted(allowed_fields)}."

    if "name" in body:
        name = body["name"]
        if not isinstance(name, str) or not name.strip():
            return False, "'name' must be a non-empty string."
        if len(name) > MAX_NAME_LENGTH:
            return False, f"'name' must not exceed {MAX_NAME_LENGTH} characters."

    if "type" in body:
        device_type = body["type"]
        if device_type not in VALID_TYPES:
            return False, f"'type' must be one of: {sorted(VALID_TYPES)}."

    if "status" in body:
        if body["status"] not in VALID_STATUSES:
            return False, f"'status' must be one of: {sorted(VALID_STATUSES)}."

    if "location" in body:
        location = body["location"]
        if location is not None and not isinstance(location, str):
            return False, "'location' must be a string or null."
        if isinstance(location, str) and len(location) > MAX_LOCATION_LENGTH:
            return False, f"'location' must not exceed {MAX_LOCATION_LENGTH} characters."

    if "metadata" in body:
        if body["metadata"] is not None and not isinstance(body["metadata"], dict):
            return False, "'metadata' must be a JSON object or null."

    return True, None
