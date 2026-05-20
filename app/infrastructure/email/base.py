
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class EmailSendResult:
    accepted: bool
    provider: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class EmailSenderBase(ABC):
    @abstractmethod
    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        plain_text_content: str | None = None,
        html_content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EmailSendResult:
        pass


