
from datetime import date
from pydantic import BaseModel, field_validator, ValidationInfo


class TrainScheduleCreateRequest(BaseModel):
    
    """
    Example request:
    {
      "train_id": 1,
      "departure_date": "2026-04-27"
    }
    """

    train_id: int
    departure_date: date

    @field_validator("train_id")
    @classmethod
    def validate_train_id(cls, v, info: ValidationInfo):
        if v <= 0:
            raise ValueError("train_id must be greater than 0")
        return v
