"""
Automatic messaging service for scheduled broadcasts.
Handles good morning/night messages, market updates, and daily content.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AutoMessagingService:
    """Service for automatic scheduled messages to channels and groups."""

    def __init__(self, db, notification_service):
        self.db = db
        self.notification = notification_service
        self._running = False
        self._tasks: List[asyncio.Task] = []

        # Default message templates
        self.morning_messages = [
            "🌅 **Good Morning Traders!**\n\n"
            "Rise and grind! The markets are waking up and opportunities await.\n\n"
            "☕ Grab your coffee and let's make today profitable!\n\n"
            "_Have a great trading day!_",

            "☀️ **Good Morning!** ☀️\n\n"
            "New day, new opportunities!\n"
            "Markets are ready, are you?\n\n"
            "Let's catch some pips today! 📈\n\n"
            "_Stay focused, stay profitable!_",

            "🌅 **Rise and Shine!**\n\n"
            "The trading day begins!\n"
            "Remember: Patience and discipline are your best tools.\n\n"
            "Let's make today count! 💪",
        ]

        self.night_messages = [
            "🌙 **Good Night Traders!**\n\n"
            "Time to rest and recharge.\n\n"
            "Today's trades are done, tomorrow brings new opportunities.\n\n"
            "_Sweet dreams and see you tomorrow!_",

            "🌃 **Trading Day Wrap!**\n\n"
            "Markets are closing down.\n"
            "Take a break, review your trades, and prepare for tomorrow.\n\n"
            "Rest well! 😴",

            "🌙 **Good Night!**\n\n"
            "End your day with a smile.\n"
            "Win or learn - both are progress.\n\n"
            "_See you bright and early!_",
        ]

        self.motivational_messages = [
            "💪 **Motivation of the Day**\n\n"
            "\"The stock market is filled with individuals who know the price of everything, but the value of nothing.\"\n\n"
            "_- Philip Fisher_\n\n"
            "Focus on value, not just price!",

            "🎯 **Trading Wisdom**\n\n"
            "\"The goal of a successful trader is to make the best trades. Money is secondary.\"\n\n"
            "_- Alexander Elder_\n\n"
            "Master your craft, profits will follow!",

            "📚 **Daily Reminder**\n\n"
            "\"Risk comes from not knowing what you're doing.\"\n\n"
            "_- Warren Buffett_\n\n"
            "Always do your research before entering a trade!",

            "🔥 **Trading Tip**\n\n"
            "\"It's not whether you're right or wrong that's important, but how much money you make when you're right and how much you lose when you're wrong.\"\n\n"
            "_- George Soros_\n\n"
            "Risk management is key!",
        ]

        self.market_open_messages = {
            "sydney": "🇦🇺 **Sydney Session Open!**\n\n"
                     "The first major session of the day begins.\n"
                     "AUD and NZD pairs may see increased activity.\n\n"
                     "_Happy Trading!_",

            "tokyo": "🇯🇵 **Tokyo Session Open!**\n\n"
                   "Asian markets are in full swing.\n"
                   "JPY crosses and Asian pairs are active.\n\n"
                   "_Trade wisely!_",

            "london": "🇬🇧 **London Session Open!**\n\n"
                     "The most liquid session begins!\n"
                     "EUR and GBP pairs take center stage.\n\n"
                     "_High volatility expected!_",

            "new_york": "🇺🇸 **New York Session Open!**\n\n"
                       "The Big Apple wakes up!\n"
                       "Maximum liquidity and volatility.\n\n"
                       "_Catch the moves!_",
        }

        self.market_close_messages = {
            "sydney": "🇦🇺 **Sydney Session Closing**\n\n"
                     "Sydney markets wrapping up.\n"
                     "Tokyo takes over soon.\n\n"
                     "_See you tomorrow!_",

            "tokyo": "🇯🇵 **Tokyo Session Closing**\n\n"
                   "Asian session ending.\n"
                   "London is next!\n\n"
                   "_Prepare for the handover!_",

            "london": "🇬🇧 **London Session Closing**\n\n"
                     "European markets signing off.\n"
                     "New York takes the lead.\n\n"
                     "_Keep an eye on your positions!_",

            "new_york": "🇺🇸 **New York Session Closing**\n\n"
                       "Trading day ends for most markets.\n"
                       "Time to review your trades.\n\n"
                       "_See you tomorrow!_",
        }

    async def start(self):
        """Start all automatic messaging tasks."""
        self._running = True

        # Schedule all auto message tasks
        tasks = [
            self._schedule_good_morning(),
            self._schedule_good_night(),
            self._schedule_daily_motivation(),
            self._schedule_market_open_notifications(),
            self._schedule_market_close_notifications(),
            self._schedule_daily_analysis(),
        ]

        for task in tasks:
            t = asyncio.create_task(task)
            self._tasks.append(t)

        logger.info("Auto messaging service started")

    async def stop(self):
        """Stop all automatic messaging tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        logger.info("Auto messaging service stopped")

    async def _schedule_good_morning(self):
        """Send good morning message at 6 AM UTC."""
        while self._running:
            try:
                now = datetime.utcnow()
                # Calculate time until 6 AM UTC
                target = now.replace(hour=6, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)

                wait_seconds = (target - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                # Send good morning message
                message = random.choice(self.morning_messages)
                await self._broadcast_to_all_channels(message)
                logger.info("Sent good morning message")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in good morning scheduler: {e}")
                await asyncio.sleep(3600)

    async def _schedule_good_night(self):
        """Send good night message at 10 PM UTC."""
        while self._running:
            try:
                now = datetime.utcnow()
                target = now.replace(hour=22, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)

                wait_seconds = (target - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                message = random.choice(self.night_messages)
                await self._broadcast_to_all_channels(message)
                logger.info("Sent good night message")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in good night scheduler: {e}")
                await asyncio.sleep(3600)

    async def _schedule_daily_motivation(self):
        """Send motivational message at 9 AM UTC."""
        while self._running:
            try:
                now = datetime.utcnow()
                target = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)

                wait_seconds = (target - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                message = random.choice(self.motivational_messages)
                await self._broadcast_to_all_channels(message)
                logger.info("Sent daily motivation message")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in motivation scheduler: {e}")
                await asyncio.sleep(3600)

    async def _schedule_market_open_notifications(self):
        """Send market open notifications."""
        session_times = {
            "sydney": 21,   # 21:00 UTC
            "tokyo": 23,    # 23:00 UTC
            "london": 7,    # 07:00 UTC
            "new_york": 12, # 12:00 UTC
        }

        while self._running:
            try:
                now = datetime.utcnow()
                current_hour = now.hour

                # Check each session
                for session, open_hour in session_times.items():
                    if current_hour == open_hour and now.minute < 5:
                        message = self.market_open_messages.get(session, "")
                        if message:
                            await self._broadcast_to_all_channels(message)
                            logger.info(f"Sent {session} session open notification")

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in market open scheduler: {e}")
                await asyncio.sleep(300)

    async def _schedule_market_close_notifications(self):
        """Send market close notifications."""
        session_close_times = {
            "sydney": 6,    # 06:00 UTC
            "tokyo": 8,     # 08:00 UTC
            "london": 16,   # 16:00 UTC
            "new_york": 21, # 21:00 UTC
        }

        while self._running:
            try:
                now = datetime.utcnow()
                current_hour = now.hour

                for session, close_hour in session_close_times.items():
                    if current_hour == close_hour and now.minute < 5:
                        message = self.market_close_messages.get(session, "")
                        if message:
                            await self._broadcast_to_all_channels(message)
                            logger.info(f"Sent {session} session close notification")

                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in market close scheduler: {e}")
                await asyncio.sleep(300)

    async def _schedule_daily_analysis(self):
        """Send daily market analysis at 8 AM UTC."""
        while self._running:
            try:
                now = datetime.utcnow()
                target = now.replace(hour=8, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)

                wait_seconds = (target - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                # Generate daily analysis
                analysis = await self._generate_daily_analysis()
                if analysis:
                    await self._broadcast_to_all_channels(analysis)
                    logger.info("Sent daily analysis")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily analysis scheduler: {e}")
                await asyncio.sleep(3600)

    async def _generate_daily_analysis(self) -> str:
        """Generate daily market analysis."""
        try:
            from market import ExchangeManager, MarketAnalysis

            exchange = ExchangeManager()
            await exchange.initialize()

            analysis = MarketAnalysis(exchange)

            # Get BTC and ETH analysis
            btc_analysis = await analysis.analyze("BTC/USDT", "1d")
            eth_analysis = await analysis.analyze("ETH/USDT", "1d")

            await exchange.close()

            lines = [
                "📊 **Daily Market Analysis**",
                f"📅 {datetime.utcnow().strftime('%A, %B %d, %Y')}",
                "",
                "📈 **BTC/USDT Overview:**",
            ]

            if btc_analysis.get("summary"):
                summary = btc_analysis["summary"]
                lines.append(f"  • Price: ${summary.get('price', 0):,.2f}")
                lines.append(f"  • Trend: {summary.get('trend', 'Neutral').upper()}")
                lines.append(f"  • Sentiment: {summary.get('sentiment', 'Neutral')}")

            lines.extend([
                "",
                "📈 **ETH/USDT Overview:**",
            ])

            if eth_analysis.get("summary"):
                summary = eth_analysis["summary"]
                lines.append(f"  • Price: ${summary.get('price', 0):,.2f}")
                lines.append(f"  • Trend: {summary.get('trend', 'Neutral').upper()}")
                lines.append(f"  • Sentiment: {summary.get('sentiment', 'Neutral')}")

            lines.extend([
                "",
                "_⚠️ Not financial advice. DYOR!_",
            ])

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error generating daily analysis: {e}")
            return None

    async def _broadcast_to_all_channels(self, message: str):
        """Broadcast message to all configured channels and groups."""
        targets = []

        if settings.CHANNEL_ID:
            targets.append(settings.CHANNEL_ID)
        if settings.GROUP_ID:
            targets.append(settings.GROUP_ID)
        if settings.PREMIUM_CHANNEL_ID:
            targets.append(settings.PREMIUM_CHANNEL_ID)

        # Get additional channels from database
        try:
            additional_channels = await self.db.get_setting("additional_channels")
            if additional_channels:
                for ch in additional_channels.split(","):
                    if ch.strip():
                        targets.append(ch.strip())
        except Exception:
            pass

        for target in targets:
            try:
                await self.notification.send_to_user(target, message)
            except Exception as e:
                logger.warning(f"Failed to send to {target}: {e}")

    async def send_trading_plan(self) -> str:
        """Generate daily trading plan."""
        from utils.helpers import get_market_session

        active_sessions = get_market_session()
        next_session = "London" if "London" not in active_sessions else "New York"

        plan = "\n".join([
            "📋 **Daily Trading Plan**",
            f"📅 {datetime.utcnow().strftime('%A, %B %d, %Y')}",
            "",
            "🎯 **Today's Focus:**",
            "• Monitor key support/resistance levels",
            "• Watch for breakouts on major pairs",
            "• Follow risk management rules strictly",
            "",
            f"🌐 **Active Sessions:** {', '.join(active_sessions) if active_sessions else 'None'}",
            f"⏰ **Next Session:** {next_session}",
            "",
            "**Remember:**",
            "✅ Stick to your strategy",
            "✅ Use proper stop losses",
            "✅ Take profits at key levels",
            "❌ Don't overtrade",
            "❌ Don't chase the market",
            "",
            "_Have a profitable day!_",
        ])

        return plan

    def get_status(self) -> Dict:
        """Get service status."""
        return {
            "running": self._running,
            "active_tasks": len(self._tasks),
            "scheduled_messages": [
                "good_morning (06:00 UTC)",
                "good_night (22:00 UTC)",
                "daily_motivation (09:00 UTC)",
                "market_open/close (varies)",
                "daily_analysis (08:00 UTC)",
            ],
        }
