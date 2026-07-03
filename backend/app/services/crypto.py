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


def validate_master_keys() -> None:
    """Eagerly construct a Fernet instance for every configured key (current +
    any previous, for rotation) — called at startup so a missing or malformed
    ENCRYPTION_MASTER_KEY fails loudly on boot, not silently the first time a
    user tries to add an API key. A malformed key otherwise passes an
    unremarkable startup and healthcheck, and only surfaces as a confusing
    500 for whoever happens to be the first real user to touch credentials.
    """
    for key in _fernet_keys():
        try:
            Fernet(key.encode())
        except Exception as e:
            raise RuntimeError(f"ENCRYPTION_MASTER_KEY (or a previous key) is not a valid Fernet key: {e}") from e


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
