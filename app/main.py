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
# Asset price generation functions
async def fetch_real_crypto_price(coin_id: str, symbol: str):
    """
    Fetch real cryptocurrency prices from CoinGecko API
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Use CoinGecko API to get real prices
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data:
                        price_data = data[coin_id]
                        current_price = price_data.get('usd', TODAYS_BASE_PRICES.get(symbol, 100))
                        change_24h = price_data.get('usd_24h_change', 0) or 0
                        
                        # Convert to KES (approximate conversion rate)
                        usd_to_kes = 130  # Approximate USD to KES rate
                        current_price_kes = current_price * usd_to_kes
                        
                        return {
                            'current_price': round(current_price_kes, 2),
                            'change_percentage': round(change_24h, 2)
                        }
    except Exception as e:
        print(f"Error fetching crypto price for {symbol}: {e}")
    
    # Fallback to simulated data
    base_price = TODAYS_BASE_PRICES.get(symbol, 100)
    change = random.uniform(-0.03, 0.03)  # More realistic crypto volatility
    current_price = base_price * (1 + change)
    return {
        'current_price': round(current_price, 2),
        'change_percentage': round(change * 100, 2)
    }

async def fetch_real_forex_price(forex_pair: str, symbol: str):
    """
    Fetch real forex prices (fallback to simulated for demo)
    """
    try:
        # Using Alpha Vantage or other free forex API would go here
        # For now, we'll use simulated data with realistic forex movements
        base_price = TODAYS_BASE_PRICES.get(symbol, 100)
        
        # Forex typically has smaller movements than crypto
        change = random.uniform(-0.008, 0.008)
        current_price = base_price * (1 + change)
        
        return {
            'current_price': round(current_price, 4),
            'change_percentage': round(change * 100, 2)
        }
    except Exception as e:
        print(f"Error fetching forex price for {symbol}: {e}")
        # Fallback
        base_price = TODAYS_BASE_PRICES.get(symbol, 100)
        change = random.uniform(-0.01, 0.01)
        current_price = base_price * (1 + change)
        return {
            'current_price': round(current_price, 4),
            'change_percentage': round(change * 100, 2)
        }

async def fetch_real_stock_price(symbol: str):
    """
    Fetch real stock prices (fallback to simulated for demo)
    """
    try:
        # Using Alpha Vantage or Yahoo Finance API would go here
        base_price = TODAYS_BASE_PRICES.get(symbol, 100)
        
        # Stock market typical movements
        change = random.uniform(-0.02, 0.02)
        current_price = base_price * (1 + change)
        
        return {
            'current_price': round(current_price, 2),
            'change_percentage': round(change * 100, 2)
        }
    except Exception as e:
        print(f"Error fetching stock price for {symbol}: {e}")
        # Fallback
        base_price = TODAYS_BASE_PRICES.get(symbol, 100)
        change = random.uniform(-0.015, 0.015)
        current_price = base_price * (1 + change)
        return {
            'current_price': round(current_price, 2),
            'change_percentage': round(change * 100, 2)
        }

async def fetch_real_commodity_price(commodity: str, symbol: str):
    """
    Fetch real commodity prices (fallback to simulated for demo)
    """
    try:
        base_price = TODAYS_BASE_PRICES.get(symbol, 100)
        
        # Commodity typical movements
        change = random.uniform(-0.015, 0.015)
        current_price = base_price * (1 + change)
        
        return {
            'current_price': round(current_price, 2),
            'change_percentage': round(change * 100, 2)
        }
    except Exception as e:
        print(f"Error fetching commodity price for {symbol}: {e}")
        # Fallback
        base_price = TODAYS_BASE_PRICES.get(symbol, 100)
        change = random.uniform(-0.01, 0.01)
        current_price = base_price * (1 + change)
        return {
            'current_price': round(current_price, 2),
            'change_percentage': round(change * 100, 2)
        }

async def generate_real_time_prices():
    """
    Generate realistic dynamic prices with real-time data where available
    """
    assets_with_prices = []
    all_assets = []
    
    # Flatten all assets from categories
    for category_assets in PRODUCTION_ASSETS.values():
        all_assets.extend(category_assets)
    
    # Fetch prices concurrently
    tasks = []
    for asset in all_assets:
        if asset['type'] == 'crypto':
            task = fetch_real_crypto_price(asset['coingecko_id'], asset['symbol'])
        elif asset['type'] == 'forex':
            task = fetch_real_forex_price(asset.get('forex_pair', ''), asset['symbol'])
        elif asset['type'] == 'stocks':
            task = fetch_real_stock_price(asset['symbol'])
        elif asset['type'] == 'commodities':
            task = fetch_real_commodity_price(asset['name'], asset['symbol'])
        else:
            # Default fallback
            base_price = TODAYS_BASE_PRICES.get(asset['symbol'], 100)
            change = random.uniform(-0.01, 0.01)
            current_price = base_price * (1 + change)
            task = asyncio.sleep(0)  # Dummy task
            task.result = lambda: {
                'current_price': round(current_price, 2),
                'change_percentage': round(change * 100, 2)
            }
        
        tasks.append((asset, task))
    
    # Execute all price fetches concurrently
    for asset, task in tasks:
        try:
            if asyncio.iscoroutine(task):
                price_data = await task
            else:
                price_data = task.result()
            
            current_price = price_data['current_price']
            change_percentage = price_data['change_percentage']
            
            # Calculate moving average (simplified)
            moving_avg = current_price * random.uniform(0.98, 1.02)
            
            # Determine trend
            trend = "up" if change_percentage >= 0 else "down"
            
            # Calculate investment metrics in KES
            hourly_income_kes = random.uniform(asset['hourly_income_range'][0], asset['hourly_income_range'][1])
            total_income_kes = hourly_income_kes * asset['duration']
            roi_percentage = (total_income_kes / asset['min_investment_kes']) * 100
            
            assets_with_prices.append({
                "id": asset["id"],
                "name": asset["name"],
                "symbol": asset["symbol"],
                "type": asset["type"],
                "current_price": current_price,
                "change_percentage": round(change_percentage, 2),
                "moving_average": round(moving_avg, 4),
                "trend": trend,
                "chart_url": f"https://www.tradingview.com/chart/?symbol={asset['symbol']}",
                "hourly_income": round(hourly_income_kes, 2),
                "min_investment": asset['min_investment_kes'],
                "duration": asset["duration"],
                "total_income": round(total_income_kes, 2),
                "roi_percentage": round(roi_percentage, 1)
            })
            
        except Exception as e:
            print(f"Error processing asset {asset['name']}: {e}")
            # Fallback for this specific asset
            base_price = TODAYS_BASE_PRICES.get(asset['symbol'], 100)
            change = random.uniform(-0.01, 0.01)
            current_price = base_price * (1 + change)
            
            hourly_income_kes = random.uniform(asset['hourly_income_range'][0], asset['hourly_income_range'][1])
            total_income_kes = hourly_income_kes * asset['duration']
            roi_percentage = (total_income_kes / asset['min_investment_kes']) * 100
            
            assets_with_prices.append({
                "id": asset["id"],
                "name": asset["name"],
                "symbol": asset["symbol"],
                "type": asset["type"],
                "current_price": round(current_price, 4),
                "change_percentage": round(change * 100, 2),
                "moving_average": round(current_price * random.uniform(0.98, 1.02), 4),
                "trend": "up" if change >= 0 else "down",
                "chart_url": f"https://www.tradingview.com/chart/?symbol={asset['symbol']}",
                "hourly_income": round(hourly_income_kes, 2),
                "min_investment": asset['min_investment_kes'],
                "duration": asset["duration"],
                "total_income": round(total_income_kes, 2),
                "roi_percentage": round(roi_percentage, 1)
            })
    
    return assets_with_prices

async def generate_dynamic_prices():
    """Generate realistic dynamic prices with real-time data"""
    try:
        return await generate_real_time_prices()
    except Exception as e:
        print(f"Error generating real-time prices: {e}")
        # Fallback to simulated data with today's prices
        return await generate_fallback_prices()

async def generate_fallback_prices():
    """Fallback price generation using today's market prices"""
    assets_with_prices = []
    
    all_assets = []
    for category_assets in PRODUCTION_ASSETS.values():
        all_assets.extend(category_assets)
    
    for asset in all_assets:
        base_price = TODAYS_BASE_PRICES.get(asset['symbol'], 100)
        
        # Different volatility based on asset type
        if asset['type'] == 'crypto':
            change = random.uniform(-0.03, 0.03)  # High volatility for crypto
        elif asset['type'] == 'stocks':
            change = random.uniform(-0.02, 0.02)  # Medium volatility for stocks
        elif asset['type'] == 'forex':
            change = random.uniform(-0.008, 0.008)  # Low volatility for forex
        else:
            change = random.uniform(-0.015, 0.015)  # Medium volatility for others
        
        current_price = base_price * (1 + change)
        change_percentage = change * 100
        
        # Calculate moving average
        moving_avg = current_price * random.uniform(0.98, 1.02)
        
        # Hourly income in KSH (realistic range based on asset type)
        if asset['type'] == 'crypto':
            hourly_income_range = [150, 350]  # Higher returns for crypto
        elif asset['type'] == 'stocks':
            hourly_income_range = [120, 280]  # Medium returns for stocks
        else:
            hourly_income_range = [100, 250]  # Lower returns for others
        
        hourly_income_kes = random.uniform(hourly_income_range[0], hourly_income_range[1])
        total_income_kes = hourly_income_kes * asset['duration']
        roi_percentage = (total_income_kes / asset['min_investment_kes']) * 100
        
        assets_with_prices.append({
            "id": asset["id"],
            "name": asset["name"],
            "symbol": asset["symbol"],
            "type": asset["type"],
            "current_price": round(current_price, 4),
            "change_percentage": round(change_percentage, 2),
            "moving_average": round(moving_avg, 4),
            "trend": "up" if change_percentage >= 0 else "down",
            "chart_url": f"https://www.tradingview.com/chart/?symbol={asset['symbol']}",
            "hourly_income": round(hourly_income_kes, 2),
            "min_investment": asset['min_investment_kes'],
            "duration": asset["duration"],
            "total_income": round(total_income_kes, 2),
            "roi_percentage": round(roi_percentage, 1)
        })
    
    return assets_with_prices

# Update investment values function
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

# User activity logging function
def log_user_activity(user_phone: str, activity_type: str, amount: float, description: str, status: str = "completed"):
    """Log user activity for tracking"""
    activities = load_data(USER_ACTIVITY_FILE, default={})
    activity_id = get_next_id(activities)
    
    activity = {
        "id": activity_id,
        "user_phone": user_phone,
        "activity_type": activity_type,
        "amount": amount,
        "description": description,
        "timestamp": datetime.utcnow().isoformat(),
        "status": status
    }
    
    activities[activity_id] = activity
    save_data(activities, USER_ACTIVITY_FILE)
    return activity

# ID generation functions
def get_next_id(data):
    """Generate next ID for data that uses numeric IDs"""
    if not data:
        return "1"
    
    numeric_keys = []
    for key in data.keys():
        try:
            numeric_keys.append(int(key))
        except ValueError:
            continue
    
    if not numeric_keys:
        return "1"
    
    max_id = max(numeric_keys)
    return str(max_id + 1)

def generate_user_id():
    """Generate a unique user ID"""
    return str(uuid.uuid4())
    

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
