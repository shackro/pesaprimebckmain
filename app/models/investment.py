# app/models/investment.py
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False)
    invested_amount = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    units = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    profit_loss = Column(Float, default=0.0)
    profit_loss_percentage = Column(Float, default=0.0)
    status = Column(String, default="active")  # active, closed, pending
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")
    asset = relationship("Asset")