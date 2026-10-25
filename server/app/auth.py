import hashlib
import secrets
from typing import Tuple


def generate_api_key(prefix: str = "ww_") -> Tuple[str, str]:
    """Generates a secure API key and its SHA-256 hash.
    Returns:
        (raw_api_key, api_key_hash)
    """
    token = secrets.token_urlsafe(32)
    raw_key = f"{prefix}{token}"
    key_hash = hash_api_key(raw_key)
    return raw_key, key_hash


def hash_api_key(raw_key: str) -> str:
    """Computes a SHA-256 hash of the API key for safe storage."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
