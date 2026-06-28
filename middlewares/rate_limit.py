"""
Rate limiting middleware to prevent spam and abuse.
"""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Any, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting user actions."""

    def __init__(
        self,
        rate_limit: int = 3,
        time_window: int = 1,
        burst_limit: int = 10,
        burst_window: int = 60,
    ):
        """
        Initialize rate limiter.

        Args:
            rate_limit: Maximum messages per time_window seconds
            time_window: Time window in seconds for rate limiting
            burst_limit: Maximum messages per burst_window seconds
            burst_window: Time window in seconds for burst protection
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.burst_limit = burst_limit
        self.burst_window = burst_window

        # User request timestamps
        self._requests: Dict[int, list] = defaultdict(list)
        self._warnings: Dict[int, int] = defaultdict(int)
        self._muted: Dict[int, datetime] = {}

        # Admin users bypass rate limits
        self._admin_ids = set(settings.ADMIN_IDS)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        if not user:
            return await handler(event, data)

        user_id = user.id

        # Skip rate limiting for admins
        if user_id in self._admin_ids:
            return await handler(event, data)

        # Check if user is muted
        if await self._is_muted(user_id):
            return None

        now = datetime.utcnow()

        # Clean old requests
        self._clean_old_requests(user_id, now)

        # Check burst limit
        if len(self._requests[user_id]) >= self.burst_limit:
            await self._handle_rate_exceeded(event, user_id, "burst")
            return None

        # Check rate limit
        recent_requests = [
            r for r in self._requests[user_id]
            if now - r < timedelta(seconds=self.time_window)
        ]

        if len(recent_requests) >= self.rate_limit:
            await self._handle_rate_exceeded(event, user_id, "rate")
            return None

        # Record request
        self._requests[user_id].append(now)

        return await handler(event, data)

    def _clean_old_requests(self, user_id: int, now: datetime):
        """Remove old requests from tracking."""
        cutoff = now - timedelta(seconds=self.burst_window)
        self._requests[user_id] = [r for r in self._requests[user_id] if r > cutoff]

    async def _is_muted(self, user_id: int) -> bool:
        """Check if user is currently muted."""
        if user_id not in self._muted:
            return False

        mute_end = self._muted[user_id]
        if datetime.utcnow() > mute_end:
            del self._muted[user_id]
            return False

        return True

    async def _handle_rate_exceeded(self, event: Message | CallbackQuery, user_id: int, limit_type: str):
        """Handle rate limit exceeded."""
        self._warnings[user_id] += 1

        # Mute user for exceeding limits multiple times
        mute_duration = min(self._warnings[user_id] * 10, 300)  # Max 5 minutes

        if self._warnings[user_id] >= 3:
            self._muted[user_id] = datetime.utcnow() + timedelta(seconds=mute_duration)

        warning_message = "⚠️ Please slow down! You're sending requests too quickly."

        if self._warnings[user_id] >= 3:
            warning_message = f"⛔ You've been muted for {mute_duration} seconds due to excessive requests."

        try:
            if isinstance(event, CallbackQuery):
                await event.answer(warning_message, show_alert=True)
            else:
                await event.answer(warning_message)
        except Exception as e:
            logger.error(f"Failed to send rate limit warning: {e}")

        logger.warning(f"Rate limit exceeded for user {user_id}: {limit_type} (warnings: {self._warnings[user_id]})")

    def reset_user(self, user_id: int):
        """Reset rate limits for a user."""
        if user_id in self._requests:
            del self._requests[user_id]
        if user_id in self._warnings:
            del self._warnings[user_id]
        if user_id in self._muted:
            del self._muted[user_id]

    def get_user_stats(self, user_id: int) -> dict:
        """Get rate limit stats for a user."""
        now = datetime.utcnow()
        return {
            "requests": len(self._requests.get(user_id, [])),
            "warnings": self._warnings.get(user_id, 0),
            "is_muted": user_id in self._muted,
            "mute_ends": self._muted.get(user_id),
        }
