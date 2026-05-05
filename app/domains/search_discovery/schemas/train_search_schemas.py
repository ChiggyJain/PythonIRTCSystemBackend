
from datetime import date
import re
from pydantic import (
    BaseModel, field_validator, 
    ValidationInfo, model_validator
)


STATION_CODE_RE = re.compile(r"^[A-Z0-9]{2,10}$")


class TrainSearchQueryRequest(BaseModel):
    
    source: str
    destination: str
    journey_date: date
    page: int = 1
    size: int = 20

    @field_validator("source", "destination")
    @classmethod
    def validate_station_code(cls, v: str) -> str:
        value = (v or "").strip().upper()
        if not STATION_CODE_RE.match(value):
            raise ValueError("must be a valid station code (2-10 uppercase alphanumeric)")
        return value

    @field_validator("journey_date")
    @classmethod
    def validate_journey_date_not_past(cls, v: date) -> date:
        today = date.today()
        if v < today:
            raise ValueError("journey_date must be current-date or future-date")
        return v

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("page must be greater than 0")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("size must be greater than 0")
        if v > 100:
            raise ValueError("size must be less than or equal to 100")
        return v

    @model_validator(mode="after")
    def validate_source_destination_not_same(self):
        if (self.source).strip().lower() == (self.destination).strip().lower():
            raise ValueError("source and destination cannot not be same")
        return self