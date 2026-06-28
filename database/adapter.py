"""
Unified database adapter that works with both Supabase and SQLite.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import secrets

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseAdapter:
    """
    Database adapter that provides a unified interface for both Supabase and SQLite.
    Automatically selects the appropriate backend based on configuration.
    """

    def __init__(self):
        self._backend = None
        self._is_supabase = False

    async def connect(self):
        """Connect to the appropriate database backend."""
        if settings.use_supabase:
            try:
                from .supabase_db import supabase_manager
                connected = await supabase_manager.connect()
                if connected:
                    self._backend = supabase_manager
                    self._is_supabase = True
                    logger.info("Using Supabase database")
                    return
            except Exception as e:
                logger.warning(f"Failed to connect to Supabase: {e}, falling back to SQLite")

        # Use SQLite as fallback
        from .models import DatabaseManager
        self._backend = DatabaseManager(settings.DATABASE_PATH)
        await self._backend.connect()
        self._is_supabase = False
        logger.info("Using SQLite database")

    async def close(self):
        """Close the database connection."""
        if self._backend:
            await self._backend.close()

    @property
    def is_supabase(self) -> bool:
        """Check if using Supabase backend."""
        return self._is_supabase

    # ============ USER OPERATIONS ============

    async def create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        language: str = "en",
        referred_by: int = None,
    ) -> Optional[Dict]:
        """Create a new user."""
        referral_code = secrets.token_hex(4).upper()

        if self._is_supabase:
            return await self._backend.create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language=language,
                referral_code=referral_code,
                referred_by=referred_by,
            )
        else:
            query = """
                INSERT INTO users (telegram_id, username, first_name, last_name, language, referral_code, referred_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
            """
            return await self._backend.fetchone(
                query,
                (telegram_id, username, first_name, last_name, language, referral_code, referred_by),
            )

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID."""
        if self._is_supabase:
            return await self._backend.get_user(telegram_id)
        else:
            query = "SELECT * FROM users WHERE telegram_id = ?"
            return await self._backend.fetchone(query, (telegram_id,))

    async def update_user(self, telegram_id: int, **kwargs) -> Optional[Dict]:
        """Update user fields."""
        if not kwargs:
            return None

        if self._is_supabase:
            return await self._backend.update_user(telegram_id, **kwargs)
        else:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            kwargs["updated_at"] = datetime.utcnow()
            values = list(kwargs.values()) + [telegram_id]
            query = f"UPDATE users SET {set_clause}, updated_at = ? WHERE telegram_id = ? RETURNING *"
            return await self._backend.fetchone(query, tuple(values))

    async def update_last_interaction(self, telegram_id: int):
        """Update user's last interaction timestamp."""
        query = "UPDATE users SET last_interaction = CURRENT_TIMESTAMP WHERE telegram_id = ?"
        await self._backend.execute(query, (telegram_id,))
        if not self._is_supabase:
            await self._backend.commit()

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
        if self._is_supabase:
            return await self._backend.get_all_users()
        else:
            query = "SELECT * FROM users ORDER BY created_at DESC"
            return await self._backend.fetchall(query)

    async def get_active_users(self) -> List[Dict]:
        """Get all active users."""
        if self._is_supabase:
            return await self._backend.get_active_users()
        else:
            query = "SELECT * FROM users WHERE is_active = TRUE AND is_banned = FALSE"
            return await self._backend.fetchall(query)

    async def get_premium_users(self) -> List[Dict]:
        """Get all premium users."""
        if self._is_supabase:
            return await self._backend.get_premium_users()
        else:
            query = "SELECT * FROM users WHERE is_premium = TRUE AND is_active = TRUE"
            return await self._backend.fetchall(query)

    async def count_users(self) -> int:
        """Count total users."""
        if self._is_supabase:
            return await self._backend.count_users()
        else:
            query = "SELECT COUNT(*) as count FROM users"
            result = await self._backend.fetchone(query)
            return result["count"] if result else 0

    async def get_user_settings(self, telegram_id: int) -> Dict:
        """Get user settings."""
        user = await self.get_user(telegram_id)
        if user and user.get("settings"):
            settings_data = user["settings"]
            if isinstance(settings_data, str):
                return json.loads(settings_data)
            return settings_data
        return {}

    async def update_user_settings(self, telegram_id: int, settings_data: Dict):
        """Update user settings."""
        current_settings = await self.get_user_settings(telegram_id)
        current_settings.update(settings_data)
        return await self.update_user(telegram_id, settings=json.dumps(current_settings))

    # ============ SIGNAL OPERATIONS ============

    async def create_signal(self, signal_data: Dict) -> Optional[Dict]:
        """Create a new signal."""
        if self._is_supabase:
            return await self._backend.create_signal(signal_data)
        else:
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
            return await self._backend.fetchone(query, params)

    async def get_signal(self, signal_id: int) -> Optional[Dict]:
        """Get signal by ID."""
        if self._is_supabase:
            return await self._backend.get_signal(signal_id)
        else:
            query = "SELECT * FROM signals WHERE id = ?"
            return await self._backend.fetchone(query, (signal_id,))

    async def get_active_signals(self) -> List[Dict]:
        """Get all active signals."""
        if self._is_supabase:
            return await self._backend.get_active_signals()
        else:
            query = """
                SELECT * FROM signals
                WHERE is_active = TRUE AND closed = FALSE
                AND (expired_at IS NULL OR expired_at > CURRENT_TIMESTAMP)
                ORDER BY created_at DESC
            """
            return await self._backend.fetchall(query)

    async def update_signal(self, signal_id: int, **kwargs) -> Optional[Dict]:
        """Update signal fields."""
        if not kwargs:
            return None

        if self._is_supabase:
            return await self._backend.update_signal(signal_id, **kwargs)
        else:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            kwargs["updated_at"] = datetime.utcnow()
            values = list(kwargs.values()) + [signal_id]
            query = f"UPDATE signals SET {set_clause}, updated_at = ? WHERE id = ? RETURNING *"
            return await self._backend.fetchone(query, tuple(values))

    async def close_signal(self, signal_id: int, hit_target: int) -> Optional[Dict]:
        """Close a signal."""
        return await self.update_signal(signal_id, closed=True, hit_target=hit_target, is_active=False)

    async def expire_signal(self, signal_id: int) -> Optional[Dict]:
        """Expire a signal."""
        return await self.update_signal(signal_id, is_active=False, closed=True)

    async def get_signal_performance(self, days: int = 30) -> Dict:
        """Get signal performance statistics."""
        if self._is_supabase:
            return await self._backend.get_signal_performance(days)
        else:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN hit_target > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN closed = TRUE AND hit_target = 0 THEN 1 ELSE 0 END) as losses
                FROM signals
                WHERE created_at >= datetime('now', ?)
            """
            result = await self._backend.fetchone(query, (f"-{days} days",))
            if result and result["total"] > 0:
                return {
                    "total": result["total"],
                    "wins": result["wins"] or 0,
                    "losses": result["losses"] or 0,
                    "win_rate": (result["wins"] or 0) / result["total"] * 100,
                }
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0}

    # ============ ALERT OPERATIONS ============

    async def create_alert(
        self,
        user_id: int,
        symbol: str,
        alert_type: str,
        target_price: float,
        condition_type: str = "above",
    ) -> Optional[Dict]:
        """Create a new price alert."""
        if self._is_supabase:
            return await self._backend.create_alert(user_id, symbol, alert_type, target_price, condition_type)
        else:
            query = """
                INSERT INTO alerts (user_id, symbol, alert_type, target_price, condition_type)
                VALUES (?, ?, ?, ?, ?)
                RETURNING *
            """
            return await self._backend.fetchone(query, (user_id, symbol, alert_type, target_price, condition_type))

    async def get_alert(self, alert_id: int) -> Optional[Dict]:
        """Get alert by ID."""
        query = "SELECT * FROM alerts WHERE id = ?"
        return await self._backend.fetchone(query, (alert_id,))

    async def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Get all alerts for a user."""
        if self._is_supabase:
            return await self._backend.get_user_alerts(user_id, active_only)
        else:
            if active_only:
                query = """
                    SELECT * FROM alerts
                    WHERE user_id = ? AND is_active = TRUE AND is_triggered = FALSE
                    ORDER BY created_at DESC
                """
            else:
                query = "SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC"
            return await self._backend.fetchall(query, (user_id,))

    async def get_all_active_alerts(self) -> List[Dict]:
        """Get all active alerts across all users."""
        if self._is_supabase:
            return await self._backend.get_all_active_alerts()
        else:
            query = "SELECT * FROM alerts WHERE is_active = TRUE AND is_triggered = FALSE"
            return await self._backend.fetchall(query)

    async def trigger_alert(self, alert_id: int) -> bool:
        """Mark alert as triggered."""
        if self._is_supabase:
            return await self._backend.trigger_alert(alert_id)
        else:
            query = """
                UPDATE alerts SET is_triggered = TRUE, triggered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            await self._backend.execute(query, (alert_id,))
            await self._backend.commit()
            return True

    async def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert."""
        if self._is_supabase:
            return await self._backend.delete_alert(alert_id)
        else:
            query = "DELETE FROM alerts WHERE id = ?"
            await self._backend.execute(query, (alert_id,))
            await self._backend.commit()
            return True

    # ============ STATISTICS OPERATIONS ============

    async def increment_stat(self, stat_name: str, value: int = 1, date: str = None):
        """Increment a daily statistic."""
        if self._is_supabase:
            return await self._backend.increment_stat(stat_name, value, date)

        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        # SQLite handling
        query = """
            INSERT INTO statistics (date) VALUES (?)
            ON CONFLICT(date) DO UPDATE SET date = date
        """
        await self._backend.execute(query, (date,))

        update_query = f"""
            UPDATE statistics SET {stat_name} = {stat_name} + ?
            WHERE date = ?
        """
        await self._backend.execute(update_query, (value, date))
        await self._backend.commit()

    async def get_statistics(self, days: int = 7) -> List[Dict]:
        """Get statistics for the past N days."""
        if self._is_supabase:
            return await self._backend.get_statistics(days)
        else:
            query = """
                SELECT * FROM statistics
                WHERE date >= date('now', ?)
                ORDER BY date DESC
            """
            return await self._backend.fetchall(query, (f"-{days} days",))

    # ============ SETTINGS OPERATIONS ============

    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value."""
        if self._is_supabase:
            return await self._backend.get_setting(key)
        else:
            query = "SELECT value FROM bot_settings WHERE key = ?"
            result = await self._backend.fetchone(query, (key,))
            return result["value"] if result else None

    async def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        if self._is_supabase:
            return await self._backend.set_setting(key, value)
        else:
            query = """
                INSERT INTO bot_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """
            await self._backend.execute(query, (key, value, value))
            await self._backend.commit()
            return True

    async def get_all_settings(self) -> Dict[str, str]:
        """Get all settings."""
        if self._is_supabase:
            return await self._backend.get_all_settings()
        else:
            query = "SELECT key, value FROM bot_settings"
            rows = await self._backend.fetchall(query)
            return {row["key"]: row["value"] for row in rows}

    # ============ RAW QUERY METHODS (for SQLite compatibility) ============

    async def execute(self, query: str, params: tuple = None):
        """Execute a raw SQL query (SQLite only)."""
        if not self._is_supabase:
            if params:
                return await self._backend.execute(query, params)
            return await self._backend.execute(query)
        raise NotImplementedError("Raw execute is not available for Supabase")

    async def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch a single row (SQLite only)."""
        if not self._is_supabase:
            async with self._backend.execute(query, params) if params else self._backend.execute(query) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        raise NotImplementedError("fetchone is not available for Supabase, use specific methods")

    async def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows (SQLite only)."""
        if not self._is_supabase:
            async with self._backend.execute(query, params) if params else self._backend.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        raise NotImplementedError("fetchall is not available for Supabase, use specific methods")

    async def commit(self):
        """Commit transaction (SQLite only)."""
        if not self._is_supabase:
            await self._backend.commit()


# Create singleton instance
db_adapter = DatabaseAdapter()
