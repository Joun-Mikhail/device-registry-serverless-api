import io
import json
import logging

import pytest

from utils.logging import JsonFormatter, get_logger, log_invocation


def test_json_formatter_outputs_valid_json_with_extras():
    formatter = JsonFormatter()
    record = logging.LogRecord("svc", logging.INFO, __file__, 1, "hello", None, None)
    record.requestId = "abc-123"
    parsed = json.loads(formatter.format(record))
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"
    assert parsed["logger"] == "svc"
    assert parsed["requestId"] == "abc-123"
    assert "timestamp" in parsed


def _attach_capture(logger) -> io.StringIO:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return buf


def _last_record(buf: io.StringIO) -> dict:
    lines = [ln for ln in buf.getvalue().strip().splitlines() if ln.strip()]
    return json.loads(lines[-1])


def test_log_invocation_emits_required_fields():
    @log_invocation("TestOp")
    def fake_handler(event, context):
        return {"statusCode": 201}

    buf = _attach_capture(get_logger(fake_handler.__module__))

    event = {"requestContext": {"http": {"method": "POST", "path": "/devices", "userAgent": "pytest"}}}

    class Ctx:
        aws_request_id = "req-42"

    resp = fake_handler(event, Ctx())
    assert resp["statusCode"] == 201

    record = _last_record(buf)
    for field in ["timestamp", "level", "operation", "requestId",
                  "method", "path", "status", "latencyMs", "userAgent"]:
        assert field in record, f"missing required log field: {field}"
    assert record["operation"] == "TestOp"
    assert record["requestId"] == "req-42"
    assert record["status"] == 201
    assert record["method"] == "POST"
    assert record["path"] == "/devices"
    assert record["userAgent"] == "pytest"
    assert isinstance(record["latencyMs"], (int, float))


def test_log_invocation_handles_missing_context_and_request_context():
    @log_invocation("Minimal")
    def fake_handler(event, context):
        return {"statusCode": 200}

    buf = _attach_capture(get_logger(fake_handler.__module__))
    fake_handler({}, None)  # no context, no requestContext
    record = _last_record(buf)
    assert record["requestId"] == "local"
    assert record["status"] == 200
    assert record["method"] is None
    assert record["path"] is None


def test_log_invocation_logs_and_reraises_on_exception():
    @log_invocation("BoomOp")
    def boom(event, context):
        raise ValueError("kaboom")

    buf = _attach_capture(get_logger(boom.__module__))

    class Ctx:
        aws_request_id = "req-err"

    with pytest.raises(ValueError):
        boom({}, Ctx())

    record = _last_record(buf)
    assert record["operation"] == "BoomOp"
    assert record["status"] == 500
    assert "exc_info" in record
