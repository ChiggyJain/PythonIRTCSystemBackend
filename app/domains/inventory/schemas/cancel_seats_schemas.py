
import re
from typing import List, Literal
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo
)


class CancelSeatsRequest(BaseModel):
    
    schedule_id: int
    booking_id: int
    user_id: int
    
    @field_validator(
        "schedule_id",
        "booking_id",
        "user_id",
    )
    @classmethod
    def validate_positive_integer_fields(
        cls,
        value: int,
        info: ValidationInfo,
    ):
        if value <= 0:
            raise ValueError(
                f"{info.field_name} must be greater than 0."
            )
        return value


    