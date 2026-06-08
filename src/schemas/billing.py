from pydantic import BaseModel, Field

class BillingQuerySchema(BaseModel):
    item_name: str = Field(..., min_length=2, max_length=100)

class InsuranceQuerySchema(BaseModel):
    provider_name: str = Field(..., min_length=2, max_length=100)
