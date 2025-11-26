from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from jose import JWSError,jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import json
import os
import random
import uuid
import aiohttp
import asyncio

# ===============================
# CONFIGURATION
# ===============================
SECRET_KEY = os.getenv("SECRET_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzaGFja3JvYXJlbEBnbWFpbC5jb20iLCJleHAiOjE3NjQwNjc3ODd9.j5xhoo0Pv1Lg9jAbrHAWPiUMnOG8b4MoTlwWaBA9FG8")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Security setup
security = HTTPBearer()

pwd_context = CryptContext(
    schemes=["sha256_crypt", "md5_crypt", "plaintext"],
    deprecated="auto"
)

# CORS origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8002",
    "http://localhost:5173",
    "https://pesaprimev2.vercel.app",
    "https://your-production-domain.com"
]

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
WALLETS_FILE = os.path.join(DATA_DIR, "wallets.json")
INVESTMENTS_FILE = os.path.join(DATA_DIR, "investments.json")
ACTIVITIES_FILE = os.path.join(DATA_DIR, "activities.json")

# ===============================
# PYDANTIC MODELS
# ===============================
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: str

class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

    @validator('phone_number')
    def phone_validation(cls, v):
        if not v.startswith('+'):
            raise ValueError('Phone number must include country code')
        return v

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
    access_token: str
    token_type: str
    user: UserResponse

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

# ===============================
# ASSETS DATA
# ===============================
ASSETS_DATA = [
    # Crypto
    {
        "id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "type": "crypto",
        "current_price": 92036.00, "change_percentage": 2.34, "moving_average": 91000.50,
        "trend": "up", "chart_url": "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT",
        "hourly_income": 160, "min_investment": 700, "duration": 24
    },
    {
        "id": "ethereum", "name": "Ethereum", "symbol": "ETH", "type": "crypto",
        "current_price": 3016.97, "change_percentage": 1.23, "moving_average": 2980.20,
        "trend": "up", "chart_url": "https://www.tradingview.com/chart/?symbol=BINANCE:ETHUSDT",
        "hourly_income": 140, "min_investment": 600, "duration": 24
    },
    {
        "id": "bnb", "name": "Binance Coin", "symbol": "BNB", "type": "crypto",
        "current_price": 321.78, "change_percentage": 0.89, "moving_average": 318.50,
        "trend": "up", "chart_url": "https://www.tradingview.com/chart/?symbol=BINANCE:BNBUSDT",
        "hourly_income": 120, "min_investment": 550, "duration": 24
    },
    # Forex
    {
        "id": "eur-usd", "name": "EUR/USD", "symbol": "EURUSD", "type": "forex",
        "current_price": 1.0892, "change_percentage": 0.15, "moving_average": 1.0880,
        "trend": "up", "chart_url": "https://www.tradingview.com/chart/?symbol=FX:EURUSD",
        "hourly_income": 150, "min_investment": 500, "duration": 24
    },
    {
        "id": "gbp-usd", "name": "GBP/USD", "symbol": "GBPUSD", "type": "forex",
        "current_price": 1.2678, "change_percentage": -0.23, "moving_average": 1.2690,
        "trend": "down", "chart_url": "https://www.tradingview.com/chart/?symbol=FX:GBPUSD",
        "hourly_income": 140, "min_investment": 500, "duration": 24
    },
    # Stocks
    {
        "id": "apple", "name": "Apple Inc", "symbol": "AAPL", "type": "stock",
        "current_price": 189.45, "change_percentage": 1.23, "moving_average": 187.20,
        "trend": "up", "chart_url": "https://www.tradingview.com/chart/?symbol=NASDAQ:AAPL",
        "hourly_income": 130, "min_investment": 600, "duration": 24
    },
    {
        "id": "microsoft", "name": "Microsoft Corp", "symbol": "MSFT", "type": "stock",
        "current_price": 378.85, "change_percentage": 0.89, "moving_average": 375.60,
        "trend": "up", "chart_url": "https://www.tradingview.com/chart/?symbol=NASDAQ:MSFT",
        "hourly_income": 125, "min_investment": 650, "duration": 24
    }
]

# ===============================
# UTILITY FUNCTIONS
# ===============================
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

def get_next_id(data):
    """Generate next numeric ID"""
    if not data:
        return "1"
    numeric_keys = [int(k) for k in data.keys() if k.isdigit()]
    return str(max(numeric_keys) + 1) if numeric_keys else "1"

