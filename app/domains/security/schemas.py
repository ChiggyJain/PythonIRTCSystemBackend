
import re
from pydantic import (
    BaseModel, field_validator, model_validator, ValidationInfo
)


OTP_REGEX = re.compile(r"^\d{6}$")
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])"
    r"(?=.*[A-Z])"
    r"(?=.*\d)"
    r"(?=.*[!@#$%^&*()_\+\-=\[\]{}|;:,.<>/?`~])"
    r"[A-Za-z\d!@#$%^&*()_\+\-=\[\]{}|;:,.<>/?`~]{8,64}$"
)


class PasswordChangeRequestOtpRequest(BaseModel):
    
    channel: str

    @field_validator("channel", mode="before")
    @classmethod
    def strip_channel(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            v = v.strip()
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v, info: ValidationInfo):
        value = v.upper()
        if value not in {"EMAIL", "MOBILE"}:
            raise ValueError("channel must be EMAIL or MOBILE")
        return value


class PasswordChangeConfirmRequest(BaseModel):
    challenge_id: str
    otp: str
    new_password: str
    confirm_password: str

    @field_validator(
        "challenge_id",
        "otp",
        "new_password",
        "confirm_password",
        mode="before",
    )
    @classmethod
    def strip_values(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            v = v.strip()
        return v

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v, info: ValidationInfo):
        if not OTP_REGEX.match(v):
            raise ValueError("otp must be a valid 6-digit number")
        return v

    @field_validator("new_password", "confirm_password")
    @classmethod
    def validate_password_format(cls, v, info: ValidationInfo):
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                f"{info.field_name} must contain uppercase, lowercase, digit, special character and length 8-64"
            )
        return v

    @model_validator(mode="after")
    def validate_password_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("new_password and confirm_password must match")
        return self
