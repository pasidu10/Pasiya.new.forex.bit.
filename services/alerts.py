"""
Alert service for price alerts, TP/SL alerts, and market alerts.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp

from database import DatabaseManager, AlertRepository
from market.exchange import ExchangeManager
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AlertService:
    """Manage price alerts and notifications."""

    def __init__(self, db: DatabaseManager, exchange: ExchangeManager):
        self.db = db
        self.exchange = exchange
        self.alert_repo = AlertRepository(db)
        self._running = False

    async def create_price_alert(
        self,
        user_id: int,
        symbol: str,
        target_price: float,
        condition: str = "above",
    ) -> Optional[Dict]:
        """Create a price alert for a user."""
        alert = await self.alert_repo.create_alert(
            user_id=user_id,
            symbol=symbol,
            alert_type="price",
            target_price=target_price,
            condition_type=condition,
        )
        logger.info(f"Created price alert for user {user_id}: {symbol} @ {target_price}")
        return alert

    async def create_tp_alert(
        self,
        user_id: int,
        symbol: str,
        target_price: float,
    ) -> Optional[Dict]:
        """Create a take profit alert."""
        alert = await self.alert_repo.create_alert(
            user_id=user_id,
            symbol=symbol,
            alert_type="take_profit",
            target_price=target_price,
            condition_type="above" if target_price > 0 else "below",
        )
        return alert

    async def create_sl_alert(
        self,
        user_id: int,
        symbol: str,
        target_price: float,
    ) -> Optional[Dict]:
        """Create a stop loss alert."""
        alert = await self.alert_repo.create_alert(
            user_id=user_id,
            symbol=symbol,
            alert_type="stop_loss",
            target_price=target_price,
            condition_type="below" if target_price > 0 else "above",
        )
        return alert

    async def get_user_alerts(self, user_id: int) -> List[Dict]:
        """Get all alerts for a user."""
        return await self.alert_repo.get_user_alerts(user_id)

    async def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert."""
        try:
            await self.alert_repo.delete_alert(alert_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting alert {alert_id}: {e}")
            return False

    async def check_alerts(self) -> List[Dict]:
        """Check all active alerts and trigger those that hit target."""
        active_alerts = await self.alert_repo.get_all_active_alerts()

        if not active_alerts:
            return []

        triggered_alerts = []

        for alert in active_alerts:
            try:
                symbol = alert.get("symbol")
                target_price = alert.get("target_price")
                condition = alert.get("condition_type")

                # Determine exchange
                exchange = "forex" if "/" in symbol and "USDT" not in symbol else "binance"

                # Get current price
                ticker = await self.exchange.get_ticker(symbol, exchange)
                if not ticker:
                    continue

                current_price = ticker.get("last", 0)

                # Check if alert should trigger
                should_trigger = False
                if condition == "above" and current_price >= target_price:
                    should_trigger = True
                elif condition == "below" and current_price <= target_price:
                    should_trigger = True

                if should_trigger:
                    await self.alert_repo.trigger_alert(alert["id"])
                    triggered_alerts.append({
                        "alert": alert,
                        "trigger_price": current_price,
                        "trigger_time": datetime.utcnow().isoformat(),
                    })
                    logger.info(f"Alert triggered: {symbol} {condition} {target_price}")

            except Exception as e:
                logger.error(f"Error checking alert {alert.get('id')}: {e}")

        return triggered_alerts

    async def start_alert_monitor(self, interval: int = 60):
        """Start the alert monitoring loop."""
        self._running = True
        logger.info("Starting alert monitor")

        while self._running:
            try:
                await self.check_alerts()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in alert monitor: {e}")
                await asyncio.sleep(10)

    def stop_alert_monitor(self):
        """Stop the alert monitor."""
        self._running = False
        logger.info("Stopping alert monitor")

    def format_alert_message(self, triggered_alert: Dict, language: str = "en") -> str:
        """Format an alert notification message."""
        alert = triggered_alert.get("alert", {})
        symbol = alert.get("symbol", "")
        target = alert.get("target_price", 0)
        condition = alert.get("condition_type", "")
        alert_type = alert.get("alert_type", "price")
        trigger_price = triggered_alert.get("trigger_price", 0)

        condition_emoji = "📈" if condition == "above" else "📉"
        alert_emoji = {
            "price": "🔔",
            "take_profit": "🎯",
            "stop_loss": "🛑",
        }.get(alert_type, "🔔")

        if language == "si":
            message = "\n".join([
                f"{alert_emoji} **මිල Alert!**",
                "",
                f"**{symbol}**",
                f"{condition_emoji} ඉලක්ම: {target:,.4f}",
                f"💰 වත්මන් මිල: {trigger_price:,.4f}",
                "",
                "_Alert එක trigger විය!_",
            ])
        else:
            message = "\n".join([
                f"{alert_emoji} **PRICE ALERT TRIGGERED!**",
                "",
                f"**{symbol}**",
                f"{condition_emoji} Target: `{target:,.4f}`",
                f"💰 Current: `{trigger_price:,.4f}`",
                "",
                "_Your alert has been triggered!_",
            ])

        return message


class MarketOpenAlertService:
    """Service for market session alerts."""

    MARKET_SESSIONS = {
        "sydney": {"open": "21:00", "close": "06:00"},
        "tokyo": {"open": "23:00", "close": "08:00"},
        "london": {"open": "07:00", "close": "16:00"},
        "new_york": {"open": "12:00", "close": "21:00"},
    }

    @classmethod
    def get_active_sessions(cls) -> List[str]:
        """Get currently active market sessions."""
        utc_now = datetime.utcnow()
        current_hour = utc_now.strftime("%H:%M")
        current_mins = int(utc_now.hour) * 60 + int(utc_now.minute)

        active = []
        for session, times in cls.MARKET_SESSIONS.items():
            open_time = times["open"]
            close_time = times["close"]

            open_mins = int(open_time.split(":")[0]) * 60 + int(open_time.split(":")[1])
            close_mins = int(close_time.split(":")[0]) * 60 + int(close_time.split(":")[1])

            if open_mins > close_mins:  # Session spans midnight
                if current_mins >= open_mins or current_mins < close_mins:
                    active.append(session.capitalize())
            else:
                if open_mins <= current_mins < close_mins:
                    active.append(session.capitalize())

        return active

    @classmethod
    def get_next_session(cls) -> Dict:
        """Get the next market session to open."""
        utc_now = datetime.utcnow()
        current_mins = int(utc_now.hour) * 60 + int(utc_now.minute)

        next_session = None
        next_time = None

        for session, times in cls.MARKET_SESSIONS.items():
            open_time = times["open"]
            open_mins = int(open_time.split(":")[0]) * 60 + int(open_time.split(":")[1])

            if open_mins > current_mins:
                mins_until = open_mins - current_mins
                if next_session is None or mins_until < next_time:
                    next_session = session
                    next_time = mins_until

        if next_session is None:
            # Find earliest session tomorrow
            for session, times in cls.MARKET_SESSIONS.items():
                open_time = times["open"]
                open_mins = int(open_time.split(":")[0]) * 60 + int(open_time.split(":")[1])
                mins_until = (24 * 60 - current_mins) + open_mins
                if next_session is None or mins_until < next_time:
                    next_session = session
                    next_time = mins_until

        return {
            "session": next_session.capitalize() if next_session else None,
            "minutes_until": next_time,
        }

    def format_session_status(self, language: str = "en") -> str:
        """Format market session status message."""
        active = self.get_active_sessions()
        next_sess = self.get_next_session()

        if language == "si":
            lines = [
                "🕒 **Market Sessions**",
                "",
                f"සක්‍රීය: {', '.join(active) if active else 'කිසිවක් නැත'}",
                "",
                f"ඊළඟ: {next_sess['session']} ({next_sess['minutes_until'] // 60}h {next_sess['minutes_until'] % 60}m තුළ)",
            ]
        else:
            lines = [
                "🕒 **Market Sessions**",
                "",
                f"Active: {', '.join(active) if active else 'None'}",
                "",
                f"Next: {next_sess['session']} (in {next_sess['minutes_until'] // 60}h {next_sess['minutes_until'] % 60}m)",
            ]

        return "\n".join(lines)
