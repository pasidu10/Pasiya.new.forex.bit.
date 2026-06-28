"""
Signal tracking service for monitoring and notifications.
Handles trade opened, SL/TP hits, signal updates, and expirations.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from config import settings
from utils.logger import get_logger
from utils.helpers import get_time_ago

logger = get_logger(__name__)


class SignalTracker:
    """Tracks signals and sends notifications for SL/TP hits."""

    def __init__(self, db, exchange_manager, notification_service):
        self.db = db
        self.exchange = exchange_manager
        self.notification = notification_service
        self._running = False
        self._monitored_signals: Dict[int, Dict] = {}

        # Price tolerance for hitting targets
        self.price_tolerance_percent = 0.1

    async def start(self):
        """Start the signal monitoring service."""
        self._running = True

        # Load active signals
        await self._load_active_signals()

        # Start monitoring loop
        asyncio.create_task(self._monitor_signals_loop())

        logger.info("Signal tracker started")

    async def stop(self):
        """Stop the signal monitoring service."""
        self._running = False
        logger.info("Signal tracker stopped")

    async def _load_active_signals(self):
        """Load all active signals from database."""
        try:
            signals = await self.db.get_active_signals()
            for signal in signals:
                self._monitored_signals[signal["id"]] = signal
            logger.info(f"Loaded {len(signals)} active signals for monitoring")
        except Exception as e:
            logger.error(f"Error loading active signals: {e}")

    async def add_signal(self, signal: Dict):
        """Add a signal to monitoring."""
        signal_id = signal.get("id")
        if signal_id:
            self._monitored_signals[signal_id] = signal
            logger.info(f"Added signal {signal_id} to monitoring")

    async def remove_signal(self, signal_id: int):
        """Remove a signal from monitoring."""
        if signal_id in self._monitored_signals:
            del self._monitored_signals[signal_id]
            logger.info(f"Removed signal {signal_id} from monitoring")

    async def _monitor_signals_loop(self):
        """Main loop for monitoring signals."""
        while self._running:
            try:
                for signal_id, signal in list(self._monitored_signals.items()):
                    await self._check_signal(signal)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in signal monitoring: {e}")
                await asyncio.sleep(60)

    async def _check_signal(self, signal: Dict):
        """Check a single signal for target hits."""
        signal_id = signal.get("id")
        symbol = signal.get("symbol")
        signal_type = signal.get("signal_type", "buy")
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss")
        tp1 = signal.get("take_profit_1")
        tp2 = signal.get("take_profit_2")
        tp3 = signal.get("take_profit_3")

        hit_target = signal.get("hit_target", 0)
        closed = signal.get("closed", False)

        if closed:
            await self.remove_signal(signal_id)
            return

        # Get current price
        try:
            exchange_type = "forex" if "/" in symbol and "USDT" not in symbol else "binance"
            ticker = await self.exchange.get_ticker(symbol, exchange_type)
            if not ticker:
                return

            current_price = ticker.get("last", 0)

        except Exception as e:
            logger.debug(f"Error getting price for {symbol}: {e}")
            return

        # Check expiration
        expired_at = signal.get("expired_at")
        if expired_at:
            if isinstance(expired_at, str):
                expired_at = datetime.fromisoformat(expired_at.replace("Z", "+00:00"))

            if datetime.utcnow() > expired_at.replace(tzinfo=None):
                await self._handle_signal_expired(signal)
                return

        # Check targets based on signal type
        if signal_type.lower() == "buy":
            await self._check_buy_targets(signal, current_price, sl, tp1, tp2, tp3, hit_target)
        else:
            await self._check_sell_targets(signal, current_price, sl, tp1, tp2, tp3, hit_target)

    async def _check_buy_targets(
        self,
        signal: Dict,
        current_price: float,
        sl: float,
        tp1: float,
        tp2: float,
        tp3: float,
        hit_target: int
    ):
        """Check targets for BUY signal."""
        signal_id = signal["id"]

        # Check stop loss hit
        if sl and current_price <= sl:
            await self._handle_stop_loss_hit(signal, current_price)
            return

        # Check TP3 (final target)
        if tp3 and current_price >= tp3 and hit_target < 3:
            await self._handle_tp_hit(signal, current_price, 3)
            return

        # Check TP2
        if tp2 and current_price >= tp2 and hit_target < 2:
            await self._handle_tp_hit(signal, current_price, 2)
            return

        # Check TP1
        if tp1 and current_price >= tp1 and hit_target < 1:
            await self._handle_tp_hit(signal, current_price, 1)
            return

    async def _check_sell_targets(
        self,
        signal: Dict,
        current_price: float,
        sl: float,
        tp1: float,
        tp2: float,
        tp3: float,
        hit_target: int
    ):
        """Check targets for SELL signal."""
        signal_id = signal["id"]

        # Check stop loss hit
        if sl and current_price >= sl:
            await self._handle_stop_loss_hit(signal, current_price)
            return

        # Check TP3 (final target)
        if tp3 and current_price <= tp3 and hit_target < 3:
            await self._handle_tp_hit(signal, current_price, 3)
            return

        # Check TP2
        if tp2 and current_price <= tp2 and hit_target < 2:
            await self._handle_tp_hit(signal, current_price, 2)
            return

        # Check TP1
        if tp1 and current_price <= tp1 and hit_target < 1:
            await self._handle_tp_hit(signal, current_price, 1)
            return

    async def _handle_stop_loss_hit(self, signal: Dict, current_price: float):
        """Handle stop loss hit."""
        signal_id = signal["id"]
        symbol = signal.get("symbol")

        # Update database
        await self.db.close_signal(signal_id, hit_target=0)

        # Add performance entry
        await self._add_performance(signal_id, current_price, "stop_loss_hit")

        # Send notification
        message = self._format_sl_hit_message(signal, current_price)
        await self._send_signal_notification(signal, message)

        # Remove from monitoring
        await self.remove_signal(signal_id)

        logger.info(f"Signal {signal_id}: SL hit at {current_price}")

    async def _handle_tp_hit(self, signal: Dict, current_price: float, tp_level: int):
        """Handle take profit hit."""
        signal_id = signal["id"]
        symbol = signal.get("symbol")

        # Update database
        await self.db.update_signal(signal_id, hit_target=tp_level)

        # Add performance entry
        await self._add_performance(signal_id, current_price, f"tp{tp_level}_hit")

        # Send notification
        message = self._format_tp_hit_message(signal, current_price, tp_level)
        await self._send_signal_notification(signal, message)

        # Update in-memory signal
        self._monitored_signals[signal_id]["hit_target"] = tp_level

        # If final TP, close the signal
        if tp_level >= 3 or not signal.get(f"take_profit_{tp_level + 1}"):
            await self.db.close_signal(signal_id, hit_target=tp_level)
            await self.remove_signal(signal_id)

        logger.info(f"Signal {signal_id}: TP{tp_level} hit at {current_price}")

    async def _handle_signal_expired(self, signal: Dict):
        """Handle signal expiration."""
        signal_id = signal["id"]

        # Update database
        await self.db.expire_signal(signal_id)

        # Send notification
        message = self._format_expired_message(signal)
        await self._send_signal_notification(signal, message)

        # Remove from monitoring
        await self.remove_signal(signal_id)

        logger.info(f"Signal {signal_id} expired")

    async def _add_performance(self, signal_id: int, price: float, status: str, notes: str = None):
        """Add performance tracking entry."""
        try:
            if hasattr(self.db, "_is_supabase") and self.db._is_supabase:
                # Supabase insert
                if hasattr(self.db._backend, "_client") and self.db._backend._client:
                    self.db._backend._client.table("signal_performance").insert({
                        "signal_id": signal_id,
                        "price": price,
                        "status": status,
                        "notes": notes,
                    }).execute()
            else:
                # SQLite insert
                query = """
                    INSERT INTO signal_performance (signal_id, price, status, notes)
                    VALUES (?, ?, ?, ?)
                """
                await self.db.execute(query, (signal_id, price, status, notes))
                await self.db.commit()
        except Exception as e:
            logger.error(f"Error adding performance entry: {e}")

    async def _send_signal_notification(self, signal: Dict, message: str):
        """Send notification for signal update."""
        created_by = signal.get("created_by")
        signal_id = signal["id"]

        # Send to premium channel
        if settings.PREMIUM_CHANNEL_ID:
            await self.notification.send_to_user(settings.PREMIUM_CHANNEL_ID, message)

        # Send to main channel
        if settings.CHANNEL_ID:
            await self.notification.send_to_user(settings.CHANNEL_ID, message)

        # Send to group
        if settings.GROUP_ID:
            await self.notification.send_to_user(settings.GROUP_ID, message)

    def _format_sl_hit_message(self, signal: Dict, current_price: float) -> str:
        """Format stop loss hit message."""
        symbol = signal.get("symbol", "")
        sl = signal.get("stop_loss", 0)
        entry = signal.get("entry_price", 0)
        signal_type = signal.get("signal_type", "buy").upper()

        # Calculate loss
        if signal_type == "BUY":
            loss_percent = ((entry - current_price) / entry * 100) if entry > 0 else 0
        else:
            loss_percent = ((current_price - entry) / entry * 100) if entry > 0 else 0

        return "\n".join([
            f"❌ **STOP LOSS HIT** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']} {signal_type}",
            f"💵 Entry: `{entry:,.8f}`",
            f"🔴 SL: `{sl:,.8f}`",
            f"📍 Hit at: `{current_price:,.8f}`",
            f"📉 Loss: `{loss_percent:.2f}%`",
            "",
            "_⚠️ Trade closed. Review and learn from this outcome!_",
        ])

    def _format_tp_hit_message(self, signal: Dict, current_price: float, tp_level: int) -> str:
        """Format take profit hit message."""
        symbol = signal.get("symbol", "")
        entry = signal.get("entry_price", 0)
        tp = signal.get(f"take_profit_{tp_level}", 0)
        signal_type = signal.get("signal_type", "buy").upper()

        # Calculate profit
        if signal_type == "BUY":
            profit_percent = ((current_price - entry) / entry * 100) if entry > 0 else 0
        else:
            profit_percent = ((entry - current_price) / entry * 100) if entry > 0 else 0

        celebration = "🎉" if tp_level >= 3 else "✨" if tp_level >= 2 else "✅"

        if tp_level == 1:
            lines = [
                f"✅ **TAKE PROFIT 1 HIT** - {symbol}",
                "",
                f"📊 **Signal:** #{signal['id']} {signal_type}",
                f"💵 Entry: `{entry:,.8f}`",
                f"🎯 TP1: `{tp:,.8f}`",
                f"📍 Hit at: `{current_price:,.8f}`",
                f"📈 Profit: `+{profit_percent:.2f}%`",
                "",
                "_💰 Partial profit secured! Move SL to breakeven!_",
            ]
        elif tp_level == 2:
            lines = [
                f"✨ **TAKE PROFIT 2 HIT** - {symbol}",
                "",
                f"📊 **Signal:** #{signal['id']} {signal_type}",
                f"💵 Entry: `{entry:,.8f}`",
                f"🎯 TP2: `{tp:,.8f}`",
                f"📍 Hit at: `{current_price:,.8f}`",
                f"📈 Profit: `+{profit_percent:.2f}%`",
                "",
                "_🎯 Book more profits! Ride the rest!_",
            ]
        else:
            lines = [
                f"🎉 **TAKE PROFIT {tp_level} HIT!** - {symbol}",
                "",
                f"📊 **Signal:** #{signal['id']} {signal_type}",
                f"💵 Entry: `{entry:,.8f}`",
                f"🎯 TP{tp_level}: `{tp:,.8f}`",
                f"📍 Hit at: `{current_price:,.8f}`",
                f"📈 Profit: `+{profit_percent:.2f}%`",
                "",
                f"{celebration} **Signal Complete!** 🎊",
                "",
                "_💪 Great trade! Full target achieved!_",
            ]

        return "\n".join(lines)

    def _format_expired_message(self, signal: Dict) -> str:
        """Format signal expired message."""
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "buy").upper()
        entry = signal.get("entry_price", 0)
        created_at = signal.get("created_at", "")

        return "\n".join([
            f"⏰ **SIGNAL EXPIRED** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']} {signal_type}",
            f"💵 Entry: `{entry:,.8f}`",
            f"📅 Created: {created_at[:19] if created_at else 'N/A'}",
            "",
            "_Signal cancelled due to time expiration._",
            "_No entry was made or targets not reached._",
        ])

    def _format_trade_opened_message(self, signal: Dict) -> str:
        """Format trade opened confirmation."""
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "buy").upper()
        entry = signal.get("entry_price", 0)

        return "\n".join([
            f"✅ **TRADE OPENED** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']} {signal_type}",
            f"💵 Entry: `{entry:,.8f}`",
            "",
            "_Trade has been activated!_",
            "_SL and TP levels are being monitored._",
        ])

    def _format_entry_hit_message(self, signal: Dict, price: float) -> str:
        """Format entry price hit message."""
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "buy").upper()
        entry = signal.get("entry_price", 0)

        return "\n".join([
            f"🎯 **ENTRY HIT** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']} {signal_type}",
            f"💵 Target Entry: `{entry:,.8f}`",
            f"📍 Current: `{price:,.8f}`",
            "",
            "_Entry zone reached! Watching for setup._",
        ])

    def _format_breakeven_message(self, signal: Dict) -> str:
        """Format break even activated message."""
        symbol = signal.get("symbol", "")
        return "\n".join([
            f"🛡️ **BREAK EVEN ACTIVATED** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']}",
            "",
            "_Stop loss moved to entry!_",
            "_Trade is now risk-free!_",
        ])

    def _format_signal_cancelled_message(self, signal: Dict, reason: str = "") -> str:
        """Format signal cancelled message."""
        symbol = signal.get("symbol", "")
        return "\n".join([
            f"🚫 **SIGNAL CANCELLED** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']}",
            f"📝 Reason: {reason or 'Market conditions changed'}",
            "",
            "_Signal no longer valid._",
        ])

    def _format_signal_updated_message(self, signal: Dict, updates: Dict) -> str:
        """Format signal updated message."""
        symbol = signal.get("symbol", "")
        lines = [
            f"📝 **SIGNAL UPDATED** - {symbol}",
            "",
            f"📊 **Signal:** #{signal['id']}",
            "",
            "**Changes:**",
        ]

        for key, value in updates.items():
            if key in ["stop_loss", "take_profit_1", "take_profit_2", "take_profit_3"]:
                lines.append(f"  • {key.replace('_', ' ').title()}: `{value:,.8f}`")

        return "\n".join(lines)
