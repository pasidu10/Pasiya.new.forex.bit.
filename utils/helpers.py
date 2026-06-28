"""
Helper utility functions for the Trading Assistant.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import re
import math


def format_currency(value: float, currency: str = "USD", decimals: int = 2) -> str:
    """Format a value as currency."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.{decimals}f}K"
    return f"${value:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a value as percentage."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a large number with appropriate suffix."""
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.{decimals}f}T"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{decimals}f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.{decimals}f}K"
    return f"{value:.{decimals}f}"


def calculate_pips(price1: float, price2: float, symbol: str = "EUR/USD") -> float:
    """Calculate pips between two prices."""
    diff = abs(price1 - price2)

    # JPY pairs have 2 decimal places
    if "JPY" in symbol:
        return diff * 100

    # Crypto pairs (8 decimals typical)
    if "/" in symbol and not any(x in symbol for x in ["USD", "EUR", "GBP"]):
        return diff * 1000000

    # Standard forex pairs (4 decimals)
    return diff * 10000


def calculate_risk_reward(
    entry: float,
    stop_loss: float,
    take_profit: float,
    side: str = "long"
) -> Tuple[float, float]:
    """Calculate risk and reward for a trade."""
    if side.lower() == "long":
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
    else:
        risk = abs(stop_loss - entry)
        reward = abs(entry - take_profit)

    rr_ratio = reward / risk if risk > 0 else 0
    return risk, reward, rr_ratio


def get_time_ago(timestamp: datetime) -> str:
    """Get human-readable time ago string."""
    if not timestamp:
        return "Never"

    now = datetime.utcnow()
    diff = now - timestamp

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    return "Just now"


def parse_timeframe(timeframe: str) -> int:
    """Parse a timeframe string to minutes."""
    timeframe = timeframe.lower().strip()

    mapping = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440,
        "1w": 10080,
    }

    return mapping.get(timeframe, 60)


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    leverage: float = 1.0,
) -> dict:
    """Calculate appropriate position size based on risk."""
    risk_amount = account_balance * (risk_percent / 100)
    price_risk = abs(entry_price - stop_loss)

    if price_risk == 0:
        return {
            "position_size": 0,
            "risk_amount": risk_amount,
            "lots": 0,
            "contracts": 0,
        }

    # For forex (lot size = 100,000 units)
    if entry_price < 200:
        pip_value = price_risk * 10000 * 10  # Standard lot pip value
        lots = risk_amount / pip_value if pip_value > 0 else 0
        return {
            "position_size": lots * 100000,
            "risk_amount": risk_amount,
            "lots": round(lots, 2),
            "contracts": 0,
        }

    # For crypto
    position_size = (risk_amount / price_risk) * leverage
    return {
        "position_size": round(position_size, 6),
        "risk_amount": round(risk_amount, 2),
        "lots": 0,
        "contracts": round(position_size, 4),
    }


def get_market_session() -> list:
    """Get current active market sessions."""
    from config import MARKET_SESSIONS

    current_hour = datetime.utcnow().hour
    active_sessions = []

    for session, times in MARKET_SESSIONS.items():
        open_hour = times["open"]
        close_hour = times["close"]

        if open_hour > close_hour:
            # Session spans midnight
            if current_hour >= open_hour or current_hour < close_hour:
                active_sessions.append(session.capitalize())
        else:
            if open_hour <= current_hour < close_hour:
                active_sessions.append(session.capitalize())

    return active_sessions


def is_market_open(symbol: str) -> bool:
    """Check if market is open for a given symbol."""
    if "/" not in symbol:
        return True  # Crypto markets are always open

    base, quote = symbol.split("/")
    sessions = get_market_session()

    # Forex is open when London or NY is open
    if quote in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]:
        return bool(sessions)

    return True


def extract_symbol(text: str) -> Optional[str]:
    """Extract trading symbol from text."""
    patterns = [
        r"([A-Z]{3}/[A-Z]{3})",  # Forex pairs like EUR/USD
        r"([A-Z]{2,4}/[A-Z]{3,4})",  # Crypto pairs like BTC/USDT
        r"([A-Z]{3,4}USDT)",  # Crypto without slash like BTCUSDT
        r"([A-Z]{2,4}USD)",  # Crypto without slash like BTCUSD
    ]

    for pattern in patterns:
        match = re.search(pattern, text.upper())
        if match:
            symbol = match.group(1)
            if "/" not in symbol:
                # Try to add slash for known pairs
                for quote in ["USDT", "USD", "BUSD", "BTC"]:
                    if symbol.endswith(quote):
                        base = symbol[:-len(quote)]
                        symbol = f"{base}/{quote}"
                        break
            return symbol

    return None


def calculate_confidence_score(indicators: dict, patterns: list) -> float:
    """Calculate overall confidence score for a signal."""
    score = 0
    total_weight = 0

    # Indicator weights
    indicator_weights = {
        "trend": 0.25,
        "momentum": 0.20,
        "volume": 0.15,
        "volatility": 0.15,
        "pattern": 0.25,
    }

    # Trend signals
    if indicators.get("ema_trend") == "bullish":
        score += 0.8 * indicator_weights["trend"]
    elif indicators.get("ema_trend") == "bearish":
        score += 0.2 * indicator_weights["trend"]
    else:
        score += 0.5 * indicator_weights["trend"]
    total_weight += indicator_weights["trend"]

    # Momentum signals
    rsi = indicators.get("rsi", 50)
    if indicators.get("signal_type") == "buy":
        if rsi < 40:
            score += 0.8 * indicator_weights["momentum"]
        elif rsi < 60:
            score += 0.6 * indicator_weights["momentum"]
        else:
            score += 0.3 * indicator_weights["momentum"]
    else:
        if rsi > 60:
            score += 0.8 * indicator_weights["momentum"]
        elif rsi > 40:
            score += 0.6 * indicator_weights["momentum"]
        else:
            score += 0.3 * indicator_weights["momentum"]
    total_weight += indicator_weights["momentum"]

    # Pattern signals
    bullish_patterns = ["hammer", "morning_star", "three_white_soldiers", "engulfing_bullish"]
    bearish_patterns = ["shooting_star", "evening_star", "three_black_crows", "engulfing_bearish"]

    pattern_match = False
    for pattern in patterns:
        if indicators.get("signal_type") == "buy" and pattern in bullish_patterns:
            pattern_match = True
            break
        elif indicators.get("signal_type") == "sell" and pattern in bearish_patterns:
            pattern_match = True
            break

    if pattern_match:
        score += 0.85 * indicator_weights["pattern"]
    else:
        score += 0.5 * indicator_weights["pattern"]
    total_weight += indicator_weights["pattern"]

    # Normalize score
    if total_weight > 0:
        normalized_score = (score / total_weight) * 100
    else:
        normalized_score = 50

    return round(min(max(normalized_score, 0), 100), 1)
