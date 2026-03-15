
"""
Security dependencies
"""

from fastapi import Depends
from app.domains.security.service import PasswordChangeOtpService
from app.domains.security.repository.base import SecurityRepositoryBase
from app.dependencies.repositories import get_security_repository


def get_password_change_otp_service(
    repo: SecurityRepositoryBase = Depends(get_security_repository),
) -> PasswordChangeOtpService:
    """
    Provide PasswordChangeOtpService
    """

    return PasswordChangeOtpService(repo)
