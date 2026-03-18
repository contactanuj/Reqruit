"""
AES-256-GCM token encryption for OAuth credentials at rest.

Provides authenticated encryption ensuring both confidentiality and integrity.
The nonce-prefixed ciphertext format is self-contained — no separate IV storage
needed. Each encryption uses a random 12-byte nonce, so encrypting the same
plaintext twice always produces different ciphertext.

Output format: nonce (12 bytes) + ciphertext + GCM tag (16 bytes)
Total overhead: 28 bytes per encrypted token.
"""

import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenDecryptionError(ValueError):
    """Raised when decryption fails due to tampered or invalid ciphertext."""

    def __init__(self, message: str = "Token decryption failed") -> None:
        super().__init__(message)


class TokenEncryptor:
    """
    AES-256-GCM encrypt/decrypt for OAuth tokens.

    Constructor accepts a 32-byte key. Encrypt produces nonce-prefixed
    ciphertext; decrypt reverses. Never logs or exposes the key.
    """

    def __init__(self, encryption_key: bytes) -> None:
        if len(encryption_key) != 32:
            msg = f"Encryption key must be exactly 32 bytes, got {len(encryption_key)}"
            raise ValueError(msg)
        self._aesgcm = AESGCM(encryption_key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a plaintext token string, returning nonce + ciphertext."""
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ciphertext

    def decrypt(self, data: bytes) -> str:
        """Decrypt nonce-prefixed ciphertext back to a plaintext string."""
        if len(data) < 28:
            raise TokenDecryptionError("Ciphertext too short")
        nonce, ciphertext = data[:12], data[12:]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
        except Exception as exc:
            raise TokenDecryptionError("Token decryption failed") from exc

    def __repr__(self) -> str:
        return "TokenEncryptor([key-hidden])"

    def __str__(self) -> str:
        return "TokenEncryptor([key-hidden])"


@lru_cache(maxsize=1)
def get_token_encryptor() -> TokenEncryptor:
    """Return a singleton TokenEncryptor using the configured encryption key."""
    from src.core.config import get_settings

    settings = get_settings()
    key_bytes = bytes.fromhex(settings.oauth.encryption_key)
    return TokenEncryptor(key_bytes)
