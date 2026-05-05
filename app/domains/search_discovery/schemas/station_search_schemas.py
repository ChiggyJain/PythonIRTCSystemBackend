
from pydantic import BaseModel, field_validator


class StationSearchQueryRequest(BaseModel):
    
    q: str
    size: int = 10

    @field_validator("q")
    @classmethod
    def validate_q(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("q is required")
        if len(value) < 2:
            raise ValueError("q must be at least 2 characters")
        if len(value) > 50:
            raise ValueError("q must be at most 50 characters")
        return value

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("size must be greater than 0")
        if v > 20:
            raise ValueError("size must be less than or equal to 20")
        return v
