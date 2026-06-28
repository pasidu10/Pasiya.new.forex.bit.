#!/usr/bin/env python3
"""
Telegram AI Trading Assistant
============================
Enterprise-grade trading bot with technical analysis, signals, and market insights.

Author: AI Trading Assistant Team
Version: 1.0.0
License: MIT
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import settings, ensure_directories
from utils.logger import setup_logger, get_logger

# Initialize logger
logger = get_logger(__name__)


async def main():
    """Main entry point for the bot."""
    # Ensure directories exist
    ensure_directories()

    # Setup logger
    setup_logger(settings.LOG_LEVEL, settings.LOG_FILE)
    logger.info("Starting Telegram AI Trading Assistant...")

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Initialize database (Supabase or SQLite fallback)
    from database.adapter import db_adapter
    await db_adapter.connect()
    db = db_adapter
    logger.info(f"Database initialized (Supabase: {db_adapter.is_supabase})")

    # Initialize exchange manager
    from market import ExchangeManager
    exchange_manager = ExchangeManager()
    await exchange_manager.initialize()
    logger.info("Exchange manager initialized")

    # Register middlewares
    from middlewares import (
        AuthMiddleware,
        RateLimitMiddleware,
        LoggingMiddleware,
        AdminMiddleware,
    )

    db_manager = db

    # Auth middleware
    auth_middleware = AuthMiddleware(db_manager)
    dp.message.middleware.register(auth_middleware)
    dp.callback_query.middleware.register(auth_middleware)

    # Rate limit middleware
    rate_limit_middleware = RateLimitMiddleware(
        rate_limit=3,
        time_window=1,
        burst_limit=15,
        burst_window=60,
    )
    dp.message.middleware.register(rate_limit_middleware)

    # Logging middleware
    logging_middleware = LoggingMiddleware(log_sensitive=False)
    dp.message.middleware.register(logging_middleware)
    dp.callback_query.middleware.register(logging_middleware)

    logger.info("Middlewares registered")

    # Register handlers
    from handlers.commands import router as commands_router
    from handlers.callbacks import router as callbacks_router
    from handlers.admin import router as admin_router

    dp.include_router(commands_router)
    dp.include_router(callbacks_router)
    dp.include_router(admin_router)

    logger.info("Handlers registered")

    # Initialize services
    from signals import SignalGenerator, SignalManager
    from services import (
        AlertService, NotificationService, SchedulerService,
        AutoSignalScheduler, AlertScheduler,
        AutoMessagingService, SignalTracker, PerformanceTracker,
        PortfolioManager, TradingJournal
    )

    signal_generator = SignalGenerator(exchange_manager)
    signal_manager = SignalManager(db_manager)
    alert_service = AlertService(db_manager, exchange_manager)
    notification_service = NotificationService(db_manager)
    notification_service.set_bot(bot)
    scheduler = SchedulerService()

    # Auto messaging service (good morning/night, market updates)
    auto_messaging = AutoMessagingService(db_manager, notification_service)

    # Signal tracker for SL/TP notifications
    signal_tracker = SignalTracker(db_manager, exchange_manager, notification_service)

    # Performance tracker
    performance_tracker = PerformanceTracker(db_manager)

    # Portfolio manager
    portfolio_manager = PortfolioManager(db_manager)

    # Trading journal
    trading_journal = TradingJournal(db_manager)

    # Set bot reference in auth middleware
    auth_middleware.bot = bot

    logger.info("Services initialized")

    # Setup scheduled tasks
    if settings.ENABLE_AUTO_SIGNALS:
        auto_signal_scheduler = AutoSignalScheduler(
            signal_generator, signal_manager, notification_service
        )

        # Add auto signal task
        scheduler.add_task(
            name="auto_signals",
            func=lambda: auto_signal_scheduler.generate_and_broadcast_signals(
                symbols=["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"],
                timeframe=settings.DEFAULT_TIMEFRAME,
            ),
            interval_seconds=settings.AUTO_SIGNAL_INTERVAL,
            start_immediately=False,
        )

    if settings.ENABLE_PRICE_ALERTS:
        alert_scheduler = AlertScheduler(alert_service, notification_service)

        scheduler.add_task(
            name="check_alerts",
            func=alert_scheduler.check_and_notify_alerts,
            interval_seconds=settings.PRICE_CHECK_INTERVAL,
            start_immediately=True,
        )

    logger.info("Scheduled tasks configured")

    # Start auto messaging service
    await auto_messaging.start()
    logger.info("Auto messaging service started")

    # Start signal tracker
    await signal_tracker.start()
    logger.info("Signal tracker started")

    # Set bot commands
    commands = [
        BotCommand(command="start", description="Initialize the bot"),
        BotCommand(command="help", description="Show help information"),
        BotCommand(command="menu", description="Open main menu"),
        BotCommand(command="signal", description="Get current signals"),
        BotCommand(command="market", description="Market information"),
        BotCommand(command="chart", description="Generate chart"),
        BotCommand(command="price", description="Get price"),
        BotCommand(command="alerts", description="Manage alerts"),
        BotCommand(command="settings", description="Bot settings"),
        BotCommand(command="profile", description="Your profile"),
        BotCommand(command="vip", description="Premium membership"),
        BotCommand(command="watchlist", description="Manage watchlist"),
        BotCommand(command="portfolio", description="Track positions"),
        BotCommand(command="report", description="Performance reports"),
        BotCommand(command="journal", description="Trading journal"),
        BotCommand(command="admin", description="Admin panel"),
    ]

    await bot.set_my_commands(commands)

    # Send startup notification to admins
    startup_message = (
        "🚀 **Bot Started Successfully!**\n\n"
        f"Environment: Production\n"
        f"Version: 1.0.0\n"
        f"Auto Signals: {'Enabled' if settings.ENABLE_AUTO_SIGNALS else 'Disabled'}\n"
        f"Price Alerts: {'Enabled' if settings.ENABLE_PRICE_ALERTS else 'Disabled'}"
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, startup_message)
        except Exception as e:
            logger.warning(f"Failed to send startup notification to admin {admin_id}: {e}")

    # Start scheduler
    await scheduler.start()

    # Start polling
    logger.info("Starting polling...")

    try:
        # Pass db and services to handlers through context
        dp["db"] = db_manager
        dp["exchange_manager"] = exchange_manager
        dp["bot"] = bot
        dp["signal_tracker"] = signal_tracker
        dp["performance_tracker"] = performance_tracker
        dp["portfolio_manager"] = portfolio_manager

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=False,
        )
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        # Cleanup
        logger.info("Shutting down...")
        scheduler.stop()
        await auto_messaging.stop()
        await signal_tracker.stop()
        await exchange_manager.close()
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped")


async def run_with_webhook():
    """Run bot with webhook (for production)."""
    ensure_directories()
    setup_logger(settings.LOG_LEVEL, settings.LOG_FILE)
    logger.info("Starting bot with webhook...")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Initialize database
    from database import DatabaseManager
    db = DatabaseManager(settings.DATABASE_PATH)
    await db.connect()

    # Setup middlewares and handlers
    from middlewares import AuthMiddleware, LoggingMiddleware
    auth_middleware = AuthMiddleware(db)
    dp.message.middleware.register(auth_middleware)
    dp.callback_query.middleware.register(auth_middleware)

    from handlers.commands import router as commands_router
    from handlers.callbacks import router as callbacks_router
    from handlers.admin import router as admin_router

    dp.include_router(commands_router)
    dp.include_router(callbacks_router)
    dp.include_router(admin_router)

    # Set webhook handler
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook", handle_get=True)

    # Setup webhook
    webhook_url = os.getenv("WEBHOOK_URL", "")
    if webhook_url:
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set: {webhook_url}")

    dp["db"] = db
    dp["bot"] = bot

    # Run web server
    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, host="0.0.0.0", port=port)


def entrypoint():
    """Application entrypoint."""
    try:
        # Check if running with webhook
        if os.getenv("WEBHOOK_URL"):
            asyncio.run(run_with_webhook())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    entrypoint()
