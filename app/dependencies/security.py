
"""
Security dependencies
"""

from fastapi import Depends
from app.domains.security.service import PasswordChangeOtpService
from app.domains.security.emailverification_service import EmailVerificationOtpService
from app.domains.security.repository.base import SecurityRepositoryBase
from app.dependencies.repositories import get_security_repository
from app.domains.security.emailchanged_service import EmailChangedOtpService



def get_password_change_otp_service(
    repo: SecurityRepositoryBase = Depends(get_security_repository),
) -> PasswordChangeOtpService:
    """
    Provide PasswordChangeOtpService
    """
    return PasswordChangeOtpService(repo)


def get_email_verification_otp_service(
    repo: SecurityRepositoryBase = Depends(get_security_repository),
) -> EmailVerificationOtpService:
    """
    Example:
        service = Depends(get_email_verification_otp_service)
    """
    return EmailVerificationOtpService(repo)


def get_email_changed_otp_service(
    repo: SecurityRepositoryBase = Depends(get_security_repository),
) -> EmailChangedOtpService:
    """
    Example:
        service: EmailChangedOtpService = Depends(get_email_changed_otp_service)
    """
    return EmailChangedOtpService(repo)
