"""
Unit tests for Pydantic schema validation.

Tests the validation rules that gate every incoming API request:
- description length bounds on JobGenerateRequest
- status pattern enforcement on StatusUpdate
- cost_usd computed field arithmetic on JobRead
"""
import pytest
from pydantic import ValidationError

from app.schemas.job import (
    CoverLetterUpdate,
    JobGenerateRequest,
    JobRead,
    StatusUpdate,
)


# ── JobGenerateRequest ────────────────────────────────────────────────────────

def test_generate_request_accepts_minimum_length():
    req = JobGenerateRequest(description="a" * 10)
    assert len(req.description) == 10


def test_generate_request_rejects_too_short():
    with pytest.raises(ValidationError) as exc_info:
        JobGenerateRequest(description="short")
    assert "min_length" in str(exc_info.value).lower() or "10" in str(exc_info.value)


def test_generate_request_accepts_50k_chars():
    req = JobGenerateRequest(description="a" * 50_000)
    assert len(req.description) == 50_000


def test_generate_request_rejects_over_50k():
    with pytest.raises(ValidationError):
        JobGenerateRequest(description="a" * 50_001)


def test_generate_request_url_defaults_to_empty():
    req = JobGenerateRequest(description="a" * 100)
    assert req.url == ""


def test_generate_request_accepts_valid_url():
    req = JobGenerateRequest(description="a" * 100, url="https://example.com/jobs/123")
    assert req.url == "https://example.com/jobs/123"


# ── StatusUpdate ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", ["generated", "applied", "skipped", "interview", "offer"])
def test_status_update_accepts_all_valid_statuses(status):
    body = StatusUpdate(status=status)
    assert body.status == status


@pytest.mark.parametrize("status", [
    "pending",
    "processing",
    "new",
    "APPLIED",
    "Applied",
    "done",
    "rejected",
    "",
    "  applied  ",
])
def test_status_update_rejects_invalid_statuses(status):
    with pytest.raises(ValidationError):
        StatusUpdate(status=status)


# ── CoverLetterUpdate ────────────────────────────────────────────────────────

def test_cover_letter_update_accepts_valid_text():
    body = CoverLetterUpdate(cover_letter="Some cover letter text.")
    assert body.cover_letter == "Some cover letter text."


def test_cover_letter_update_rejects_empty():
    with pytest.raises(ValidationError):
        CoverLetterUpdate(cover_letter="")


def test_cover_letter_update_rejects_over_10k():
    with pytest.raises(ValidationError):
        CoverLetterUpdate(cover_letter="a" * 10_001)


# ── JobRead.cost_usd ─────────────────────────────────────────────────────────

def _make_job_read(**kwargs):
    defaults = dict(
        id=1,
        title="SWE",
        status="generated",
        input_tokens=None,
        output_tokens=None,
        cache_read_tokens=None,
        cache_write_tokens=None,
        compression_attempts=None,
    )
    defaults.update(kwargs)
    return JobRead(**defaults)


def test_cost_usd_is_none_when_no_token_data():
    job = _make_job_read()
    assert job.cost_usd is None


def test_cost_usd_is_positive_with_token_data():
    job = _make_job_read(input_tokens=1000, output_tokens=500)
    assert job.cost_usd is not None
    assert job.cost_usd > 0


def test_cost_usd_output_tokens_most_expensive():
    # Output tokens cost $15/M — dominate for equal token counts
    job_output_heavy = _make_job_read(input_tokens=100, output_tokens=1000)
    job_input_heavy  = _make_job_read(input_tokens=1000, output_tokens=100)
    assert job_output_heavy.cost_usd > job_input_heavy.cost_usd


def test_cost_usd_cache_reads_cheaper_than_uncached():
    # Cached reads ($0.30/M) much cheaper than uncached input ($3/M)
    job_cached   = _make_job_read(input_tokens=1000, cache_read_tokens=800, output_tokens=0)
    job_uncached = _make_job_read(input_tokens=1000, output_tokens=0)
    assert job_cached.cost_usd < job_uncached.cost_usd


def test_cost_usd_rounds_to_4_decimal_places():
    job = _make_job_read(input_tokens=123, output_tokens=456)
    cost = job.cost_usd
    assert cost == round(cost, 4)


def test_cost_usd_zero_when_all_tokens_zero():
    job = _make_job_read(input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0)
    assert job.cost_usd == 0.0
