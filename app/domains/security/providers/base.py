
"""
Provider contracts for OTP delivery.
"""

from abc import (
    ABC, abstractmethod
)
from dataclasses import dataclass


@dataclass(slots=True)
class OtpSendResult:
    accepted: bool
    provider: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class EmailOtpSenderBase(ABC):
    @abstractmethod
    async def send_otp(
        self,
        *,
        to_email: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:
        pass


class SmsOtpSenderBase(ABC):
    @abstractmethod
    async def send_otp(
        self,
        *,
        to_mobile: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:
        pass
