"""The worker runs as its own process — separate from app.main, which is where
JSON logging / Sentry init actually get wired for the API. Without its own
on_startup hook, the worker (arguably the most exception-prone code in the
app — Anthropic calls, LaTeX compilation) would silently never get either."""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import anthropic
import httpx
import pytest

from app import worker
from app.services.llm_client import StructuredOutputTruncatedError


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


def test_truncated_structured_output_has_actionable_failure_code():
    assert worker._generation_failure_code(StructuredOutputTruncatedError("too large")) == "generation_output_too_large"


def test_apply_result_preserves_paragraphs_and_repairs_em_dash_spacing():
    job = SimpleNamespace()
    worker._apply_result(job, {
        "job_title": "Engineer",
        "job_company": "Canonical",
        "fit_score": 7,
        "cover_letter": (
            "Building fleet tooling—spanning 4,083 machines—requires discipline.\n\n"
            "I built CareerOS—an application platform—and made failures visible."
        ),
    })

    assert job.cover_letter == (
        "Building fleet tooling, spanning 4,083 machines, requires discipline.\n\n"
        "I built CareerOS, an application platform, and made failures visible."
    )
