"""
Notification service for broadcasts and user notifications.
"""
from typing import List, Dict, Optional
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
import asyncio

from database import DatabaseManager, UserRepository, StatisticsRepository
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Handle notifications and broadcasts."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.user_repo = UserRepository(db)
        self.stats_repo = StatisticsRepository(db)
        self.bot: Optional[Bot] = None

    def set_bot(self, bot: Bot):
        """Set the bot instance."""
        self.bot = bot

    async def send_to_user(
        self,
        user_id: int,
        message: str,
        keyboard: InlineKeyboardMarkup = None,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Send message to a single user."""
        if not self.bot:
            logger.error("Bot not configured")
            return False

        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode=parse_mode,
            )
            await self.stats_repo.increment_stat("messages_sent")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            return False

    async def broadcast(
        self,
        message: str,
        filter_premium: bool = False,
        filter_active: bool = True,
        limit: Optional[int] = None,
    ) -> Dict:
        """Broadcast message to multiple users."""
        if not self.bot:
            logger.error("Bot not configured")
            return {"success": 0, "failed": 0}

        try:
            if filter_premium:
                users = await self.user_repo.get_premium_users()
            elif filter_active:
                users = await self.user_repo.get_active_users()
            else:
                users = await self.user_repo.get_all_users()

            if limit:
                users = users[:limit]

            success = 0
            failed = 0

            for user in users:
                try:
                    await self.bot.send_message(
                        chat_id=user["telegram_id"],
                        text=message,
                        parse_mode="Markdown",
                    )
                    success += 1
                    await asyncio.sleep(0.05)  # Rate limit
                except Exception as e:
                    logger.warning(f"Failed to send to {user['telegram_id']}: {e}")
                    failed += 1

            await self.stats_repo.increment_stat("broadcasts_sent", success)
            logger.info(f"Broadcast completed: {success} success, {failed} failed")

            return {"success": success, "failed": failed}

        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            return {"success": 0, "failed": 0}

    async def send_signal_notification(
        self,
        signal: Dict,
        premium_only: bool = False,
    ) -> Dict:
        """Send signal notification to users."""
        if not self.bot:
            return {"success": 0, "failed": 0}

        try:
            # Get users
            if premium_only:
                users = await self.user_repo.get_premium_users()
            else:
                users = await self.user_repo.get_active_users()

            success = 0
            failed = 0

            for user in users:
                try:
                    await self.bot.send_message(
                        chat_id=user["telegram_id"],
                        text=signal,
                        parse_mode="Markdown",
                    )
                    success += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.warning(f"Failed to send signal to {user['telegram_id']}: {e}")
                    failed += 1

            logger.info(f"Signal notification sent: {success} success, {failed} failed")
            return {"success": success, "failed": failed}

        except Exception as e:
            logger.error(f"Signal notification error: {e}")
            return {"success": 0, "failed": 0}

    async def send_admin_notification(
        self,
        message: str,
        keyboard: InlineKeyboardMarkup = None,
    ) -> bool:
        """Send notification to all admins."""
        if not self.bot:
            return False

        admin_ids = settings.ADMIN_IDS + [settings.SUPER_ADMIN_ID]

        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Failed to send admin notification to {admin_id}: {e}")

        return True

    async def send_alert_notification(
        self,
        user_id: int,
        alert_message: str,
    ) -> bool:
        """Send alert notification to user."""
        return await self.send_to_user(user_id, alert_message)

    async def send_welcome_message(self, user_id: int, first_name: str, language: str = "en") -> bool:
        """Send welcome message to new user."""
        if language == "si":
            message = "\n".join([
                f"👋 **ආයුබෝවන් {first_name}!**",
                "",
                "AI Trading Assistant වෙත සාදරයෙන් පිළිගනිමු! 🚀",
                "",
                "මෙම bot එක මගින්:",
                "• ස්වයංක්‍රීය Trading Signals",
                "• Technical Analysis",
                "• Market Charts",
                "• Price Alerts",
                "",
                "/menu භාවිතා කර ප්‍රධාන මෙනුව බලන්න.",
            ])
        else:
            message = "\n".join([
                f"👋 **Welcome {first_name}!**",
                "",
                "Welcome to AI Trading Assistant! 🚀",
                "",
                "This bot provides:",
                "• Automated Trading Signals",
                "• Technical Analysis",
                "• Market Charts",
                "• Price Alerts",
                "",
                "Use /menu to access the main menu.",
            ])

        return await self.send_to_user(user_id, message)

    async def broadcast_to_channel(
        self,
        channel_id: str,
        message: str,
        keyboard: InlineKeyboardMarkup = None,
    ) -> bool:
        """Broadcast message to a channel."""
        if not self.bot:
            return False

        try:
            await self.bot.send_message(
                chat_id=channel_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send to channel {channel_id}: {e}")
            return False
