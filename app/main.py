from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import secrets
from passlib.context import CryptContext
import json
import os
import random
import uuid
import aiohttp
import asyncio

# Security setup - Remove JWT dependencies
pwd_context = CryptContext(schemes=["md5_crypt"], deprecated="auto")

# Get allowed origins from environment
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://pesaprime.vercel.app")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "https://pesaprime.vercel.app",
    "http://localhost:5173"  # Vite default port
]

app = FastAPI(
    title="Pesaprime API",
    description="Personal Finance Dashboard Backend",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use absolute paths for production
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
USER_ACTIVITY_FILE = os.path.join(BASE_DIR, "user_activity.json")
USER_WALLETS_FILE = os.path.join(BASE_DIR, "user_wallets.json")
USER_INVESTMENTS_FILE = os.path.join(BASE_DIR, "user_investments.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "sessions.json")  # New sessions file

# Pydantic models (remove token-related fields)
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone_number: str
    created_at: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: UserResponse
    session_id: str  # Replace token with session_id

class WalletData(BaseModel):
    balance: float
    equity: float
    currency: str

class DepositRequest(BaseModel):
    amount: float
    phone_number: str
    session_id: str  # Add session_id to requests

class WithdrawRequest(BaseModel):
    amount: float
    phone_number: str
    session_id: str

class InvestmentRequest(BaseModel):
    asset_id: str
    amount: float
    phone_number: str
    session_id: str

class TransactionResponse(BaseModel):
    success: bool
    message: str
    new_balance: float
    new_equity: float
    transaction_id: str

# ... (keep your existing Asset, UserInvestment, UserActivity, PnLData models)

# Session management
class SessionManager:
    def __init__(self):
        self.sessions_file = SESSIONS_FILE
    
    def load_sessions(self):
        return load_data(self.sessions_file, default={})
    
    def save_sessions(self, sessions):
        save_data(sessions, self.sessions_file)
    
    def create_session(self, user_email: str, phone_number: str) -> str:
        sessions = self.load_sessions()
        session_id = secrets.token_urlsafe(32)
        
        sessions[session_id] = {
            "user_email": user_email,
            "phone_number": phone_number,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }
        
        self.save_sessions(sessions)
        return session_id
    
    def validate_session(self, session_id: str) -> dict:
        sessions = self.load_sessions()
        session = sessions.get(session_id)
        
        if not session:
            return None
        
        # Update last accessed time
        session["last_accessed"] = datetime.utcnow().isoformat()
        sessions[session_id] = session
        self.save_sessions(sessions)
        
        return session
    
    def delete_session(self, session_id: str):
        sessions = self.load_sessions()
        if session_id in sessions:
            del sessions[session_id]
            self.save_sessions(sessions)

session_manager = SessionManager()

# Simple dependency for session validation
async def get_current_user(session_id: str):
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    session = session_manager.validate_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    users = load_data(USERS_FILE)
    user = users.get(session["user_email"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Utility functions (keep your existing ones)
def load_data(filename, default=None):
    """Load data from JSON file"""
    if default is None:
        default = {}
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading data from {filename}: {e}")
        return default

def save_data(data, filename):
    """Save data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data to {filename}: {e}")

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except:
        return plain_password == hashed_password

def get_password_hash(password):
    try:
        return pwd_context.hash(password)
    except:
        return password

# ... (keep your existing asset price generation functions)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    required_files = [USERS_FILE, USER_ACTIVITY_FILE, USER_WALLETS_FILE, USER_INVESTMENTS_FILE, SESSIONS_FILE]
    for file_path in required_files:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)
            print(f"Created {file_path}")

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to PesaDash API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "PesaDash API", "timestamp": datetime.utcnow().isoformat()}

# Authentication endpoints (updated)
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    users = load_data(USERS_FILE)
    
    if user_data.email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if phone number is already registered
    for existing_user in users.values():
        if isinstance(existing_user, dict) and existing_user.get("phone_number") == user_data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    user_id = generate_user_id()
    hashed_password = get_password_hash(user_data.password)
    
    user = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "phone_number": user_data.phone_number,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Initialize user wallet
    wallets = load_data(USER_WALLETS_FILE, default={})
    wallets[user_data.phone_number] = {
        "balance": 5000.0,  # Start with 5000 KES
        "equity": 5000.0,
        "currency": "KES"
    }
    
    users[user_data.email] = user
    save_data(users, USERS_FILE)
    save_data(wallets, USER_WALLETS_FILE)
    
    # Create session
    session_id = session_manager.create_session(user_data.email, user_data.phone_number)
    
    # Log registration activity
    log_user_activity(user_data.phone_number, "registration", 0, "User registered successfully")
    log_user_activity(user_data.phone_number, "deposit", 5000, "Welcome bonus deposited")
    
    return AuthResponse(
        success=True,
        message="User registered successfully",
        user=UserResponse(**{k: v for k, v in user.items() if k != 'hashed_password'}),
        session_id=session_id
    )

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(login_data: UserLogin):
    users = load_data(USERS_FILE)
    
    print(f"Login attempt for email: {login_data.email}")
    print(f"Available users: {list(users.keys())}")
    
    user = users.get(login_data.email)
    
    if not user:
        print(f"User not found: {login_data.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not verify_password(login_data.password, user["hashed_password"]):
        print("Password verification failed")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Create session
    session_id = session_manager.create_session(user["email"], user["phone_number"])
    
    print(f"Login successful for: {user['email']}")
    
    return AuthResponse(
        success=True,
        message="Login successful",
        user=UserResponse(**{k: v for k, v in user.items() if k != 'hashed_password'}),
        session_id=session_id
    )

@app.post("/api/auth/logout")
async def logout(session_id: str):
    session_manager.delete_session(session_id)
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(session_id: str):
    """Get current user information"""
    user = await get_current_user(session_id)
    return UserResponse(**{k: v for k, v in user.items() if k != 'hashed_password'})

# Wallet endpoints (updated with session_id)
@app.get("/api/wallet/balance/{phone_number}")
async def get_wallet_balance(phone_number: str, session_id: str):
    # Validate session
    await get_current_user(session_id)
    
    wallets = load_data(USER_WALLETS_FILE, default={})
    user_wallet = wallets.get(phone_number, {"balance": 0, "equity": 0, "currency": "KES"})
    
    # Update equity based on investments
    await update_investment_values(phone_number)
    
    return WalletData(**user_wallet)

@app.post("/api/wallet/deposit", response_model=TransactionResponse)
async def deposit_funds(deposit_data: DepositRequest):
    # Validate session and get user
    user = await get_current_user(deposit_data.session_id)
    
    if deposit_data.phone_number != user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(USER_WALLETS_FILE, default={})
    user_wallet = wallets.get(user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    user_wallet["balance"] += deposit_data.amount
    user_wallet["equity"] += deposit_data.amount
    
    wallets[user["phone_number"]] = user_wallet
    save_data(wallets, USER_WALLETS_FILE)
    
    log_user_activity(
        user["phone_number"], 
        "deposit", 
        deposit_data.amount, 
        f"Deposit of KSh {deposit_data.amount}"
    )
    
    return TransactionResponse(
        success=True,
        message="Deposit successful",
        new_balance=user_wallet["balance"],
        new_equity=user_wallet["equity"],
        transaction_id=f"DEP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

@app.post("/api/wallet/withdraw", response_model=TransactionResponse)
async def withdraw_funds(withdraw_data: WithdrawRequest):
    # Validate session and get user
    user = await get_current_user(withdraw_data.session_id)
    
    if withdraw_data.phone_number != user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(USER_WALLETS_FILE, default={})
    user_wallet = wallets.get(user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    if user_wallet["balance"] < withdraw_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    user_wallet["balance"] -= withdraw_data.amount
    user_wallet["equity"] -= withdraw_data.amount
    
    wallets[user["phone_number"]] = user_wallet
    save_data(wallets, USER_WALLETS_FILE)
    
    log_user_activity(
        user["phone_number"], 
        "withdraw", 
        withdraw_data.amount, 
        f"Withdrawal of KSh {withdraw_data.amount}"
    )
    
    return TransactionResponse(
        success=True,
        message="Withdrawal successful",
        new_balance=user_wallet["balance"],
        new_equity=user_wallet["equity"],
        transaction_id=f"WD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

# Investment endpoints (updated with session_id)
@app.post("/api/investments/buy")
async def buy_investment(investment_data: InvestmentRequest):
    # Validate session and get user
    user = await get_current_user(investment_data.session_id)
    
    if investment_data.phone_number != user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(USER_WALLETS_FILE, default={})
    user_wallet = wallets.get(user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    # Convert investment amount to KES for validation
    amount_kes = investment_data.amount
    
    if user_wallet["balance"] < amount_kes:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    assets = await generate_dynamic_prices()
    asset = next((a for a in assets if a["id"] == investment_data.asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Check minimum investment (already in KES)
    if amount_kes < asset["min_investment"]:
        raise HTTPException(status_code=400, detail=f"Minimum investment is {asset['min_investment']} KES")
    
    units = amount_kes / asset["current_price"]
    
    investments = load_data(USER_INVESTMENTS_FILE, default={})
    investment_id = get_next_id(investments)
    
    investment = {
        "id": investment_id,
        "user_phone": user["phone_number"],
        "asset_id": investment_data.asset_id,
        "asset_name": asset["name"],
        "invested_amount": amount_kes,
        "current_value": amount_kes,
        "units": units,
        "entry_price": asset["current_price"],
        "current_price": asset["current_price"],
        "hourly_income": asset["hourly_income"],
        "total_income": asset["total_income"],
        "duration": asset["duration"],
        "roi_percentage": asset["roi_percentage"],
        "profit_loss": 0.0,
        "profit_loss_percentage": 0.0,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "completion_time": (datetime.utcnow() + timedelta(hours=asset["duration"])).isoformat()
    }
    
    investments[investment_id] = investment
    save_data(investments, USER_INVESTMENTS_FILE)
    
    user_wallet["balance"] -= amount_kes
    wallets[user["phone_number"]] = user_wallet
    save_data(wallets, USER_WALLETS_FILE)
    
    log_user_activity(
        user["phone_number"], 
        "investment", 
        amount_kes, 
        f"Investment in {asset['name']} - {units:.4f} units"
    )
    
    return {
        "success": True,
        "message": f"Investment in {asset['name']} successful",
        "investment": investment,
        "new_balance": user_wallet["balance"]
    }

# Market data endpoints (public - no auth required)
@app.get("/api/assets/market", response_model=List[Asset])
async def get_market_assets():
    return await generate_dynamic_prices()

@app.get("/api/investments/my/{phone_number}", response_model=List[UserInvestment])
async def get_my_investments(phone_number: str, session_id: str):
    # Validate session
    await get_current_user(session_id)
    
    investments = load_data(USER_INVESTMENTS_FILE, default={})
    user_investments = [
        inv for inv in investments.values() 
        if inv["user_phone"] == phone_number and inv["status"] == "active"
    ]
    
    await update_investment_values(phone_number)
    
    return user_investments

@app.get("/api/activities/my/{phone_number}", response_model=List[UserActivity])
async def get_my_activities(phone_number: str, session_id: str):
    # Validate session
    await get_current_user(session_id)
    
    activities = load_data(USER_ACTIVITY_FILE, default={})
    user_activities = [
        activity for activity in activities.values() 
        if activity["user_phone"] == phone_number
    ]
    user_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return user_activities[:20]

@app.get("/api/wallet/pnl", response_model=PnLData)
async def get_user_pnl(phone_number: str, session_id: str):
    """Calculate user's overall PnL across active investments"""
    # Validate session
    await get_current_user(session_id)
    
    await update_investment_values(phone_number)
    investments = load_data(USER_INVESTMENTS_FILE, default={})
    
    total_invested = 0
    total_current_value = 0
    
    for inv in investments.values():
        if inv["user_phone"] == phone_number and inv["status"] == "active":
            total_invested += inv.get("invested_amount", 0)
            total_current_value += inv.get("current_value", 0)
    
    if total_invested == 0:
        profit_loss = 0
        percentage = 0
        trend = "neutral"
    else:
        profit_loss = total_current_value - total_invested
        percentage = (profit_loss / total_invested) * 100
        trend = "up" if profit_loss >= 0 else "down"
    
    return PnLData(
        profit_loss=round(profit_loss, 2),
        percentage=round(percentage, 2),
        trend=trend
    )

# ADD MISSING ROUTES THAT YOUR FRONTEND EXPECTS
@app.get("/api/investments/assets")
async def get_investment_assets():
    """Alternative route for assets"""
    return await generate_dynamic_prices()

@app.get("/api/investments/my-investments")
async def get_my_investments_alt(phone_number: str, session_id: str):
    """Alternative route for investments without phone number in URL"""
    return await get_my_investments(phone_number, session_id)

@app.get("/api/activities")
async def get_activities_alt(phone_number: str, session_id: str):
    """Alternative route for activities without phone number in URL"""
    # Validate session
    await get_current_user(session_id)
    
    activities = load_data(USER_ACTIVITY_FILE, default={})
    user_activities = [
        activity for activity in activities.values() 
        if activity["user_phone"] == phone_number
    ]
    user_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return user_activities[:20]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
