
import re
from typing import List, Literal
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo
)



class CreatePaymentOrderRequest(BaseModel):

    idempotency_key: str
    user_id: int
    booking_id: int
    amount: int
    
    @field_validator(
        "user_id",
        "booking_id",
        "amount",
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
