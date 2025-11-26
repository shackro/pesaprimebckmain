from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os
import random
import uuid
import aiohttp
import asyncio

# Security setup - Simple session-based auth
app = FastAPI(
    title="Pesaprime API",
    description="Personal Finance Dashboard Backend",
    version="1.0.0"
)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
USER_ACTIVITY_FILE = os.path.join(BASE_DIR, "user_activity.json")
USER_WALLETS_FILE = os.path.join(BASE_DIR, "user_wallets.json")
USER_INVESTMENTS_FILE = os.path.join(BASE_DIR, "user_investments.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "sessions.json")

# Pydantic Models
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
    session_id: str

class WalletData(BaseModel):
    balance: float
    equity: float
    currency: str

class DepositRequest(BaseModel):
    amount: float
    phone_number: str

class WithdrawRequest(BaseModel):
    amount: float
    phone_number: str

class InvestmentRequest(BaseModel):
    asset_id: str
    amount: float
    phone_number: str

class TransactionResponse(BaseModel):
    success: bool
    message: str
    new_balance: float
    new_equity: float
    transaction_id: str

class Asset(BaseModel):
    id: str
    name: str
    symbol: str
    type: str
    current_price: float
    change_percentage: float
    moving_average: float
    trend: str
    chart_url: str
    hourly_income: float
    min_investment: float
    duration: int
    total_income: float
    roi_percentage: float

class UserInvestment(BaseModel):
    id: str
    user_phone: str
    asset_id: str
    asset_name: str
    invested_amount: float
    current_value: float
    units: float
    entry_price: float
    current_price: float
    profit_loss: float
    profit_loss_percentage: float
    status: str
    created_at: str
    hourly_income: Optional[float] = None
    total_income: Optional[float] = None
    duration: Optional[int] = None
    roi_percentage: Optional[float] = None
    completion_time: Optional[str] = None

class UserActivity(BaseModel):
    id: str
    user_phone: str
    activity_type: str
    amount: float
    description: str
    timestamp: str
    status: str

class PnLData(BaseModel):
    profit_loss: float
    percentage: float
    trend: str

# Dynamic Assets Data
PRODUCTION_ASSETS = {
    'crypto': [
        {'id': 'bitcoin', 'name': 'Bitcoin', 'symbol': 'BTC', 'type': 'crypto', 'coingecko_id': 'bitcoin', 'min_investment_kes': 450, 'hourly_income_range': [90, 150], 'duration': 24},
        {'id': 'ethereum', 'name': 'Ethereum', 'symbol': 'ETH', 'type': 'crypto', 'coingecko_id': 'ethereum', 'min_investment_kes': 450, 'hourly_income_range': [85, 140], 'duration': 24},
        {'id': 'binancecoin', 'name': 'Binance Coin', 'symbol': 'BNB', 'type': 'crypto', 'coingecko_id': 'binancecoin', 'min_investment_kes': 450, 'hourly_income_range': [80, 130], 'duration': 24},
        {'id': 'solana', 'name': 'Solana', 'symbol': 'SOL', 'type': 'crypto', 'coingecko_id': 'solana', 'min_investment_kes': 450, 'hourly_income_range': [95, 160], 'duration': 24},
        {'id': 'ripple', 'name': 'Ripple', 'symbol': 'XRP', 'type': 'crypto', 'coingecko_id': 'ripple', 'min_investment_kes': 450, 'hourly_income_range': [75, 120], 'duration': 24},
    ],
    'stocks': [
        {'id': 'apple', 'name': 'Apple Inc', 'symbol': 'AAPL', 'type': 'stocks', 'min_investment_kes': 500, 'hourly_income_range': [60, 100], 'duration': 24},
        {'id': 'microsoft', 'name': 'Microsoft Corp', 'symbol': 'MSFT', 'type': 'stocks', 'min_investment_kes': 500, 'hourly_income_range': [55, 95], 'duration': 24},
        {'id': 'tesla', 'name': 'Tesla Inc', 'symbol': 'TSLA', 'type': 'stocks', 'min_investment_kes': 500, 'hourly_income_range': [70, 120], 'duration': 24},
        {'id': 'amazon', 'name': 'Amazon.com Inc', 'symbol': 'AMZN', 'type': 'stocks', 'min_investment_kes': 500, 'hourly_income_range': [65, 110], 'duration': 24},
        {'id': 'google', 'name': 'Alphabet Inc', 'symbol': 'GOOGL', 'type': 'stocks', 'min_investment_kes': 500, 'hourly_income_range': [60, 105], 'duration': 24},
    ],
    'forex': [
        {'id': 'usd-kes', 'name': 'USD/KES', 'symbol': 'USDKES', 'type': 'forex', 'min_investment_kes': 400, 'hourly_income_range': [50, 90], 'duration': 24},
        {'id': 'eur-kes', 'name': 'EUR/KES', 'symbol': 'EURKES', 'type': 'forex', 'min_investment_kes': 400, 'hourly_income_range': [45, 85], 'duration': 24},
        {'id': 'gbp-kes', 'name': 'GBP/KES', 'symbol': 'GBPKES', 'type': 'forex', 'min_investment_kes': 400, 'hourly_income_range': [48, 88], 'duration': 24},
    ],
    'commodities': [
        {'id': 'gold', 'name': 'Gold', 'symbol': 'XAU', 'type': 'commodities', 'min_investment_kes': 600, 'hourly_income_range': [55, 95], 'duration': 24},
        {'id': 'silver', 'name': 'Silver', 'symbol': 'XAG', 'type': 'commodities', 'min_investment_kes': 600, 'hourly_income_range': [50, 90], 'duration': 24},
        {'id': 'crude-oil', 'name': 'Crude Oil', 'symbol': 'OIL', 'type': 'commodities', 'min_investment_kes': 600, 'hourly_income_range': [65, 110], 'duration': 24},
    ]
}

# Base Prices for Dynamic Generation
TODAYS_BASE_PRICES = {
    'BTC': 9203600.00, 'ETH': 301697.00, 'BNB': 32178.00, 'SOL': 10789.00, 'XRP': 650.50,
    'AAPL': 18500.00, 'MSFT': 34200.00, 'TSLA': 21500.00, 'AMZN': 15200.00, 'GOOGL': 12800.00,
    'USDKES': 130.50, 'EURKES': 142.25, 'GBPKES': 165.80,
    'XAU': 9500.00, 'XAG': 110.50, 'OIL': 9800.00
}

# Core Utility Functions
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
        print(f"Error loading {filename}: {e}")
        return default

def save_data(data, filename):
    """Save data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def generate_id():
    """Generate unique ID"""
    return str(uuid.uuid4())

def get_next_id(data):
    """Generate next numeric ID"""
    if not data:
        return "1"
    numeric_keys = [int(k) for k in data.keys() if k.isdigit()]
    return str(max(numeric_keys) + 1) if numeric_keys else "1"

# Session Management
class SessionManager:
    def create_session(self, user_email: str, phone_number: str) -> str:
        sessions = load_data(SESSIONS_FILE)
        session_id = generate_id()
        sessions[session_id] = {
            "user_email": user_email,
            "phone_number": phone_number,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }
        save_data(sessions, SESSIONS_FILE)
        return session_id

    def validate_session(self, session_id: str):
        sessions = load_data(SESSIONS_FILE)
        session = sessions.get(session_id)
        if not session:
            return None
        # Update last accessed
        session["last_accessed"] = datetime.utcnow().isoformat()
        sessions[session_id] = session
        save_data(sessions, SESSIONS_FILE)
        return session

session_manager = SessionManager()

# Authentication Dependency
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

# Dynamic Price Generation
async def generate_dynamic_prices():
    """Generate realistic dynamic prices"""
    assets_with_prices = []
    all_assets = []
    
    # Flatten all assets
    for category_assets in PRODUCTION_ASSETS.values():
        all_assets.extend(category_assets)
    
    for asset in all_assets:
        base_price = TODAYS_BASE_PRICES.get(asset['symbol'], 100)
        
        # Different volatility based on asset type
        volatility = {
            'crypto': 0.03,
            'stocks': 0.02,
            'forex': 0.008,
            'commodities': 0.015
        }.get(asset['type'], 0.01)
        
        change = random.uniform(-volatility, volatility)
        current_price = base_price * (1 + change)
        change_percentage = change * 100
        
        # Calculate investment metrics
        hourly_income_kes = random.uniform(asset['hourly_income_range'][0], asset['hourly_income_range'][1])
        total_income_kes = hourly_income_kes * asset['duration']
        roi_percentage = (total_income_kes / asset['min_investment_kes']) * 100
        
        assets_with_prices.append({
            "id": asset["id"],
            "name": asset["name"],
            "symbol": asset["symbol"],
            "type": asset["type"],
            "current_price": round(current_price, 4),
            "change_percentage": round(change_percentage, 2),
            "moving_average": round(current_price * random.uniform(0.98, 1.02), 4),
            "trend": "up" if change_percentage >= 0 else "down",
            "chart_url": f"https://www.tradingview.com/chart/?symbol={asset['symbol']}",
            "hourly_income": round(hourly_income_kes, 2),
            "min_investment": asset['min_investment_kes'],
            "duration": asset["duration"],
            "total_income": round(total_income_kes, 2),
            "roi_percentage": round(roi_percentage, 1)
        })
    
    return assets_with_prices

# Investment Management
async def update_investment_values(user_phone: str):
    """Update investment values based on current market prices"""
    investments = load_data(USER_INVESTMENTS_FILE, default={})
    current_assets = await generate_dynamic_prices()
    
    for inv_id, investment in investments.items():
        if investment["user_phone"] == user_phone and investment["status"] == "active":
            asset = next((a for a in current_assets if a["id"] == investment["asset_id"]), None)
            if asset:
                current_value = investment["units"] * asset["current_price"]
                profit_loss = current_value - investment["invested_amount"]
                profit_loss_percentage = (profit_loss / investment["invested_amount"]) * 100
                
                investment.update({
                    "current_value": current_value,
                    "current_price": asset["current_price"],
                    "profit_loss": profit_loss,
                    "profit_loss_percentage": profit_loss_percentage
                })
    
    save_data(investments, USER_INVESTMENTS_FILE)

def log_user_activity(user_phone: str, activity_type: str, amount: float, description: str):
    """Log user activity"""
    activities = load_data(USER_ACTIVITY_FILE, default={})
    activity_id = get_next_id(activities)
    
    activity = {
        "id": activity_id,
        "user_phone": user_phone,
        "activity_type": activity_type,
        "amount": amount,
        "description": description,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "completed"
    }
    
    activities[activity_id] = activity
    save_data(activities, USER_ACTIVITY_FILE)
    return activity

# Initialize application
@app.on_event("startup")
async def startup():
    """Initialize required files"""
    required_files = [USERS_FILE, USER_ACTIVITY_FILE, USER_WALLETS_FILE, USER_INVESTMENTS_FILE, SESSIONS_FILE]
    for file_path in required_files:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)
            print(f"Created {file_path}")

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to PesaPrime API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Authentication Routes
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    users = load_data(USERS_FILE)
    
    if user_data.email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check phone number
    for user in users.values():
        if user.get("phone_number") == user_data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    user_id = generate_id()
    user = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "phone_number": user_data.phone_number,
        "password": user_data.password,  # Simple storage for demo
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Initialize wallet
    wallets = load_data(USER_WALLETS_FILE)
    wallets[user_data.phone_number] = {
        "balance": 5000.0,
        "equity": 5000.0,
        "currency": "KES"
    }
    
    users[user_data.email] = user
    save_data(users, USERS_FILE)
    save_data(wallets, USER_WALLETS_FILE)
    
    # Create session
    session_id = session_manager.create_session(user_data.email, user_data.phone_number)
    
    # Log activities
    log_user_activity(user_data.phone_number, "registration", 0, "User registered successfully")
    log_user_activity(user_data.phone_number, "deposit", 5000, "Welcome bonus deposited")
    
    return AuthResponse(
        success=True,
        message="Registration successful",
        user=UserResponse(**{k: v for k, v in user.items() if k != 'password'}),
        session_id=session_id
    )

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(login_data: UserLogin):
    users = load_data(USERS_FILE)
    user = users.get(login_data.email)
    
    if not user or user["password"] != login_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    session_id = session_manager.create_session(user["email"], user["phone_number"])
    
    return AuthResponse(
        success=True,
        message="Login successful",
        user=UserResponse(**{k: v for k, v in user.items() if k != 'password'}),
        session_id=session_id
    )

# Wallet Routes
@app.get("/api/wallet/balance/{phone_number}")
async def get_wallet_balance(phone_number: str, session_id: str):
    user = await get_current_user(session_id)
    
    wallets = load_data(USER_WALLETS_FILE)
    user_wallet = wallets.get(phone_number, {"balance": 0, "equity": 0, "currency": "KES"})
    
    await update_investment_values(phone_number)
    
    return WalletData(**user_wallet)

@app.post("/api/wallet/deposit", response_model=TransactionResponse)
async def deposit_funds(data: DepositRequest, session_id: str):
    user = await get_current_user(session_id)
    
    if data.phone_number != user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(USER_WALLETS_FILE)
    user_wallet = wallets.get(user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    user_wallet["balance"] += data.amount
    user_wallet["equity"] += data.amount
    
    wallets[user["phone_number"]] = user_wallet
    save_data(wallets, USER_WALLETS_FILE)
    
    log_user_activity(user["phone_number"], "deposit", data.amount, f"Deposit of KSh {data.amount}")
    
    return TransactionResponse(
        success=True,
        message="Deposit successful",
        new_balance=user_wallet["balance"],
        new_equity=user_wallet["equity"],
        transaction_id=f"DEP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

@app.post("/api/wallet/withdraw", response_model=TransactionResponse)
async def withdraw_funds(data: WithdrawRequest, session_id: str):
    user = await get_current_user(session_id)
    
    if data.phone_number != user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(USER_WALLETS_FILE)
    user_wallet = wallets.get(user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    if user_wallet["balance"] < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    user_wallet["balance"] -= data.amount
    user_wallet["equity"] -= data.amount
    
    wallets[user["phone_number"]] = user_wallet
    save_data(wallets, USER_WALLETS_FILE)
    
    log_user_activity(user["phone_number"], "withdraw", data.amount, f"Withdrawal of KSh {data.amount}")
    
    return TransactionResponse(
        success=True,
        message="Withdrawal successful",
        new_balance=user_wallet["balance"],
        new_equity=user_wallet["equity"],
        transaction_id=f"WD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

# Investment Routes
@app.post("/api/investments/buy")
async def buy_investment(data: InvestmentRequest, session_id: str):
    user = await get_current_user(session_id)
    
    if data.phone_number != user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(USER_WALLETS_FILE)
    user_wallet = wallets.get(user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    if user_wallet["balance"] < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    assets = await generate_dynamic_prices()
    asset = next((a for a in assets if a["id"] == data.asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if data.amount < asset["min_investment"]:
        raise HTTPException(status_code=400, detail=f"Minimum investment is {asset['min_investment']} KES")
    
    units = data.amount / asset["current_price"]
    
    investments = load_data(USER_INVESTMENTS_FILE)
    investment_id = get_next_id(investments)
    
    investment = {
        "id": investment_id,
        "user_phone": user["phone_number"],
        "asset_id": data.asset_id,
        "asset_name": asset["name"],
        "invested_amount": data.amount,
        "current_value": data.amount,
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
    
    user_wallet["balance"] -= data.amount
    wallets[user["phone_number"]] = user_wallet
    save_data(wallets, USER_WALLETS_FILE)
    
    log_user_activity(user["phone_number"], "investment", data.amount, f"Investment in {asset['name']}")
    
    return {
        "success": True,
        "message": f"Investment in {asset['name']} successful",
        "investment": investment,
        "new_balance": user_wallet["balance"]
    }

# Market Data Routes
@app.get("/api/assets/market", response_model=List[Asset])
async def get_market_assets():
    return await generate_dynamic_prices()

@app.get("/api/investments/my/{phone_number}", response_model=List[UserInvestment])
async def get_my_investments(phone_number: str, session_id: str):
    await get_current_user(session_id)
    
    investments = load_data(USER_INVESTMENTS_FILE)
    user_investments = [
        inv for inv in investments.values() 
        if inv["user_phone"] == phone_number and inv["status"] == "active"
    ]
    
    await update_investment_values(phone_number)
    
    return user_investments

@app.get("/api/activities/my/{phone_number}", response_model=List[UserActivity])
async def get_my_activities(phone_number: str, session_id: str):
    await get_current_user(session_id)
    
    activities = load_data(USER_ACTIVITY_FILE)
    user_activities = [
        activity for activity in activities.values() 
        if activity["user_phone"] == phone_number
    ]
    user_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return user_activities[:20]

@app.get("/api/wallet/pnl", response_model=PnLData)
async def get_user_pnl(phone_number: str, session_id: str):
    await get_current_user(session_id)
    
    await update_investment_values(phone_number)
    investments = load_data(USER_INVESTMENTS_FILE)
    
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

# Additional Routes for Frontend
@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(session_id: str):
    user = await get_current_user(session_id)
    return UserResponse(**{k: v for k, v in user.items() if k != 'password'})

@app.get("/api/investments/assets")
async def get_investment_assets():
    return await generate_dynamic_prices()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
