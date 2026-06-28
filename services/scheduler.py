"""
Scheduler service for automated tasks.
"""
import asyncio
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta
import schedule
from threading import Thread

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """Schedule and run automated tasks."""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._loop: Optional[asyncio.BaseEventLoop] = None

    def add_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        start_immediately: bool = False,
    ) -> bool:
        """Add a scheduled task."""
        if name in self._tasks:
            logger.warning(f"Task {name} already exists")
            return False

        async def task_wrapper():
            if start_immediately:
                try:
                    await func()
                except Exception as e:
                    logger.error(f"Error in task {name}: {e}")

            while self._running:
                try:
                    await asyncio.sleep(interval_seconds)
                    await func()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in scheduled task {name}: {e}")

        self._tasks[name] = task_wrapper
        logger.info(f"Added scheduled task: {name} (every {interval_seconds}s)")
        return True

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name not in self._tasks:
            return False

        task = asyncio.all_tasks(self._loop) if self._loop else []
        for t in task:
            if hasattr(t, '_name') and t._name == name:
                t.cancel()
                break

        del self._tasks[name]
        logger.info(f"Removed task: {name}")
        return True

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._loop = asyncio.get_event_loop()

        # Start all tasks
        for name, task_coro in self._tasks.items():
            asyncio.create_task(task_coro())
            logger.debug(f"Started task: {name}")

        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("Scheduler stopped")

    def get_tasks(self) -> List[str]:
        """Get list of scheduled tasks."""
        return list(self._tasks.keys())


class AutoSignalScheduler:
    """Scheduler for automatic signal generation."""

    def __init__(self, signal_generator, signal_manager, notification_service):
        self.signal_generator = signal_generator
        self.signal_manager = signal_manager
        self.notification_service = notification_service
        self._last_signal_time: Optional[datetime] = None
        self._daily_signal_count = 0
        self._last_reset: Optional[datetime] = None

    async def generate_and_broadcast_signals(self, symbols: List[str], timeframe: str = "1h"):
        """Generate signals and broadcast to users."""
        # Check if we've hit daily limit
        now = datetime.utcnow()
        if self._last_reset is None or self._last_reset.date() != now.date():
            self._daily_signal_count = 0
            self._last_reset = now

        if self._daily_signal_count >= settings.MAX_DAILY_SIGNALS:
            logger.debug("Daily signal limit reached")
            return []

        try:
            # Generate signals
            signals = await self.signal_generator.generate_batch_signals(
                symbols=symbols,
                timeframe=timeframe,
                max_signals=3,
            )

            if not signals:
                return []

            saved_signals = []
            for signal in signals:
                # Save to database
                saved = await self.signal_manager.save_signal(signal, is_auto=True)
                if saved:
                    saved_signals.append(saved)
                    self._daily_signal_count += 1

                    # Format message
                    message = self.signal_manager.format_signal_message(saved)

                    # Send to channels and groups
                    from config import settings
                    if settings.CHANNEL_ID:
                        await self.notification_service.send_to_user(settings.CHANNEL_ID, message)
                    if settings.GROUP_ID:
                        await self.notification_service.send_to_user(settings.GROUP_ID, message)
                    if settings.PREMIUM_CHANNEL_ID:
                        await self.notification_service.send_to_user(settings.PREMIUM_CHANNEL_ID, message)

                    self._last_signal_time = now

            logger.info(f"Generated and broadcast {len(saved_signals)} signals")
            return saved_signals

        except Exception as e:
            logger.error(f"Error in auto signal scheduler: {e}")
            return []


class AlertScheduler:
    """Scheduler for checking price alerts."""

    def __init__(self, alert_service, notification_service):
        self.alert_service = alert_service
        self.notification_service = notification_service

    async def check_and_notify_alerts(self):
        """Check alerts and send notifications."""
        try:
            triggered_alerts = await self.alert_service.check_alerts()

            for alert_data in triggered_alerts:
                alert = alert_data.get("alert", {})
                user_id = alert.get("user_id")

                if user_id:
                    message = self.alert_service.format_alert_message(alert_data)
                    await self.notification_service.send_alert_notification(user_id, message)

            logger.debug(f"Checked alerts: {len(triggered_alerts)} triggered")

        except Exception as e:
            logger.error(f"Error in alert scheduler: {e}")


class StatisticsScheduler:
    """Scheduler for updating statistics."""

    def __init__(self, db, user_repo):
        self.db = db
        self.user_repo = user_repo

    async def update_daily_stats(self):
        """Update daily statistics."""
        try:
            # Get user counts
            total_users = await self.user_repo.count_users()
            active_users = await self.user_repo.count_active_users()
            premium_users = len(await self.user_repo.get_premium_users())

            # Update statistics
            today = datetime.utcnow().strftime("%Y-%m-%d")
            await self.db.increment_stat("total_users", total_users)
            await self.db.increment_stat("premium_users", premium_users)

            logger.debug(f"Updated statistics: {total_users} users, {active_users} active")

        except Exception as e:
            logger.error(f"Error updating statistics: {e}")


def create_scheduler():
    """Factory function to create scheduler."""
    return SchedulerService()

