"""
Signal management for tracking and handling signals.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

from database import DatabaseManager, SignalRepository
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalManager:
    """Manage trading signals lifecycle."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.signal_repo = SignalRepository(db)

    async def save_signal(self, signal: Dict, created_by: int = None, is_auto: bool = True) -> Dict:
        """Save a signal to the database."""
        signal_data = {
            "symbol": signal.get("symbol"),
            "market_type": signal.get("market_type", "crypto"),
            "signal_type": signal.get("signal_type"),
            "timeframe": signal.get("timeframe", "1h"),
            "entry_price": signal.get("entry_price"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit_1": signal.get("take_profit_1"),
            "take_profit_2": signal.get("take_profit_2"),
            "take_profit_3": signal.get("take_profit_3"),
            "risk_reward_ratio": signal.get("risk_reward_ratio"),
            "confidence_score": signal.get("confidence_score"),
            "indicators": signal.get("indicators", {}),
            "patterns": signal.get("patterns", []),
            "analysis_notes": signal.get("analysis_notes"),
            "created_by": created_by,
            "is_auto": is_auto,
            "expired_at": signal.get("expired_at"),
        }

        saved_signal = await self.signal_repo.create_signal(signal_data)
        logger.info(f"Saved signal {saved_signal['id']} for {signal.get('symbol')}")
        return saved_signal

    async def get_active_signals(self) -> List[Dict]:
        """Get all active signals."""
        return await self.signal_repo.get_active_signals()

    async def get_signal_by_id(self, signal_id: int) -> Optional[Dict]:
        """Get a signal by ID."""
        return await self.signal_repo.get_signal(signal_id)

    async def close_signal(self, signal_id: int, hit_target: int = 0) -> bool:
        """Close a signal and record the result."""
        try:
            await self.signal_repo.close_signal(signal_id, hit_target)

            # Update statistics
            from database import StatisticsRepository
            stats_repo = StatisticsRepository(self.db)
            await stats_repo.increment_stat("signals_generated")
            if hit_target > 0:
                await stats_repo.increment_stat("signals_hit")
            else:
                await stats_repo.increment_stat("signals_missed")

            logger.info(f"Closed signal {signal_id} with target {hit_target}")
            return True
        except Exception as e:
            logger.error(f"Error closing signal {signal_id}: {e}")
            return False

    async def expire_old_signals(self) -> int:
        """Expire signals past their expiry date."""
        active_signals = await self.get_active_signals()
        expired_count = 0

        for signal in active_signals:
            expired_at = signal.get("expired_at")
            if expired_at:
                if isinstance(expired_at, str):
                    expired_at = datetime.fromisoformat(expired_at)

                if datetime.utcnow() > expired_at:
                    await self.signal_repo.expire_signal(signal["id"])
                    expired_count += 1

        if expired_count > 0:
            logger.info(f"Expired {expired_count} old signals")

        return expired_count

    def format_signal_message(self, signal: Dict, language: str = "en") -> str:
        """Format a signal as a user-friendly message."""
        if language == "si":
            return self._format_signal_sinhala(signal)
        return self._format_signal_english(signal)

    def _format_signal_english(self, signal: Dict) -> str:
        """Format signal in English."""
        signal_type = signal.get("signal_type", "").upper()
        symbol = signal.get("symbol", "")
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp1 = signal.get("take_profit_1", 0)
        tp2 = signal.get("take_profit_2", 0)
        tp3 = signal.get("take_profit_3", 0)
        rr = signal.get("risk_reward_ratio", 0)
        confidence = signal.get("confidence_score", 0)
        timeframe = signal.get("timeframe", "1h")
        market_type = signal.get("market_type", "crypto").upper()

        direction_emoji = "🟢" if signal_type == "BUY" else "🔴"

        message_lines = [
            f"🚀 **NEW {signal_type} SIGNAL**",
            f"**{symbol}** | {timeframe} | {market_type}",
            "",
            f"{direction_emoji} **Entry Price:** `{entry:,.8f}`",
            f"🔴 **Stop Loss:** `{sl:,.8f}`",
            "",
            "**Take Profit Levels:**",
        ]

        if tp1:
            message_lines.append(f"🎯 **TP1:** `{tp1:,.8f}` *(1R)*")
        if tp2:
            message_lines.append(f"🎯 **TP2:** `{tp2:,.8f}` *(2.5R)*")
        if tp3:
            message_lines.append(f"🎯 **TP3:** `{tp3:,.8f}` *(4R)*")

        message_lines.extend([
            "",
            f"📊 **Risk:Reward:** `{rr:.2f}`",
            f"📈 **Confidence:** `{confidence:.0f}%`",
        ])

        # Add technical reasons
        reasons = signal.get("reasons", [])
        if reasons:
            message_lines.append("")
            message_lines.append("**Technical Analysis:**")
            for reason in reasons[:5]:
                message_lines.append(f"• {reason}")

        # Add timestamp
        created_at = signal.get("created_at", "")
        message_lines.extend([
            "",
            f"⏰ Generated: {created_at[:19] if created_at else 'N/A'}",
            "",
            "_⚠️ Trade responsibly. Not financial advice._",
        ])

        return "\n".join(message_lines)

    def _format_signal_sinhala(self, signal: Dict) -> str:
        """Format signal in Sinhala."""
        signal_type = signal.get("signal_type", "").upper()
        symbol = signal.get("symbol", "")
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp1 = signal.get("take_profit_1", 0)
        rr = signal.get("risk_reward_ratio", 0)
        confidence = signal.get("confidence_score", 0)

        direction_emoji = "🟢" if signal_type == "BUY" else "🔴"

        return "\n".join([
            f"🚀 **නව {signal_type} SIGNAL**",
            f"**{symbol}**",
            "",
            f"{direction_emoji} **Entry:** `{entry:,.8f}`",
            f"🔴 **Stop Loss:** `{sl:,.8f}`",
            f"🎯 **Take Profit:** `{tp1:,.8f}`",
            "",
            f"📊 **Risk:Reward:** `{rr:.2f}`",
            f"📈 **Confidence:** `{confidence:.0f}%`",
            "",
            "_⚠️ වගකීම් භාර නොගනිමු_",
        ])

    async def calculate_performance_stats(self, days: int = 30) -> Dict:
        """Calculate signal performance statistics."""
        return await self.signal_repo.get_signal_performance(days)

    async def get_user_signals_by_target(self, user_id: int, target: int = None) -> List[Dict]:
        """Get signals for a user filtered by target hit."""
        all_signals = await self.signal_repo.fetchall(
            "SELECT * FROM signals WHERE hit_target = ? ORDER BY created_at DESC LIMIT 10",
            (target,)
        ) if target else await self.get_active_signals()
        return all_signals

    def calculate_potential_profit(
        self,
        signal: Dict,
        current_price: float,
        position_size: float = 1.0,
    ) -> Dict:
        """Calculate potential profit/loss for a signal."""
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp1 = signal.get("take_profit_1", 0)
        signal_type = signal.get("signal_type", "buy")

        if signal_type == "buy":
            # Potential loss if stopped out
            potential_loss = (entry - sl) * position_size
            # Potential profit at TP1
            potential_profit = (tp1 - entry) * position_size
            # Current P/L
            current_pl = (current_price - entry) * position_size
        else:
            potential_loss = (sl - entry) * position_size
            potential_profit = (entry - tp1) * position_size
            current_pl = (entry - current_price) * position_size

        return {
            "potential_profit": potential_profit,
            "potential_loss": potential_loss,
            "current_pl": current_pl,
            "prr_percent": (potential_profit / potential_loss * 100) if potential_loss > 0 else 0,
        }
