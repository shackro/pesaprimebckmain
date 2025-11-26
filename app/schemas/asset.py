# app/schemas/asset.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AssetBase(BaseModel):
    name: str
    symbol: str
    type: str
    current_price: float
    change_percentage: float
    moving_average: float
    trend: str
    chart_url: Optional[str] = None
    hourly_income: float
    min_investment: float
    duration: int

class AssetCreate(AssetBase):
    id: str

class AssetResponse(AssetBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class AssetUpdate(BaseModel):
    current_price: Optional[float] = None
    change_percentage: Optional[float] = None
    moving_average: Optional[float] = None
    trend: Optional[str] = None
    hourly_income: Optional[float] = None
    min_investment: Optional[float] = None

class PriceHistoryResponse(BaseModel):
    asset_id: str
    price: float
    timestamp: datetime

    class Config:
        from_attributes = True