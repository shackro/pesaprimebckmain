# backend/main.py
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict
from datetime import datetime
import json, os, uuid, random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend domain + mobile + local dev
origins = [
    "*",  # Temp: allow all until stable
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],      # <-- MUST ALLOW OPTIONS HERE
    allow_headers=["*"],      # <-- MUST ALLOW ALL HEADERS
)

# ------------------------------
# IMPORT ROUTES AFTER CORS
# ------------------------------
from app.routes import auth, wallet, pnl, investments

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(pnl.router, prefix="/api/pnl", tags=["P&L"])
app.include_router(investments.router, prefix="/api/investments", tags=["Investments"])


    
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
WALLETS_FILE = os.path.join(DATA_DIR, "wallets.json")
INVESTMENTS_FILE = os.path.join(DATA_DIR, "investments.json")
ACTIVITIES_FILE = os.path.join(DATA_DIR, "activities.json")

def load_data(filename, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default

def save_data(data, filename):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def get_next_id(data: Dict):
    if not data:
        return "1"
    numeric_keys = [int(k) for k in data.keys() if k.isdigit()]
    return str(max(numeric_keys) + 1) if numeric_keys else "1"

def log_activity(user_phone: str, activity_type: str, amount: float, description: str):
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

# Simple password hash (very lightweight placeholder)
def get_password_hash(pw: str):
    return pw[::-1]  # DO NOT USE IN PRODUCTION

def verify_password(plain: str, hashed: str):
    return get_password_hash(plain) == hashed

# Pydantic models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: str

class UserCreate(UserBase):
    password: str

    @validator('phone_number')
    def phone_must_have_plus(cls, v):
        if not v.startswith('+'):
            raise ValueError("phone must include country code and start with +")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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

# Basic assets (kept from your original)
ASSETS_DATA = [
    {"id":"bitcoin","name":"Bitcoin","symbol":"BTC","type":"crypto","current_price":92036.00,"change_percentage":2.34,"moving_average":91000.50,"trend":"up","chart_url":"https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT","hourly_income":160,"min_investment":700,"duration":24},
    {"id":"ethereum","name":"Ethereum","symbol":"ETH","type":"crypto","current_price":3016.97,"change_percentage":1.23,"moving_average":2980.20,"trend":"up","chart_url":"https://www.tradingview.com/chart/?symbol=BINANCE:ETHUSDT","hourly_income":140,"min_investment":600,"duration":24},
    {"id":"bnb","name":"Binance Coin","symbol":"BNB","type":"crypto","current_price":321.78,"change_percentage":0.89,"moving_average":318.50,"trend":"up","chart_url":"https://www.tradingview.com/chart/?symbol=BINANCE:BNBUSDT","hourly_income":120,"min_investment":550,"duration":24},
    {"id":"eur-usd","name":"EUR/USD","symbol":"EURUSD","type":"forex","current_price":1.0892,"change_percentage":0.15,"moving_average":1.0880,"trend":"up","chart_url":"https://www.tradingview.com/chart/?symbol=FX:EURUSD","hourly_income":150,"min_investment":500,"duration":24},
    {"id":"apple","name":"Apple Inc","symbol":"AAPL","type":"stock","current_price":189.45,"change_percentage":1.23,"moving_average":187.20,"trend":"up","chart_url":"https://www.tradingview.com/chart/?symbol=NASDAQ:AAPL","hourly_income":130,"min_investment":600,"duration":24},
]

app = FastAPI(title="PesaPrime (no-jwt)")

@app.on_event("startup")
def startup():
    for f in [USERS_FILE, WALLETS_FILE, INVESTMENTS_FILE, ACTIVITIES_FILE]:
        if not os.path.exists(f):
            save_data({}, f)

@app.get("/")
def root():
    return {"message":"PesaPrime API", "status":"running"}

# AUTH: register + login (no JWT). returns the user object only
@app.post("/api/auth/register")
def register(user_data: UserCreate):
    users = load_data(USERS_FILE, {})
    if user_data.email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    for u in users.values():
        if u.get("phone_number") == user_data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "phone_number": user_data.phone_number,
        "hashed_password": get_password_hash(user_data.password),
        "created_at": datetime.utcnow().isoformat()
    }
    users[user_data.email] = user
    save_data(users, USERS_FILE)

    wallets = load_data(WALLETS_FILE, {})
    wallets[user_data.phone_number] = {"balance": 0.0, "equity": 0.0, "currency": "KES"}
    save_data(wallets, WALLETS_FILE)

    log_activity(user_data.phone_number, "registration", 0, "Account created")
    log_activity(user_data.phone_number, "deposit", 200, "Welcome bonus")
    # Return user object (no token)
    response_user = {k:v for k,v in user.items() if k != "hashed_password"}
    return {"success": True, "user": response_user}

@app.post("/api/auth/login")
def login(login_data: UserLogin):
    users = load_data(USERS_FILE, {})
    user = users.get(login_data.email)
    if not user or not verify_password(login_data.password, user.get("hashed_password","")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "user": {k:v for k,v in user.items() if k != "hashed_password"} }

