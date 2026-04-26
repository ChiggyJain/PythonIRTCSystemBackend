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
from app.core.exceptions import BaseAppException


settings = get_settings()


# =========================
# Create token
# =========================

def _create_token(
    *,
    user_id: int,
    user_profile: str = "User",
    token_type: str,
    expires_delta: timedelta,
    token_id: int | None = None,
    against_token_type: str,
    against_token_id: int
) -> str:

    expire = now_ist() + expires_delta
    payload = {
        "profile" : user_profile,
        "sub": str(user_id),
        "type": token_type,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "againt_token_type": against_token_type,
        "against_token_id": str(against_token_id),
        "jti" : str(token_id)
    }
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
    user_profile: str = "User",
    token_id: int,
    against_token_type: str,
    against_token_id: int
) -> str:

    expire = timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    return _create_token(
        user_id=user_id,
        user_profile=user_profile,
        token_type="access",
        expires_delta=expire,
        token_id=token_id,
        against_token_type=against_token_type,
        against_token_id=against_token_id,
    )


# =========================
# Refresh token
# =========================

def create_refresh_token(
    *,
    user_id: int,
    user_profile: str = "User",
    token_id: int,
    against_token_type: str,
    against_token_id: int
) -> str:

    expire = timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    return _create_token(
        user_id=user_id,
        user_profile=user_profile,
        token_type="refresh",
        expires_delta=expire,
        token_id=token_id,
        against_token_type=against_token_type,
        against_token_id=against_token_id,
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

    except JWTError as e:
        raise BaseAppException(
            messages=[f"Error occured due to decoding the token and message: {str(e)}"],
            status_code=401,
        )