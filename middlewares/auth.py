"""
Authentication and authorization middleware.
"""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Any, Dict
from datetime import datetime, timedelta
import asyncio

from config import settings
from database import DatabaseManager, UserRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware for user authentication and authorization."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.user_repo = UserRepository(db)
        self._cache: Dict[int, dict] = {}
        self._cache_ttl = 300  # 5 minutes

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Get user from event
        user = event.from_user
        if not user:
            return await handler(event, data)

        telegram_id = user.id

        # Check cache
        cached_user = self._cache.get(telegram_id)
        if cached_user and cached_user.get("expires") > datetime.utcnow():
            user_data = cached_user.get("data")
        else:
            # Get or create user from database
            user_data = await self.user_repo.get_user(telegram_id)

            if not user_data and user:
                # Create new user
                user_data = await self.user_repo.create_user(
                    telegram_id=telegram_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language=settings.DEFAULT_LANGUAGE,
                )
                logger.info(f"New user created: {telegram_id}")

            # Update cache
            self._cache[telegram_id] = {
                "data": user_data,
                "expires": datetime.utcnow() + timedelta(seconds=self._cache_ttl)
            }

        # Check if user is banned
        if user_data and user_data.get("is_banned"):
            if isinstance(event, CallbackQuery):
                await event.answer("You are banned from using this bot.", show_alert=True)
            else:
                await event.answer("You are banned from using this bot.")
            logger.warning(f"Banned user attempted access: {telegram_id}")
            return None

        # Update last interaction
        await self.user_repo.update_last_interaction(telegram_id)

        # Add user data to context
        data["user"] = user_data
        data["is_admin"] = user_data.get("is_admin", False) if user_data else False
        data["is_premium"] = user_data.get("is_premium", False) if user_data else False
        data["user_language"] = user_data.get("language", settings.DEFAULT_LANGUAGE) if user_data else settings.DEFAULT_LANGUAGE

        return await handler(event, data)

    async def get_user(self, telegram_id: int) -> dict:
        """Get cached user data."""
        cached = self._cache.get(telegram_id)
        if cached and cached.get("expires") > datetime.utcnow():
            return cached.get("data")

        user = await self.user_repo.get_user(telegram_id)
        if user:
            self._cache[telegram_id] = {
                "data": user,
                "expires": datetime.utcnow() + timedelta(seconds=self._cache_ttl)
            }
        return user

    async def invalidate_cache(self, telegram_id: int):
        """Invalidate user cache."""
        if telegram_id in self._cache:
            del self._cache[telegram_id]

    async def refresh_user(self, telegram_id: int) -> dict:
        """Refresh user data from database."""
        user = await self.user_repo.get_user(telegram_id)
        if user:
            self._cache[telegram_id] = {
                "data": user,
                "expires": datetime.utcnow() + timedelta(seconds=self._cache_ttl)
            }
        return user
