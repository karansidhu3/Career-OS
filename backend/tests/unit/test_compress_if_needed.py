"""Unit tests for app.services.generation._compress_if_needed — the resume
compile/compression loop. Covers a security-audit finding: the resume body is
AI-generated LaTeX that isn't re-escaped after the model writes it, so a
compile failure is a real possibility, not just theoretical. compile_latex_to_pdf
and PdfReader are mocked; no real Tectonic/PDF parsing involved.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.generation import (
    _assemble_resume_latex,
    _compress_if_needed,
    _remove_optional_experience_bullet_once,
)

pytestmark = pytest.mark.asyncio


RESCUE_BODY = r"""
\section{Experience}
  \resumeSubHeadingListStart
    \resumeSubheading{Acme}{Jun 2026 -- Present}{Developer}{BC}
      \resumeItemListStart
        \item \small{Built a reliable application service with measurable operational results.}
        \item \small{Designed transactional processing that preserved records during injected failures.}
      \resumeItemListEnd
  \resumeSubHeadingListEnd
\section{Projects}
  \resumeSubHeadingListStart
    \projectSubheading{Project One | Platform}{2026}{Python}{}{https://example.com/one}
      \resumeItemListStart
        \item \small{Built the first relevant project for a clearly defined user workflow.}
        \item \small{Designed its backend boundary around a specific operational constraint.}
      \resumeItemListEnd
    \projectSubheading{Project Two | Platform}{2026}{Java}{}{https://example.com/two}
      \resumeItemListStart
        \item \small{Built the second relevant project for another defined user workflow.}
        \item \small{Designed its persistence boundary around transactional correctness requirements.}
      \resumeItemListEnd
    \projectSubheading{Project Three | Platform}{2026}{TypeScript}{}{https://example.com/three}
      \resumeItemListStart
        \item \small{Built the lowest-ranked project for an additional internal workflow.}
        \item \small{Designed its queue boundary around recoverable asynchronous processing.}
      \resumeItemListEnd
  \resumeSubHeadingListEnd
\section{Skills}
\begin{itemize}
  \item \textbf{Languages:} Python, Java, TypeScript
  \item \textbf{Tools:} Docker, Git, Vercel
\end{itemize}
"""


def _mock_pdf_reader(page_count: int):
    reader = MagicMock()
    reader.pages = [MagicMock() for _ in range(page_count)]
    return reader


async def test_returns_original_latex_when_it_fits_one_page():
    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake") as mock_compile, \
         patch("app.services.generation.PdfReader", return_value=_mock_pdf_reader(1)):
        result, attempts, rescue_actions = await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake")
    assert result == "ORIGINAL_LATEX"
    assert attempts == 0
    assert rescue_actions == []
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
        result, attempts, rescue_actions = await _compress_if_needed("ORIGINAL_LATEX", "sk-ant-fake")

    assert result == "ASSEMBLED_COMPRESSED"
    assert attempts == 1
    assert rescue_actions == []


async def test_final_compression_removes_low_relevance_skills_before_project():
    page_counts = [2, 2, 1]

    def fake_reader(pdf_bytes):
        return _mock_pdf_reader(page_counts.pop(0))

    original = _assemble_resume_latex(RESCUE_BODY)
    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake") as compile_mock, \
         patch("app.services.generation.PdfReader", side_effect=fake_reader), \
         patch("app.services.generation._call_compression", return_value=RESCUE_BODY) as compression_mock:
        result, attempts, rescue_actions = await _compress_if_needed(
            original,
            "sk-ant-fake",
        )

    assert attempts == 1
    assert rescue_actions == ["removed_skill_item:Tools:Vercel"]
    assert r"\textbf{Languages:}" in result
    assert r"\textbf{Tools:}" in result
    assert "Vercel" not in result
    assert "Project Three" in result
    assert compression_mock.await_count == 1
    assert compile_mock.await_count == 3


async def test_compression_cannot_remove_a_selected_project_before_skills_rescue():
    compressed_without_third = RESCUE_BODY.replace(
        RESCUE_BODY[
            RESCUE_BODY.index("    \\projectSubheading{Project Three"):
            RESCUE_BODY.index("  \\resumeSubHeadingListEnd\n\\section{Skills}")
        ],
        "",
    )
    page_counts = [2, 2, 1]

    def fake_reader(pdf_bytes):
        return _mock_pdf_reader(page_counts.pop(0))

    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake"), \
         patch("app.services.generation.PdfReader", side_effect=fake_reader), \
         patch("app.services.generation._call_compression", return_value=compressed_without_third):
        result, attempts, rescue_actions = await _compress_if_needed(
            _assemble_resume_latex(RESCUE_BODY),
            "sk-ant-fake",
        )

    assert attempts == 1
    assert rescue_actions == ["removed_skill_item:Tools:Vercel"]
    assert "Project Three" in result


async def test_layout_rescue_prunes_items_then_skills_before_reducing_projects():
    one_skill_row = RESCUE_BODY.replace(
        "  \\item \\textbf{Tools:} Docker, Git, Vercel\n",
        "",
    )
    page_counts = [2, 2, 2, 1]

    def fake_reader(pdf_bytes):
        return _mock_pdf_reader(page_counts.pop(0))

    original = _assemble_resume_latex(one_skill_row)
    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake") as compile_mock, \
         patch("app.services.generation.PdfReader", side_effect=fake_reader), \
         patch("app.services.generation._call_compression", return_value=one_skill_row) as compression_mock:
        result, attempts, rescue_actions = await _compress_if_needed(
            original,
            "sk-ant-fake",
            jd_text="Java backend engineer",
        )

    assert attempts == 1
    # The unsuccessful one-item experiment is discarded. The row-level action
    # is retained because it is the first change that actually fixes layout.
    assert rescue_actions == ["removed_skills_section"]
    assert r"\section{Skills}" not in result
    assert "Project One" in result
    assert "Project Two" in result
    assert "Project Three" in result
    assert compression_mock.await_count == 1
    assert compile_mock.await_count == 4


async def test_required_skill_row_is_last_skills_reduction_before_project():
    body = RESCUE_BODY[
        :RESCUE_BODY.index(r"\section{Skills}")
    ] + r"""\section{Skills}
\begin{itemize}
  \item \textbf{Languages:} Rust
\end{itemize}
"""
    page_counts = [2, 2, 1]

    def fake_reader(pdf_bytes):
        return _mock_pdf_reader(page_counts.pop(0))

    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake"), \
         patch("app.services.generation.PdfReader", side_effect=fake_reader), \
         patch("app.services.generation._call_compression", return_value=body):
        result, attempts, rescue_actions = await _compress_if_needed(
            _assemble_resume_latex(body),
            "sk-ant-fake",
            jd_text="Rust backend engineer",
        )

    assert attempts == 1
    assert rescue_actions == ["removed_skills_section"]
    assert r"\textbf{Languages:} Rust" not in result
    assert "Project Three" in result


async def test_layout_rescue_still_rejects_when_two_projects_without_skills_overflow():
    minimal_body = RESCUE_BODY.replace(
        RESCUE_BODY[RESCUE_BODY.index("    \\projectSubheading{Project Three"):RESCUE_BODY.index("  \\resumeSubHeadingListEnd\n\\section{Skills}")],
        "",
    )
    minimal_body = minimal_body[:minimal_body.index(r"\section{Skills}")]

    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-two-pages") as compile_mock, \
         patch("app.services.generation.PdfReader", return_value=_mock_pdf_reader(2)), \
         patch("app.services.generation._call_compression", return_value=minimal_body) as compression_mock:
        with pytest.raises(ValueError, match="deterministic layout rescue"):
            await _compress_if_needed(
                _assemble_resume_latex(minimal_body),
                "sk-ant-fake",
            )

    assert compression_mock.await_count == 1
    assert compile_mock.await_count == 2


async def test_layout_rescue_removes_optional_experience_bullet_before_project_or_skills():
    body = RESCUE_BODY.replace(
        "        \\item \\small{Designed transactional processing that preserved records during injected failures.}\n",
        "        \\item \\small{Designed transactional processing that preserved records during injected failures.}\n"
        "        \\item \\small{Documented a lower-priority operational detail for future reference.}\n",
    )
    page_counts = [2, 2, 1]

    def fake_reader(pdf_bytes):
        return _mock_pdf_reader(page_counts.pop(0))

    with patch("app.services.generation.compile_latex_to_pdf", return_value=b"%PDF-fake"), \
         patch("app.services.generation.PdfReader", side_effect=fake_reader), \
         patch("app.services.generation._call_compression", return_value=body):
        result, attempts, rescue_actions = await _compress_if_needed(
            _assemble_resume_latex(body),
            "sk-ant-fake",
        )

    assert attempts == 1
    assert rescue_actions == ["removed_optional_experience_bullet:1"]
    assert "lower-priority operational detail" not in result
    assert "Project Three" in result
    assert r"\textbf{Tools:}" in result


async def test_optional_experience_reduction_preserves_surrounding_latex_structure():
    body = RESCUE_BODY.replace(
        "        \\item \\small{Designed transactional processing that preserved records during injected failures.}\n",
        "        \\item \\small{Designed transactional processing that preserved records during injected failures.}\n"
        "        \\item \\small{Documented a lower-priority operational detail for future reference.}\n",
    )

    reduced = _remove_optional_experience_bullet_once(body)

    assert reduced is not None
    reduced_body, action = reduced
    assert action == "removed_optional_experience_bullet:1"
    assert "lower-priority operational detail" not in reduced_body
    assert "Designed transactional processing" in reduced_body
    assert reduced_body.count(r"\resumeItemListStart") == body.count(r"\resumeItemListStart")
    assert reduced_body.count(r"\resumeItemListEnd") == body.count(r"\resumeItemListEnd")
    assert reduced_body.count("{") == reduced_body.count("}")
