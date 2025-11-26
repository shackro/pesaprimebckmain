# app/schemas/investment.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InvestmentBase(BaseModel):
    asset_id: str
    invested_amount: float
    units: float
    entry_price: float

class InvestmentCreate(InvestmentBase):
    phone_number: str

class InvestmentResponse(InvestmentBase):
    id: int
    user_id: int
    current_value: float
    current_price: float
    profit_loss: float
    profit_loss_percentage: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    asset_name: str

    class Config:
        from_attributes = True

class InvestmentUpdate(BaseModel):
    current_value: Optional[float] = None
    current_price: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percentage: Optional[float] = None
    status: Optional[str] = None

class PnLData(BaseModel):
    profit_loss: float
    percentage: float
    trend: str