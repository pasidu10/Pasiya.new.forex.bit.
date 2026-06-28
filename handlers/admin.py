"""
Admin handlers for Telegram bot.
"""
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import json

from config import settings
from keyboards.keyboards import get_admin_keyboard, get_admin_users_keyboard, get_confirmation_keyboard
from database import UserRepository, SignalRepository, StatisticsRepository, SettingsRepository
from signals import SignalGenerator, SignalManager
from market import ExchangeManager
from utils.logger import get_logger
from utils.helpers import format_number, format_currency
from utils.validators import parse_signal_input

logger = get_logger(__name__)

router = Router()


class AdminStates(StatesGroup):
    """Admin FSM states."""
    broadcast = State()
    add_signal = State()
    add_user = State()
    ban_user = State()
    settings = State()


@router.message(F.text == "📊 Statistics")
async def admin_statistics(message: types.Message, db):
    """Show admin statistics."""
    user_repo = UserRepository(db)
    signal_repo = SignalRepository(db)
    stats_repo = StatisticsRepository(db)

    # Get stats
    total_users = await user_repo.count_users()
    active_users = await user_repo.count_active_users()
    premium_users = len(await user_repo.get_premium_users())
    signal_performance = await signal_repo.get_signal_performance(30)
    daily_stats = await stats_repo.get_statistics(7)

    # Format message
    stats_text = "\n".join([
        "📊 **Bot Statistics**",
        "",
        f"👥 **Users:**",
        f"  • Total: `{total_users:,}`",
        f"  • Active: `{active_users:,}`",
        f"  • Premium: `{premium_users:,}`",
        "",
        f"📈 **Signal Performance (30 days):**",
        f"  • Total Signals: `{signal_performance.get('total', 0)}`",
        f"  • Win Rate: `{signal_performance.get('win_rate', 0):.1f}%`",
        f"  • Hits: `{signal_performance.get('wins', 0)}`",
        f"  • Misses: `{signal_performance.get('losses', 0)}`",
        "",
        f"📅 **Last 7 Days:**",
    ])

    # Add daily stats
    for stat in daily_stats[:5]:
        date = stat.get("date", "")
        new_users = stat.get("new_users", 0)
        signals = stat.get("signals_generated", 0)
        stats_text += f"  `{date}`: {new_users} users, {signals} signals\n"

    await message.answer(stats_text, parse_mode="Markdown")


