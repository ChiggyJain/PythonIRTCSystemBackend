
"""
Password Utility (Enterprise)
Uses passlib + bcrypt
Features:
---------
- hash password
- verify password
- future upgrade ready
- multi-worker safe
- stateless
"""

from passlib.context import CryptContext


# =========================================================
# Crypt context
# =========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# =========================================================
# Hash password
# =========================================================

def hash_password(password: str) -> str:
    """
    Hash plain password
    """

    return pwd_context.hash(password)


# =========================================================
# Verify password
# =========================================================

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify password
    """

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )