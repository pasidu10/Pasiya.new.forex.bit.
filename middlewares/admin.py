"""
Admin middleware for admin-only commands.
"""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Any, Dict

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AdminMiddleware(BaseMiddleware):
    """Middleware to check admin privileges."""

    def __init__(self):
        self.admin_ids = set(settings.ADMIN_IDS)
        self.super_admin_id = settings.SUPER_ADMIN_ID

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        user_id = user.id if user else None

        # Check if user is in admin list or is super admin
        is_admin = user_id in self.admin_ids or user_id == self.super_admin_id

        # Also check database admin status if available
        if not is_admin and data.get("user"):
            is_admin = data["user"].get("is_admin", False)

        data["is_admin"] = is_admin
        data["is_super_admin"] = user_id == self.super_admin_id

        if not is_admin:
            if isinstance(event, CallbackQuery):
                await event.answer("This action is restricted to admins only.", show_alert=True)
            else:
                await event.answer("⚠️ This command is restricted to admins only.")

            logger.warning(f"Non-admin user {user_id} attempted admin action")
            return None

        return await handler(event, data)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        return user_id in self.admin_ids or user_id == self.super_admin_id

    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin."""
        return user_id == self.super_admin_id

    async def check_channel_admin(self, bot, user_id: int, channel_id: str) -> bool:
        """Check if user is admin of a specific channel."""
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            return member.status in ["administrator", "creator"]
        except Exception as e:
            logger.error(f"Failed to check channel admin status: {e}")
            return False
