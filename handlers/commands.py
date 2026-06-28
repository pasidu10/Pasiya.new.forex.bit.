"""
Command handlers for Telegram bot.
"""
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from typing import Optional

from config import settings, MESSAGES
from keyboards.keyboards import (
    get_main_menu_keyboard,
    get_signal_keyboard,
    get_market_keyboard,
    get_timeframe_keyboard,
    get_language_keyboard,
    get_settings_keyboard,
    get_vip_keyboard,
    get_alert_keyboard,
    get_exchange_keyboard,
)
from database import UserRepository, SignalRepository, AlertRepository
from utils.logger import get_logger
from utils.helpers import get_time_ago, format_percentage, get_market_session
from utils.validators import validate_symbol

logger = get_logger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, user: dict, user_language: str):
    """Handle /start command."""
    lang = user_language or "en"
    welcome_msg = MESSAGES.get(lang, MESSAGES["en"]).get("welcome", "Welcome!")

    keyboard = get_main_menu_keyboard(lang)

    # Check if new user
    if user and user.get("created_at"):
        created_time = get_time_ago(user["created_at"]) if isinstance(user["created_at"], str) else "Just now"
        welcome_msg = MESSAGES.get(lang, MESSAGES["en"]).get("welcome", "Welcome!") + f"\n\n📅 Account created: {created_time}"

    await message.answer(welcome_msg, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message, user_language: str):
    """Handle /help command."""
    if user_language == "si":
        help_text = "\n".join([
            "📚 **උදව් මැදිරිය**",
            "",
            "**ප්‍රධාන විධාන:**",
            "/start - Bot එක ආරම්භ කරන්න",
            "/help - උදව් පෙන්වයි",
            "/menu - ප්‍රධාන මෙනුව",
            "/signal - වත්මන් signals",
            "/market - වෙළඳපොළ තොරතුරු",
            "/chart - Charts ලබා ගන්න",
            "/price - මිල තොරතුරු",
            "/news - වෙළඳපොළ ප්‍රවෘත්ති",
            "/alerts - මිල alerts",
            "/settings - සැකසුම්",
            "/profile - ඔබේ profile",
            "/vip - Premium සාමාජිකත්වය",
            "",
            "_වැඩි විස්තර /menu භාවිතා කරන්න_",
        ])
    else:
        help_text = "\n".join([
            "📚 **Help Center**",
            "",
            "**Main Commands:**",
            "/start - Initialize the bot",
            "/help - Show this help",
            "/menu - Main menu",
            "/signal - Get current signals",
            "/market - Market information",
            "/chart - Generate charts",
            "/price - Price information",
            "/news - Market news",
            "/alerts - Price alerts",
            "/settings - Bot settings",
            "/profile - Your profile",
            "/vip - Premium membership",
            "",
            "_Use /menu for full functionality_",
        ])

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("menu"))
async def cmd_menu(message: types.Message, user_language: str):
    """Handle /menu command."""
    keyboard = get_main_menu_keyboard(user_language)
    await message.answer("📋 **Main Menu**", reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("signal"))
async def cmd_signal(message: types.Message, db, user: dict):
    """Handle /signal command."""
    signal_repo = SignalRepository(db)
    active_signals = await signal_repo.get_active_signals()

    if not active_signals:
        await message.answer("📭 No active signals at the moment.\n\nCheck back later or wait for notifications!")
        return

    for signal in active_signals[:3]:
        # Format signal message
        signal_type = signal.get("signal_type", "").upper()
        symbol = signal.get("symbol", "")
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp1 = signal.get("take_profit_1", 0)
        rr = signal.get("risk_reward_ratio", 0)
        confidence = signal.get("confidence_score", 0)

        direction_emoji = "🟢" if signal_type == "BUY" else "🔴"

        signal_text = "\n".join([
            f"🚀 **{signal_type} SIGNAL** - {symbol}",
            "",
            f"{direction_emoji} Entry: `{entry:,.8f}`",
            f"🔴 SL: `{sl:,.8f}`",
            f"🎯 TP: `{tp1:,.8f}`",
            "",
            f"📊 R:R: `{rr:.2f}` | Confidence: `{confidence:.0f}%`",
        ])

        keyboard = get_signal_keyboard(signal["id"], user.get("is_admin", False) if user else False)
        await message.answer(signal_text, parse_mode="Markdown", reply_markup=keyboard)


