
"""
Users Schemas (Enterprise Validation)

Signup validation rules:
------------------------
- first_name / last_name -> alphabets + space only
- mobile -> 10 digits
- email -> valid + lowercase
- password -> strong password policy
- confirm_password -> must match password
- email != password
- mobile != password
"""

import re

from pydantic import (
    BaseModel,
    EmailStr,
    field_validator,
    model_validator,
)


# =========================================================
# Regex constants
# =========================================================

NAME_REGEX = re.compile(r"^[A-Za-z ]+$")

MOBILE_REGEX = re.compile(r"^[0-9]{10}$")


# allow many special chars except ' and "
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])"
    r"(?=.*[A-Z])"
    r"(?=.*\d)"
    r"(?=.*[!@#$%^&*()_\+\-=\[\]{}|;:,.<>/?`~])"
    r"[A-Za-z\d!@#$%^&*()_\+\-=\[\]{}|;:,.<>/?`~]{8,64}$"
)


# =========================================================
# Signup Schema
# =========================================================


class UserSignupRequest(BaseModel):

    first_name: str
    last_name: str
    mobile: str
    email: EmailStr
    gender: str
    password: str
    confirm_password: str

    # -------------------------
    # strip spaces
    # -------------------------

    @field_validator(
        "first_name",
        "last_name",
        "mobile",
        "email",
        "password",
        "confirm_password",
        mode="before",
    )
    @classmethod
    def strip_values(cls, v):

        if isinstance(v, str):
            v = v.strip()

        return v

    # -------------------------
    # name validation
    # -------------------------

    @field_validator(
        "first_name",
        "last_name",
    )
    @classmethod
    def validate_name(cls, v):

        if not NAME_REGEX.match(v):
            raise ValueError(
                "Only alphabets and space allowed"
            )

        return v

    # -------------------------
    # mobile validation
    # -------------------------

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v):

        if not MOBILE_REGEX.match(v):
            raise ValueError(
                "Mobile must be 10 digits"
            )

        return v

    # -------------------------
    # email lowercase
    # -------------------------

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):

        return v.lower()

    # -------------------------
    # password regex validation
    # -------------------------

    @field_validator(
        "password",
        "confirm_password",
    )
    @classmethod
    def validate_password_format(cls, v):

        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, special character and length 8-64"
            )

        return v

    # -------------------------
    # cross-field validation
    # -------------------------

    @model_validator(mode="after")
    def validate_password_rules(self):

        if self.password != self.confirm_password:
            raise ValueError(
                "Password and confirm password must match"
            )

        if self.password == self.email:
            raise ValueError(
                "Password cannot be same as email"
            )

        if self.confirm_password == self.email:
            raise ValueError(
                "Confirm password cannot be same as email"
            )

        if self.password == self.mobile:
            raise ValueError(
                "Password cannot be same as mobile"
            )

        if self.confirm_password == self.mobile:
            raise ValueError(
                "Confirm password cannot be same as mobile"
            )

        return self