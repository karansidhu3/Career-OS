"""Unit tests for app.services.pdf_storage — the local-filesystem and R2 PDF cache seams."""
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.pdf_storage import LocalFilesystemStorage, R2Storage, cover_letter_pdf_key, get_pdf_storage, resume_pdf_key


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


# ── R2Storage (boto3 mocked — no real Cloudflare account needed) ─────────────

@pytest.fixture
def mock_boto_client():
    with patch("boto3.client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        yield mock_client


def _r2():
    return R2Storage(account_id="acct123", access_key_id="key", secret_access_key="secret", bucket_name="careeros-pdfs")


def test_r2_client_configured_with_r2_endpoint(mock_boto_client):
    with patch("boto3.client") as mock_client_factory:
        _r2()
        _, kwargs = mock_client_factory.call_args
        assert kwargs["endpoint_url"] == "https://acct123.r2.cloudflarestorage.com"
        assert kwargs["region_name"] == "auto"


async def test_r2_save_calls_put_object(mock_boto_client):
    storage = _r2()
    await storage.save("resume-1.pdf", b"%PDF-data")
    mock_boto_client.put_object.assert_called_once_with(
        Bucket="careeros-pdfs", Key="resume-1.pdf", Body=b"%PDF-data", ContentType="application/pdf"
    )


async def test_r2_load_returns_bytes_on_hit(mock_boto_client):
    mock_boto_client.get_object.return_value = {"Body": BytesIO(b"%PDF-data")}
    storage = _r2()
    assert await storage.load("resume-1.pdf") == b"%PDF-data"


async def test_r2_load_returns_none_on_miss(mock_boto_client):
    from botocore.exceptions import ClientError
    mock_boto_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "not found"}}, "GetObject"
    )
    storage = _r2()
    assert await storage.load("nonexistent.pdf") is None


async def test_r2_load_reraises_unexpected_errors(mock_boto_client):
    from botocore.exceptions import ClientError
    mock_boto_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "nope"}}, "GetObject"
    )
    storage = _r2()
    with pytest.raises(ClientError):
        await storage.load("resume-1.pdf")


async def test_r2_delete_calls_delete_object(mock_boto_client):
    storage = _r2()
    await storage.delete("resume-1.pdf")
    mock_boto_client.delete_object.assert_called_once_with(Bucket="careeros-pdfs", Key="resume-1.pdf")


# ── get_pdf_storage() backend selection ───────────────────────────────────────

def test_get_pdf_storage_uses_local_filesystem_when_r2_not_configured():
    from app.config import settings
    with patch.object(settings, "r2_bucket_name", ""):
        assert isinstance(get_pdf_storage(), LocalFilesystemStorage)


def test_get_pdf_storage_uses_r2_when_configured(mock_boto_client):
    from app.config import settings
    with patch.object(settings, "r2_bucket_name", "careeros-pdfs"), \
         patch.object(settings, "r2_account_id", "acct123"), \
         patch.object(settings, "r2_access_key_id", "key"), \
         patch.object(settings, "r2_secret_access_key", "secret"):
        assert isinstance(get_pdf_storage(), R2Storage)
