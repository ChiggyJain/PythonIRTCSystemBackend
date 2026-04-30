
"""
Security dependencies
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.security.services.passwordchanged_services import PasswordChangeOtpService
from app.domains.security.services.emailverification_services import EmailVerificationOtpService
from app.domains.security.repository.base import SecurityRepositoryBase
from app.dependencies.repositories import get_security_repository
from app.domains.security.services.emailchanged_services import EmailChangedOtpService



def get_password_change_otp_service(
    repo: SecurityRepositoryBase = Depends(get_security_repository),
) -> PasswordChangeOtpService:
    """
    Provide PasswordChangeOtpService
    """
    return PasswordChangeOtpService(repo)


def get_email_verification_otp_service(
    db_session: AsyncSession = Depends(get_db),
) -> EmailVerificationOtpService:
    return EmailVerificationOtpService(db_session)


def get_email_changed_otp_service(
    db_session: AsyncSession = Depends(get_db),
) -> EmailChangedOtpService:
    return EmailChangedOtpService(db_session)
