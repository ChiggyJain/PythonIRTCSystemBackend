
from decimal import Decimal
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
    amount: Decimal
    
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
    


class CreatePaymentOrderRefundRequest(BaseModel):

    idempotency_key: str
    payment_order_id: int
    amount: Decimal
    reason: str
    
    @field_validator(
        "payment_order_id",
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
