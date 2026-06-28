"""
Keyboard generators for Telegram Bot.
"""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Optional, Dict


def get_main_menu_keyboard(language: str = "en") -> ReplyKeyboardMarkup:
    """Generate main menu keyboard."""
    labels = {
        "en": {
            "signal": "📊 Signals",
            "market": "📈 Market",
            "chart": "📊 Charts",
            "price": "💰 Prices",
            "news": "📰 News",
            "alert": "🔔 Alerts",
            "profile": "👤 Profile",
            "settings": "⚙️ Settings",
            "vip": "💎 Premium",
            "help": "❓ Help",
        },
        "si": {
            "signal": "📊 Signals",
            "market": "📈 Market",
            "chart": "📊 Charts",
            "price": "💰 Prices",
            "news": "📰 News",
            "alert": "🔔 Alerts",
            "profile": "👤 Profile",
            "settings": "⚙️ Settings",
            "vip": "💎 Premium",
            "help": "❓ Help",
        },
    }

    l = labels.get(language, labels["en"])

    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=l["signal"]),
        KeyboardButton(text=l["market"]),
    )
    builder.row(
        KeyboardButton(text=l["chart"]),
        KeyboardButton(text=l["price"]),
    )
    builder.row(
        KeyboardButton(text=l["news"]),
        KeyboardButton(text=l["alert"]),
    )
    builder.row(
        KeyboardButton(text=l["profile"]),
        KeyboardButton(text=l["settings"]),
    )
    builder.row(
        KeyboardButton(text=l["vip"]),
        KeyboardButton(text=l["help"]),
    )

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Generate admin panel keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Statistics"),
        KeyboardButton(text="📤 Broadcast"),
    )
    builder.row(
        KeyboardButton(text="📢 Post Signal"),
        KeyboardButton(text="🤖 Auto Signals"),
    )
    builder.row(
        KeyboardButton(text="👥 Users"),
        KeyboardButton(text="💎 Premium"),
    )
    builder.row(
        KeyboardButton(text="📺 Channels"),
        KeyboardButton(text="💬 Groups"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Settings"),
        KeyboardButton(text="🔙 Main Menu"),
    )

    return builder.as_markup(resize_keyboard=True)


def get_signal_keyboard(signal_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Generate signal action keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Analysis", callback_data=f"signal_analysis_{signal_id}"),
        InlineKeyboardButton(text="📈 Chart", callback_data=f"signal_chart_{signal_id}"),
    )

    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✏️ Edit", callback_data=f"signal_edit_{signal_id}"),
            InlineKeyboardButton(text="🗑️ Delete", callback_data=f"signal_delete_{signal_id}"),
        )

    builder.row(
        InlineKeyboardButton(text="📤 Share", callback_data=f"signal_share_{signal_id}"),
    )

    return builder.as_markup()


def get_market_keyboard(market_type: str = "crypto") -> InlineKeyboardMarkup:
    """Generate market selection keyboard."""
    builder = InlineKeyboardBuilder()

    if market_type == "crypto":
        coins = ["BTC", "ETH", "BNB", "XRP", "SOL", "DOGE", "ADA", "AVAX", "MATIC", "DOT"]
        for i in range(0, len(coins), 3):
            row = []
            for coin in coins[i:i+3]:
                row.append(
                    InlineKeyboardButton(
                        text=coin,
                        callback_data=f"market_coin_{coin}/USDT"
                    )
                )
            builder.row(*row)
    else:
        pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]
        for pair in pairs:
            builder.row(
                InlineKeyboardButton(text=pair, callback_data=f"market_pair_{pair}")
            )

    builder.row(
        InlineKeyboardButton(text="🔄 Refresh", callback_data="market_refresh"),
        InlineKeyboardButton(text="🔙 Back", callback_data="menu_main"),
    )

    return builder.as_markup()


def get_timeframe_keyboard() -> InlineKeyboardMarkup:
    """Generate timeframe selection keyboard."""
    builder = InlineKeyboardBuilder()

    timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    for i in range(0, len(timeframes), 3):
        row = []
        for tf in timeframes[i:i+3]:
            row.append(
                InlineKeyboardButton(text=tf, callback_data=f"timeframe_{tf}")
            )
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="menu_main")
    )

    return builder.as_markup()


def get_language_keyboard(current_lang: str = "en") -> InlineKeyboardMarkup:
    """Generate language selection keyboard."""
    builder = InlineKeyboardBuilder()

    languages = [
        ("English 🇺🇸", "en"),
        ("Sinhala 🇱🇰", "si"),
    ]

    for name, code in languages:
        marker = "✅ " if code == current_lang else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{marker}{name}",
                callback_data=f"lang_{code}"
            )
        )

    return builder.as_markup()


