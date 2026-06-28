"""
Signal generation logic for trading signals.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

from config import settings
from market.exchange import ExchangeManager
from market.indicators import TechnicalIndicators
from market.patterns import CandlestickPatterns, SupportResistance
from market.scanner import MarketScanner
from utils.helpers import calculate_risk_reward, calculate_confidence_score
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalGenerator:
    """Generate trading signals based on technical analysis."""

    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange = exchange_manager
        self.scanner = MarketScanner(exchange_manager)
        self.min_confidence = 50

    async def generate_signal(
        self,
        symbol: str,
        timeframe: str = "1h",
        risk_reward_min: float = 1.5,
    ) -> Optional[Dict]:
        """Generate a trading signal for the given symbol."""
        try:
            # Scan the symbol
            scan_result = await self.scanner.scan_symbol(symbol, timeframe)

            if not scan_result:
                logger.warning(f"No scan result for {symbol}")
                return None

            indicators = scan_result.get("indicators", {})
            momentum = scan_result.get("momentum", {})
            patterns = scan_result.get("patterns", [])
            sr_levels = scan_result.get("support_resistance", {})

            # Determine signal direction
            signal_type, confidence, reasons = self._determine_signal(
                indicators, momentum, patterns
            )

            if confidence < self.min_confidence:
                logger.debug(f"Confidence too low for {symbol}: {confidence}")
                return None

            # Calculate entry/SL/TP
            price = scan_result.get("price", 0)
            atr = indicators.get("atr", price * 0.02)
            atr_percent = indicators.get("atr_percent", 2)

            entry_price, stop_loss, take_profits = self._calculate_levels(
                price=price,
                atr=atr,
                signal_type=signal_type,
                sr_levels=sr_levels,
                confidence=confidence,
            )

            # Calculate risk reward
            _, _, rr_ratio = calculate_risk_reward(entry_price, stop_loss, take_profits[0], signal_type)

            if rr_ratio < risk_reward_min:
                logger.debug(f"Risk/reward too low for {symbol}: {rr_ratio:.2f}")
                return None

            # Build signal
            signal = {
                "symbol": symbol,
                "signal_type": signal_type,
                "market_type": "crypto" if "USDT" in symbol or "BUSD" in symbol else "forex",
                "timeframe": timeframe,
                "entry_price": round(entry_price, 8),
                "stop_loss": round(stop_loss, 8),
                "take_profit_1": round(take_profits[0], 8),
                "take_profit_2": round(take_profits[1], 8) if len(take_profits) > 1 else None,
                "take_profit_3": round(take_profits[2], 8) if len(take_profits) > 2 else None,
                "risk_reward_ratio": round(rr_ratio, 2),
                "confidence_score": confidence,
                "reasons": reasons,
                "indicators": {
                    "rsi": round(indicators.get("rsi", 50), 2),
                    "macd_status": momentum.get("macd_status", "neutral"),
                    "trend": indicators.get("trend", "neutral"),
                    "ema_trend": indicators.get("ema_crossover"),
                    "atr": round(atr, 8),
                    "atr_percent": round(atr_percent, 2),
                },
                "patterns": [p.get("patterns", []) for p in patterns[:3]],
                "support_resistance": sr_levels,
                "analysis_notes": self._generate_notes(signal_type, reasons),
                "created_at": datetime.utcnow().isoformat(),
                "expired_at": (datetime.utcnow() + timedelta(hours=settings.SIGNAL_EXPIRY_HOURS)).isoformat(),
            }

            logger.info(f"Generated {signal_type} signal for {symbol} with confidence {confidence}")
            return signal

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None

    def _determine_signal(
        self,
        indicators: Dict,
        momentum: Dict,
        patterns: List,
    ) -> tuple:
        """Determine signal type from analysis."""
        bullish_score = 0
        bearish_score = 0
        reasons = []

        trend = indicators.get("trend", "neutral")
        rsi = indicators.get("rsi", 50)
        macd_hist = indicators.get("macd_histogram", 0)
        ema_cross = indicators.get("ema_crossover")

        # Trend analysis
        if trend == "bullish":
            bullish_score += 25
            reasons.append("Uptrend confirmed")
        elif trend == "bearish":
            bearish_score += 25
            reasons.append("Downtrend confirmed")

        # RSI analysis
        if rsi < 30:
            bullish_score += 20
            reasons.append("RSI oversold (<30)")
        elif rsi > 70:
            bearish_score += 20
            reasons.append("RSI overbought (>70)")
        elif rsi < 40:
            bullish_score += 10
            reasons.append("RSI near oversold")
        elif rsi > 60:
            bearish_score += 10
            reasons.append("RSI near overbought")

        # MACD analysis
        if macd_hist > 0:
            bullish_score += 15
            reasons.append("MACD histogram positive")
        elif macd_hist < 0:
            bearish_score += 15
            reasons.append("MACD histogram negative")

        # EMA crossover
        if ema_cross == "bullish_crossover":
            bullish_score += 20
            reasons.append("Bullish EMA crossover detected")
        elif ema_cross == "bearish_crossover":
            bearish_score += 20
            reasons.append("Bearish EMA crossover detected")

        # Pattern analysis
        bullish_patterns = [
            "hammer", "morning_star", "three_white_soldiers",
            "engulfing_bullish", "tweezer_bottom", "piercing_line", "inverted_hammer"
        ]
        bearish_patterns = [
            "shooting_star", "evening_star", "three_black_crows",
            "engulfing_bearish", "tweezer_top", "dark_cloud_cover", "hanging_man"
        ]

        for pattern_data in patterns:
            for pattern in pattern_data.get("patterns", []):
                if pattern in bullish_patterns:
                    bullish_score += 15
                    reasons.append(f"Bullish pattern: {pattern.replace('_', ' ')}")
                elif pattern in bearish_patterns:
                    bearish_score += 15
                    reasons.append(f"Bearish pattern: {pattern.replace('_', ' ')}")

        # Bollinger Band position
        bb_position = momentum.get("bb_position", "middle")
        if bb_position == "lower":
            bullish_score += 10
            reasons.append("Price at lower Bollinger Band")
        elif bb_position == "upper":
            bearish_score += 10
            reasons.append("Price at upper Bollinger Band")

        # Determine signal
        if bullish_score > bearish_score and bullish_score >= 40:
            signal_type = "buy"
            confidence = min(bullish_score, 95)
        elif bearish_score > bullish_score and bearish_score >= 40:
            signal_type = "sell"
            confidence = min(bearish_score, 95)
        else:
            signal_type = None
            confidence = 0

        return signal_type, confidence, reasons

    def _calculate_levels(
        self,
        price: float,
        atr: float,
        signal_type: str,
        sr_levels: Dict,
        confidence: float,
    ) -> tuple:
        """Calculate entry, stop loss, and take profit levels."""
        # Entry is current price
        entry_price = price

        # Calculate stop loss based on ATR
        sl_multiplier = 1.5 + (1 - confidence / 100) * 0.5  # Adjust SL based on confidence

        if signal_type == "buy":
            # For buy signals
            stop_loss = entry_price - (atr * sl_multiplier)

            # Use support level if available and better
            support_levels = sr_levels.get("support", [])
            if support_levels:
                nearest_support = max(s for s in support_levels if s < entry_price)
                if nearest_support and nearest_support > stop_loss:
                    stop_loss = nearest_support - (nearest_support * 0.005)  # Small buffer

            # Calculate take profits
            # TP1: 1.5R, TP2: 2R, TP3: 3R
            risk = entry_price - stop_loss
            take_profits = [
                entry_price + (risk * 1.5),
                entry_price + (risk * 2.5),
                entry_price + (risk * 4.0),
            ]

            # Check resistance levels
            resistance_levels = sr_levels.get("resistance", [])
            if resistance_levels:
                for i, r in enumerate(resistance_levels[:3]):
                    if r > entry_price and i < len(take_profits):
                        # Adjust TP to be slightly below resistance
                        take_profits[i] = r * 0.995

        else:
            # For sell signals
            stop_loss = entry_price + (atr * sl_multiplier)

            # Use resistance level if available
            resistance_levels = sr_levels.get("resistance", [])
            if resistance_levels:
                nearest_resistance = min(r for r in resistance_levels if r > entry_price)
                if nearest_resistance and nearest_resistance < stop_loss:
                    stop_loss = nearest_resistance + (nearest_resistance * 0.005)

            # Take profits for shorts
            risk = stop_loss - entry_price
            take_profits = [
                entry_price - (risk * 1.5),
                entry_price - (risk * 2.5),
                entry_price - (risk * 4.0),
            ]

            # Check support levels
            support_levels = sr_levels.get("support", [])
            if support_levels:
                for i, s in enumerate(support_levels[:3]):
                    if s < entry_price and i < len(take_profits):
                        take_profits[i] = s * 1.005

        return entry_price, stop_loss, take_profits

    def _generate_notes(self, signal_type: str, reasons: List[str]) -> str:
        """Generate analysis notes for the signal."""
        direction = "LONG" if signal_type == "buy" else "SHORT"
        notes = f"Generated {direction} signal based on: {', '.join(reasons[:3])}."
        return notes

    async def generate_batch_signals(
        self,
        symbols: List[str],
        timeframe: str = "1h",
        max_signals: int = 5,
    ) -> List[Dict]:
        """Generate signals for multiple symbols."""
        tasks = [self.generate_signal(symbol, timeframe) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals = []
        for result in results:
            if isinstance(result, dict) and result:
                signals.append(result)

        # Sort by confidence and limit
        signals.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
        return signals[:max_signals]
