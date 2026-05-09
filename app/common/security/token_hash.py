
"""
Token hash utility.
Store only hash in DB, never raw JWT.
"""

import hashlib
import hmac
from app.core.settings import get_settings


settings = get_settings()


def build_token_hash(token: str) -> str:
    """
    Build deterministic HMAC-SHA256 hash for token.
    """
    value = (token or "").strip()
    if not value:
        return ""
    return hmac.new(
        settings.TOKEN_HASH_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def is_token_hash_match(
    *,
    raw_token: str,
    stored_hash: str | None,
) -> bool:
    
    if not stored_hash:
        return False
    candidate = build_token_hash(raw_token)
    return hmac.compare_digest(candidate, stored_hash)
