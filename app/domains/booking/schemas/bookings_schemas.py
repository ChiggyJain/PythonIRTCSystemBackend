
import re
from typing import List, Literal
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo
)

class PassengerSchema(BaseModel):

    seat_id: int
    name: str
    age: int
    gender: Literal["Male", "Female", "Transgender", "Other"]

    @field_validator("seat_id")
    @classmethod
    def validate_seat_id(cls, value: int):
        if value <= 0:
            raise ValueError("passenger seat_id must be greater than 0.")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("passenger name is required.")
        if not re.fullmatch(r"[A-Za-z ]+", value):
            raise ValueError(
                "passenger name must contain alphabets and spaces only."
            )
        return value

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int):
        if value <= 0:
            raise ValueError("passenger age must be greater than 0.")
        return value


class CreateBookingRequest(BaseModel):

    idempotency_key: str
    schedule_id: int
    from_station_id: int
    to_station_id: int
    from_station_sequence_number: int
    to_station_sequence_number: int
    seat_ids: List[int]
    passengers: List[PassengerSchema]

    @field_validator(
        "schedule_id",
        "from_station_id",
        "to_station_id",
        "from_station_sequence_number",
        "to_station_sequence_number",
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


    @field_validator("seat_ids")
    @classmethod
    def validate_seat_ids(
        cls,
        value: List[int],
    ):

        if not value:
            raise ValueError(
                "seat_ids cannot be empty."
            )
        for seat_id in value:
            if seat_id <= 0:
                raise ValueError(
                    "all seat_ids must be greater than 0."
                )
        if len(value) != len(set(value)):
            raise ValueError(
                "duplicate seat_ids are not allowed."
            )
        
        return value


    @model_validator(mode="after")
    def validate_booking_request(self):

        # from_station_id != to_station_id
        if (
            self.from_station_id
            == self.to_station_id
        ):
            raise ValueError(
                "from_station_id and to_station_id cannot be same."
            )

        # sequence number cannot be same
        if (
            self.from_station_sequence_number
            == self.to_station_sequence_number
        ):
            raise ValueError(
                "from_station_sequence_number and "
                "to_station_sequence_number cannot be same."
            )

        # from sequence must be less than to sequence
        if (
            self.from_station_sequence_number
            > self.to_station_sequence_number
        ):
            raise ValueError(
                "from_station_sequence_number must be "
                "less than to_station_sequence_number."
            )

        # seat_ids length == passengers length
        if (
            len(self.seat_ids)
            != len(self.passengers)
        ):
            raise ValueError(
                "seat_ids length must match passengers length."
            )

        # passenger seat_ids validation
        passenger_seat_ids = [
            passenger.seat_id
            for passenger in self.passengers
        ]

        if len(passenger_seat_ids) != len(set(passenger_seat_ids)):
            raise ValueError(
                "duplicate passenger seat_id values are not allowed."
            )

        # seat_ids must exist in passengers
        if set(self.seat_ids) != set(passenger_seat_ids):
            raise ValueError(
                "seat_ids must match passengers seat_id values."
            )

        return self