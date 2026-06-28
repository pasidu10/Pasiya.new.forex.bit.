"""
Market scanner for automated market analysis.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from config import CRYPTO_PAIRS, FOREX_PAIRS, settings
from market.exchange import ExchangeManager
from market.indicators import TechnicalIndicators
from market.patterns import CandlestickPatterns, SupportResistance
from utils.logger import get_logger
from utils.helpers import calculate_confidence_score

logger = get_logger(__name__)


class MarketScanner:
    """Scanner for identifying trading opportunities."""

    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange = exchange_manager

    async def scan_symbol(self, symbol: str, timeframe: str = "1h") -> Optional[Dict]:
        """Scan a single symbol for trading signals."""
        try:
            # Determine exchange type
            exchange = "forex" if "/" in symbol and "USDT" not in symbol else "binance"

            # Fetch OHLCV data
            ohlcv = await self.exchange.get_ohlcv(symbol, timeframe, exchange, limit=200)

            if not ohlcv or len(ohlcv) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None

            # Calculate indicators
            indicators = TechnicalIndicators.get_all_indicators(ohlcv)

            # Detect patterns
            pattern_detector = CandlestickPatterns(ohlcv)
            patterns = pattern_detector.detect_all_patterns()

            # Find support/resistance
            sr_detector = SupportResistance(ohlcv)
            levels = sr_detector.get_nearest_levels(ohlcv[-1][4])

            # Get ticker
            ticker = await self.exchange.get_ticker(symbol, exchange)

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.utcnow().isoformat(),
                "price": ohlcv[-1][4],
                "ticker": ticker,
                "indicators": indicators,
                "patterns": patterns,
                "support_resistance": levels,
                "volume_analysis": self._analyze_volume(ohlcv),
                "momentum": self._analyze_momentum(ohlcv, indicators),
            }

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None

    def _analyze_volume(self, ohlcv: List[List]) -> Dict:
        """Analyze volume patterns."""
        if len(ohlcv) < 20:
            return {}

        volumes = [float(c[5]) for c in ohlcv[-20:]]
        closes = [float(c[4]) for c in ohlcv[-20:]]

        avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
        current_volume = volumes[-1]

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        # Calculate if volume is increasing
        recent_volumes = volumes[-5:]
        prev_volumes = volumes[-10:-5]
        volume_increasing = sum(recent_volumes) > sum(prev_volumes)

        # Price-volume relationship
        price_up = closes[-1] > closes[-2]
        volume_high = current_volume > avg_volume

        if price_up and volume_high:
            volume_signal = "bullish_confirmation"
        elif not price_up and volume_high:
            volume_signal = "bearish_confirmation"
        else:
            volume_signal = "neutral"

        return {
            "current_volume": current_volume,
            "average_volume": avg_volume,
            "volume_ratio": round(volume_ratio, 2),
            "volume_increasing": volume_increasing,
            "volume_signal": volume_signal,
        }

    def _analyze_momentum(self, ohlcv: List[List], indicators: Dict) -> Dict:
        """Analyze market momentum."""
        if not indicators:
            return {}

        close = float(ohlcv[-1][4])

        # EMA trend
        ema_trend = indicators.get("trend", "neutral")

        # RSI analysis
        rsi = indicators.get("rsi", 50)
        rsi_signal = "neutral"
        if rsi < 30:
            rsi_signal = "oversold"
        elif rsi > 70:
            rsi_signal = "overbought"

        # MACD analysis
        macd_line = indicators.get("macd_line", 0)
        macd_signal = indicators.get("macd_signal", 0)
        macd_diff = macd_line - macd_signal

        macd_status = "neutral"
        if macd_line > macd_signal and macd_diff > 0:
            macd_status = "bullish"
        elif macd_line < macd_signal and macd_diff < 0:
            macd_status = "bearish"

        # Bollinger Bands
        bb_position = "middle"
        bb_upper = indicators.get("bb_upper", close)
        bb_lower = indicators.get("bb_lower", close)
        bb_middle = indicators.get("bb_middle", close)

        if close >= bb_upper * 0.98:
            bb_position = "upper"
        elif close <= bb_lower * 1.02:
            bb_position = "lower"

        # Overall momentum
        momentum_score = 0
        if ema_trend == "bullish":
            momentum_score += 25
        elif ema_trend == "bearish":
            momentum_score -= 25

        if rsi_signal == "oversold":
            momentum_score += 15
        elif rsi_signal == "overbought":
            momentum_score -= 15

        if macd_status == "bullish":
            momentum_score += 20
        elif macd_status == "bearish":
            momentum_score -= 20

        momentum_direction = "neutral"
        if momentum_score >= 30:
            momentum_direction = "strong_bullish"
        elif momentum_score >= 10:
            momentum_direction = "bullish"
        elif momentum_score <= -30:
            momentum_direction = "strong_bearish"
        elif momentum_score <= -10:
            momentum_direction = "bearish"

        return {
            "trend": ema_trend,
            "rsi_signal": rsi_signal,
            "rsi_value": round(rsi, 2),
            "macd_status": macd_status,
            "bb_position": bb_position,
            "momentum_direction": momentum_direction,
            "momentum_score": momentum_score,
        }

    async def scan_all_crypto(self, timeframe: str = "1h") -> List[Dict]:
        """Scan all crypto pairs."""
        results = []
        tasks = []

        for symbol in CRYPTO_PAIRS[:10]:  # Limit to prevent rate limiting
            tasks.append(self.scan_symbol(symbol, timeframe))

        scan_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in scan_results:
            if isinstance(result, dict):
                results.append(result)

        return results

    async def scan_all_forex(self, timeframe: str = "1h") -> List[Dict]:
        """Scan all forex pairs."""
        results = []
        tasks = []

        for symbol in FOREX_PAIRS[:5]:  # Limit to prevent rate limiting
            tasks.append(self.scan_symbol(symbol, timeframe))

        scan_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in scan_results:
            if isinstance(result, dict):
                results.append(result)

        return results

    async def find_opportunities(self, min_confidence: float = 60.0) -> List[Dict]:
        """Find trading opportunities across all markets."""
        opportunities = []

        # Scan crypto
        crypto_results = await self.scan_all_crypto()
        for result in crypto_results:
            opportunity = self._evaluate_opportunity(result)
            if opportunity and opportunity.get("confidence", 0) >= min_confidence:
                opportunities.append(opportunity)

        # Scan forex
        forex_results = await self.scan_all_forex()
        for result in forex_results:
            opportunity = self._evaluate_opportunity(result)
            if opportunity and opportunity.get("confidence", 0) >= min_confidence:
                opportunities.append(opportunity)

        # Sort by confidence
        opportunities.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return opportunities

    def _evaluate_opportunity(self, scan_result: Dict) -> Optional[Dict]:
        """Evaluate scan result for trading opportunity."""
        if not scan_result:
            return None

        indicators = scan_result.get("indicators", {})
        momentum = scan_result.get("momentum", {})
        patterns = scan_result.get("patterns", [])
        price = scan_result.get("price", 0)
        symbol = scan_result.get("symbol", "")
        sr_levels = scan_result.get("support_resistance", {})

        # Determine signal direction
        signal_type = None
        confidence = 0
        reasons = []

        trend = momentum.get("trend", "neutral")
        rsi_signal = momentum.get("rsi_signal", "neutral")
        macd_status = momentum.get("macd_status", "neutral")
        volume_signal = scan_result.get("volume_analysis", {}).get("volume_signal", "neutral")

        # Bullish conditions
        bullish_score = 0
        if trend == "bullish":
            bullish_score += 30
            reasons.append("Uptrend detected")

        if rsi_signal == "oversold":
            bullish_score += 25
            reasons.append("RSI oversold - potential reversal")

        if macd_status == "bullish":
            bullish_score += 20
            reasons.append("MACD bullish crossover")

        if volume_signal == "bullish_confirmation":
            bullish_score += 15
            reasons.append("Volume confirms upward move")

        # Check for bullish patterns
        bullish_patterns = ["hammer", "morning_star", "three_white_soldiers", "engulfing_bullish"]
        for pattern_list in patterns:
            for p in pattern_list.get("patterns", []):
                if p in bullish_patterns:
                    bullish_score += 20
                    reasons.append(f"Bullish pattern: {p}")
                    break

        # Bearish conditions
        bearish_score = 0
        if trend == "bearish":
            bearish_score += 30
            reasons.append("Downtrend detected")

        if rsi_signal == "overbought":
            bearish_score += 25
            reasons.append("RSI overbought - potential reversal")

        if macd_status == "bearish":
            bearish_score += 20
            reasons.append("MACD bearish crossover")

        if volume_signal == "bearish_confirmation":
            bearish_score += 15
            reasons.append("Volume confirms downward move")

        # Check for bearish patterns
        bearish_patterns = ["shooting_star", "evening_star", "three_black_crows", "engulfing_bearish"]
        for pattern_list in patterns:
            for p in pattern_list.get("patterns", []):
                if p in bearish_patterns:
                    bearish_score += 20
                    reasons.append(f"Bearish pattern: {p}")
                    break

        # Determine signal
        if bullish_score >= 40 and bullish_score > bearish_score:
            signal_type = "buy"
            confidence = min(bullish_score, 95)
        elif bearish_score >= 40 and bearish_score > bullish_score:
            signal_type = "sell"
            confidence = min(bearish_score, 95)

        if not signal_type:
            return None

        # Calculate entry, SL, TP
        atr = indicators.get("atr", price * 0.01)

        if signal_type == "buy":
            entry = price
            stop_loss = round(price - atr * 1.5, 8)
            tp_multiplier = 1.5 + (confidence / 100)
            take_profit = round(price + atr * tp_multiplier, 8)
        else:
            entry = price
            stop_loss = round(price + atr * 1.5, 8)
            tp_multiplier = 1.5 + (confidence / 100)
            take_profit = round(price - atr * tp_multiplier, 8)

        return {
            "symbol": symbol,
            "signal_type": signal_type,
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "reasons": reasons,
            "indicators": {
                "rsi": momentum.get("rsi_value"),
                "trend": trend,
                "macd_status": macd_status,
            },
            "support_resistance": sr_levels,
            "timestamp": scan_result.get("timestamp"),
        }
