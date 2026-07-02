"""The worker runs as its own process — separate from app.main, which is where
JSON logging / Sentry init actually get wired for the API. Without its own
on_startup hook, the worker (arguably the most exception-prone code in the
app — Anthropic calls, LaTeX compilation) would silently never get either."""
from unittest.mock import patch

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
