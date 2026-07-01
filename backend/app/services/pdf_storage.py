"""PDF storage seam (Phase 5): compile once at generation time, cache the bytes,
and stop recompiling LaTeX on every download — the previous compile-on-request
pattern doesn't scale past a handful of users.

PDFStorage is provider-agnostic (mirrors the LLMClient pattern from Phase 2).
LocalFilesystemStorage is the only implementation today. Cloudflare R2 is the
intended production backend — deferred because it needs a real bucket + API
token (Karan's own Cloudflare account, which nothing here can provision).
Swapping it in later means implementing this same interface; no caller changes.

Keys are deterministic functions of job_id, so nothing needs to be stored in the
database to know where a job's cached PDF lives — callers just recompute the key.
"""
import os
from abc import ABC, abstractmethod


class PDFStorage(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    async def load(self, key: str) -> bytes | None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalFilesystemStorage(PDFStorage):
    """Dev/local-only fallback. Not shared across replicas or survivable across a
    Railway redeploy — real production use needs the R2 implementation instead."""

    def __init__(self, base_dir: str):
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self._base_dir, key)

    async def save(self, key: str, data: bytes) -> None:
        with open(self._path(key), "wb") as f:
            f.write(data)

    async def load(self, key: str) -> bytes | None:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)


def get_pdf_storage() -> PDFStorage:
    from app.config import settings
    return LocalFilesystemStorage(settings.pdf_storage_dir)


def resume_pdf_key(job_id: int) -> str:
    return f"resume-{job_id}.pdf"


def cover_letter_pdf_key(job_id: int) -> str:
    return f"cover-letter-{job_id}.pdf"


async def cache_resume_pdf(job_id: int, resume_latex: str) -> bytes:
    """Compile the resume once and store it — called right after generation succeeds,
    and again on demand if a request finds the cache empty (compile-on-miss)."""
    from app.services.pdf import compile_latex_to_pdf
    pdf_bytes = await compile_latex_to_pdf(resume_latex)
    await get_pdf_storage().save(resume_pdf_key(job_id), pdf_bytes)
    return pdf_bytes


async def cache_cover_letter_pdf(job_id: int, latex: str) -> bytes:
    from app.services.pdf import compile_latex_to_pdf
    pdf_bytes = await compile_latex_to_pdf(latex)
    await get_pdf_storage().save(cover_letter_pdf_key(job_id), pdf_bytes)
    return pdf_bytes


async def invalidate_cover_letter_pdf(job_id: int) -> None:
    """Called whenever cover_letter text is edited — the cached PDF is now stale."""
    await get_pdf_storage().delete(cover_letter_pdf_key(job_id))
