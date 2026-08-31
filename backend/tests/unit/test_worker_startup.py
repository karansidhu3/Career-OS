"""Worker startup and generation-result lifecycle tests."""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import anthropic
import httpx
import pytest

from app import worker
from app.models.job import Job
from app.services.generation import GENERATION_VERSION
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


def test_generation_version_fits_persisted_schema():
    max_length = Job.__table__.c.generation_version.type.length
    assert len(GENERATION_VERSION) <= max_length


def test_bad_anthropic_schema_is_classified_as_configuration_failure():
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    error = anthropic.BadRequestError("invalid schema", response=response, body={})

    assert worker._generation_failure_code(error) == "generation_configuration"


def test_timeout_is_classified_separately_from_other_failures():
    assert worker._generation_failure_code(asyncio.TimeoutError()) == "anthropic_timeout"


def test_truncated_structured_output_has_actionable_failure_code():
    assert worker._generation_failure_code(StructuredOutputTruncatedError("too large")) == "generation_output_too_large"


def test_interrupted_job_is_retryable_instead_of_remaining_processing():
    job = SimpleNamespace(
        status="processing",
        title="Generating…",
        generation_metadata={"started_at": "2026-08-27T00:00:00+00:00"},
    )

    worker._mark_job_failed(job, "generation_interrupted")

    assert job.status == "failed"
    assert job.title == "Generation failed"
    assert job.generation_metadata["failure_code"] == "generation_interrupted"
    assert job.generation_metadata["started_at"] == "2026-08-27T00:00:00+00:00"
    assert "failed_at" in job.generation_metadata


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


def test_apply_result_does_not_cut_structured_analysis_at_legacy_boundary():
    job = SimpleNamespace()
    strategic_note = "GOOD FIT\n• " + ("Grounded evidence. " * 140)

    worker._apply_result(job, {
        "job_title": "Engineer",
        "job_company": "Canonical",
        "fit_score": 7,
        "strategic_note": strategic_note,
    })

    assert len(strategic_note) > 2_000
    assert job.strategic_note == strategic_note
