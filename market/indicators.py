"""
Technical indicator calculations for market analysis.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import pandas_ta as ta

from config import INDICATOR_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Class for calculating various technical indicators."""

    @staticmethod
    def calculate_ema(data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data["close"].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_sma(data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return data["close"].rolling(window=period).mean()

    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(
        data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        ema_fast = data["close"].ewm(span=fast_period, adjust=False).mean()
        ema_slow = data["close"].ewm(span=slow_period, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        middle_band = data["close"].rolling(window=period).mean()
        std = data["close"].rolling(window=period).std()

        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)

        return middle_band, upper_band, lower_band

    @staticmethod
    def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = data["high"]
        low = data["low"]
        close = data["close"].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def calculate_stochastic(
        data: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator."""
        low_min = data["low"].rolling(window=k_period).min()
        high_max = data["high"].rolling(window=k_period).max()

        stoch_k = ((data["close"] - low_min) / (high_max - low_min)) * 100
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return stoch_k, stoch_d

    @staticmethod
    def calculate_vwap(data: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price."""
        vwp = (data["high"] + data["low"] + data["close"]) / 3
        vwap = (vwp * data["volume"]).cumsum() / data["volume"].cumsum()
        return vwap

    @staticmethod
    def calculate_obv(data: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume."""
        obv = [0]
        for i in range(1, len(data)):
            if data["close"].iloc[i] > data["close"].iloc[i-1]:
                obv.append(obv[-1] + data["volume"].iloc[i])
            elif data["close"].iloc[i] < data["close"].iloc[i-1]:
                obv.append(obv[-1] - data["volume"].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=data.index)

    @staticmethod
    def detect_trend(data: pd.DataFrame, short_period: int = 20, long_period: int = 50) -> str:
        """Detect current market trend."""
        if len(data) < long_period:
            return "neutral"

        short_ma = TechnicalIndicators.calculate_sma(data, short_period)
        long_ma = TechnicalIndicators.calculate_sma(data, long_period)

        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]

        if current_short > current_long * 1.02:
            return "bullish"
        elif current_short < current_long * 0.98:
            return "bearish"
        return "neutral"

    @staticmethod
    def detect_ema_crossover(
        data: pd.DataFrame,
        fast_period: int = 9,
        slow_period: int = 21
    ) -> Optional[str]:
        """Detect EMA crossover signals."""
        if len(data) < slow_period + 2:
            return None

        fast_ema = TechnicalIndicators.calculate_ema(data, fast_period)
        slow_ema = TechnicalIndicators.calculate_ema(data, slow_period)

        # Current values
        current_fast = fast_ema.iloc[-1]
        current_slow = slow_ema.iloc[-1]

        # Previous values
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]

        # Bullish crossover
        if prev_fast <= prev_slow and current_fast > current_slow:
            return "bullish_crossover"

        # Bearish crossover
        if prev_fast >= prev_slow and current_fast < current_slow:
            return "bearish_crossover"

        return None

    @staticmethod
    def calculate_momentum(data: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate Price Momentum."""
        return data["close"].pct_change(period) * 100

    @staticmethod
    def calculate_williams_r(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R."""
        high_max = data["high"].rolling(window=period).max()
        low_min = data["low"].rolling(window=period).min()

        williams_r = ((high_max - data["close"]) / (high_max - low_min)) * -100
        return williams_r

    @staticmethod
    def calculate_adx(data: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Average Directional Index."""
        high = data["high"]
        low = data["low"]
        close = data["close"]

        # Plus Directional Movement
        plus_dm = high.diff()
        plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > (low.diff().abs() * -1)), 0)

        # Minus Directional Movement
        minux_dm = low.diff().abs()
        minux_dm = minux_dm.where((minux_dm > 0) & (minux_dm > plus_dm), 0)

        # True Range
        tr = TechnicalIndicators.calculate_atr(data, 1)

        # Smoothed values
        atr = TechnicalIndicators.calculate_atr(data, period)
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minux_dm.rolling(window=period).mean() / atr)

        # ADX
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)) * 100
        adx = dx.rolling(window=period).mean()

        return adx, plus_di, minus_di

    @classmethod
    def get_all_indicators(cls, ohlcv: List[List]) -> Dict:
        """Calculate all configured indicators from OHLCV data."""
        if not ohlcv or len(ohlcv) < 50:
            logger.warning("Insufficient data for indicator calculation")
            return {}

        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["close"] = pd.to_numeric(df["close"])
        df["open"] = pd.to_numeric(df["open"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["volume"] = pd.to_numeric(df["volume"])

        indicators = {}

        # EMA
        for period in INDICATOR_CONFIG["ema"]["periods"]:
            indicators[f"ema_{period}"] = cls.calculate_ema(df, period).iloc[-1]

        # SMA
        for period in INDICATOR_CONFIG["sma"]["periods"]:
            indicators[f"sma_{period}"] = cls.calculate_sma(df, period).iloc[-1]

        # RSI
        indicators["rsi"] = cls.calculate_rsi(df, INDICATOR_CONFIG["rsi"]["period"]).iloc[-1]

        # MACD
        macd_line, signal_line, histogram = cls.calculate_macd(
            df,
            INDICATOR_CONFIG["macd"]["fast_period"],
            INDICATOR_CONFIG["macd"]["slow_period"],
            INDICATOR_CONFIG["macd"]["signal_period"]
        )
        indicators["macd_line"] = macd_line.iloc[-1]
        indicators["macd_signal"] = signal_line.iloc[-1]
        indicators["macd_histogram"] = histogram.iloc[-1]

        # Bollinger Bands
        middle, upper, lower = cls.calculate_bollinger_bands(
            df,
            INDICATOR_CONFIG["bollinger_bands"]["period"],
            INDICATOR_CONFIG["bollinger_bands"]["std_dev"]
        )
        indicators["bb_middle"] = middle.iloc[-1]
        indicators["bb_upper"] = upper.iloc[-1]
        indicators["bb_lower"] = lower.iloc[-1]

        # ATR
        indicators["atr"] = cls.calculate_atr(df, INDICATOR_CONFIG["atr"]["period"]).iloc[-1]

        # Trend
        indicators["trend"] = cls.detect_trend(df)

        # EMA Crossover
        indicators["ema_crossover"] = cls.detect_ema_crossover(df)

        # Momentum
        indicators["momentum"] = cls.calculate_momentum(df).iloc[-1]

        # ATR for position sizing
        indicators["atr_percent"] = (indicators["atr"] / df["close"].iloc[-1]) * 100

        return indicators
