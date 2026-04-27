
from datetime import time
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ValidationInfo,
)


class RouteStationItemRequest(BaseModel):

    # Example:
    # {
    #   "station_id": 1,
    #   "sequence_number": 1,
    #   "arrival_time": "15:00",
    #   "departure_time": "15:10",
    #   "distance_from_origin": 0
    # }

    station_id: int
    sequence_number: int
    arrival_time: time
    departure_time: time
    distance_from_origin: float

    @field_validator("station_id")
    @classmethod
    def validate_station_id(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("station_id must be greater than 0")
        return v

    @field_validator("sequence_number")
    @classmethod
    def validate_sequence_number(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("sequence_number must be greater than 0")
        return v

    @field_validator("distance_from_origin")
    @classmethod
    def validate_distance_non_negative(cls, v, info: ValidationInfo):
        if v < 0:
            raise ValueError("distance_from_origin cannot be negative")
        return v

    @model_validator(mode="after")
    def validate_arrival_departure_for_row(self):
        # For same station row: arrival must be before departure
        if self.arrival_time >= self.departure_time:
            raise ValueError("arrival_time must be less than departure_time for each station")
        return self


class TrainRouteCreateRequest(BaseModel):

    # Example:
    # {
    #   "train_id": 1,
    #   "station_details": [
    #     {
    #       "station_id": 1,
    #       "sequence_number": 1,
    #       "arrival_time": "15:00",
    #       "departure_time": "15:10",
    #       "distance_from_origin": 0
    #     },
    #     {
    #       "station_id": 2,
    #       "sequence_number": 2,
    #       "arrival_time": "15:30",
    #       "departure_time": "15:40",
    #       "distance_from_origin": 10
    #     }
    #   ]
    # }
    
    train_id: int
    station_details: list[RouteStationItemRequest]

    @field_validator("train_id")
    @classmethod
    def validate_train_id(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("train_id must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_route_structure(self):
        if not self.station_details:
            raise ValueError("station_details is required")

        seq_values = [s.sequence_number for s in self.station_details]

        # Sequence numbers must be unique
        if len(set(seq_values)) != len(seq_values):
            raise ValueError("sequence_number must be unique in station_details")

        # Must be strict sequence 1..N
        expected_sequence = list(range(1, len(self.station_details) + 1))
        if sorted(seq_values) != expected_sequence:
            raise ValueError(f"sequence_number must be strict sequence 1..{len(self.station_details)}")

        # station_id should not repeat in same route (also protected by DB unique index)
        station_ids = [s.station_id for s in self.station_details]
        if len(set(station_ids)) != len(station_ids):
            raise ValueError("station_id must be unique in station_details")

        # Validate by sequence order
        ordered = sorted(self.station_details, key=lambda x: x.sequence_number)

        # First station distance must be zero
        if ordered[0].distance_from_origin != 0:
            raise ValueError("distance_from_origin must be 0 for first station (sequence_number=1)")

        # Remaining stations distance must be > 0
        for row in ordered[1:]:
            if row.distance_from_origin <= 0:
                raise ValueError(
                    "distance_from_origin must be greater than 0 except first station (sequence_number=1)"
                )

        # No time overlap across stations:
        # next arrival must be strictly greater than previous departure
        for i in range(1, len(ordered)):
            prev_row = ordered[i - 1]
            curr_row = ordered[i]
            if curr_row.arrival_time <= prev_row.departure_time:
                raise ValueError(
                    "arrival_time and departure_time must not overlap between consecutive stations"
                )

        return self