def get_confirmation_keyboard(action: str, item_id: int = None) -> InlineKeyboardMarkup:
    """Generate confirmation keyboard."""
    builder = InlineKeyboardBuilder()

    callback_data = f"confirm_{action}"
    if item_id:
        callback_data += f"_{item_id}"

    builder.row(
        InlineKeyboardButton(text="✅ Yes", callback_data=callback_data),
        InlineKeyboardButton(text="❌ No", callback_data=f"cancel_{action}"),
    )

    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """Generate pagination keyboard."""
    builder = InlineKeyboardBuilder()

    # Previous button
    if current_page > 1:
        builder.add(
            InlineKeyboardButton(
                text="◀️ Previous",
                callback_data=f"{callback_prefix}_page_{current_page - 1}"
            )
        )

    # Page indicator
    builder.add(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="page_info"
        )
    )

    # Next button
    if current_page < total_pages:
        builder.add(
            InlineKeyboardButton(
                text="Next ▶️",
                callback_data=f"{callback_prefix}_page_{current_page + 1}"
            )
        )

    return builder.as_markup()


def get_settings_keyboard(user_settings: dict) -> InlineKeyboardMarkup:
    """Generate settings keyboard."""
    builder = InlineKeyboardBuilder()

    # Language
    builder.row(
        InlineKeyboardButton(
            text="🌐 Language",
            callback_data="settings_language"
        )
    )

    # Notifications
    notif_status = "🟢" if user_settings.get("notifications", True) else "🔴"
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 Notifications {notif_status}",
            callback_data="settings_toggle_notifications"
        )
    )

    # Price alerts
    alert_status = "🟢" if user_settings.get("price_alerts", True) else "🔴"
    builder.row(
        InlineKeyboardButton(
            text=f"💰 Price Alerts {alert_status}",
            callback_data="settings_toggle_price_alerts"
        )
    )

    # Signal alerts
    signal_status = "🟢" if user_settings.get("signal_alerts", True) else "🔴"
    builder.row(
        InlineKeyboardButton(
            text=f"📊 Signal Alerts {signal_status}",
            callback_data="settings_toggle_signal_alerts"
        )
    )

    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="menu_main")
    )

    return builder.as_markup()


def get_vip_keyboard() -> InlineKeyboardMarkup:
    """Generate VIP subscription keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💎 Monthly - $29.99",
            callback_data="vip_monthly"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💎 Yearly - $299.99 (17% OFF)",
            callback_data="vip_yearly"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Enter Promo Code", callback_data="vip_promo")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="menu_main")
    )

    return builder.as_markup()


def get_alert_keyboard(alerts: List[dict]) -> InlineKeyboardMarkup:
    """Generate alerts list keyboard."""
    builder = InlineKeyboardBuilder()

    for alert in alerts[:8]:  # Max 8 alerts
        status = "🔔" if alert["is_active"] else "🔕"
        condition = "↑" if alert["condition_type"] == "above" else "↓"
        text = f"{status} {alert['symbol']} {condition} ${alert['target_price']}"
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"alert_view_{alert['id']}"
            )
        )

    if len(alerts) > 0:
        builder.row(
            InlineKeyboardButton(
                text="🗑️ Delete All",
                callback_data="alert_delete_all"
            )
        )

    builder.row(
        InlineKeyboardButton(text="➕ Add Alert", callback_data="alert_add"),
        InlineKeyboardButton(text="🔙 Back", callback_data="menu_main")
    )

    return builder.as_markup()


def get_admin_users_keyboard(users: List[dict], page: int = 1) -> InlineKeyboardMarkup:
    """Generate admin users list keyboard."""
    builder = InlineKeyboardBuilder()

    for user in users[:8]:
        status = "🟢" if user["is_active"] else "🔴"
        premium = "💎" if user["is_premium"] else ""
        admin = "👑" if user["is_admin"] else ""
        banned = "🚫" if user["is_banned"] else ""

        text = f"{status}{premium}{admin}{banned} {user['first_name'] or user['telegram_id']}"
        builder.row(
            InlineKeyboardButton(
                text=text[:30],
                callback_data=f"admin_user_{user['telegram_id']}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Back to Admin", callback_data="admin_menu")
    )

    return builder.as_markup()


def get_exchange_keyboard() -> InlineKeyboardMarkup:
    """Generate exchange selection keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🟡 Binance", callback_data="exchange_binance"),
        InlineKeyboardButton(text="🟠 Bybit", callback_data="exchange_bybit"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Forex", callback_data="exchange_forex"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="market_main")
    )

    return builder.as_markup()