@router.message(Command("market"))
async def cmd_market(message: types.Message, user_language: str):
    """Handle /market command."""
    keyboard = get_exchange_keyboard()
    await message.answer("📈 **Select Market**", reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("chart"))
async def cmd_chart(message: types.Message, user_language: str):
    """Handle /chart command."""
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "📊 **Chart Generator**\n\n"
            "Usage: `/chart <symbol>`\n"
            "Example: `/chart BTC/USDT`\n\n"
            "Available: BTC, ETH, BNB, SOL, etc.",
            parse_mode="Markdown"
        )
        return

    symbol = args[1].upper()
    is_valid, symbol = validate_symbol(symbol)

    if not is_valid:
        await message.answer("⚠️ Invalid symbol. Please use format like: `BTC/USDT`", parse_mode="Markdown")
        return

    # Notify user chart is being generated
    wait_msg = await message.answer(f"📊 Generating chart for {symbol}...")

    try:
        # Import here to avoid circular imports
        from market import ExchangeManager
        from charts import ChartGenerator

        exchange = ExchangeManager()
        await exchange.initialize()

        ohlcv = await exchange.get_ohlcv(symbol, "1h", "binance", limit=200)

        if ohlcv:
            chart_gen = ChartGenerator()
            chart_path = chart_gen.generate_candlestick_chart(ohlcv, symbol, "1h")

            if chart_path:
                with open(chart_path, "rb") as photo:
                    await message.answer_photo(types.FSInputFile(photo, filename=f"{symbol}.png"))
                await wait_msg.delete()
            else:
                await wait_msg.edit_text("❌ Failed to generate chart. Please try again.")

        await exchange.close()

    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        await wait_msg.edit_text("❌ Error generating chart. Please try again later.")


