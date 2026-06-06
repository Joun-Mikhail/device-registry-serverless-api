import json
import pytest
from moto import mock_aws
import boto3
import os


@pytest.fixture(autouse=True)
def mock_table(dynamodb_table):
    """Each handler test gets a fresh mock table via the conftest fixture."""
    pass


def _event(method="POST", body=None, path_params=None):
    return {
        "httpMethod": method,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body else None,
    }


def _create(body):
    from src.handlers.create_device import handler
    # Reset module-level singleton between tests
    import src.handlers.create_device as m
    m._repository = None
    return handler(_event("POST", body), None)


def _get(device_id):
    from src.handlers.get_device import handler
    import src.handlers.get_device as m
    m._repository = None
    return handler(_event("GET", path_params={"deviceId": device_id}), None)


def _list():
    from src.handlers.list_devices import handler
    import src.handlers.list_devices as m
    m._repository = None
    return handler(_event("GET"), None)


def _update(device_id, body):
    from src.handlers.update_device import handler
    import src.handlers.update_device as m
    m._repository = None
    return handler(_event("PUT", body=body, path_params={"deviceId": device_id}), None)


def _delete(device_id):
    from src.handlers.delete_device import handler
    import src.handlers.delete_device as m
    m._repository = None
    return handler(_event("DELETE", path_params={"deviceId": device_id}), None)


class TestCreateDevice:
    def test_returns_201_with_valid_payload(self):
        resp = _create({"name": "Temp Sensor", "type": "sensor"})
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["name"] == "Temp Sensor"
        assert "deviceId" in body

    def test_returns_400_missing_name(self):
        resp = _create({"type": "sensor"})
        assert resp["statusCode"] == 400

    def test_returns_400_invalid_type(self):
        resp = _create({"name": "X", "type": "invalid"})
        assert resp["statusCode"] == 400

    def test_returns_400_on_bad_json(self):
        from src.handlers.create_device import handler
        import src.handlers.create_device as m
        m._repository = None
        event = {"body": "not-json", "pathParameters": {}}
        resp = handler(event, None)
        assert resp["statusCode"] == 400


class TestGetDevice:
    def test_returns_200_for_existing_device(self):
        created = json.loads(_create({"name": "Sensor B", "type": "sensor"})["body"])
        resp = _get(created["deviceId"])
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["deviceId"] == created["deviceId"]

    def test_returns_404_for_missing_device(self):
        resp = _get("nonexistent-id")
        assert resp["statusCode"] == 404


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


class TestUpdateDevice:
    def test_updates_status(self):
        created = json.loads(_create({"name": "Dev C", "type": "gateway"})["body"])
        resp = _update(created["deviceId"], {"status": "maintenance"})
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "maintenance"
        assert body["name"] == "Dev C"

    def test_returns_404_for_missing_device(self):
        resp = _update("no-such-id", {"status": "inactive"})
        assert resp["statusCode"] == 404

    def test_returns_400_for_unknown_field(self):
        created = json.loads(_create({"name": "Dev D", "type": "sensor"})["body"])
        resp = _update(created["deviceId"], {"colour": "red"})
        assert resp["statusCode"] == 400


class TestDeleteDevice:
    def test_deletes_existing_device(self):
        created = json.loads(_create({"name": "Dev E", "type": "sensor"})["body"])
        resp = _delete(created["deviceId"])
        assert resp["statusCode"] == 200
        # Confirm it's gone
        assert _get(created["deviceId"])["statusCode"] == 404

    def test_returns_404_for_missing_device(self):
        resp = _delete("ghost-id")
        assert resp["statusCode"] == 404
