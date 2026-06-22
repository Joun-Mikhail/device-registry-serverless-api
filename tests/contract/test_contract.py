"""
Contract tests: every handler response must conform to the response schema
published in docs/openapi.yaml.

Why not Schemathesis/Dredd? Both drive a live HTTP server. This service is a set
of AWS Lambda handlers with no server process, so we invoke the handlers directly
(against a moto-mocked DynamoDB, exactly as in the unit tests) and validate each
real response body against the OpenAPI response schema with jsonschema. This is a
more faithful contract check for a serverless app and stays deterministic.
"""
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

SPEC_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml"


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _table(dynamodb_table):
    """Provide the moto-mocked table to every contract test (from tests/conftest.py)."""
    pass


def _assert_conforms(spec, component, instance):
    # Self-contained schema: the top-level $ref plus an embedded components block,
    # so all '#/components/schemas/...' pointers resolve within this document.
    schema = {
        "$ref": f"#/components/schemas/{component}",
        "components": {"schemas": spec["components"]["schemas"]},
    }
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    assert not errors, f"{component} contract mismatch: " + "; ".join(e.message for e in errors)


# ── handler invocation helpers (mirror the unit-test pattern) ─────────────────


def _event(method="GET", body=None, path_params=None, query=None):
    return {
        "httpMethod": method,
        "pathParameters": path_params or {},
        "queryStringParameters": query,
        "body": json.dumps(body) if body is not None else None,
    }


def _call(module_name, event):
    import importlib
    import sys
    mod = sys.modules.get(module_name)
    if mod:
        mod._repository = None
    handler = importlib.import_module(module_name).handler
    return handler(event, None)


def _create(body):
    return _call("handlers.create_device", _event("POST", body=body))


def _body(resp):
    return json.loads(resp["body"])


# ── POST /devices ─────────────────────────────────────────────────────────


class TestCreateContract:
    def test_201_matches_device_schema(self, spec):
        resp = _create({"name": "Sensor", "type": "sensor", "location": "Floor 1",
                        "metadata": {"fw": "1.0"}})
        assert resp["statusCode"] == 201
        _assert_conforms(spec, "Device", _body(resp))

    def test_400_matches_error_schema(self, spec):
        resp = _create({"type": "sensor"})  # missing name
        assert resp["statusCode"] == 400
        _assert_conforms(spec, "Error", _body(resp))


# ── GET /devices ──────────────────────────────────────────────────────────


class TestListContract:
    def test_200_matches_device_list_schema(self, spec):
        _create({"name": "A", "type": "sensor"})
        _create({"name": "B", "type": "gateway"})
        resp = _call("handlers.list_devices", _event("GET", query={"limit": "1"}))
        assert resp["statusCode"] == 200
        _assert_conforms(spec, "DeviceList", _body(resp))

    def test_200_filtered_matches_schema(self, spec):
        _create({"name": "A", "type": "sensor"})
        resp = _call("handlers.list_devices", _event("GET", query={"type": "sensor"}))
        assert resp["statusCode"] == 200
        _assert_conforms(spec, "DeviceList", _body(resp))

    def test_400_matches_error_schema(self, spec):
        resp = _call("handlers.list_devices", _event("GET", query={"limit": "0"}))
        assert resp["statusCode"] == 400
        _assert_conforms(spec, "Error", _body(resp))


# ── GET /devices/{deviceId} ───────────────────────────────────────────────


class TestGetContract:
    def test_200_matches_device_schema(self, spec):
        created = _body(_create({"name": "G", "type": "sensor"}))
        resp = _call("handlers.get_device", _event("GET", path_params={"deviceId": created["deviceId"]}))
        assert resp["statusCode"] == 200
        _assert_conforms(spec, "Device", _body(resp))

    def test_404_matches_error_schema(self, spec):
        resp = _call("handlers.get_device", _event("GET", path_params={"deviceId": "missing"}))
        assert resp["statusCode"] == 404
        _assert_conforms(spec, "Error", _body(resp))


# ── PATCH /devices/{deviceId} ─────────────────────────────────────────────


class TestUpdateContract:
    def test_200_matches_device_schema(self, spec):
        created = _body(_create({"name": "U", "type": "sensor"}))
        resp = _call(
            "handlers.update_device",
            _event("PATCH", body={"status": "maintenance"}, path_params={"deviceId": created["deviceId"]}),
        )
        assert resp["statusCode"] == 200
        _assert_conforms(spec, "Device", _body(resp))

    def test_404_matches_error_schema(self, spec):
        resp = _call(
            "handlers.update_device",
            _event("PATCH", body={"status": "inactive"}, path_params={"deviceId": "missing"}),
        )
        assert resp["statusCode"] == 404
        _assert_conforms(spec, "Error", _body(resp))


# ── DELETE /devices/{deviceId} ────────────────────────────────────────────


class TestDeleteContract:
    def test_200_matches_delete_result_schema(self, spec):
        created = _body(_create({"name": "D", "type": "sensor"}))
        resp = _call("handlers.delete_device", _event("DELETE", path_params={"deviceId": created["deviceId"]}))
        assert resp["statusCode"] == 200
        _assert_conforms(spec, "DeleteResult", _body(resp))

    def test_404_matches_error_schema(self, spec):
        resp = _call("handlers.delete_device", _event("DELETE", path_params={"deviceId": "missing"}))
        assert resp["statusCode"] == 404
        _assert_conforms(spec, "Error", _body(resp))
