from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
import re

class SlotCheckSchema(BaseModel):
    doctor_name: str = Field(..., min_length=2, max_length=100)
    appointment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    appointment_time: str = Field(..., pattern=r"^(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM|am|pm)$")

    @field_validator("appointment_date")
    @classmethod
    def validate_date_not_past(cls, v: str) -> str:
        try:
            parsed_date = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        if parsed_date < date.today():
            raise ValueError("Appointment date cannot be in the past.")
        return v

class AppointmentBookSchema(SlotCheckSchema):
    patient_name: str = Field(..., min_length=1, max_length=100)
    patient_phone: str = Field(...)

    @field_validator("patient_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = "".join(filter(str.isdigit, v))
        if len(clean) > 10 and (clean.startswith("91") or clean.startswith("0")):
            clean = clean[-10:]
        if len(clean) != 10:
            raise ValueError("Phone number must be exactly 10 digits.")
        return clean

class AppointmentCancelSchema(BaseModel):
    appointment_id: int = Field(..., ge=1)
