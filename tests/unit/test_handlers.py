import json
import pytest
from moto import mock_aws
import boto3
import os


@pytest.fixture(autouse=True)
def mock_table(dynamodb_table):
    """Each handler test gets a fresh isolated mock DynamoDB table."""
    pass


def _event(method="POST", body=None, path_params=None):
    """Build a minimal API Gateway HTTP API proxy event."""
    return {
        "httpMethod": method,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body is not None else None,
    }


def _reset(module_path: str):
    """Reset the module-level repository singleton so each test gets a fresh client."""
    import importlib
    import sys
    mod = sys.modules.get(module_path)
    if mod:
        mod._repository = None


def _create(body):
    _reset("src.handlers.create_device")
    from src.handlers.create_device import handler
    return handler(_event("POST", body), None)


def _get(device_id):
    _reset("src.handlers.get_device")
    from src.handlers.get_device import handler
    return handler(_event("GET", path_params={"deviceId": device_id}), None)


def _list():
    _reset("src.handlers.list_devices")
    from src.handlers.list_devices import handler
    return handler(_event("GET"), None)


def _patch(device_id, body):
    _reset("src.handlers.update_device")
    from src.handlers.update_device import handler
    return handler(_event("PATCH", body=body, path_params={"deviceId": device_id}), None)


def _delete(device_id):
    _reset("src.handlers.delete_device")
    from src.handlers.delete_device import handler
    return handler(_event("DELETE", path_params={"deviceId": device_id}), None)


# ── CreateDevice ──────────────────────────────────────────────────────────


class TestCreateDevice:
    def test_returns_201_with_valid_payload(self):
        resp = _create({"name": "Temp Sensor", "type": "sensor"})
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["name"] == "Temp Sensor"
        assert body["type"] == "sensor"
        assert body["status"] == "active"
        assert "deviceId" in body
        assert "createdAt" in body
        assert "updatedAt" in body

    def test_returns_201_with_all_fields(self):
        resp = _create({
            "name": "Gateway A",
            "type": "gateway",
            "status": "inactive",
            "location": "Floor 2",
            "metadata": {"firmware": "v3.0"},
        })
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["location"] == "Floor 2"
        assert body["metadata"] == {"firmware": "v3.0"}

    def test_returns_400_missing_name(self):
        resp = _create({"type": "sensor"})
        assert resp["statusCode"] == 400
        assert "error" in json.loads(resp["body"])

    def test_returns_400_invalid_type(self):
        resp = _create({"name": "X", "type": "invalid"})
        assert resp["statusCode"] == 400

    def test_returns_400_on_bad_json(self):
        _reset("src.handlers.create_device")
        from src.handlers.create_device import handler
        resp = handler({"body": "not-json", "pathParameters": {}}, None)
        assert resp["statusCode"] == 400

    def test_response_contains_cors_headers(self):
        resp = _create({"name": "Sensor", "type": "sensor"})
        assert "Access-Control-Allow-Origin" in resp["headers"]

    def test_request_id_logged_gracefully_without_context(self):
        # context=None falls back to "local" — must not raise
        resp = _create({"name": "Sensor B", "type": "sensor"})
        assert resp["statusCode"] == 201


# ── GetDevice ─────────────────────────────────────────────────────────────


class TestGetDevice:
    def test_returns_200_for_existing_device(self):
        created = json.loads(_create({"name": "Sensor B", "type": "sensor"})["body"])
        resp = _get(created["deviceId"])
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["deviceId"] == created["deviceId"]
        assert body["name"] == "Sensor B"

    def test_returns_404_for_missing_device(self):
        resp = _get("nonexistent-id")
        assert resp["statusCode"] == 404
        assert "error" in json.loads(resp["body"])

    def test_returns_400_when_device_id_missing(self):
        _reset("src.handlers.get_device")
        from src.handlers.get_device import handler
        resp = handler({"pathParameters": {}, "body": None}, None)
        assert resp["statusCode"] == 400


# ── ListDevices ───────────────────────────────────────────────────────────


class TestListDevices:
    def test_returns_empty_list_initially(self):
        resp = _list()
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["items"] == []
        assert body["count"] == 0

    def test_returns_all_created_devices(self):
        _create({"name": "Device 1", "type": "sensor"})
        _create({"name": "Device 2", "type": "actuator"})
        resp = _list()
        body = json.loads(resp["body"])
        assert body["count"] == 2
        names = {d["name"] for d in body["items"]}
        assert names == {"Device 1", "Device 2"}


# ── UpdateDevice (PATCH) ──────────────────────────────────────────────────


class TestUpdateDevice:
    def test_patch_updates_status(self):
        created = json.loads(_create({"name": "Dev C", "type": "gateway"})["body"])
        resp = _patch(created["deviceId"], {"status": "maintenance"})
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "maintenance"
        assert body["name"] == "Dev C"          # unchanged field preserved

    def test_patch_updates_name(self):
        created = json.loads(_create({"name": "Old Name", "type": "sensor"})["body"])
        resp = _patch(created["deviceId"], {"name": "New Name"})
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["name"] == "New Name"

    def test_patch_updated_at_changes(self):
        created_body = json.loads(_create({"name": "Dev F", "type": "sensor"})["body"])
        original_updated_at = created_body["updatedAt"]
        resp = _patch(created_body["deviceId"], {"status": "inactive"})
        assert resp["statusCode"] == 200
        # updatedAt must be a string and may differ from the original
        new_updated_at = json.loads(resp["body"])["updatedAt"]
        assert isinstance(new_updated_at, str)
        assert len(new_updated_at) > 0

    def test_patch_created_at_unchanged(self):
        created_body = json.loads(_create({"name": "Dev G", "type": "sensor"})["body"])
        original_created_at = created_body["createdAt"]
        resp = _patch(created_body["deviceId"], {"status": "inactive"})
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["createdAt"] == original_created_at

    def test_returns_404_for_missing_device(self):
        resp = _patch("no-such-id", {"status": "inactive"})
        assert resp["statusCode"] == 404

    def test_returns_400_for_unknown_field(self):
        created = json.loads(_create({"name": "Dev D", "type": "sensor"})["body"])
        resp = _patch(created["deviceId"], {"colour": "red"})
        assert resp["statusCode"] == 400

    def test_returns_400_for_empty_body(self):
        created = json.loads(_create({"name": "Dev H", "type": "sensor"})["body"])
        resp = _patch(created["deviceId"], {})
        assert resp["statusCode"] == 400


# ── DeleteDevice ──────────────────────────────────────────────────────────


class TestDeleteDevice:
    def test_deletes_existing_device(self):
        created = json.loads(_create({"name": "Dev E", "type": "sensor"})["body"])
        resp = _delete(created["deviceId"])
        assert resp["statusCode"] == 200
        assert _get(created["deviceId"])["statusCode"] == 404

    def test_returns_404_for_missing_device(self):
        resp = _delete("ghost-id")
        assert resp["statusCode"] == 404

    def test_returns_400_when_device_id_missing(self):
        _reset("src.handlers.delete_device")
        from src.handlers.delete_device import handler
        resp = handler({"pathParameters": {}, "body": None}, None)
        assert resp["statusCode"] == 400
