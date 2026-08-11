"""The worker runs as its own process — separate from app.main, which is where
JSON logging / Sentry init actually get wired for the API. Without its own
on_startup hook, the worker (arguably the most exception-prone code in the
app — Anthropic calls, LaTeX compilation) would silently never get either."""
import asyncio
from unittest.mock import patch

import anthropic
import httpx
import pytest

from app import worker


@pytest.mark.asyncio
async def test_on_startup_configures_logging_and_error_tracking():
    with patch("app.worker.configure_logging") as mock_configure, \
         patch("app.worker.init_error_tracking") as mock_init:
        await worker._on_startup({})
        mock_configure.assert_called_once()
        mock_init.assert_called_once()


def test_worker_settings_wires_on_startup():
    assert worker.WorkerSettings.on_startup is worker._on_startup


def test_bad_anthropic_schema_is_classified_as_configuration_failure():
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    error = anthropic.BadRequestError("invalid schema", response=response, body={})

    assert worker._generation_failure_code(error) == "generation_configuration"


def test_timeout_is_classified_separately_from_other_failures():
    assert worker._generation_failure_code(asyncio.TimeoutError()) == "anthropic_timeout"