@router.message(Command("price"))
async def cmd_price(message: types.Message):
    """Handle /price command."""
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "💰 **Price Lookup**\n\n"
            "Usage: `/price <symbol>`\n"
            "Example: `/price BTC/USDT`\n\n"
            "Crypto: BTC/USDT, ETH/USDT\n"
            "Forex: EUR/USD, GBP/USD",
            parse_mode="Markdown"
        )
        return

    symbol = args[1].upper()

    try:
        from market import ExchangeManager

        exchange = ExchangeManager()
        await exchange.initialize()

        exchange_type = "forex" if "/" in symbol and "USDT" not in symbol else "binance"
        ticker = await exchange.get_ticker(symbol, exchange_type)

        await exchange.close()

        if ticker:
            price = ticker.get("last", 0)
            change = ticker.get("change_percent", 0)
            vol = ticker.get("volume", 0)

            change_emoji = "📈" if change >= 0 else "📉"
            change_sign = "+" if change >= 0 else ""

            price_text = "\n".join([
                f"💰 **{symbol}**",
                "",
                f"💵 Price: `{price:,.8f}`",
                f"{change_emoji} 24h: `{change_sign}{change:.2f}%`",
                f"📊 Volume: `{vol:,.0f}`",
            ])

            await message.answer(price_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Could not fetch price for {symbol}")

    except Exception as e:
        logger.error(f"Error fetching price: {e}")
        await message.answer("❌ Error fetching price. Please try again.")


@router.message(Command("alerts"))
async def cmd_alerts(message: types.Message, db, user: dict):
    """Handle /alerts command."""
    alert_repo = AlertRepository(db)
    alerts = await alert_repo.get_user_alerts(user["telegram_id"])

    keyboard = get_alert_keyboard(alerts)

    if alerts:
        await message.answer(
            f"🔔 **Your Alerts** ({len(alerts)} active)",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🔔 **Alerts**\n\n"
            "You have no active alerts.\n"
            "Use the button below to create one.",
            reply_markup=keyboard
        )


@router.message(Command("settings"))
async def cmd_settings(message: types.Message, db, user: dict):
    """Handle /settings command."""
    user_repo = UserRepository(db)
    user_settings = await user_repo.get_user_settings(user["telegram_id"])

    keyboard = get_settings_keyboard(user_settings)
    await message.answer("⚙️ **Settings**", reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("profile"))
async def cmd_profile(message: types.Message, db, user: dict, user_language: str):
    """Handle /profile command."""
    user_repo = UserRepository(db)

    if user_language == "si":
        lang_name = "සිංහල"
    else:
        lang_name = "English"

    # Get user stats
    created_at = user.get("created_at", "")
    is_premium = user.get("is_premium", False)
    referral_code = user.get("referral_code", "")

    premium_status = "💎 **Premium**" if is_premium else "🆓 **Free**"

    profile_text = "\n".join([
        "👤 **Your Profile**",
        "",
        f"🆔 ID: `{user['telegram_id']}`",
        f"📝 Username: @{user.get('username', 'N/A')}",
        "",
        f"📊 Status: {premium_status}",
        f"🌐 Language: {lang_name}",
        f"📅 Joined: {created_at[:10] if created_at else 'N/A'}",
        "",
        f"🔗 Referral Code: `{referral_code}`",
        "",
        "_Share your referral code and earn rewards!_",
    ])

    await message.answer(profile_text, parse_mode="Markdown")


@router.message(Command("vip"))
async def cmd_vip(message: types.Message, user_language: str):
    """Handle /vip command."""
    keyboard = get_vip_keyboard()

    if user_language == "si":
        vip_text = "\n".join([
            "💎 **Premium සාමාජිකත්වය**",
            "",
            "**විශේෂාංග:**",
            "• ස්වයංක්‍රීය Signals",
            "• Premium Channel Access",
            "• Priority Support",
            "• More daily signals",
            "",
            "**මිල:**",
            "Monthly: $29.99",
            "Yearly: $299.99 (17% OFF)",
        ])
    else:
        vip_text = "\n".join([
            "💎 **Premium Membership**",
            "",
            "**Features:**",
            "• Automated Signals",
            "• Premium Channel Access",
            "• Priority Support",
            "• More daily signals",
            "",
            "**Pricing:**",
            "Monthly: $29.99",
            "Yearly: $299.99 (17% OFF)",
        ])

    await message.answer(vip_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("news"))
async def cmd_news(message: types.Message, user_language: str):
    """Handle /news command."""
    # Placeholder for news functionality
    if user_language == "si":
        await message.answer("📰 News feature coming soon...")
    else:
        await message.answer(
            "📰 **Market News**\n\n"
            "News feature is coming soon!\n"
            "Stay tuned for market updates and analysis.",
            parse_mode="Markdown"
        )


@router.message(Command("watchlist"))
async def cmd_watchlist(message: types.Message, db, user: dict, exchange_manager):
    """Handle /watchlist command."""
    from services.portfolio import PortfolioManager

    args = message.text.split()
    portfolio = PortfolioManager(db)

    if len(args) > 1:
        action = args[1].lower()

        if action == "add" and len(args) > 2:
            symbol = args[2].upper()
            # Validate symbol
            is_valid, symbol = validate_symbol(symbol)
            if not is_valid:
                await message.answer("❌ Invalid symbol format.", parse_mode="Markdown")
                return

            success = await portfolio.add_to_watchlist(user["telegram_id"], symbol)
            if success:
                await message.answer(f"✅ Added `{symbol}` to your watchlist.", parse_mode="Markdown")
            else:
                await message.answer(f"⚠️ `{symbol}` is already in your watchlist.", parse_mode="Markdown")

        elif action == "remove" and len(args) > 2:
            symbol = args[2].upper()
            success = await portfolio.remove_from_watchlist(user["telegram_id"], symbol)
            if success:
                await message.answer(f"✅ Removed `{symbol}` from your watchlist.", parse_mode="Markdown")
            else:
                await message.answer(f"⚠️ `{symbol}` not found in your watchlist.", parse_mode="Markdown")

        elif action == "clear":
            await portfolio.clear_watchlist(user["telegram_id"])
            await message.answer("✅ Watchlist cleared.")

        else:
            await message.answer(
                "📋 **Watchlist Commands**\n\n"
                "Usage:\n"
                "`/watchlist` - View watchlist\n"
                "`/watchlist add SYMBOL` - Add symbol\n"
                "`/watchlist remove SYMBOL` - Remove symbol\n"
                "`/watchlist clear` - Clear all",
                parse_mode="Markdown"
            )
    else:
        # Show watchlist
        watchlist = await portfolio.get_watchlist(user["telegram_id"])

        # Get current prices
        prices = {}
        for symbol in watchlist[:10]:
            try:
                exchange_type = "forex" if "/" in symbol and "USDT" not in symbol else "binance"
                ticker = await exchange_manager.get_ticker(symbol, exchange_type)
                if ticker:
                    prices[symbol] = ticker.get("last", 0)
            except Exception:
                pass

        watchlist_text = portfolio.format_watchlist(watchlist, prices)
        await message.answer(watchlist_text, parse_mode="Markdown")


@router.message(Command("portfolio"))
async def cmd_portfolio(message: types.Message, db, user: dict, exchange_manager):
    """Handle /portfolio command."""
    from services.portfolio import PortfolioManager

    args = message.text.split()
    portfolio = PortfolioManager(db)

    if len(args) > 1:
        action = args[1].lower()

        if action == "add" and len(args) >= 5:
            try:
                symbol = args[2].upper()
                is_valid, symbol = validate_symbol(symbol)
                entry_price = float(args[3])
                size = float(args[4])
                position_type = args[5].lower() if len(args) > 5 else "long"

                position = await portfolio.add_portfolio_position(
                    user_id=user["telegram_id"],
                    symbol=symbol,
                    entry_price=entry_price,
                    size=size,
                    position_type=position_type,
                )

                if position:
                    await message.answer(
                        f"✅ **Position Added**\n\n"
                        f"Symbol: `{symbol}`\n"
                        f"Entry: `{entry_price}`\n"
                        f"Size: `{size}`\n"
                        f"Type: `{position_type.upper()}`",
                        parse_mode="Markdown"
                    )
                else:
                    await message.answer("❌ Failed to add position.")

            except ValueError:
                await message.answer("❌ Invalid values. Usage: `/portfolio add SYMBOL ENTRY SIZE [long/short]`")

        elif action == "close" and len(args) >= 4:
            try:
                position_id = int(args[2])
                exit_price = float(args[3])

                trade = await portfolio.close_portfolio_position(
                    user_id=user["telegram_id"],
                    position_id=position_id,
                    exit_price=exit_price,
                )

                if trade:
                    await message.answer(
                        f"✅ **Position Closed**\n\n"
                        f"Exit Price: `{exit_price}`\n"
                        f"P/L: `${trade['pnl']:,.2f}` ({trade['pnl_percent']:+.2f}%)",
                        parse_mode="Markdown"
                    )
                else:
                    await message.answer("❌ Position not found.")

            except ValueError:
                await message.answer("❌ Invalid values. Usage: `/portfolio close ID EXIT_PRICE`")

        elif action == "list":
            portfolio_data = await portfolio.calculate_portfolio_value(user["telegram_id"], exchange_manager)
            portfolio_text = portfolio.format_portfolio(portfolio_data)
            await message.answer(portfolio_text, parse_mode="Markdown")

        elif action == "history":
            trades = await portfolio.get_trade_history(user["telegram_id"])
            history_text = portfolio.format_trade_history(trades)
            await message.answer(history_text, parse_mode="Markdown")

        else:
            await message.answer(
                "💼 **Portfolio Commands**\n\n"
                "Usage:\n"
                "`/portfolio list` - View portfolio\n"
                "`/portfolio add SYMBOL ENTRY SIZE [long/short]` - Add position\n"
                "`/portfolio close ID EXIT_PRICE` - Close position\n"
                "`/portfolio history` - Trade history",
                parse_mode="Markdown"
            )
    else:
        # Show portfolio
        portfolio_data = await portfolio.calculate_portfolio_value(user["telegram_id"], exchange_manager)
        portfolio_text = portfolio.format_portfolio(portfolio_data)
        await message.answer(portfolio_text, parse_mode="Markdown")


@router.message(Command("report"))
async def cmd_report(message: types.Message, db, user_language: str):
    """Handle /report command for performance reports."""
    from services.performance import PerformanceTracker

    args = message.text.split()
    performance = PerformanceTracker(db)

    if len(args) > 1:
        report_type = args[1].lower()

        if report_type == "daily":
            report = await performance.get_daily_report()
            text = performance.format_daily_report(report, user_language)
            await message.answer(text, parse_mode="Markdown")

        elif report_type == "weekly":
            report = await performance.get_weekly_report()
            text = performance.format_weekly_report(report, user_language)
            await message.answer(text, parse_mode="Markdown")

        elif report_type == "monthly":
            report = await performance.get_monthly_report()
            text = performance.format_monthly_report(report, user_language)
            await message.answer(text, parse_mode="Markdown")

        elif report_type == "accuracy":
            accuracy = await performance.get_signal_accuracy(30)
            text = "\n".join([
                "📊 **Signal Accuracy Report** (Last 30 Days)",
                "",
                f"📈 Total Signals: `{accuracy['total_signals']}`",
                f"✅ Winners: `{accuracy['winning_signals']}`",
                f"❌ Losers: `{accuracy['losing_signals']}`",
                f"📊 Win Rate: `{accuracy['win_rate']:.1f}%`",
                f"📉 Loss Rate: `{accuracy['loss_rate']:.1f}%`",
                f"📍 Avg Signals/Day: `{accuracy['signal_frequency']}`",
                f"🎯 Grade: `{accuracy['performance_grade']}`",
            ])
            await message.answer(text, parse_mode="Markdown")

        else:
            await message.answer(
                "📊 **Report Commands**\n\n"
                "Usage:\n"
                "`/report daily` - Today's report\n"
                "`/report weekly` - Weekly report\n"
                "`/report monthly` - Monthly report\n"
                "`/report accuracy` - Signal accuracy",
                parse_mode="Markdown"
            )
    else:
        # Show daily report by default
        report = await performance.get_daily_report()
        text = performance.format_daily_report(report, user_language)
        await message.answer(text, parse_mode="Markdown")


@router.message(Command("journal"))
async def cmd_journal(message: types.Message, db, user: dict, user_language: str):
    """Handle /journal command for trading journal."""
    from services.portfolio import TradingJournal

    args = message.text.split()
    journal = TradingJournal(db)

    if len(args) > 1:
        action = args[1].lower()

        if action == "add" and len(args) >= 4:
            symbol = args[2].upper()
            content = " ".join(args[3:])

            entry = await journal.add_entry(
                user_id=user["telegram_id"],
                symbol=symbol,
                entry_type="note",
                content=content,
            )

            if entry:
                await message.answer(
                    f"📝 **Journal Entry Added**\n\n"
                    f"Symbol: `{symbol}`\n"
                    f"Note: {content[:100]}{'...' if len(content) > 100 else ''}",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Failed to add journal entry.")

        elif action == "list":
            symbol = args[2].upper() if len(args) > 2 else None
            entries = await journal.get_entries(user["telegram_id"], symbol=symbol)

            if entries:
                text_lines = ["📔 **Trading Journal**", ""]
                for e in entries[-10:]:
                    text_lines.append(f"#{e['id']} `{e['symbol']}` - {e['created_at'][:10]}")
                    text_lines.append(f"  {e['content'][:50]}...")
                    text_lines.append("")

                await message.answer("\n".join(text_lines), parse_mode="Markdown")
            else:
                await message.answer("📔 **Trading Journal**\n\nNo entries yet.\nUse `/journal add SYMBOL your notes`")

        else:
            await message.answer(
                "📔 **Journal Commands**\n\n"
                "Usage:\n"
                "`/journal list` - View entries\n"
                "`/journal list SYMBOL` - View for symbol\n"
                "`/journal add SYMBOL your notes` - Add entry\n"
                "`/journal delete ID` - Delete entry",
                parse_mode="Markdown"
            )
    else:
        # Show recent entries
        entries = await journal.get_entries(user["telegram_id"])

        if entries:
            text_lines = ["📔 **Recent Journal Entries**", ""]
            for e in entries[-5:]:
                text_lines.append(f"#{e['id']} `{e['symbol']}` - {e['created_at'][:10]}")
                text_lines.append(f"  {e['content'][:50]}...")
                text_lines.append("")

            await message.answer("\n".join(text_lines), parse_mode="Markdown")
        else:
            await message.answer(
                "📔 **Trading Journal**\n\n"
                "Your journal is empty.\n"
                "Use `/journal add SYMBOL your notes` to add an entry.",
                parse_mode="Markdown"
            )


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, is_admin: bool):
    """Handle /admin command."""
    if not is_admin:
        await message.answer("⚠️ This command is restricted to admins.")
        return

    from keyboards.keyboards import get_admin_keyboard
    keyboard = get_admin_keyboard()
    await message.answer("🔐 **Admin Panel**", reply_markup=keyboard, parse_mode="Markdown")
