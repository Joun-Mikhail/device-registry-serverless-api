"""
Integration tests — these hit the real deployed API endpoint.

Set the API_BASE_URL environment variable before running:

    export API_BASE_URL=https://<api-id>.execute-api.eu-central-1.amazonaws.com/dev
    pytest tests/integration/ -v

These tests are intentionally excluded from the CI unit-test run.
"""
import os
import uuid
import pytest
import urllib.request
import urllib.error
import json

BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")


def skip_if_no_url():
    if not BASE_URL:
        pytest.skip("API_BASE_URL not set — skipping integration tests.")


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.fixture(scope="module")
def created_device():
    skip_if_no_url()
    status, body = _request("POST", "/devices", {"name": "Integration Sensor", "type": "sensor"})
    assert status == 201, f"Setup failed: {body}"
    yield body
    # Teardown — delete the device created during this test module
    _request("DELETE", f"/devices/{body['deviceId']}")


def test_create_device():
    skip_if_no_url()
    status, body = _request("POST", "/devices", {"name": "Test Device", "type": "actuator"})
    assert status == 201
    assert "deviceId" in body
    assert body["name"] == "Test Device"
    # Cleanup
    _request("DELETE", f"/devices/{body['deviceId']}")


def test_get_device(created_device):
    skip_if_no_url()
    status, body = _request("GET", f"/devices/{created_device['deviceId']}")
    assert status == 200
    assert body["deviceId"] == created_device["deviceId"]


def test_list_devices(created_device):
    skip_if_no_url()
    status, body = _request("GET", "/devices")
    assert status == 200
    assert "items" in body
    assert body["count"] >= 1


def test_list_devices_with_limit(created_device):
    skip_if_no_url()
    status, body = _request("GET", "/devices?limit=1")
    assert status == 200
    assert body["count"] <= 1


def test_list_devices_filter_by_type(created_device):
    skip_if_no_url()
    status, body = _request("GET", "/devices?type=sensor")
    assert status == 200
    assert all(d["type"] == "sensor" for d in body["items"])


def test_list_devices_invalid_limit_returns_400():
    skip_if_no_url()
    status, _ = _request("GET", "/devices?limit=0")
    assert status == 400


def test_update_device(created_device):
    skip_if_no_url()
    device_id = created_device["deviceId"]
    status, body = _request("PATCH", f"/devices/{device_id}", {"status": "maintenance"})
    assert status == 200
    assert body["status"] == "maintenance"


def test_get_nonexistent_returns_404():
    skip_if_no_url()
    status, body = _request("GET", f"/devices/{uuid.uuid4()}")
    assert status == 404


def test_create_with_invalid_type_returns_400():
    skip_if_no_url()
    status, body = _request("POST", "/devices", {"name": "Bad Device", "type": "spaceship"})
    assert status == 400
    assert "error" in body


def test_delete_device():
    skip_if_no_url()
    _, created = _request("POST", "/devices", {"name": "Temp", "type": "gateway"})
    status, body = _request("DELETE", f"/devices/{created['deviceId']}")
    assert status == 200
    gone_status, _ = _request("GET", f"/devices/{created['deviceId']}")
    assert gone_status == 404
