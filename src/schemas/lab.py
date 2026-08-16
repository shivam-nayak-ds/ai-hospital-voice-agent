from pydantic import BaseModel, Field, field_validator


class LabReportQuerySchema(BaseModel):
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
