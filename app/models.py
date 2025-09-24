from pydantic import BaseModel
from typing import Optional

class Company(BaseModel):
    name: str
    sector: Optional[str] = None
    valuation: Optional[str] = None  # Now a string
    website: Optional[str] = None
    investors: Optional[str] = None
    latest_funding: Optional[str] = None
    latest_funding_date: Optional[str] = None
    total_funding: Optional[str] = None
    overview: Optional[str] = None

    # This allows creating the model from a pandas row easily
    class Config:
        from_attributes = True
