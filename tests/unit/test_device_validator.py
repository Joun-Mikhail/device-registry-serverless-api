import pytest
from validation.device_validator import (
    validate_create_payload,
    validate_update_payload,
    validate_list_params,
    DEFAULT_LIMIT,
    MAX_LIMIT,
)


# ── Create ────────────────────────────────────────────────────────────────


class TestValidateCreate:
    def test_valid_minimal(self):
        valid, msg = validate_create_payload({"name": "Sensor A", "type": "sensor"})
        assert valid is True
        assert msg is None

    def test_valid_full(self):
        valid, msg = validate_create_payload({
            "name": "Gateway 01",
            "type": "gateway",
            "status": "inactive",
            "location": "Floor 3",
            "metadata": {"firmware": "2.0"},
        })
        assert valid is True

    def test_missing_name(self):
        valid, msg = validate_create_payload({"type": "sensor"})
        assert valid is False
        assert "name" in msg

    def test_empty_name(self):
        valid, msg = validate_create_payload({"name": "  ", "type": "sensor"})
        assert valid is False
        assert "name" in msg

    def test_name_too_long(self):
        valid, msg = validate_create_payload({"name": "x" * 101, "type": "sensor"})
        assert valid is False
        assert "100" in msg

    def test_missing_type(self):
        valid, msg = validate_create_payload({"name": "Device"})
        assert valid is False
        assert "type" in msg

    def test_invalid_type(self):
        valid, msg = validate_create_payload({"name": "Device", "type": "robot"})
        assert valid is False
        assert "type" in msg

    def test_invalid_status(self):
        valid, msg = validate_create_payload({"name": "Device", "type": "sensor", "status": "broken"})
        assert valid is False
        assert "status" in msg

    def test_invalid_metadata(self):
        valid, msg = validate_create_payload({"name": "Device", "type": "sensor", "metadata": "not-a-dict"})
        assert valid is False
        assert "metadata" in msg

    def test_not_a_dict(self):
        valid, msg = validate_create_payload("string")
        assert valid is False

    def test_location_too_long(self):
        valid, msg = validate_create_payload({"name": "Device", "type": "sensor", "location": "x" * 201})
        assert valid is False
        assert "location" in msg


# ── Update ────────────────────────────────────────────────────────────────


class TestValidateUpdate:
    def test_valid_partial(self):
        valid, msg = validate_update_payload({"status": "inactive"})
        assert valid is True

    def test_empty_body(self):
        valid, msg = validate_update_payload({})
        assert valid is False

    def test_unknown_field(self):
        valid, msg = validate_update_payload({"colour": "red"})
        assert valid is False
        assert "Unknown" in msg

    def test_invalid_type_in_update(self):
        valid, msg = validate_update_payload({"type": "spaceship"})
        assert valid is False

    def test_null_location_allowed(self):
        valid, msg = validate_update_payload({"location": None})
        assert valid is True

    def test_null_metadata_allowed(self):
        valid, msg = validate_update_payload({"metadata": None})
        assert valid is True


# ── List params ─────────────────────────────────────────────────────────────


class TestValidateListParams:
    def test_defaults_when_no_query(self):
        valid, msg, parsed = validate_list_params(None)
        assert valid is True
        assert parsed["limit"] == DEFAULT_LIMIT
        assert parsed["type"] is None
        assert parsed["next_token"] is None

    def test_valid_limit_parsed_to_int(self):
        valid, msg, parsed = validate_list_params({"limit": "10"})
        assert valid is True
        assert parsed["limit"] == 10

    def test_limit_zero_rejected(self):
        valid, msg, _ = validate_list_params({"limit": "0"})
        assert valid is False
        assert "limit" in msg

    def test_limit_over_max_rejected(self):
        valid, msg, _ = validate_list_params({"limit": str(MAX_LIMIT + 1)})
        assert valid is False

    def test_non_numeric_limit_rejected(self):
        valid, msg, _ = validate_list_params({"limit": "abc"})
        assert valid is False

    def test_valid_type_accepted(self):
        valid, msg, parsed = validate_list_params({"type": "sensor"})
        assert valid is True
        assert parsed["type"] == "sensor"

    def test_invalid_type_rejected(self):
        valid, msg, _ = validate_list_params({"type": "spaceship"})
        assert valid is False
        assert "type" in msg

    def test_next_token_passed_through(self):
        valid, msg, parsed = validate_list_params({"nextToken": "abc"})
        assert valid is True
        assert parsed["next_token"] == "abc"

    def test_empty_next_token_rejected(self):
        valid, msg, _ = validate_list_params({"nextToken": "   "})
        assert valid is False
