"""
Logging middleware for request tracking.
"""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Any, Dict
from datetime import datetime
import time

from utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging all bot interactions."""

    def __init__(self, log_sensitive: bool = False):
        """
        Initialize logging middleware.

        Args:
            log_sensitive: Whether to log sensitive data (message content)
        """
        self.log_sensitive = log_sensitive

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        user_id = user.id if user else "Unknown"
        username = user.username if user else "Unknown"

        start_time = time.time()

        # Log incoming request
        if isinstance(event, Message):
            log_data = {
                "type": "message",
                "user_id": user_id,
                "username": username,
                "text": event.text[:100] if self.log_sensitive and event.text else "[HIDDEN]",
                "chat_id": event.chat.id,
            }
            logger.info(f"Received message from {user_id} (@{username})")
        elif isinstance(event, CallbackQuery):
            log_data = {
                "type": "callback",
                "user_id": user_id,
                "username": username,
                "data": event.data if self.log_sensitive else "[HIDDEN]",
                "message_id": event.message.message_id if event.message else None,
            }
            logger.info(f"Received callback from {user_id} (@{username}): {event.data}")

        # Execute handler
        try:
            result = await handler(event, data)

            # Log successful execution
            duration = time.time() - start_time
            logger.debug(f"Request processed in {duration:.3f}s for user {user_id}")

            return result

        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Error processing request from {user_id}: {e}\n"
                f"Duration: {duration:.3f}s",
                exc_info=True
            )
            raise
