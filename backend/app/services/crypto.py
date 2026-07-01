"""Envelope encryption for per-user AI provider API keys (Phase 3).

encrypt() always uses the current master key (encryption_master_key). decrypt()
tries every configured key via MultiFernet, so rotating the master key — moving
the old value into encryption_master_key_previous — doesn't break decryption of
rows encrypted under it; they keep working until naturally rewritten.
"""
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.config import settings

CURRENT_KEY_VERSION = 1


def _fernet_keys() -> list[str]:
    keys = [settings.encryption_master_key]
    if settings.encryption_master_key_previous:
        keys += [k.strip() for k in settings.encryption_master_key_previous.split(",") if k.strip()]
    if not keys[0]:
        raise RuntimeError("ENCRYPTION_MASTER_KEY is not configured")
    return keys


def encrypt(plaintext: str) -> tuple[str, int]:
    """Returns (ciphertext, key_version) for storage."""
    fernet = Fernet(_fernet_keys()[0].encode())
    return fernet.encrypt(plaintext.encode()).decode(), CURRENT_KEY_VERSION


def decrypt(ciphertext: str) -> str:
    multi = MultiFernet([Fernet(k.encode()) for k in _fernet_keys()])
    try:
        return multi.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Stored API key could not be decrypted — master key may have changed")
