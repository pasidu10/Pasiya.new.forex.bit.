"""
Callback query handlers for Telegram bot.
"""
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from typing import Optional

from config import settings
from keyboards.keyboards import (
    get_main_menu_keyboard,
    get_market_keyboard,
    get_timeframe_keyboard,
    get_language_keyboard,
    get_signal_keyboard,
    get_alert_keyboard,
    get_pagination_keyboard,
    get_confirmation_keyboard,
)
from database import UserRepository, SignalRepository, AlertRepository
from utils.logger import get_logger

logger = get_logger(__name__)

router = Router()


@router.callback_query(F.data == "menu_main")
async def callback_menu_main(callback: types.CallbackQuery, user_language: str):
    """Handle main menu callback."""
    keyboard = get_main_menu_keyboard(user_language)
    await callback.message.edit_text("📋 **Main Menu**", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("lang_"))
async def callback_language(callback: types.CallbackQuery, db, user: dict):
    """Handle language selection callback."""
    lang_code = callback.data.split("_")[1]

    user_repo = UserRepository(db)
    await user_repo.update_user(user["telegram_id"], language=lang_code)

    keyboard = get_language_keyboard(lang_code)

    if lang_code == "si":
        text = "🌐 **භාෂාව වෙනස් කරන ලදී!**"
    else:
        text = "🌐 **Language changed!**"

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("Language updated!")


@router.callback_query(F.data == "settings_language")
async def callback_settings_language(callback: types.CallbackQuery, user: dict):
    """Handle language settings callback."""
    keyboard = get_language_keyboard(user.get("language", "en"))
    await callback.message.edit_text("🌐 **Select Language**", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "settings_toggle_notifications")
async def callback_toggle_notifications(callback: types.CallbackQuery, db, user: dict):
    """Handle notification toggle callback."""
    user_repo = UserRepository(db)
    current_settings = await user_repo.get_user_settings(user["telegram_id"])

    new_value = not current_settings.get("notifications", True)
    await user_repo.update_user_settings(user["telegram_id"], {"notifications": new_value})

    status = "ON" if new_value else "OFF"
    await callback.answer(f"Notifications {status}")
    await callback.message.answer(f"🔔 Notifications turned {status}")


@router.callback_query(F.data == "settings_toggle_price_alerts")
async def callback_toggle_price_alerts(callback: types.CallbackQuery, db, user: dict):
    """Handle price alerts toggle callback."""
    user_repo = UserRepository(db)
    current_settings = await user_repo.get_user_settings(user["telegram_id"])

    new_value = not current_settings.get("price_alerts", True)
    await user_repo.update_user_settings(user["telegram_id"], {"price_alerts": new_value})

    status = "ON" if new_value else "OFF"
    await callback.answer(f"Price alerts {status}")
    await callback.message.answer(f"💰 Price alerts turned {status}")


