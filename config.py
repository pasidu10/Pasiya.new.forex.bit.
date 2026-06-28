"""
Configuration settings for the Telegram AI Trading Assistant.
Uses pydantic-settings for environment variable management.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Configuration
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = []
    SUPER_ADMIN_ID: int = 0

    # Exchange API Keys
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    BYBIT_API_KEY: Optional[str] = None
    BYBIT_API_SECRET: Optional[str] = None

    # Channel & Group Configuration
    CHANNEL_ID: Optional[str] = None
    GROUP_ID: Optional[int] = None
    PREMIUM_CHANNEL_ID: Optional[str] = None

    # Premium Configuration
    VIP_PRICE_MONTHLY: float = 29.99
    VIP_PRICE_YEARLY: float = 299.99

    # Database Configuration
    DATABASE_PATH: str = "data/trading_bot.db"

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    @field_validator("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", mode="before")
    @classmethod
    def validate_supabase(cls, v):
        if v and isinstance(v, str) and v.startswith("your_supabase"):
            return None
        return v

    @property
    def use_supabase(self) -> bool:
        """Check if Supabase is configured."""
        return all([self.SUPABASE_URL, self.SUPABASE_ANON_KEY, self.SUPABASE_SERVICE_ROLE_KEY])

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"

    # Market Configuration
    DEFAULT_TIMEFRAME: str = "1h"
    SUPPORTED_TIMEFRAMES: List[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]

    # Signal Configuration
    AUTO_SIGNAL_INTERVAL: int = 300
    SIGNAL_EXPIRY_HOURS: int = 24
    MAX_DAILY_SIGNALS: int = 10

    # Alert Configuration
    PRICE_CHECK_INTERVAL: int = 60
    ALERT_THRESHOLD_PERCENT: float = 2.0

    # News API
    NEWS_API_KEY: Optional[str] = None

    # Feature Flags
    ENABLE_AUTO_SIGNALS: bool = True
    ENABLE_NEWS_ALERTS: bool = True
    ENABLE_PRICE_ALERTS: bool = True

    # Localization
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: List[str] = ["en", "si"]

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        return v

    @field_validator("SUPPORTED_TIMEFRAMES", mode="before")
    @classmethod
    def parse_timeframes(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Create directories if they don't exist
def ensure_directories():
    """Create necessary directories for the application."""
    directories = ["data", "logs", "charts", "assets/locales"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Initialize settings
settings = Settings()


# Exchange Configuration
BINANCE_CONFIG = {
    "name": "binance",
    "type": "crypto",
    "currencies": ["USDT", "BUSD", "BTC"],
}

BYBIT_CONFIG = {
    "name": "bybit",
    "type": "crypto",
    "currencies": ["USDT", "BTC"],
}

FOREX_BROKERS = {
    "oanda": {
        "name": "OANDA",
        "pairs": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"],
    },
}

# Supported Trading Pairs
CRYPTO_PAIRS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    "SOL/USDT", "DOGE/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT",
    "LINK/USDT", "LTC/USDT", "UNI/USDT", "ATOM/USDT", "XLM/USDT",
]

FOREX_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD",
    "USD/CAD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY",
]

# Technical Indicator Settings
INDICATOR_CONFIG = {
    "ema": {
        "periods": [9, 20, 50, 200],
    },
    "sma": {
        "periods": [20, 50, 100, 200],
    },
    "rsi": {
        "period": 14,
        "overbought": 70,
        "oversold": 30,
    },
    "macd": {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
    },
    "bollinger_bands": {
        "period": 20,
        "std_dev": 2,
    },
    "atr": {
        "period": 14,
    },
}

# Candlestick Pattern Settings
PATTERNS_TO_DETECT = [
    "doji", "hammer", "inverted_hammer", "engulfing",
    "morning_star", "evening_star", "three_white_soldiers",
    "three_black_crows", "shooting_star", "hanging_man",
]

# Market Sessions (UTC times)
MARKET_SESSIONS = {
    "sydney": {"open": 21, "close": 6},
    "tokyo": {"open": 23, "close": 8},
    "london": {"open": 7, "close": 16},
    "new_york": {"open": 12, "close": 21},
}

# Messages
MESSAGES = {
    "en": {
        "welcome": "Welcome to AI Trading Assistant!",
        "not_authorized": "You are not authorized to use this bot.",
        "premium_required": "This feature requires Premium subscription.",
        "channel_verification_required": "Please join our channel to use this feature.",
        "signal_generated": "🚀 New Signal Generated!",
        "error_occurred": "An error occurred. Please try again later.",
    },
    "si": {
        "welcome": "AI Trading Assistant වෙත සාදරයෙන් පිළිගනිමු!",
        "not_authorized": "ඔබට මෙම bot භාවිතා කිරීමට අවසර නොමැත.",
        "premium_required": "මෙම විශේෂාංගය සඳහා Premium subscription අවශ්‍යයි.",
        "channel_verification_required": "කරුණාකර මෙම විශේෂාංගය භාවිතා කිරීමට අපගේ channel සමඟ එක්වන්න.",
        "signal_generated": "🚀 නව Signal එකක්!",
        "error_occurred": "දෝෂයක් සිදුවිය. කරුණාකර පසුව නැවත උත්සහ කරන්න.",
    },
}
