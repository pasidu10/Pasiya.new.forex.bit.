"""
Candlestick pattern detection for market analysis.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from enum import Enum

from config import PATTERNS_TO_DETECT
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class CandlestickPatterns:
    """Class for detecting candlestick patterns."""

    def __init__(self, ohlcv_data: List[List]):
        """
        Initialize with OHLCV data.

        Args:
            ohlcv_data: List of [timestamp, open, high, low, close, volume]
        """
        if not ohlcv_data:
            self.df = None
            return

        self.df = pd.DataFrame(
            ohlcv_data,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        self.df["open"] = pd.to_numeric(self.df["open"])
        self.df["high"] = pd.to_numeric(self.df["high"])
        self.df["low"] = pd.to_numeric(self.df["low"])
        self.df["close"] = pd.to_numeric(self.df["close"])
        self.df["volume"] = pd.to_numeric(self.df["volume"])

    def _get_body(self, idx: int = -1) -> float:
        """Get candle body size."""
        return abs(self.df["close"].iloc[idx] - self.df["open"].iloc[idx])

    def _get_upper_shadow(self, idx: int = -1) -> float:
        """Get upper shadow size."""
        row = self.df.iloc[idx]
        if row["close"] >= row["open"]:
            return row["high"] - row["close"]
        return row["high"] - row["open"]

    def _get_lower_shadow(self, idx: int = -1) -> float:
        """Get lower shadow size."""
        row = self.df.iloc[idx]
        if row["close"] >= row["open"]:
            return row["open"] - row["low"]
        return row["close"] - row["low"]

    def _get_candle_range(self, idx: int = -1) -> float:
        """Get total candle range."""
        row = self.df.iloc[idx]
        return row["high"] - row["low"]

    def _is_bullish(self, idx: int = -1) -> bool:
        """Check if candle is bullish."""
        return self.df["close"].iloc[idx] > self.df["open"].iloc[idx]

    def _is_bearish(self, idx: int = -1) -> bool:
        """Check if candle is bearish."""
        return self.df["close"].iloc[idx] < self.df["open"].iloc[idx]

    def detect_doji(self, idx: int = -1) -> bool:
        """Detect Doji pattern."""
        if len(self.df) < abs(idx):
            return False

        body = self._get_body(idx)
        total_range = self._get_candle_range(idx)

        if total_range == 0:
            return False

        # Doji has a very small body relative to the range
        return body / total_range < 0.1

    def detect_hammer(self, idx: int = -1) -> bool:
        """Detect Hammer pattern."""
        if len(self.df) < abs(idx):
            return False

        body = self._get_body(idx)
        upper_shadow = self._get_upper_shadow(idx)
        lower_shadow = self._get_lower_shadow(idx)
        total_range = self._get_candle_range(idx)

        if total_range == 0:
            return False

        # Hammer has long lower shadow (2x body), small upper shadow
        if body == 0:
            return False

        return (
            lower_shadow >= body * 2
            and upper_shadow < body * 0.3
            and lower_shadow > upper_shadow
        )

    def detect_inverted_hammer(self, idx: int = -1) -> bool:
        """Detect Inverted Hammer pattern."""
        if len(self.df) < abs(idx):
            return False

        body = self._get_body(idx)
        upper_shadow = self._get_upper_shadow(idx)
        lower_shadow = self._get_lower_shadow(idx)
        total_range = self._get_candle_range(idx)

        if total_range == 0 or body == 0:
            return False

        return (
            upper_shadow >= body * 2
            and lower_shadow < body * 0.3
            and upper_shadow > lower_shadow
        )

    def detect_hanging_man(self, idx: int = -1) -> bool:
        """Detect Hanging Man pattern (bearish hammer after uptrend)."""
        if len(self.df) < abs(idx) + 10:
            return False

        # Check if there's been an uptrend
        close_prices = self.df["close"].iloc[idx-10:idx]
        if len(close_prices) < 10:
            return False

        trend = close_prices.pct_change().sum()
        if trend <= 0:
            return False

        return self.detect_hammer(idx)

    def detect_shooting_star(self, idx: int = -1) -> bool:
        """Detect Shooting Star pattern."""
        if len(self.df) < abs(idx) + 10:
            return False

        # Check uptrend
        close_prices = self.df["close"].iloc[idx-10:idx]
        if len(close_prices) < 10:
            return False

        trend = close_prices.pct_change().sum()
        if trend <= 0:
            return False

        return self.detect_inverted_hammer(idx)

    def detect_engulfing(self, idx: int = -1) -> Optional[str]:
        """Detect Engulfing pattern."""
        if len(self.df) < abs(idx) + 1:
            return None

        current = self.df.iloc[idx]
        previous = self.df.iloc[idx - 1]

        current_body = self._get_body(idx)
        prev_body = self._get_body(idx - 1)

        if current_body == 0 or prev_body == 0:
            return None

        # Bullish engulfing
        if (
            self._is_bearish(idx - 1)
            and self._is_bullish(idx)
            and current["open"] < previous["close"]
            and current["close"] > previous["open"]
            and current_body > prev_body
        ):
            return "engulfing_bullish"

        # Bearish engulfing
        if (
            self._is_bullish(idx - 1)
            and self._is_bearish(idx)
            and current["open"] > previous["close"]
            and current["close"] < previous["open"]
            and current_body > prev_body
        ):
            return "engulfing_bearish"

        return None

    def detect_morning_star(self, idx: int = -1) -> bool:
        """Detect Morning Star pattern (bullish reversal)."""
        if len(self.df) < abs(idx) + 2:
            return False

        first = self.df.iloc[idx - 2]
        second = self.df.iloc[idx - 1]
        third = self.df.iloc[idx]

        # First candle: bearish
        if not (first["close"] < first["open"]):
            return False

        # Second candle: small body (doji or spinning top)
        second_body = abs(second["close"] - second["open"])
        first_body = abs(first["close"] - first["open"])
        third_body = abs(third["close"] - third["open"])

        if second_body > first_body * 0.3:
            return False

        # Third candle: bullish, closes above first candle's midpoint
        if not (third["close"] > third["open"]):
            return False

        first_midpoint = (first["open"] + first["close"]) / 2
        return third["close"] > first_midpoint

    def detect_evening_star(self, idx: int = -1) -> bool:
        """Detect Evening Star pattern (bearish reversal)."""
        if len(self.df) < abs(idx) + 2:
            return False

        first = self.df.iloc[idx - 2]
        second = self.df.iloc[idx - 1]
        third = self.df.iloc[idx]

        # First candle: bullish
        if not (first["close"] > first["open"]):
            return False

        # Second candle: small body
        second_body = abs(second["close"] - second["open"])
        first_body = abs(first["close"] - first["open"])

        if second_body > first_body * 0.3:
            return False

        # Third candle: bearish, closes below first candle's midpoint
        if not (third["close"] < third["open"]):
            return False

        first_midpoint = (first["open"] + first["close"]) / 2
        return third["close"] < first_midpoint

    def detect_three_white_soldiers(self, idx: int = -1) -> bool:
        """Detect Three White Soldiers pattern."""
        if len(self.df) < abs(idx) + 2:
            return False

        for i in range(3):
            candle_idx = idx - (2 - i)
            candle = self.df.iloc[candle_idx]

            # Each candle should be bullish
            if candle["close"] <= candle["open"]:
                return False

            # Should have reasonable body
            body = candle["close"] - candle["open"]
            upper_shadow = candle["high"] - candle["close"]

            # Upper shadow should be small relative to body
            if body > 0 and upper_shadow > body * 0.3:
                return False

        # Each candle should close higher
        if (
            self.df["close"].iloc[idx] > self.df["close"].iloc[idx - 1]
            and self.df["close"].iloc[idx - 1] > self.df["close"].iloc[idx - 2]
        ):
            return True

        return False

    def detect_three_black_crows(self, idx: int = -1) -> bool:
        """Detect Three Black Crows pattern."""
        if len(self.df) < abs(idx) + 2:
            return False

        for i in range(3):
            candle_idx = idx - (2 - i)
            candle = self.df.iloc[candle_idx]

            # Each candle should be bearish
            if candle["close"] >= candle["open"]:
                return False

            # Should have reasonable body
            body = candle["open"] - candle["close"]
            lower_shadow = candle["close"] - candle["low"]

            # Lower shadow should be small relative to body
            if body > 0 and lower_shadow > body * 0.3:
                return False

        # Each candle should close lower
        if (
            self.df["close"].iloc[idx] < self.df["close"].iloc[idx - 1]
            and self.df["close"].iloc[idx - 1] < self.df["close"].iloc[idx - 2]
        ):
            return True

        return False

    def detect_tweezer_top(self, idx: int = -1, tolerance: float = 0.001) -> bool:
        """Detect Tweezer Top pattern."""
        if len(self.df) < abs(idx) + 1:
            return False

        current = self.df.iloc[idx]
        previous = self.df.iloc[idx - 1]

        # Both candles should have similar highs
        if abs(current["high"] - previous["high"]) / current["high"] < tolerance:
            # First should be bullish, second bearish
            if self._is_bullish(idx - 1) and self._is_bearish(idx):
                return True

        return False

    def detect_tweezer_bottom(self, idx: int = -1, tolerance: float = 0.001) -> bool:
        """Detect Tweezer Bottom pattern."""
        if len(self.df) < abs(idx) + 1:
            return False

        current = self.df.iloc[idx]
        previous = self.df.iloc[idx - 1]

        # Both candles should have similar lows
        if abs(current["low"] - previous["low"]) / current["low"] < tolerance:
            # First should be bearish, second bullish
            if self._is_bearish(idx - 1) and self._is_bullish(idx):
                return True

        return False

    def detect_piercing_line(self, idx: int = -1) -> bool:
        """Detect Piercing Line pattern (bullish reversal)."""
        if len(self.df) < abs(idx) + 1:
            return False

        first = self.df.iloc[idx - 1]
        second = self.df.iloc[idx]

        # First candle: bearish
        if first["close"] >= first["open"]:
            return False

        # Second candle: bullish
        if second["close"] <= second["open"]:
            return False

        # Second opens below first's low
        if second["open"] >= first["low"]:
            return False

        # Second closes above first's midpoint
        first_midpoint = (first["high"] + first["low"]) / 2
        if second["close"] <= first_midpoint:
            return False

        return True

    def detect_dark_cloud_cover(self, idx: int = -1) -> bool:
        """Detect Dark Cloud Cover pattern (bearish reversal)."""
        if len(self.df) < abs(idx) + 1:
            return False

        first = self.df.iloc[idx - 1]
        second = self.df.iloc[idx]

        # First candle: bullish
        if first["close"] <= first["open"]:
            return False

        # Second candle: bearish
        if second["close"] >= second["open"]:
            return False

        # Second opens above first's high
        if second["open"] <= first["high"]:
            return False

        # Second closes below first's midpoint
        first_midpoint = (first["high"] + first["low"]) / 2
        if second["close"] >= first_midpoint:
            return False

        return True

    def detect_all_patterns(self) -> List[Dict]:
        """Detect all candlestick patterns in the data."""
        if self.df is None or len(self.df) < 5:
            return []

        patterns = []

        # Check last 5 candles for patterns
        for i in range(-1, -min(6, len(self.df)), -1):
            pattern_dict = {"candle_index": i}

            detected = []

            if self.detect_doji(i):
                detected.append("doji")

            if self.detect_hammer(i):
                detected.append("hammer")

            if self.detect_inverted_hammer(i):
                detected.append("inverted_hammer")

            if self.detect_shooting_star(i):
                detected.append("shooting_star")

            engulfing = self.detect_engulfing(i)
            if engulfing:
                detected.append(engulfing)

            if self.detect_morning_star(i):
                detected.append("morning_star")

            if self.detect_evening_star(i):
                detected.append("evening_star")

            if self.detect_three_white_soldiers(i):
                detected.append("three_white_soldiers")

            if self.detect_three_black_crows(i):
                detected.append("three_black_crows")

            if self.detect_tweezer_top(i):
                detected.append("tweezer_top")

            if self.detect_tweezer_bottom(i):
                detected.append("tweezer_bottom")

            if self.detect_piercing_line(i):
                detected.append("piercing_line")

            if self.detect_dark_cloud_cover(i):
                detected.append("dark_cloud_cover")

            if detected:
                pattern_dict["patterns"] = detected
                pattern_dict["timestamp"] = int(self.df.iloc[i]["timestamp"])
                patterns.append(pattern_dict)

        return patterns


class SupportResistance:
    """Class for detecting support and resistance levels."""

    def __init__(self, ohlcv_data: List[List]):
        if not ohlcv_data:
            self.df = None
            return

        self.df = pd.DataFrame(
            ohlcv_data,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        self.df["high"] = pd.to_numeric(self.df["high"])
        self.df["low"] = pd.to_numeric(self.df["low"])
        self.df["close"] = pd.to_numeric(self.df["close"])

    def find_pivot_points(self, window: int = 5) -> Dict:
        """Calculate pivot points."""
        if self.df is None or len(self.df) < window * 2:
            return {}

        high = self.df["high"].rolling(window=window, center=True).max()
        low = self.df["low"].rolling(window=window, center=True).min()

        # Current levels for pivot calculation
        prev_high = self.df["high"].iloc[-window * 2:-window].max()
        prev_low = self.df["low"].iloc[-window * 2:-window].min()
        prev_close = self.df["close"].iloc[-window - 1]

        pivot = (prev_high + prev_low + prev_close) / 3

        return {
            "pivot": pivot,
            "r1": 2 * pivot - prev_low,
            "r2": pivot + (prev_high - prev_low),
            "r3": prev_high + 2 * (pivot - prev_low),
            "s1": 2 * pivot - prev_high,
            "s2": pivot - (prev_high - prev_low),
            "s3": prev_low - 2 * (prev_high - pivot),
        }

    def find_levels(self, window: int = 20, num_levels: int = 5) -> Dict:
        """Find significant support and resistance levels."""
        if self.df is None or len(self.df) < window:
            return {"resistance": [], "support": []}

        highs = self.df["high"].values
        lows = self.df["low"].values
        closes = self.df["close"].values

        resistance_levels = []
        support_levels = []

        # Find local maxima and minima
        for i in range(window, len(highs) - window):
            # Check for local maximum
            if highs[i] == max(highs[i-window:i+window+1]):
                resistance_levels.append(highs[i])

            # Check for local minimum
            if lows[i] == min(lows[i-window:i+window+1]):
                support_levels.append(lows[i])

        # Cluster nearby levels
        def cluster_levels(levels, tolerance=0.02):
            if not levels:
                return []

            levels = sorted(set(levels))
            clusters = []

            i = 0
            while i < len(levels):
                cluster = [levels[i]]
                j = i + 1

                while j < len(levels) and levels[j] <= levels[i] * (1 + tolerance):
                    cluster.append(levels[j])
                    j += 1

                avg = sum(cluster) / len(cluster)
                clusters.append(avg)
                i = j

            return sorted(clusters, reverse=True)[:num_levels]

        current_price = closes[-1]

        resistance = [r for r in cluster_levels(resistance_levels) if r > current_price]
        support = [s for s in cluster_levels(support_levels) if s < current_price]

        return {
            "resistance": resistance[:num_levels],
            "support": support[:num_levels],
            "current_price": current_price,
        }

    def is_near_level(self, price: float, level: float, tolerance: float = 0.01) -> bool:
        """Check if price is near a support/resistance level."""
        return abs(price - level) / level < tolerance

    def get_nearest_levels(self, price: float, num_levels: int = 3) -> Dict:
        """Get nearest support and resistance levels."""
        levels = self.find_levels(num_levels=num_levels)

        nearest_resistance = sorted(
            [r for r in levels.get("resistance", []) if r > price],
            key=lambda x: x - price
        )[:num_levels]

        nearest_support = sorted(
            [s for s in levels.get("support", []) if s < price],
            key=lambda x: price - x,
            reverse=True
        )[:num_levels]

        return {
            "resistance": nearest_resistance,
            "support": nearest_support,
        }
