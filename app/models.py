from pydantic import BaseModel
from typing import Optional

class Company(BaseModel):
    name: str
    website: Optional[str] = None
    latest_funding: Optional[str] = None
    latest_funding_date: Optional[str] = None
    total_funding: Optional[str] = None
    investors: Optional[str] = None
    valuation: Optional[str] = None
    overview: Optional[str] = None
    sector: Optional[str] = None
    sinarmas_interest: Optional[str] = None
    implied_valuation: Optional[str] = None
    share_transfer_allowed: Optional[str] = None
    liquidity_ez: Optional[str] = None
    liquidity_forge: Optional[str] = None
    liquidity_nasdaq: Optional[str] = None

    # This allows creating the model from a pandas row easily
    class Config:
        from_attributes = True
