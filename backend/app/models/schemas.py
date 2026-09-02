from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FlightPredictionRequest(BaseModel):
    airline: str
    flight: str | None = None
    source_city: str
    departure_time: str
    stops: str
    arrival_time: str
    destination_city: str
    class_: str | None = None
    duration: float
    days_left: int
    month: str | None = None
    holiday: str | None = None
    trip_purpose: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("airline", "source_city", "departure_time", "arrival_time", "destination_city", "class_")
    @classmethod
    def validate_required_string(cls, value: str | None, info):
        if value is None or not str(value).strip():
            raise ValueError(f"{info.field_name.replace('_', ' ').title()} is required.")
        return str(value).strip()

    @field_validator("flight")
    @classmethod
    def validate_flight(cls, value: str | None):
        return str(value).strip() if value is not None else value

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: float):
        if value <= 0:
            raise ValueError("Duration must be greater than 0.")
        return value

    @field_validator("days_left")
    @classmethod
    def validate_days_left(cls, value: int):
        if value < 1:
            raise ValueError("Days left must be at least 1.")
        return value

    @field_validator("stops")
    @classmethod
    def validate_stops(cls, value: str):
        normalized = str(value).strip()
        if normalized not in {"zero", "one", "two_or_more"}:
            raise ValueError("Stops must be one of: zero, one, or two_or_more.")
        return normalized

    @field_validator("departure_time", "arrival_time")
    @classmethod
    def validate_time(cls, value: str):
        normalized = str(value).strip()
        allowed = {"Early Morning", "Morning", "Afternoon", "Evening", "Night", "Late Night", "Early_Morning", "Late_Night"}
        if normalized not in allowed:
            raise ValueError("Departure and arrival times must be selected from the allowed values.")
        return normalized

    @field_validator("month", "trip_purpose")
    @classmethod
    def validate_optional_text(cls, value: str | None):
        return str(value).strip() or None if value is not None else value

    @field_validator("holiday")
    @classmethod
    def validate_holiday(cls, value: str | None):
        normalized = str(value).strip() if value is not None else value
        if normalized and normalized not in {"Yes", "No", "yes", "no", "true", "false"}:
            raise ValueError("Holiday must be Yes or No.")
        return normalized or None if normalized is not None else None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    trip_context: dict[str, Any] | None = None
    conversation_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def map_class_key(cls, data: Any):
        if isinstance(data, dict) and "class" in data and "class_" not in data:
            data["class_"] = data["class"]
        return data