# WALLET: pass phone_number as query param
@app.get("/api/wallet/balance")
def get_wallet_balance(phone_number: str = Query(...)):
    wallets = load_data(WALLETS_FILE, {})
    wallet = wallets.get(phone_number)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    # equity update would go here (we keep simple)
    return wallet

@app.post("/api/wallet/deposit")
def deposit(req: DepositRequest):
    wallets = load_data(WALLETS_FILE, {})
    wallet = wallets.get(req.phone_number, {"balance":0.0,"equity":0.0,"currency":"KES"})
    wallet["balance"] += req.amount
    wallet["equity"] += req.amount
    wallets[req.phone_number] = wallet
    save_data(wallets, WALLETS_FILE)
    log_activity(req.phone_number, "deposit", req.amount, f"Deposit: KES {req.amount}")
    return {"success": True, "message":"Deposit successful", "new_balance": wallet["balance"], "transaction_id": f"DEP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"}

@app.post("/api/wallet/withdraw")
def withdraw(req: WithdrawRequest):
    wallets = load_data(WALLETS_FILE, {})
    wallet = wallets.get(req.phone_number)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if wallet["balance"] < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    wallet["balance"] -= req.amount
    wallet["equity"] -= req.amount
    wallets[req.phone_number] = wallet
    save_data(wallets, WALLETS_FILE)
    log_activity(req.phone_number, "withdraw", -req.amount, f"Withdrawal: KES {req.amount}")
    return {"success": True, "message":"Withdrawal successful", "new_balance": wallet["balance"], "transaction_id": f"WD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"}

# ASSETS
@app.get("/api/assets/market")
def get_assets():
    # Slight randomization for "live" feel
    live = []
    for a in ASSETS_DATA:
        change = random.uniform(-0.02, 0.02)
        current_price = round(a["current_price"] * (1+change), 4)
        live.append({**a, "current_price": current_price, "change_percentage": round(change*100,2)})
    return live

# INVESTMENTS (legacy style CRUD)
@app.get("/api/investments/")
def get_investments():
    investments = load_data(INVESTMENTS_FILE, {})
    return list(investments.values())

@app.post("/api/investments/")
def create_investment(payload: dict):
    # payload expects {user_id, title, amount, category}
    investments = load_data(INVESTMENTS_FILE, {})
    inv_id = get_next_id(investments)
    inv = {
        "id": int(inv_id),
        "user_id": payload.get("user_id"),
        "title": payload.get("title"),
        "amount": float(payload.get("amount",0)),
        "category": payload.get("category","general"),
        "created_at": datetime.utcnow().isoformat()
    }
    investments[inv_id] = inv
    save_data(investments, INVESTMENTS_FILE)
    return inv

@app.get("/api/investments/{inv_id}")
def get_investment(inv_id: int):
    investments = load_data(INVESTMENTS_FILE, {})
    inv = investments.get(str(inv_id))
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")
    return inv

@app.put("/api/investments/{inv_id}")
def update_investment(inv_id: int, payload: dict):
    investments = load_data(INVESTMENTS_FILE, {})
    key = str(inv_id)
    if key not in investments:
        raise HTTPException(status_code=404, detail="Investment not found")
    investments[key].update(payload)
    save_data(investments, INVESTMENTS_FILE)
    return investments[key]

@app.delete("/api/investments/{inv_id}")
def delete_investment(inv_id: int):
    investments = load_data(INVESTMENTS_FILE, {})
    key = str(inv_id)
    if key not in investments:
        raise HTTPException(status_code=404, detail="Investment not found")
    del investments[key]
    save_data(investments, INVESTMENTS_FILE)
    return {"success": True, "message": "Deleted"}

# USER-SPECIFIC investments by phone (for UI)
@app.get("/api/investments/my")
def get_my_investments(phone_number: str = Query(...)):
    investments = load_data(INVESTMENTS_FILE, {})
    user_invs = [inv for inv in investments.values() if inv.get("user_id") == phone_number or inv.get("user_phone")==phone_number]
    return user_invs

# ACTIVITIES
@app.get("/api/activities/my")
def get_my_activities(phone_number: str = Query(...)):
    activities = load_data(ACTIVITIES_FILE, {})
    user_acts = [a for a in activities.values() if a.get("user_phone") == phone_number]
    user_acts.sort(key=lambda x: x["timestamp"], reverse=True)
    return user_acts[:50]

# PnL (simplified)
@app.get("/api/pnl/current")
def get_pnl(phone_number: str = Query(...)):
    investments = load_data(INVESTMENTS_FILE, {})
    total_invested = 0.0
    total_current = 0.0
    for inv in investments.values():
        if inv.get("user_id") == phone_number or inv.get("user_phone")==phone_number:
            invested = float(inv.get("amount",0))
            total_invested += invested
            # Simulate current value with small random change
            total_current += invested * (1 + random.uniform(-0.1, 0.1))
    profit_loss = total_current - total_invested
    percentage = (profit_loss / total_invested * 100) if total_invested>0 else 0
    return {"profit_loss": round(profit_loss,2), "percentage": round(percentage,2), "trend": "up" if profit_loss>=0 else "down"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
