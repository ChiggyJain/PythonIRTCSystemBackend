
import re
from typing import List, Literal
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo
)


class LockSeatsRequest(BaseModel):
    
    user_id: int
    schedule_id: int
    seat_ids: List[int]
    ttl_seconds: int
    from_station_sequence_number: int
    to_station_sequence_number: int
    
    @field_validator(
        "user_id",
        "schedule_id",
        "ttl_seconds",
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
    def validate_sequence_number(self):

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

        return self