@router.callback_query(F.data.startswith("exchange_"))
async def callback_exchange(callback: types.CallbackQuery, db):
    """Handle exchange selection callback."""
    exchange = callback.data.split("_")[1]

    if exchange == "forex":
        keyboard = get_market_keyboard("forex")
        await callback.message.edit_text("📊 **Forex Pairs**", reply_markup=keyboard, parse_mode="Markdown")
    else:
        keyboard = get_market_keyboard("crypto")
        await callback.message.edit_text(f"📊 **{exchange.capitalize()} Crypto Pairs**", reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer()


@router.callback_query(F.data.startswith("market_coin_") | F.data.startswith("market_pair_"))
async def callback_market_pair(callback: types.CallbackQuery):
    """Handle market pair selection callback."""
    if "coin_" in callback.data:
        symbol = callback.data.replace("market_coin_", "")
    else:
        symbol = callback.data.replace("market_pair_", "")

    wait_msg = await callback.message.answer(f"📊 Loading data for {symbol}...")

    try:
        from market import ExchangeManager, MarketAnalysis

        exchange = ExchangeManager()
        await exchange.initialize()

        analysis = MarketAnalysis(exchange)
        result = await analysis.analyze(symbol, "1h")

        await exchange.close()

        if result:
            report = await analysis.generate_report(symbol, "1h")
            await wait_msg.edit_text(report, parse_mode="Markdown")
        else:
            await wait_msg.edit_text(f"❌ Could not load data for {symbol}")

    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        await wait_msg.edit_text("❌ Error loading market data. Please try again.")

    await callback.answer()


@router.callback_query(F.data == "market_refresh")
async def callback_market_refresh(callback: types.CallbackQuery):
    """Handle market refresh callback."""
    await callback.answer("Refreshing...")
    # Re-get market data
    await callback.message.answer("🔄 Refreshing market data...")


@router.callback_query(F.data.startswith("signal_"))
async def callback_signal(callback: types.CallbackQuery, db, user: dict):
    """Handle signal callbacks."""
    parts = callback.data.split("_")
    action = parts[1]
    signal_id = int(parts[2]) if len(parts) > 2 else None

    signal_repo = SignalRepository(db)

    if action == "analysis":
        signal = await signal_repo.get_signal(signal_id)
        if signal:
            indicators = signal.get("indicators", {})
            analysis_text = "\n".join([
                f"📊 **Signal Analysis #{signal_id}**",
                f"Symbol: {signal.get('symbol')}",
                "",
                f"**Indicators:**",
                f"RSI: {indicators.get('rsi', 'N/A')}",
                f"MACD: {indicators.get('macd_status', 'N/A')}",
                f"Trend: {indicators.get('trend', 'N/A')}",
                "",
                f"**Confidence:** {signal.get('confidence_score', 0):.0f}%",
            ])
            await callback.message.answer(analysis_text, parse_mode="Markdown")

    elif action == "chart":
        signal = await signal_repo.get_signal(signal_id)
        if signal:
            try:
                from market import ExchangeManager
                from charts import ChartGenerator

                exchange = ExchangeManager()
                await exchange.initialize()

                symbol = signal.get("symbol")
                exchange_type = "forex" if "/" in symbol and "USDT" not in symbol else "binance"
                ohlcv = await exchange.get_ohlcv(symbol, signal.get("timeframe", "1h"), exchange_type, limit=100)

                if ohlcv:
                    chart_gen = ChartGenerator()
                    chart_path = chart_gen.generate_signal_chart(
                        ohlcv, signal, symbol, signal.get("timeframe", "1h")
                    )

                    if chart_path:
                        with open(chart_path, "rb") as photo:
                            await callback.message.answer_photo(
                                types.FSInputFile(photo, filename=f"signal_{signal_id}.png")
                            )

                await exchange.close()

            except Exception as e:
                logger.error(f"Error generating signal chart: {e}")
                await callback.message.answer("❌ Error generating chart")

    elif action == "share":
        from signals import SignalManager
        signal_manager = SignalManager(db)
        signal = await signal_repo.get_signal(signal_id)
        if signal:
            message = signal_manager.format_signal_message(signal)
            await callback.message.answer(message, parse_mode="Markdown")

    elif action == "delete":
        if user and user.get("is_admin"):
            keyboard = get_confirmation_keyboard("delete_signal", signal_id)
            await callback.message.answer(
                f"⚠️ Are you sure you want to delete signal #{signal_id}?",
                reply_markup=keyboard
            )

    await callback.answer()


@router.callback_query(F.data.startswith("alert_"))
async def callback_alert(callback: types.CallbackQuery, db, user: dict):
    """Handle alert callbacks."""
    parts = callback.data.split("_")
    action = parts[1]
    alert_id = int(parts[2]) if len(parts) > 2 else None

    alert_repo = AlertRepository(db)

    if action == "view":
        alert = await alert_repo.get_alert(alert_id)
        if alert:
            alert_text = "\n".join([
                f"🔔 **Alert #{alert_id}**",
                f"Symbol: {alert.get('symbol')}",
                f"Target: {alert.get('target_price'):,.4f}",
                f"Condition: {alert.get('condition_type')}",
                f"Status: {'Active' if alert.get('is_active') else 'Inactive'}",
            ])
            await callback.message.answer(alert_text)

    elif action == "add":
        await callback.message.answer(
            "📋 **Create Alert**\n\n"
            "Format: `/alert SYMBOL PRICE [above/below]`\n"
            "Example: `/alert BTC/USDT 50000 above`"
        )

    elif action == "delete" and alert_id:
        await alert_repo.delete_alert(alert_id)
        await callback.answer("Alert deleted!")
        alerts = await alert_repo.get_user_alerts(user["telegram_id"])
        keyboard = get_alert_keyboard(alerts)
        await callback.message.edit_text("🔔 **Alerts Updated**", reply_markup=keyboard)

    elif action == "delete" and "all" in callback.data:
        alerts = await alert_repo.get_user_alerts(user["telegram_id"])
        for alert in alerts:
            await alert_repo.delete_alert(alert["id"])
        await callback.answer("All alerts deleted!")
        keyboard = get_alert_keyboard([])
        await callback.message.edit_text("🔔 **All alerts removed**", reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("vip_"))
async def callback_vip(callback: types.CallbackQuery):
    """Handle VIP callbacks."""
    action = callback.data.split("_")[1]

    if action == "monthly":
        await callback.message.answer(
            "💎 **Monthly Premium**\n\n"
            "To subscribe, please contact support or use the payment link.\n\n"
            "Price: $29.99/month"
        )
    elif action == "yearly":
        await callback.message.answer(
            "💎 **Yearly Premium**\n\n"
            "To subscribe, please contact support or use the payment link.\n\n"
            "Price: $299.99/year (Save 17%!)"

        )
    elif action == "promo":
        await callback.message.answer(
            "🎁 **Promo Code**\n\n"
            "Please enter your promo code:\n"
            "Usage: `/promo YOUR_CODE`"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("page_"))
async def callback_pagination(callback: types.CallbackQuery):
    """Handle pagination callbacks."""
    await callback.answer("Page navigation")


@router.callback_query(F.data.startswith("confirm_") | F.data.startswith("cancel_"))
async def callback_confirmation(callback: types.CallbackQuery, db, user: dict):
    """Handle confirmation callbacks."""
    parts = callback.data.split("_")
    action = parts[1]
    item_id = int(parts[2]) if len(parts) > 2 else None

    if action == "delete" and item_id:
        signal_repo = SignalRepository(db)
        await signal_repo.update_signal(item_id, is_active=False)
        await callback.answer("Signal deleted!")
        await callback.message.edit_text("✅ Signal has been deleted.")
    elif action.startswith("cancel"):
        await callback.answer("Cancelled")
        await callback.message.edit_text("❌ Action cancelled.")

    await callback.answer()
