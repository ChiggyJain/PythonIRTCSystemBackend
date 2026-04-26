
import re
from pydantic import (
    BaseModel, field_validator, ValidationInfo
)

STATION_CODE_REGEX = re.compile(r"^[A-Z0-9_]{2,20}$")


class StationCreateRequest(BaseModel):
    
    name: str
    code: str
    city: str
    state: str

    @field_validator("name", "code", "city", "state", mode="before")
    @classmethod
    def strip_values(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            v = v.strip()
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v, info: ValidationInfo):
        if not v:
            raise ValueError("name is required")
        if len(v) > 150:
            raise ValueError("name max length is 150")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v, info: ValidationInfo):
        value = (v or "").upper()
        if not value:
            raise ValueError("code is required")
        if not STATION_CODE_REGEX.match(value):
            raise ValueError("code must be 2-20 chars (A-Z, 0-9, _)")
        return value

    @field_validator("city")
    @classmethod
    def validate_city(cls, v, info: ValidationInfo):
        if not v:
            raise ValueError("city is required")
        if len(v) > 100:
            raise ValueError("city max length is 100")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v, info: ValidationInfo):
        if not v:
            raise ValueError("state is required")
        if len(v) > 100:
            raise ValueError("state max length is 100")
        return v
