"""Unit tests for app.services.generation._compress_if_needed — the resume
compile/compression loop. Covers a security-audit finding: the resume body is
AI-generated LaTeX that isn't re-escaped after the model writes it, so a
compile failure is a real possibility, not just theoretical. compile_latex_to_pdf
and PdfReader are mocked; no real Tectonic/PDF parsing involved.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.generation import _compress_if_needed

pytestmark = pytest.mark.asyncio


def _mock_pdf_reader(page_count: int):
    reader = MagicMock()
    reader.pages = [MagicMock() for _ in range(page_count)]
    return reader


async def test_returns_original_latex_when_it_fits_one_page():
    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake") as mock_compile, \
         patch("app.services.generation.PdfReader", return_value=_mock_pdf_reader(1)):
        result, attempts = await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake")
    assert result == "ORIGINAL_LATEX"
    assert attempts == 0
    mock_compile.assert_awaited_once_with("ORIGINAL_LATEX")


async def test_first_compile_failure_raises_instead_of_returning_broken_latex():
    """No known-good LaTeX exists yet — must propagate so the caller (worker.py)
    marks the job as failed, not silently store unusable LaTeX."""
    with patch("app.services.generation.compile_latex_to_pdf", side_effect=RuntimeError("tectonic failed")):
        with pytest.raises(RuntimeError):
            await _compress_if_needed("BROKEN_LATEX", "sk-ant-fake")


async def test_later_compile_failure_rejects_multi_page_fallback():
    compile_results = [
        b"%PDF-two-pages",           # first compile: succeeds, 2 pages
        RuntimeError("broken output"),  # second compile (post-compression): fails
    ]

    async def fake_compile(latex):
        result = compile_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    with patch("app.services.generation.compile_latex_to_pdf", side_effect=fake_compile), \
         patch("app.services.generation.PdfReader", return_value=_mock_pdf_reader(2)), \
         patch("app.services.generation._call_compression", return_value="COMPRESSED_BODY"):
        with pytest.raises(ValueError, match="refusing"):
            await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake")


async def test_compression_call_failure_rejects_multi_page_result():
    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-two-pages"), \
         patch("app.services.generation.PdfReader", return_value=_mock_pdf_reader(2)), \
         patch("app.services.generation._call_compression", side_effect=RuntimeError("claude call failed")):
        with pytest.raises(ValueError, match="multi-page"):
            await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake")


async def test_successful_compression_returns_compressed_latex():
    page_counts = [2, 1]

    async def fake_compile(latex):
        return b"%PDF-fake"

    def fake_reader(pdf_bytes):
        return _mock_pdf_reader(page_counts.pop(0))

    with patch("app.services.generation.compile_latex_to_pdf", side_effect=fake_compile), \
         patch("app.services.generation.PdfReader", side_effect=fake_reader), \
         patch("app.services.generation._call_compression", return_value="COMPRESSED_BODY"), \
         patch("app.services.generation._assemble_resume_latex", return_value="ASSEMBLED_COMPRESSED"):
        result, attempts = await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake")

    assert result == "ASSEMBLED_COMPRESSED"
    assert attempts == 1


async def test_final_compression_output_is_validated_and_rejected_if_still_two_pages():
    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-two-pages") as compile_mock, \
         patch("app.services.generation.PdfReader", return_value=_mock_pdf_reader(2)), \
         patch("app.services.generation._call_compression", return_value="COMPRESSED_BODY"), \
         patch("app.services.generation._assemble_resume_latex", return_value="ASSEMBLED_COMPRESSED"):
        with pytest.raises(ValueError, match="still renders to 2 pages"):
            await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake", max_attempts=2)
    assert compile_mock.await_count == 3
