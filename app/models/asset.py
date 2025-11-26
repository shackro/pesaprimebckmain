# app/models/asset.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    type = Column(String, nullable=False)  # crypto, forex, stock
    current_price = Column(Float, default=0.0)
    change_percentage = Column(Float, default=0.0)
    moving_average = Column(Float, default=0.0)
    trend = Column(String, default="up")  # up, down
    chart_url = Column(Text)
    hourly_income = Column(Float, default=0.0)
    min_investment = Column(Float, default=0.0)
    duration = Column(Integer, default=24)  # hours
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())