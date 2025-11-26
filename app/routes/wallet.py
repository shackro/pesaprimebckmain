# app/routes/wallet.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from app.core.database import get_db
from app.routes.users import get_current_user
from app.schemas.wallet import WalletResponse, TransactionResponse, DepositRequest, WithdrawRequest
from app.models.user import User
from app.models.wallet import Wallet, Transaction
from app.models.activity import Activity

router = APIRouter()

@router.get("/balance", response_model=WalletResponse)
def get_wallet_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    return wallet

@router.post("/deposit")
def deposit_funds(
    deposit_data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if deposit_data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )
    
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Create transaction
    transaction = Transaction(
        wallet_id=wallet.id,
        amount=deposit_data.amount,
        transaction_type="deposit",
        status="completed",
        description=f"Deposit via {deposit_data.phone_number}",
        reference=str(uuid.uuid4())
    )
    
    # Update wallet balance
    wallet.balance += deposit_data.amount
    wallet.equity += deposit_data.amount
    
    # Create activity
    activity = Activity(
        user_id=current_user.id,
        activity_type="deposit",
        amount=deposit_data.amount,
        description=f"Deposit of {deposit_data.amount} {wallet.currency}",
        status="completed"
    )
    
    db.add(transaction)
    db.add(activity)
    db.commit()
    
    return {
        "message": "Deposit successful",
        "new_balance": wallet.balance,
        "transaction_reference": transaction.reference
    }

@router.post("/withdraw")
def withdraw_funds(
    withdraw_data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if withdraw_data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )
    
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    if wallet.balance < withdraw_data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )
    
    # Create transaction
    transaction = Transaction(
        wallet_id=wallet.id,
        amount=withdraw_data.amount,
        transaction_type="withdraw",
        status="completed",
        description=f"Withdrawal to {withdraw_data.phone_number}",
        reference=str(uuid.uuid4())
    )
    
    # Update wallet balance
    wallet.balance -= withdraw_data.amount
    wallet.equity -= withdraw_data.amount
    
    # Create activity
    activity = Activity(
        user_id=current_user.id,
        activity_type="withdraw",
        amount=-withdraw_data.amount,
        description=f"Withdrawal of {withdraw_data.amount} {wallet.currency}",
        status="completed"
    )
    
    db.add(transaction)
    db.add(activity)
    db.commit()
    
    return {
        "message": "Withdrawal successful",
        "new_balance": wallet.balance,
        "transaction_reference": transaction.reference
    }

@router.get("/transactions")
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    transactions = db.query(Transaction).filter(
        Transaction.wallet_id == wallet.id
    ).order_by(Transaction.created_at.desc()).all()
    
    return transactions