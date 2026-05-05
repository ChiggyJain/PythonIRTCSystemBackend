
from datetime import time
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo,
)


class BookingRequest(BaseModel):

    idempotency_key: str
    schedule_id: int
    from_station_id: int
    to_station_id: int
    from_station_sequence_number: int
    to_station_sequence_number: int
    seat_ids: int
    passengers: str
 