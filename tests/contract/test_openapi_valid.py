"""The OpenAPI document itself must be a valid OpenAPI 3.0 spec."""
import pathlib
import yaml
from openapi_spec_validator import validate

SPEC_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml"


def test_openapi_document_is_valid():
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    # Raises OpenAPIValidationError if the document is not a valid OpenAPI 3.0 spec.
    validate(spec)


def test_all_endpoints_documented():
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    paths = spec["paths"]
    assert set(paths) == {"/devices", "/devices/{deviceId}"}
    assert set(paths["/devices"]) >= {"get", "post"}
    assert set(paths["/devices/{deviceId}"]) >= {"get", "patch", "delete"}
