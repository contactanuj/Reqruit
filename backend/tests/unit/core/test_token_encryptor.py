"""Tests for TokenEncryptor AES-256-GCM encryption."""

import os

import pytest

from src.core.token_encryptor import TokenDecryptionError, TokenEncryptor


def _key() -> bytes:
    """Generate a valid 32-byte key for testing."""
    return os.urandom(32)


class TestEncryptDecryptRoundTrip:
    def test_roundtrip_basic(self):
        enc = TokenEncryptor(_key())
        token = "ya29.a0ARrdaM_test_oauth_token_value"
        assert enc.decrypt(enc.encrypt(token)) == token

    def test_roundtrip_various_tokens(self):
        enc = TokenEncryptor(_key())
        tokens = [
            "short",
            "a" * 1000,
            "ya29.a0ARrdaM8example",
            "1/fFAGRNJru1FTz70BzhT3Zg",
        ]
        for token in tokens:
            assert enc.decrypt(enc.encrypt(token)) == token

    def test_encrypt_returns_bytes_longer_than_input(self):
        enc = TokenEncryptor(_key())
        token = "test_token"
        encrypted = enc.encrypt(token)
        assert isinstance(encrypted, bytes)
        # 12 bytes nonce + len(plaintext) + 16 bytes GCM tag
        assert len(encrypted) == 12 + len(token.encode()) + 16

    def test_encrypt_same_plaintext_produces_different_ciphertext(self):
        enc = TokenEncryptor(_key())
        token = "same_token_value"
        ct1 = enc.encrypt(token)
        ct2 = enc.encrypt(token)
        assert ct1 != ct2
        # Both still decrypt to the same value
        assert enc.decrypt(ct1) == token
        assert enc.decrypt(ct2) == token

    def test_encrypt_empty_string(self):
        enc = TokenEncryptor(_key())
        encrypted = enc.encrypt("")
        assert enc.decrypt(encrypted) == ""

    def test_encrypt_unicode_characters(self):
        enc = TokenEncryptor(_key())
        token = "tökën_wïth_ünïcödë_🔑"
        assert enc.decrypt(enc.encrypt(token)) == token


class TestDecryptErrors:
    def test_tampered_ciphertext_raises(self):
        enc = TokenEncryptor(_key())
        encrypted = enc.encrypt("secret_token")
        # Flip a byte in the ciphertext portion (after nonce)
        tampered = encrypted[:15] + bytes([encrypted[15] ^ 0xFF]) + encrypted[16:]
        with pytest.raises(TokenDecryptionError):
            enc.decrypt(tampered)

    def test_wrong_key_raises(self):
        enc1 = TokenEncryptor(_key())
        enc2 = TokenEncryptor(_key())
        encrypted = enc1.encrypt("secret_token")
        with pytest.raises(TokenDecryptionError):
            enc2.decrypt(encrypted)

    def test_too_short_ciphertext_raises(self):
        enc = TokenEncryptor(_key())
        with pytest.raises(TokenDecryptionError, match="too short"):
            enc.decrypt(b"short")


class TestConstructorValidation:
    def test_rejects_key_shorter_than_32_bytes(self):
        with pytest.raises(ValueError, match="exactly 32 bytes"):
            TokenEncryptor(b"too_short")

    def test_rejects_key_longer_than_32_bytes(self):
        with pytest.raises(ValueError, match="exactly 32 bytes"):
            TokenEncryptor(os.urandom(64))

    def test_accepts_exactly_32_bytes(self):
        enc = TokenEncryptor(os.urandom(32))
        assert enc is not None


class TestReprStr:
    def test_repr_hides_key(self):
        key = os.urandom(32)
        enc = TokenEncryptor(key)
        assert key.hex() not in repr(enc)
        assert "key-hidden" in repr(enc)

    def test_str_hides_key(self):
        key = os.urandom(32)
        enc = TokenEncryptor(key)
        assert key.hex() not in str(enc)
        assert "key-hidden" in str(enc)
