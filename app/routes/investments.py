# app/routes/investments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.routes.users import get_current_user
from app.schemas.investment import InvestmentCreate, InvestmentResponse, PnLData
from app.models.user import User
from app.models.asset import Asset
from app.models.investment import Investment
from app.models.wallet import Wallet, Transaction
from app.models.activity import Activity

router = APIRouter()

@router.get("/my", response_model=list[InvestmentResponse])
def get_my_investments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    investments = db.query(Investment).filter(
        Investment.user_id == current_user.id
    ).order_by(Investment.created_at.desc()).all()
    
    # Add asset names to response
    result = []
    for investment in investments:
        investment_dict = InvestmentResponse.from_orm(investment).dict()
        investment_dict['asset_name'] = investment.asset.name
        result.append(investment_dict)
    
    return result

@router.post("/buy", response_model=InvestmentResponse)
def buy_investment(
    investment_data: InvestmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get asset
    asset = db.query(Asset).filter(Asset.id == investment_data.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Check minimum investment
    if investment_data.invested_amount < asset.min_investment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum investment is {asset.min_investment}"
        )
    
    # Get wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Check balance
    if wallet.balance < investment_data.invested_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )
    
    # Calculate units
    units = investment_data.invested_amount / asset.current_price
    
    # Create investment
    investment = Investment(
        user_id=current_user.id,
        asset_id=asset.id,
        invested_amount=investment_data.invested_amount,
        current_value=investment_data.invested_amount,
        units=units,
        entry_price=asset.current_price,
        current_price=asset.current_price,
        profit_loss=0.0,
        profit_loss_percentage=0.0,
        status="active"
    )
    
    # Update wallet
    wallet.balance -= investment_data.invested_amount
    
    # Create transaction
    transaction = Transaction(
        wallet_id=wallet.id,
        amount=-investment_data.invested_amount,
        transaction_type="investment",
        status="completed",
        description=f"Investment in {asset.name}",
        reference=f"INV_{current_user.id}_{asset.id}"
    )
    
    # Create activity
    activity = Activity(
        user_id=current_user.id,
        activity_type="investment",
        amount=-investment_data.invested_amount,
        description=f"Invested {investment_data.invested_amount} in {asset.name}",
        status="completed"
    )
    
    db.add(investment)
    db.add(transaction)
    db.add(activity)
    db.commit()
    db.refresh(investment)
    
    # Prepare response
    response = InvestmentResponse.from_orm(investment)
    response.asset_name = asset.name
    
    return response

@router.get("/pnl/current", response_model=PnLData)
def get_current_pnl(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    investments = db.query(Investment).filter(
        Investment.user_id == current_user.id,
        Investment.status == "active"
    ).all()
    
    total_invested = sum(inv.invested_amount for inv in investments)
    total_current = sum(inv.current_value for inv in investments)
    total_pnl = total_current - total_invested
    
    if total_invested > 0:
        pnl_percentage = (total_pnl / total_invested) * 100
    else:
        pnl_percentage = 0.0
    
    return PnLData(
        profit_loss=total_pnl,
        percentage=pnl_percentage,
        trend="up" if total_pnl >= 0 else "down"
    )