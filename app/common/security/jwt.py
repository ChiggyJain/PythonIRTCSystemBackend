"""
JWT Utility (Enterprise)
Supports:
- access token
- refresh token
- token type
- expiry
- issuer
- audience
- IST datetime
"""

from datetime import timedelta
from jose import jwt, JWTError
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist

settings = get_settings()


# =========================
# Create token
# =========================

def _create_token(
    *,
    user_id: int,
    token_type: str,
    expires_delta: timedelta,
    token_id: int | None = None,
) -> str:

    expire = now_ist() + expires_delta
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if token_id:
        payload["tid"] = token_id
    print(f"_create_token payload: {payload}")
    encoded = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded


# =========================
# Access token
# =========================

def create_access_token(
    *,
    user_id: int,
    token_id: int,
) -> str:

    expire = timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=expire,
        token_id=token_id,
    )


# =========================
# Refresh token
# =========================

def create_refresh_token(
    *,
    user_id: int,
    token_id: int,
) -> str:

    expire = timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=expire,
        token_id=token_id,
    )


# =========================
# Decode token
# =========================

def decode_token(
    token: str,
) -> dict:

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        return payload

    except JWTError:

        return {}