def get_password_hash(password: str) -> str:
    """Hash password using sha256_crypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except:
        return plain_password == hashed_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    users = load_data(USERS_FILE)
    user = users.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def log_activity(user_phone: str, activity_type: str, amount: float, description: str):
    """Log user activity"""
    activities = load_data(ACTIVITIES_FILE, {})
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
    save_data(activities, ACTIVITIES_FILE)
    return activity

async def update_investment_prices():
    """Update investment prices with realistic fluctuations"""
    investments = load_data(INVESTMENTS_FILE, {})
    
    for inv_id, investment in investments.items():
        if investment["status"] == "active":
            # Find current asset price
            asset = next((a for a in ASSETS_DATA if a["id"] == investment["asset_id"]), None)
            if asset:
                # Add some random fluctuation
                fluctuation = random.uniform(-0.02, 0.02)
                current_price = asset["current_price"] * (1 + fluctuation)
                current_value = investment["units"] * current_price
                profit_loss = current_value - investment["invested_amount"]
                profit_loss_percentage = (profit_loss / investment["invested_amount"]) * 100
                
                investment.update({
                    "current_value": round(current_value, 2),
                    "current_price": round(current_price, 4),
                    "profit_loss": round(profit_loss, 2),
                    "profit_loss_percentage": round(profit_loss_percentage, 2)
                })
    
    save_data(investments, INVESTMENTS_FILE)

async def generate_live_prices():
    """Generate live prices with small fluctuations"""
    live_assets = []
    for asset in ASSETS_DATA:
        # Add small random fluctuations
        change = random.uniform(-0.015, 0.015)
        current_price = asset["current_price"] * (1 + change)
        
        live_assets.append({
            **asset,
            "current_price": round(current_price, 4),
            "change_percentage": round(change * 100, 2),
            "moving_average": round(current_price * random.uniform(0.99, 1.01), 4),
            "trend": "up" if change >= 0 else "down"
        })
    
    return live_assets

# ===============================
# FASTAPI APP
# ===============================
app = FastAPI(
    title="PesaPrime API",
    description="Investment Platform Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Initialize data files"""
    for file_path in [USERS_FILE, WALLETS_FILE, INVESTMENTS_FILE, ACTIVITIES_FILE]:
        if not os.path.exists(file_path):
            save_data({}, file_path)

# ===============================
# ROUTES
# ===============================
@app.get("/")
async def root():
    return {"message": "PesaPrime API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# AUTH ROUTES
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    users = load_data(USERS_FILE)
    
    # Check existing user
    if user_data.email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    for user in users.values():
        if user.get("phone_number") == user_data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "phone_number": user_data.phone_number,
        "hashed_password": get_password_hash(user_data.password),
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Initialize wallet
    wallets = load_data(WALLETS_FILE)
    wallets[user_data.phone_number] = {
        "balance": 0.0,  # Starting bonus
        "equity": 0.0,
        "currency": "KES"
    }
    
    users[user_data.email] = user
    save_data(users, USERS_FILE)
    save_data(wallets, WALLETS_FILE)
    
    # Log activities
    log_activity(user_data.phone_number, "registration", 0, "Account created")
    log_activity(user_data.phone_number, "deposit", 200, "Welcome bonus")
    
    # Create token
    access_token = create_access_token({"sub": user_data.email})
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**{k: v for k, v in user.items() if k != "hashed_password"})
    )

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(login_data: UserLogin):
    users = load_data(USERS_FILE)
    user = users.get(login_data.email)
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": user["email"]})
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**{k: v for k, v in user.items() if k != "hashed_password"})
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: v for k, v in current_user.items() if k != "hashed_password"})

