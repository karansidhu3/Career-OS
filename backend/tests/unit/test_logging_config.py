import json
import logging

from app.logging_config import JsonFormatter


def _make_record(msg="hello", extra=None, exc_info=None):
    record = logging.LogRecord(
        name="app.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=exc_info,
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_format_produces_valid_json_with_core_fields():
    record = _make_record("something happened")
    payload = json.loads(JsonFormatter().format(record))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "something happened"


def test_format_surfaces_extra_fields():
    record = _make_record("request done", extra={
        "request_id": "abc-123", "user_id": "u-1", "duration_ms": 12.5, "status_code": 200,
    })
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "abc-123"
    assert payload["user_id"] == "u-1"
    assert payload["duration_ms"] == 12.5
    assert payload["status_code"] == 200


def test_format_omits_extra_fields_when_absent():
    record = _make_record("plain message")
    payload = json.loads(JsonFormatter().format(record))
    assert "request_id" not in payload
    assert "user_id" not in payload


def test_format_includes_exc_info_on_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = _make_record("failed", exc_info=sys.exc_info())
    payload = json.loads(JsonFormatter().format(record))
    assert "boom" in payload["exc_info"]


def test_format_serializes_non_json_native_extra_values():
    """Extra values that aren't natively JSON-serializable (e.g. a UUID) shouldn't crash
    the formatter — default=str in json.dumps stringifies them instead."""
    import uuid
    record = _make_record("has uuid", extra={"user_id": uuid.uuid4()})
    payload = json.loads(JsonFormatter().format(record))
    assert isinstance(payload["user_id"], str)
