# app/routes/assets.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.routes.users import get_current_user
from app.schemas.asset import AssetResponse
from app.models.asset import Asset, PriceHistory
from app.models.user import User

router = APIRouter()

@router.get("/market", response_model=list[AssetResponse])
def get_market_assets(
    type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Asset).filter(Asset.is_active == True)
    
    if type:
        query = query.filter(Asset.type == type)
    
    assets = query.order_by(Asset.name).all()
    return assets

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    return asset

@router.get("/{asset_id}/history")
def get_asset_history(
    asset_id: str,
    timeframe: str = "1h",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Get price history (simplified - in production, use proper time filtering)
    history = db.query(PriceHistory).filter(
        PriceHistory.asset_id == asset_id
    ).order_by(PriceHistory.timestamp.desc()).limit(100).all()
    
    return history