# WALLET ROUTES
@app.get("/api/wallet/balance", response_model=WalletData)
async def get_balance(current_user: dict = Depends(get_current_user)):
    wallets = load_data(WALLETS_FILE)
    wallet = wallets.get(current_user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    # Update equity based on investments
    await update_investment_prices()
    
    return WalletData(**wallet)

@app.post("/api/wallet/deposit", response_model=TransactionResponse)
async def deposit(deposit_data: DepositRequest, current_user: dict = Depends(get_current_user)):
    if deposit_data.phone_number != current_user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(WALLETS_FILE)
    wallet = wallets.get(current_user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    wallet["balance"] += deposit_data.amount
    wallet["equity"] += deposit_data.amount
    
    wallets[current_user["phone_number"]] = wallet
    save_data(wallets, WALLETS_FILE)
    
    log_activity(current_user["phone_number"], "deposit", deposit_data.amount, f"Deposit: KES {deposit_data.amount}")
    
    return TransactionResponse(
        success=True,
        message="Deposit successful",
        new_balance=wallet["balance"],
        transaction_id=f"DEP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

@app.post("/api/wallet/withdraw", response_model=TransactionResponse)
async def withdraw(withdraw_data: WithdrawRequest, current_user: dict = Depends(get_current_user)):
    if withdraw_data.phone_number != current_user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(WALLETS_FILE)
    wallet = wallets.get(current_user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    if wallet["balance"] < withdraw_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    wallet["balance"] -= withdraw_data.amount
    wallet["equity"] -= withdraw_data.amount
    
    wallets[current_user["phone_number"]] = wallet
    save_data(wallets, WALLETS_FILE)
    
    log_activity(current_user["phone_number"], "withdraw", -withdraw_data.amount, f"Withdrawal: KES {withdraw_data.amount}")
    
    return TransactionResponse(
        success=True,
        message="Withdrawal successful",
        new_balance=wallet["balance"],
        transaction_id=f"WD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

# ASSETS ROUTES
@app.get("/api/assets/market", response_model=List[Asset])
async def get_assets():
    return await generate_live_prices()

# INVESTMENT ROUTES
@app.get("/api/investments/my", response_model=List[UserInvestment])
async def get_my_investments(current_user: dict = Depends(get_current_user)):
    await update_investment_prices()
    investments = load_data(INVESTMENTS_FILE, {})
    
    user_investments = [
        inv for inv in investments.values() 
        if inv["user_phone"] == current_user["phone_number"] and inv["status"] == "active"
    ]
    
    return user_investments

@app.post("/api/investments/buy")
async def buy_investment(investment_data: InvestmentRequest, current_user: dict = Depends(get_current_user)):
    if investment_data.phone_number != current_user["phone_number"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    wallets = load_data(WALLETS_FILE)
    wallet = wallets.get(current_user["phone_number"], {"balance": 0, "equity": 0, "currency": "KES"})
    
    if wallet["balance"] < investment_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Get asset
    assets = await generate_live_prices()
    asset = next((a for a in assets if a["id"] == investment_data.asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if investment_data.amount < asset["min_investment"]:
        raise HTTPException(status_code=400, detail=f"Minimum investment: KES {asset['min_investment']}")
    
    # Calculate units
    units = investment_data.amount / asset["current_price"]
    
    # Create investment
    investments = load_data(INVESTMENTS_FILE, {})
    investment_id = get_next_id(investments)
    
    investment = {
        "id": investment_id,
        "user_phone": current_user["phone_number"],
        "asset_id": asset["id"],
        "asset_name": asset["name"],
        "invested_amount": investment_data.amount,
        "current_value": investment_data.amount,
        "units": units,
        "entry_price": asset["current_price"],
        "current_price": asset["current_price"],
        "profit_loss": 0.0,
        "profit_loss_percentage": 0.0,
        "status": "active",
        "created_at": datetime.utcnow().isoformat()
    }
    
    investments[investment_id] = investment
    save_data(investments, INVESTMENTS_FILE)
    
    # Update wallet
    wallet["balance"] -= investment_data.amount
    wallets[current_user["phone_number"]] = wallet
    save_data(wallets, WALLETS_FILE)
    
    log_activity(current_user["phone_number"], "investment", -investment_data.amount, f"Investment in {asset['name']}")
    
    return {
        "success": True,
        "message": f"Investment in {asset['name']} successful",
        "investment": investment,
        "new_balance": wallet["balance"]
    }

# ACTIVITIES ROUTES
@app.get("/api/activities/my", response_model=List[UserActivity])
async def get_my_activities(current_user: dict = Depends(get_current_user)):
    activities = load_data(ACTIVITIES_FILE, {})
    user_activities = [
        activity for activity in activities.values() 
        if activity["user_phone"] == current_user["phone_number"]
    ]
    user_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return user_activities[:20]

# PnL ROUTES
@app.get("/api/pnl/current", response_model=PnLData)
async def get_pnl(current_user: dict = Depends(get_current_user)):
    await update_investment_prices()
    investments = load_data(INVESTMENTS_FILE, {})
    
    total_invested = 0
    total_current = 0
    
    for inv in investments.values():
        if inv["user_phone"] == current_user["phone_number"] and inv["status"] == "active":
            total_invested += inv["invested_amount"]
            total_current += inv["current_value"]
    
    profit_loss = total_current - total_invested
    percentage = (profit_loss / total_invested * 100) if total_invested > 0 else 0
    
    return PnLData(
        profit_loss=round(profit_loss, 2),
        percentage=round(percentage, 2),
        trend="up" if profit_loss >= 0 else "down"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
