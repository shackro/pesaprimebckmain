# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PesaPrime Capital"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/pesaprime"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # External APIs
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    FX_RATES_API_KEY: Optional[str] = None
    
    # Trading Configuration
    DEFAULT_CURRENCY: str = "KES"
    MIN_DEPOSIT_AMOUNT: float = 100.0
    MIN_WITHDRAWAL_AMOUNT: float = 100.0
    TRADING_FEE_PERCENT: float = 0.001  # 0.1%
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()