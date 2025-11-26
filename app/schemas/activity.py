# app/schemas/activity.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ActivityBase(BaseModel):
    activity_type: str
    amount: float
    description: Optional[str] = None

class ActivityResponse(ActivityBase):
    id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ActivityCreate(ActivityBase):
    user_id: int
    metadata: Optional[str] = None