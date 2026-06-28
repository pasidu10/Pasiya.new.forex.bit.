"""
Validator utility functions for input validation.
"""
import re
from typing import Optional, Tuple


def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a trading symbol.

    Returns:
        Tuple of (is_valid, normalized_symbol)
    """
    if not symbol:
        return False, None

    symbol = symbol.upper().strip()

    # Valid patterns
    patterns = [
        # Forex pairs: EUR/USD, GBP/JPY
        (r"^([A-Z]{3})/([A-Z]{3})$", "forex"),
        # Crypto pairs: BTC/USDT, ETH/BUSD
        (r"^([A-Z]{2,6})/(USDT|USDT-USD|BUSD|USD|BTC|ETH)$", "crypto"),
        # No slash versions
        (r"^([A-Z]{2,6})(USDT|BUSD|USD)$", "crypto"),
    ]

    for pattern, market_type in patterns:
        match = re.match(pattern, symbol)
        if match:
            if market_type == "crypto" and "/" not in symbol:
                # Normalize to add slash
                quote = match.group(2)
                base = symbol[:-len(quote)]
                symbol = f"{base}/{quote}"
            return True, symbol

    return False, None


def validate_timeframe(timeframe: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a timeframe.

    Returns:
        Tuple of (is_valid, normalized_timeframe)
    """
    if not timeframe:
        return False, None

    valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    timeframe = timeframe.lower().strip()

    if timeframe in valid_timeframes:
        return True, timeframe

    # Try to normalize
    replacements = {
        "m": "m",
        "min": "m",
        "minute": "m",
        "h": "h",
        "hour": "h",
        "d": "d",
        "day": "d",
        "w": "w",
        "week": "w",
    }

    match = re.match(r"^(\d+)(.+)$", timeframe)
    if match:
        num, unit = match.groups()
        normalized_unit = replacements.get(unit)
        if normalized_unit:
            normalized = f"{num}{normalized_unit}"
            if normalized in valid_timeframes:
                return True, normalized

    return False, None


def validate_telegram_id(telegram_id: int) -> bool:
    """Validate a Telegram user ID."""
    if not isinstance(telegram_id, int):
        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            return False

    # Telegram IDs are positive integers
    return telegram_id > 0


def validate_api_key(api_key: str) -> bool:
    """Validate an API key format (basic check)."""
    if not api_key:
        return False

    # Most API keys are at least 16 characters
    if len(api_key) < 16:
        return False

    # Should only contain alphanumeric characters and some special chars
    valid_pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(valid_pattern, api_key))


def validate_price(price: float) -> bool:
    """Validate a price value."""
    if not isinstance(price, (int, float)):
        return False
    return price > 0


def validate_percentage(value: float) -> bool:
    """Validate a percentage value."""
    if not isinstance(value, (int, float)):
        return False
    return 0 <= value <= 100


def validate_signal_type(signal_type: str) -> Tuple[bool, Optional[str]]:
    """Validate signal type."""
    if not signal_type:
        return False, None

    signal_type = signal_type.lower().strip()
    valid_types = ["buy", "sell", "long", "short"]

    if signal_type in valid_types:
        # Normalize to buy/sell
        if signal_type == "long":
            signal_type = "buy"
        elif signal_type == "short":
            signal_type = "sell"
        return True, signal_type

    return False, None


def validate_referral_code(code: str) -> bool:
    """Validate a referral code format."""
    if not code:
        return False

    # Referral codes should be 8 characters alphanumeric
    pattern = r"^[A-Z0-9]{8}$"
    return bool(re.match(pattern, code.upper()))


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input text."""
    if not text:
        return ""

    # Remove any control characters
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def parse_signal_input(text: str) -> dict:
    """
    Parse signal input from text.

    Format: SYMBOL TYPE ENTRY [SL] [TP1] [TP2] [TP3]
    Example: BTC/USDT BUY 45000 44000 46000 47000 48000
    """
    parts = text.upper().split()

    if len(parts) < 3:
        return None

    result = {
        "symbol": None,
        "signal_type": None,
        "entry": None,
        "stop_loss": None,
        "take_profits": [],
    }

    # Parse symbol
    valid, symbol = validate_symbol(parts[0])
    if not valid:
        return None
    result["symbol"] = symbol

    # Parse signal type
    valid, signal_type = validate_signal_type(parts[1])
    if not valid:
        return None
    result["signal_type"] = signal_type

    # Parse prices
    try:
        result["entry"] = float(parts[2])
    except (ValueError, IndexError):
        return None

    # Try to identify SL and TPs based on position relative to entry
    remaining = []
    for part in parts[3:]:
        try:
            remaining.append(float(part))
        except ValueError:
            pass

    if remaining:
        if result["signal_type"] == "buy":
            # For buy, SL should be below entry, TPs above
            below_entry = sorted([p for p in remaining if p < result["entry"]])
            above_entry = sorted([p for p in remaining if p > result["entry"]])

            if below_entry:
                result["stop_loss"] = below_entry[0]
            result["take_profits"] = above_entry
        else:
            # For sell, SL should be above entry, TPs below
            above_entry = sorted([p for p in remaining if p > result["entry"]], reverse=True)
            below_entry = sorted([p for p in remaining if p < result["entry"]], reverse=True)

            if above_entry:
                result["stop_loss"] = above_entry[0]
            result["take_profits"] = below_entry

    return result
