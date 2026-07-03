"""Unit tests for app.services.crypto — envelope encryption of per-user API keys."""
import pytest

from app.services import crypto


def test_encrypt_decrypt_round_trip():
    ciphertext, version = crypto.encrypt("sk-ant-real-key-12345")
    assert version == crypto.CURRENT_KEY_VERSION
    assert ciphertext != "sk-ant-real-key-12345"
    assert crypto.decrypt(ciphertext) == "sk-ant-real-key-12345"


def test_encrypt_is_nondeterministic():
    """Fernet includes a random nonce — encrypting the same plaintext twice
    must not produce identical ciphertext (defends against replay/pattern leaks)."""
    ct1, _ = crypto.encrypt("same-plaintext")
    ct2, _ = crypto.encrypt("same-plaintext")
    assert ct1 != ct2
    assert crypto.decrypt(ct1) == crypto.decrypt(ct2) == "same-plaintext"


def test_decrypt_rejects_garbage():
    with pytest.raises(ValueError):
        crypto.decrypt("not-a-real-fernet-token")


def test_validate_master_keys_passes_with_real_key():
    crypto.validate_master_keys()  # should not raise — test env has a real key configured


def test_validate_master_keys_rejects_malformed_current_key(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "encryption_master_key", "not-a-valid-fernet-key")
    with pytest.raises(RuntimeError):
        crypto.validate_master_keys()


def test_validate_master_keys_rejects_malformed_previous_key(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "encryption_master_key_previous", "also-not-valid")
    with pytest.raises(RuntimeError):
        crypto.validate_master_keys()


def test_validate_master_keys_rejects_missing_key(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "encryption_master_key", "")
    with pytest.raises(RuntimeError):
        crypto.validate_master_keys()


def test_decrypt_works_after_key_rotation(monkeypatch):
    """A key encrypted under the old master key must still decrypt once that key
    moves to encryption_master_key_previous — this is the whole point of MultiFernet."""
    from cryptography.fernet import Fernet
    from app.config import settings

    old_key = settings.encryption_master_key
    ciphertext, _ = crypto.encrypt("pre-rotation-key")

    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "encryption_master_key", new_key)
    monkeypatch.setattr(settings, "encryption_master_key_previous", old_key)

    assert crypto.decrypt(ciphertext) == "pre-rotation-key"
    # New encryptions use the new (current) key, not the previous one
    new_ciphertext, _ = crypto.encrypt("post-rotation-key")
    assert crypto.decrypt(new_ciphertext) == "post-rotation-key"
