"""Structured JSON logging (Phase 7). Configures the root logger to emit one
JSON object per line instead of default text — retrofitting this after real
users exist is much more painful than building it now, since every historical
log line before the switch is unstructured and unsearchable.

Called once, at import time of app.main, before any other logger is used.
"""
import json
import logging
import sys

# Attributes every LogRecord already has — anything else on a record was
# passed via logging.info(..., extra={...}) and should be surfaced as its
# own JSON field (e.g. request_id, user_id, duration_ms).
_STANDARD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
