from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).isoformat()


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if not isinstance(password, str) or len(password) < 10:
        raise ValueError("Password must contain at least 10 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    try:
        _, computed = hash_password(password, bytes.fromhex(salt_hex))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(computed, digest_hex)


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry(hours: int) -> str:
    return utc_iso(utc_now() + timedelta(hours=hours))
