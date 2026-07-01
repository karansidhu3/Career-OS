"""Unit tests for app.services.pdf_storage — the local-filesystem PDF cache seam."""
import pytest

from app.services.pdf_storage import LocalFilesystemStorage, cover_letter_pdf_key, resume_pdf_key


@pytest.fixture
def storage(tmp_path):
    return LocalFilesystemStorage(str(tmp_path))


def test_resume_and_cover_letter_keys_are_deterministic_and_distinct():
    assert resume_pdf_key(42) == resume_pdf_key(42)
    assert resume_pdf_key(42) != cover_letter_pdf_key(42)


async def test_load_returns_none_when_nothing_stored(storage):
    assert await storage.load("nonexistent.pdf") is None


async def test_save_then_load_round_trips_bytes(storage):
    await storage.save("resume-1.pdf", b"%PDF-fake-bytes")
    assert await storage.load("resume-1.pdf") == b"%PDF-fake-bytes"


async def test_delete_removes_stored_file(storage):
    await storage.save("resume-1.pdf", b"data")
    await storage.delete("resume-1.pdf")
    assert await storage.load("resume-1.pdf") is None


async def test_delete_is_a_noop_when_nothing_stored(storage):
    await storage.delete("never-existed.pdf")  # must not raise
