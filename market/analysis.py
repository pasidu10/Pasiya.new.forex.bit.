"""
Comprehensive market analysis module.
"""
from typing import Dict, List, Optional
from datetime import datetime

from market.exchange import ExchangeManager
from market.indicators import TechnicalIndicators
from market.patterns import CandlestickPatterns, SupportResistance
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketAnalysis:
    """Comprehensive market analysis."""

    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange = exchange_manager

    async def analyze(self, symbol: str, timeframe: str = "1h") -> Dict:
        """Perform comprehensive market analysis."""
        # Determine exchange
        exchange = "forex" if "/" in symbol and "USDT" not in symbol else "binance"

        # Fetch data
        ohlcv = await self.exchange.get_ohlcv(symbol, timeframe, exchange, limit=300)

        if not ohlcv or len(ohlcv) < 50:
            return {"error": "Insufficient data"}

        # Calculate all indicators
        indicators = TechnicalIndicators.get_all_indicators(ohlcv)

        # Detect patterns
        pattern_detector = CandlestickPatterns(ohlcv)
        patterns = pattern_detector.detect_all_patterns()

        # Support/Resistance
        sr_detector = SupportResistance(ohlcv)
        sr_levels = sr_detector.get_nearest_levels(float(ohlcv[-1][4]))
        pivot_points = sr_detector.find_pivot_points()

        # Get ticker
        ticker = await self.exchange.get_ticker(symbol, exchange)

        # Market summary
        summary = self._generate_summary(ohlcv, indicators, patterns, sr_levels)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat(),
            "price": float(ohlcv[-1][4]),
            "ticker": ticker,
            "indicators": indicators,
            "patterns": patterns,
            "support_resistance": sr_levels,
            "pivot_points": pivot_points,
            "summary": summary,
            "ohlcv_summary": {
                "open": float(ohlcv[-1][1]),
                "high": float(ohlcv[-1][2]),
                "low": float(ohlcv[-1][3]),
                "close": float(ohlcv[-1][4]),
                "volume": float(ohlcv[-1][5]),
            },
        }

    def _generate_summary(
        self,
        ohlcv: List[List],
        indicators: Dict,
        patterns: List,
        sr_levels: Dict
    ) -> Dict:
        """Generate market summary."""
        close = float(ohlcv[-1][4])
        prev_close = float(ohlcv[-2][4]) if len(ohlcv) > 1 else close

        price_change = ((close - prev_close) / prev_close) * 100 if prev_close > 0 else 0

        trend = indicators.get("trend", "neutral")
        rsi = indicators.get("rsi", 50)
        macd_hist = indicators.get("macd_histogram", 0)

        # Determine overall sentiment
        sentiment_score = 0

        if trend == "bullish":
            sentiment_score += 30
        elif trend == "bearish":
            sentiment_score -= 30

        if rsi < 30:
            sentiment_score += 20  # Oversold - bullish
        elif rsi > 70:
            sentiment_score -= 20  # Overbought - bearish

        if macd_hist > 0:
            sentiment_score += 15
        elif macd_hist < 0:
            sentiment_score -= 15

        # Check patterns
        for pattern_data in patterns[:2]:
            for p in pattern_data.get("patterns", []):
                if "bullish" in p.lower() or p in ["hammer", "morning_star", "three_white_soldiers"]:
                    sentiment_score += 10
                elif "bearish" in p.lower() or p in ["shooting_star", "evening_star", "three_black_crows"]:
                    sentiment_score -= 10

        if sentiment_score >= 40:
            sentiment = "Strongly Bullish"
            signal_bias = "buy"
        elif sentiment_score >= 15:
            sentiment = "Bullish"
            signal_bias = "buy"
        elif sentiment_score <= -40:
            sentiment = "Strongly Bearish"
            signal_bias = "sell"
        elif sentiment_score <= -15:
            sentiment = "Bearish"
            signal_bias = "sell"
        else:
            sentiment = "Neutral"
            signal_bias = "hold"

        return {
            "price": close,
            "price_change_percent": round(price_change, 2),
            "trend": trend,
            "rsi": round(rsi, 2),
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "signal_bias": signal_bias,
            "support_levels": sr_levels.get("support", []),
            "resistance_levels": sr_levels.get("resistance", []),
        }

    async def get_market_overview(self) -> Dict:
        """Get overview of major markets."""
        from config import CRYPTO_PAIRS, FOREX_PAIRS

        crypto_overview = []
        for symbol in CRYPTO_PAIRS[:5]:
            ticker = await self.exchange.get_ticker(symbol, "binance")
            if ticker:
                crypto_overview.append({
                    "symbol": symbol,
                    "price": ticker["last"],
                    "change_24h": ticker.get("change_percent", 0),
                })

        forex_overview = []
        for symbol in FOREX_PAIRS[:3]:
            ticker = await self.exchange.get_ticker(symbol, "forex")
            if ticker:
                forex_overview.append({
                    "symbol": symbol,
                    "price": ticker["last"],
                })

        return {
            "crypto": crypto_overview,
            "forex": forex_overview,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def generate_report(self, symbol: str, timeframe: str = "1h") -> str:
        """Generate human-readable analysis report."""
        analysis = await self.analyze(symbol, timeframe)

        if analysis.get("error"):
            return f"Error: {analysis['error']}"

        summary = analysis.get("summary", {})
        indicators = analysis.get("indicators", {})
        patterns = analysis.get("patterns", [])

        report_lines = [
            f"📊 **Market Analysis: {symbol}**",
            f"Timeframe: {timeframe}",
            "",
            f"💵 **Price**: {summary.get('price', 0):,.4f}",
            f"📈 **24h Change**: {summary.get('price_change_percent', 0):+.2f}%",
            f"📊 **Trend**: {summary.get('trend', 'neutral').upper()}",
            f"💭 **Sentiment**: {summary.get('sentiment', 'neutral')}",
            "",
            "**Technical Indicators:**",
            f"  • RSI (14): {indicators.get('rsi', 50):.1f}",
            f"  • MACD: {'Bullish' if indicators.get('macd_histogram', 0) > 0 else 'Bearish'}",
            f"  • EMA Trend: {indicators.get('trend', 'neutral')}",
            f"  • ATR: {indicators.get('atr', 0):.4f} ({indicators.get('atr_percent', 0):.2f}%)",
        ]

        if patterns:
            report_lines.append("")
            report_lines.append("**Candlestick Patterns:**")
            for pattern_data in patterns[:3]:
                for p in pattern_data.get("patterns", []):
                    report_lines.append(f"  • {p.replace('_', ' ').title()}")

        sr = analysis.get("support_resistance", {})
        if sr.get("support") or sr.get("resistance"):
            report_lines.append("")
            report_lines.append("**Support/Resistance:**")
            for r in sr.get("resistance", [])[:2]:
                report_lines.append(f"  🔴 Resistance: {r:,.4f}")
            for s in sr.get("support", [])[:2]:
                report_lines.append(f"  🟢 Support: {s:,.4f}")

        report_lines.append("")
        report_lines.append(f"**Signal Bias:** {summary.get('signal_bias', 'hold').upper()}")

        return "\n".join(report_lines)
