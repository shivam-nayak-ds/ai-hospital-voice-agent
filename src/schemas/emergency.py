from pydantic import BaseModel, Field

class EmergencyQuerySchema(BaseModel):
    user_query: str = Field(..., min_length=3, max_length=500)