@router.message(F.text == "📤 Broadcast")
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    """Start broadcast process."""
    await state.set_state(AdminStates.broadcast)
    await message.answer(
        "📤 **Broadcast Message**\n\n"
        "Send the message you want to broadcast to all users.\n\n"
        "You can use Markdown formatting.\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )


@router.message(AdminStates.broadcast)
async def admin_broadcast_execute(message: types.Message, state: FSMContext, db, bot):
    """Execute broadcast."""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Broadcast cancelled.")
        return

    await state.clear()
    await message.answer("📤 Broadcasting message...")

    try:
        from services import NotificationService
        notification = NotificationService(db)
        notification.set_bot(bot)

        result = await notification.broadcast(message.text)

        await message.answer(
            f"✅ **Broadcast Complete**\n\n"
            f"✅ Success: {result['success']}\n"
            f"❌ Failed: {result['failed']}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await message.answer(f"❌ Error: {str(e)}")


@router.message(F.text == "📢 Post Signal")
async def admin_post_signal_start(message: types.Message, state: FSMContext):
    """Start manual signal posting."""
    await state.set_state(AdminStates.add_signal)
    await message.answer(
        "📢 **Post Manual Signal**\n\n"
        "Format: `SYMBOL TYPE ENTRY [SL] [TP1] [TP2] [TP3]`\n\n"
        "Example: `BTC/USDT BUY 45000 44000 46000 47000 48000`\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )


@router.message(AdminStates.add_signal)
async def admin_post_signal_execute(message: types.Message, state: FSMContext, db, user: dict):
    """Execute manual signal posting."""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Signal posting cancelled.")
        return

    await state.clear()

    try:
        signal_data = parse_signal_input(message.text)

        if not signal_data or not signal_data.get("symbol"):
            await message.answer("❌ Invalid signal format. Please try again.")
            return

        signal_manager = SignalManager(db)

        # Create signal object
        signal = {
            "symbol": signal_data["symbol"],
            "signal_type": signal_data["signal_type"],
            "market_type": "crypto" if "USDT" in signal_data["symbol"] else "forex",
            "timeframe": "manual",
            "entry_price": signal_data["entry"],
            "stop_loss": signal_data.get("stop_loss"),
            "take_profit_1": signal_data["take_profits"][0] if signal_data["take_profits"] else None,
            "take_profit_2": signal_data["take_profits"][1] if len(signal_data["take_profits"]) > 1 else None,
            "take_profit_3": signal_data["take_profits"][2] if len(signal_data["take_profits"]) > 2 else None,
            "risk_reward_ratio": 2.0,  # Default
            "confidence_score": 85,  # Manual signal confidence
            "analysis_notes": "Manual signal posted by admin",
        }

        # Save signal
        saved_signal = await signal_manager.save_signal(signal, user["telegram_id"], is_auto=False)

        # Format and show
        message_text = signal_manager.format_signal_message(saved_signal)
        await message.answer(message_text, parse_mode="Markdown")

        # Broadcast to premium users
        from services import NotificationService
        notification = NotificationService(db)
        # notification.set_bot(bot)  # Would need bot reference
        # await notification.send_signal_notification(message_text, premium_only=True)

        await message.answer("✅ Signal posted successfully!")

    except Exception as e:
        logger.error(f"Error posting signal: {e}")
        await message.answer(f"❌ Error: {str(e)}")


@router.message(F.text == "🤖 Auto Signals")
async def admin_auto_signals(message: types.Message, db):
    """Manage auto signals."""
    settings_repo = SettingsRepository(db)
    auto_signals_enabled = await settings_repo.get_setting("auto_signals_enabled")

    if auto_signals_enabled is None:
        auto_signals_enabled = "true"

    status = "✅ ENABLED" if auto_signals_enabled.lower() == "true" else "❌ DISABLED"

    await message.answer(
        f"🤖 **Auto Signals Status**\n\n"
        f"Current: {status}\n\n"
        f"Commands:\n"
        f"/autosignals_on - Enable auto signals\n"
        f"/autosignals_off - Disable auto signals",
        parse_mode="Markdown"
    )


@router.message(F.text == "👥 Users")
async def admin_users(message: types.Message, db):
    """Show users management."""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_users()

    # Limit to recent users
    recent_users = users[:20]

    keyboard = get_admin_users_keyboard(recent_users)

    await message.answer(
        f"👥 **Users Management**\n\n"
        f"Total Users: {len(users)}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(F.text == "💎 Premium")
async def admin_premium(message: types.Message, db):
    """Manage premium users."""
    user_repo = UserRepository(db)
    premium_users = await user_repo.get_premium_users()

    text_lines = [
        "💎 **Premium Users**",
        "",
        f"Total Premium: `{len(premium_users)}`",
        "",
        "**Commands:**",
        "/premium_add USER_ID - Add premium",
        "/premium_remove USER_ID - Remove premium",
    ]

    # List some premium users
    if premium_users:
        text_lines.append("")
        text_lines.append("**Recent Premium Users:**")
        for user in premium_users[:10]:
            username = user.get("username") or user.get("first_name") or str(user.get("telegram_id"))
            text_lines.append(f"  • @{username}")

    await message.answer("\n".join(text_lines), parse_mode="Markdown")


@router.message(F.text == "📺 Channels")
async def admin_channels(message: types.Message):
    """Manage channel settings."""
    await message.answer(
        "📺 **Channel Management**\n\n"
        "**Commands:**\n"
        "/channel_set CHANNEL_ID - Set main channel\n"
        "/premium_channel_set CHANNEL_ID - Set premium channel\n"
        "/channel_test - Test channel connection\n\n"
        f"_Current Channel: {settings.CHANNEL_ID or 'Not set'}_\n"
        f"_Premium Channel: {settings.PREMIUM_CHANNEL_ID or 'Not set'}_",
        parse_mode="Markdown"
    )


@router.message(F.text == "💬 Groups")
async def admin_groups(message: types.Message):
    """Manage group settings."""
    await message.answer(
        "💬 **Group Management**\n\n"
        "**Commands:**\n"
        "/group_set GROUP_ID - Set main group\n"
        "/group_test - Test group connection\n\n"
        f"_Current Group: {settings.GROUP_ID or 'Not set'}_",
        parse_mode="Markdown"
    )


@router.message(F.text == "⚙️ Settings")
async def admin_settings_menu(message: types.Message, db):
    """Show settings menu."""
    settings_repo = SettingsRepository(db)
    all_settings = await settings_repo.get_all_settings()

    text_lines = [
        "⚙️ **Bot Settings**",
        "",
    ]

    for key, value in all_settings.items():
        text_lines.append(f"  • `{key}`: {value}")

    text_lines.extend([
        "",
        "**Commands:**",
        "/setting_set KEY VALUE - Update setting",
        "/setting_get KEY - Get setting value",
    ])

    await message.answer("\n".join(text_lines), parse_mode="Markdown")


@router.message(F.text == "🔙 Main Menu")
async def admin_back_to_main(message: types.Message, user_language: str):
    """Return to main menu."""
    from keyboards.keyboards import get_main_menu_keyboard
    keyboard = get_main_menu_keyboard(user_language)
    await message.answer("📋 **Main Menu**", reply_markup=keyboard, parse_mode="Markdown")


# Helper commands for admin actions

@router.message(lambda m: m.text and m.text.startswith("/premium_add"))
async def cmd_premium_add(message: types.Message, db):
    """Add premium to user."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /premium_add USER_ID")
        return

    try:
        user_id = int(parts[1])
        user_repo = UserRepository(db)
        await user_repo.set_premium(user_id, True)
        await message.answer(f"✅ Premium added to user {user_id}")
    except ValueError:
        await message.answer("❌ Invalid user ID")


@router.message(lambda m: m.text and m.text.startswith("/premium_remove"))
async def cmd_premium_remove(message: types.Message, db):
    """Remove premium from user."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /premium_remove USER_ID")
        return

    try:
        user_id = int(parts[1])
        user_repo = UserRepository(db)
        await user_repo.set_premium(user_id, False)
        await message.answer(f"✅ Premium removed from user {user_id}")
    except ValueError:
        await message.answer("❌ Invalid user ID")


@router.message(lambda m: m.text and m.text.startswith("/ban"))
async def cmd_ban_user(message: types.Message, db):
    """Ban a user."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /ban USER_ID")
        return

    try:
        user_id = int(parts[1])
        user_repo = UserRepository(db)
        await user_repo.ban_user(user_id)
        await message.answer(f"🚫 User {user_id} has been banned")
    except ValueError:
        await message.answer("❌ Invalid user ID")


@router.message(lambda m: m.text and m.text.startswith("/unban"))
async def cmd_unban_user(message: types.Message, db):
    """Unban a user."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /unban USER_ID")
        return

    try:
        user_id = int(parts[1])
        user_repo = UserRepository(db)
        await user_repo.unban_user(user_id)
        await message.answer(f"✅ User {user_id} has been unbanned")
    except ValueError:
        await message.answer("❌ Invalid user ID")


@router.message(lambda m: m.text and m.text.startswith("/admin_add"))
async def cmd_admin_add(message: types.Message, db):
    """Add admin to user."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /admin_add USER_ID")
        return

    try:
        user_id = int(parts[1])
        user_repo = UserRepository(db)
        await user_repo.set_admin(user_id, True)
        await message.answer(f"👑 User {user_id} is now an admin")
    except ValueError:
        await message.answer("❌ Invalid user ID")


@router.message(lambda m: m.text and m.text.startswith("/autosignals_on"))
async def cmd_autosignals_on(message: types.Message, db):
    """Enable auto signals."""
    settings_repo = SettingsRepository(db)
    await settings_repo.set_setting("auto_signals_enabled", "true")
    await message.answer("✅ Auto signals ENABLED")


@router.message(lambda m: m.text and m.text.startswith("/autosignals_off"))
async def cmd_autosignals_off(message: types.Message, db):
    """Disable auto signals."""
    settings_repo = SettingsRepository(db)
    await settings_repo.set_setting("auto_signals_enabled", "false")
    await message.answer("❌ Auto signals DISABLED")
