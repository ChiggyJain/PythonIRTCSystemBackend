
import re
from decimal import Decimal
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo,
)

TRAIN_NUMBER_REGEX = re.compile(r"^[A-Z0-9_-]{2,30}$")
COACH_NAME_REGEX = re.compile(r"^[A-Z0-9_]{1,10}$")

ALLOWED_SEAT_TYPES = {
    "LOWER",
    "MIDDLE",
    "UPPER",
    "SIDE_LOWER",
    "SIDE_UPPER",
}


class TrainSeatItemRequest(BaseModel):

    # Example: {"seat_number": 1, "seat_type": "LOWER", "price": 500}
    seat_number: int
    seat_type: str
    price: Decimal

    @field_validator("seat_type", mode="before")
    @classmethod
    def strip_seat_type(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            v = v.strip()
        return v

    @field_validator("seat_number")
    @classmethod
    def validate_seat_number(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("seat_number must be greater than 0")
        return v

    @field_validator("seat_type")
    @classmethod
    def validate_seat_type(cls, v, info: ValidationInfo):
        value = (v or "").upper()
        if value not in ALLOWED_SEAT_TYPES:
            raise ValueError("seat_type must be one of LOWER, MIDDLE, UPPER, SIDE_LOWER, SIDE_UPPER")
        return value

    @field_validator("price")
    @classmethod
    def validate_price(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("price must be greater than 0")
        return v


class TrainCreateRequest(BaseModel):

    # Example:
    # {
    #   "train_number": "Train1233",
    #   "train_name": "T1",
    #   "coach_name": "AC",
    #   "total_seats": 2,
    #   "seat_details": [
    #       {"seat_number": 1, "seat_type": "LOWER", "price": 500},
    #       {"seat_number": 2, "seat_type": "UPPER", "price": 300}
    #   ]
    # }
    train_number: str
    train_name: str
    coach_name: str
    total_seats: int
    seat_details: list[TrainSeatItemRequest]


    @field_validator("train_number", "train_name", "coach_name", mode="before")
    @classmethod
    def strip_values(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            v = v.strip()
        return v


    @field_validator("train_number")
    @classmethod
    def validate_train_number(cls, v, info: ValidationInfo):
        value = (v or "").upper()
        if not value:
            raise ValueError("train_number is required")
        if not TRAIN_NUMBER_REGEX.match(value):
            raise ValueError("train_number must be 2-30 chars (A-Z, 0-9, _, -)")
        return value

    @field_validator("train_name")
    @classmethod
    def validate_train_name(cls, v, info: ValidationInfo):
        if not v:
            raise ValueError("train_name is required")
        if len(v) > 100:
            raise ValueError("train_name max length is 100")
        return v

    @field_validator("coach_name")
    @classmethod
    def validate_coach_name(cls, v, info: ValidationInfo):
        value = (v or "").upper()
        if not value:
            raise ValueError("coach_name is required")
        if not COACH_NAME_REGEX.match(value):
            raise ValueError("coach_name must be 1-10 chars (A-Z, 0-9, _)")
        return value

    @field_validator("total_seats")
    @classmethod
    def validate_total_seats(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("total_seats must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_seat_details_structure(self):
        if not self.seat_details:
            raise ValueError("seat_details is required")

        if len(self.seat_details) != self.total_seats:
            raise ValueError("seat_details length must match total_seats")

        seat_numbers = [item.seat_number for item in self.seat_details]

        if len(set(seat_numbers)) != len(seat_numbers):
            raise ValueError("seat_number must be unique in seat_details")

        expected_sequence = list(range(1, self.total_seats + 1))
        if sorted(seat_numbers) != expected_sequence:
            raise ValueError(f"seat_number must be strict sequence 1..{self.total_seats}")

        return self
