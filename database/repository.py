"""
Repository classes for database operations.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import secrets

from .models import DatabaseManager


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        language: str = "en",
        referred_by: int = None,
    ) -> Dict:
        """Create a new user."""
        referral_code = secrets.token_hex(4).upper()
        query = """
            INSERT INTO users (telegram_id, username, first_name, last_name, language, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING *
        """
        return await self.db.fetchone(
            query,
            (telegram_id, username, first_name, last_name, language, referral_code, referred_by),
        )

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID."""
        query = "SELECT * FROM users WHERE telegram_id = ?"
        return await self.db.fetchone(query, (telegram_id,))

    async def get_user_by_referral_code(self, referral_code: str) -> Optional[Dict]:
        """Get user by referral code."""
        query = "SELECT * FROM users WHERE referral_code = ?"
        return await self.db.fetchone(query, (referral_code,))

    async def update_user(self, telegram_id: int, **kwargs) -> Optional[Dict]:
        """Update user fields."""
        if not kwargs:
            return None
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        kwargs["updated_at"] = datetime.utcnow()
        values = list(kwargs.values()) + [telegram_id]
        query = f"UPDATE users SET {set_clause}, updated_at = ? WHERE telegram_id = ? RETURNING *"
        return await self.db.fetchone(query, tuple(values))

    async def update_last_interaction(self, telegram_id: int):
        """Update user's last interaction timestamp."""
        query = "UPDATE users SET last_interaction = CURRENT_TIMESTAMP WHERE telegram_id = ?"
        await self.db.execute(query, (telegram_id,))
        await self.db.commit()

    async def ban_user(self, telegram_id: int) -> Optional[Dict]:
        """Ban a user."""
        return await self.update_user(telegram_id, is_banned=True)

    async def unban_user(self, telegram_id: int) -> Optional[Dict]:
        """Unban a user."""
        return await self.update_user(telegram_id, is_banned=False)

    async def set_admin(self, telegram_id: int, is_admin: bool = True) -> Optional[Dict]:
        """Set user as admin."""
        return await self.update_user(telegram_id, is_admin=is_admin)

    async def set_premium(self, telegram_id: int, is_premium: bool = True) -> Optional[Dict]:
        """Set user premium status."""
        return await self.update_user(telegram_id, is_premium=is_premium)

    async def get_all_users(self) -> List[Dict]:
        """Get all users."""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        return await self.db.fetchall(query)

    async def get_active_users(self) -> List[Dict]:
        """Get all active users."""
        query = "SELECT * FROM users WHERE is_active = TRUE AND is_banned = FALSE"
        return await self.db.fetchall(query)

    async def get_premium_users(self) -> List[Dict]:
        """Get all premium users."""
        query = "SELECT * FROM users WHERE is_premium = TRUE AND is_active = TRUE"
        return await self.db.fetchall(query)

    async def get_admin_users(self) -> List[Dict]:
        """Get all admin users."""
        query = "SELECT * FROM users WHERE is_admin = TRUE"
        return await self.db.fetchall(query)

    async def count_users(self) -> int:
        """Count total users."""
        query = "SELECT COUNT(*) as count FROM users"
        result = await self.db.fetchone(query)
        return result["count"] if result else 0

    async def count_active_users(self) -> int:
        """Count active users."""
        query = "SELECT COUNT(*) as count FROM users WHERE is_active = TRUE AND is_banned = FALSE"
        result = await self.db.fetchone(query)
        return result["count"] if result else 0

    async def increment_free_signals(self, telegram_id: int) -> Optional[Dict]:
        """Increment user's free signal usage."""
        query = "UPDATE users SET free_signals_used = free_signals_used + 1 WHERE telegram_id = ? RETURNING *"
        return await self.db.fetchone(query, (telegram_id,))

    async def get_user_settings(self, telegram_id: int) -> Dict:
        """Get user settings."""
        user = await self.get_user(telegram_id)
        if user and user.get("settings"):
            return json.loads(user["settings"])
        return {}

    async def update_user_settings(self, telegram_id: int, settings: Dict):
        """Update user settings."""
        current_settings = await self.get_user_settings(telegram_id)
        current_settings.update(settings)
        return await self.update_user(telegram_id, settings=json.dumps(current_settings))


class SignalRepository:
    """Repository for signal-related database operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_signal(self, signal_data: Dict) -> Dict:
        """Create a new signal."""
        query = """
            INSERT INTO signals (
                symbol, market_type, signal_type, timeframe, entry_price,
                stop_loss, take_profit_1, take_profit_2, take_profit_3,
                risk_reward_ratio, confidence_score, indicators, patterns,
                analysis_notes, created_by, is_auto, expired_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
        """
        params = (
            signal_data.get("symbol"),
            signal_data.get("market_type"),
            signal_data.get("signal_type"),
            signal_data.get("timeframe"),
            signal_data.get("entry_price"),
            signal_data.get("stop_loss"),
            signal_data.get("take_profit_1"),
            signal_data.get("take_profit_2"),
            signal_data.get("take_profit_3"),
            signal_data.get("risk_reward_ratio"),
            signal_data.get("confidence_score"),
            json.dumps(signal_data.get("indicators", {})),
            json.dumps(signal_data.get("patterns", [])),
            signal_data.get("analysis_notes"),
            signal_data.get("created_by"),
            signal_data.get("is_auto", False),
            signal_data.get("expired_at"),
        )
        return await self.db.fetchone(query, params)

    async def get_signal(self, signal_id: int) -> Optional[Dict]:
        """Get signal by ID."""
        query = "SELECT * FROM signals WHERE id = ?"
        return await self.db.fetchone(query, (signal_id,))

    async def get_active_signals(self) -> List[Dict]:
        """Get all active signals."""
        query = """
            SELECT * FROM signals
            WHERE is_active = TRUE AND closed = FALSE
            AND (expired_at IS NULL OR expired_at > CURRENT_TIMESTAMP)
            ORDER BY created_at DESC
        """
        return await self.db.fetchall(query)

    async def get_signals_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get signals by symbol."""
        query = """
            SELECT * FROM signals WHERE symbol = ?
            ORDER BY created_at DESC LIMIT ?
        """
        return await self.db.fetchall(query, (symbol, limit))

    async def update_signal(self, signal_id: int, **kwargs) -> Optional[Dict]:
        """Update signal fields."""
        if not kwargs:
            return None
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        kwargs["updated_at"] = datetime.utcnow()
        values = list(kwargs.values()) + [signal_id]
        query = f"UPDATE signals SET {set_clause}, updated_at = ? WHERE id = ? RETURNING *"
        return await self.db.fetchone(query, tuple(values))

    async def close_signal(self, signal_id: int, hit_target: int) -> Optional[Dict]:
        """Close a signal."""
        return await self.update_signal(signal_id, closed=True, hit_target=hit_target, is_active=False)

    async def expire_signal(self, signal_id: int) -> Optional[Dict]:
        """Expire a signal."""
        return await self.update_signal(signal_id, is_active=False, closed=True)

    async def get_daily_signals_count(self) -> int:
        """Get count of signals created today."""
        query = """
            SELECT COUNT(*) as count FROM signals
            WHERE DATE(created_at) = DATE('now')
        """
        result = await self.db.fetchone(query)
        return result["count"] if result else 0

    async def get_signal_performance(self, days: int = 30) -> Dict:
        """Get signal performance statistics."""
        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN hit_target > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN closed = TRUE AND hit_target = 0 THEN 1 ELSE 0 END) as losses
            FROM signals
            WHERE created_at >= datetime('now', ?)
        """
        result = await self.db.fetchone(query, (f"-{days} days",))
        if result and result["total"] > 0:
            return {
                "total": result["total"],
                "wins": result["wins"] or 0,
                "losses": result["losses"] or 0,
                "win_rate": (result["wins"] or 0) / result["total"] * 100,
            }
        return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0}

    async def add_performance_entry(self, signal_id: int, price: float, status: str, notes: str = None):
        """Add a performance tracking entry."""
        query = """
            INSERT INTO signal_performance (signal_id, price, status, notes)
            VALUES (?, ?, ?, ?)
        """
        await self.db.execute(query, (signal_id, price, status, notes))
        await self.db.commit()


class AlertRepository:
    """Repository for alert-related database operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_alert(
        self,
        user_id: int,
        symbol: str,
        alert_type: str,
        target_price: float,
        condition_type: str = "above",
    ) -> Dict:
        """Create a new price alert."""
        query = """
            INSERT INTO alerts (user_id, symbol, alert_type, target_price, condition_type)
            VALUES (?, ?, ?, ?, ?)
            RETURNING *
        """
        return await self.db.fetchone(query, (user_id, symbol, alert_type, target_price, condition_type))

    async def get_alert(self, alert_id: int) -> Optional[Dict]:
        """Get alert by ID."""
        query = "SELECT * FROM alerts WHERE id = ?"
        return await self.db.fetchone(query, (alert_id,))

    async def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Get all alerts for a user."""
        if active_only:
            query = """
                SELECT * FROM alerts
                WHERE user_id = ? AND is_active = TRUE AND is_triggered = FALSE
                ORDER BY created_at DESC
            """
        else:
            query = "SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC"
        return await self.db.fetchall(query, (user_id,))

    async def get_all_active_alerts(self) -> List[Dict]:
        """Get all active alerts across all users."""
        query = """
            SELECT * FROM alerts WHERE is_active = TRUE AND is_triggered = FALSE
        """
        return await self.db.fetchall(query)

    async def trigger_alert(self, alert_id: int) -> Optional[Dict]:
        """Mark alert as triggered."""
        query = """
            UPDATE alerts SET is_triggered = TRUE, triggered_at = CURRENT_TIMESTAMP
            WHERE id = ? RETURNING *
        """
        return await self.db.fetchone(query, (alert_id,))

    async def delete_alert(self, alert_id: int):
        """Delete an alert."""
        query = "DELETE FROM alerts WHERE id = ?"
        await self.db.execute(query, (alert_id,))
        await self.db.commit()

    async def deactivate_alert(self, alert_id: int) -> Optional[Dict]:
        """Deactivate an alert."""
        query = "UPDATE alerts SET is_active = FALSE WHERE id = ? RETURNING *"
        return await self.db.fetchone(query, (alert_id,))


class StatisticsRepository:
    """Repository for statistics-related database operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_or_create_daily_stats(self, date: str = None) -> Dict:
        """Get or create daily statistics."""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        query = """
            INSERT INTO statistics (date) VALUES (?)
            ON CONFLICT(date) DO UPDATE SET date = date
            RETURNING *
        """
        return await self.db.fetchone(query, (date,))

    async def increment_stat(self, stat_name: str, value: int = 1, date: str = None):
        """Increment a daily statistic."""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        await self.get_or_create_daily_stats(date)
        query = f"""
            UPDATE statistics SET {stat_name} = {stat_name} + ?
            WHERE date = ?
        """
        await self.db.execute(query, (value, date))
        await self.db.commit()

    async def get_statistics(self, days: int = 7) -> List[Dict]:
        """Get statistics for the past N days."""
        query = """
            SELECT * FROM statistics
            WHERE date >= date('now', ?)
            ORDER BY date DESC
        """
        return await self.db.fetchall(query, (f"-{days} days",))

    async def get_summary_stats(self) -> Dict:
        """Get summary statistics."""
        query = """
            SELECT
                SUM(signals_generated) as total_signals,
                SUM(signals_hit) as total_hits,
                SUM(total_users) as total_user_count,
                SUM(new_users) as total_new_users,
                SUM(premium_revenue) as total_revenue,
                AVG(CAST(signals_hit AS FLOAT) / NULLIF(signals_generated, 0) * 100) as avg_win_rate
            FROM statistics
        """
        result = await self.db.fetchone(query)
        return result if result else {}


class SettingsRepository:
    """Repository for bot settings operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value."""
        query = "SELECT value FROM bot_settings WHERE key = ?"
        result = await self.db.fetchone(query, (key,))
        return result["value"] if result else None

    async def set_setting(self, key: str, value: str):
        """Set a setting value."""
        query = """
            INSERT INTO bot_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
        """
        await self.db.execute(query, (key, value, value))
        await self.db.commit()

    async def delete_setting(self, key: str):
        """Delete a setting."""
        query = "DELETE FROM bot_settings WHERE key = ?"
        await self.db.execute(query, (key,))
        await self.db.commit()

    async def get_all_settings(self) -> Dict[str, str]:
        """Get all settings."""
        query = "SELECT key, value FROM bot_settings"
        rows = await self.db.fetchall(query)
        return {row["key"]: row["value"] for row in rows}
