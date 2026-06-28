"""
Supabase database integration for the Telegram AI Trading Assistant.
Provides cloud-based PostgreSQL storage with real-time capabilities.
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from supabase import create_client, Client
from postgrest import APIError

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseManager:
    """Supabase database manager for cloud storage."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._is_connected = False

    @property
    def client(self) -> Optional[Client]:
        return self._client

    async def connect(self) -> bool:
        """Initialize Supabase connection."""
        if not settings.use_supabase:
            logger.info("Supabase not configured, using SQLite fallback")
            return False

        try:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            self._is_connected = True
            logger.info("Supabase connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            self._is_connected = False
            return False

    async def close(self):
        """Close Supabase connection (if needed)."""
        self._is_connected = False
        logger.info("Supabase connection closed")

    def is_connected(self) -> bool:
        """Check if connected to Supabase."""
        return self._is_connected and self._client is not None

    # ============ USER OPERATIONS ============

    async def create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        language: str = "en",
        referral_code: str = None,
        referred_by: int = None,
    ) -> Optional[Dict]:
        """Create a new user in Supabase."""
        if not self.is_connected():
            return None

        try:
            user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "language": language,
                "referral_code": referral_code,
                "referred_by": referred_by,
                "is_active": True,
                "is_banned": False,
                "is_admin": False,
                "is_premium": False,
                "free_signals_used": 0,
                "settings": {},
            }

            response = self._client.table("users").insert(user_data).execute()
            return response.data[0] if response.data else None

        except APIError as e:
            if "duplicate" in str(e).lower():
                # User already exists, return existing
                return await self.get_user(telegram_id)
            logger.error(f"Error creating user: {e}")
            return None

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID."""
        if not self.is_connected():
            return None

        try:
            response = self._client.table("users").select("*").eq("telegram_id", telegram_id).execute()
            return response.data[0] if response.data else None
        except APIError as e:
            logger.error(f"Error getting user: {e}")
            return None

    async def update_user(self, telegram_id: int, **kwargs) -> Optional[Dict]:
        """Update user fields."""
        if not self.is_connected():
            return None

        kwargs["updated_at"] = datetime.utcnow().isoformat()

        try:
            # Handle settings JSON field
            if "settings" in kwargs and isinstance(kwargs["settings"], dict):
                kwargs["settings"] = json.dumps(kwargs["settings"])

            response = self._client.table("users").update(kwargs).eq("telegram_id", telegram_id).execute()
            return response.data[0] if response.data else None
        except APIError as e:
            logger.error(f"Error updating user: {e}")
            return None

    async def get_all_users(self) -> List[Dict]:
        """Get all users."""
        if not self.is_connected():
            return []

        try:
            response = self._client.table("users").select("*").order("created_at", desc=True).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_active_users(self) -> List[Dict]:
        """Get all active users."""
        if not self.is_connected():
            return []

        try:
            response = self._client.table("users").select("*").eq("is_active", True).eq("is_banned", False).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting active users: {e}")
            return []

    async def get_premium_users(self) -> List[Dict]:
        """Get all premium users."""
        if not self.is_connected():
            return []

        try:
            response = self._client.table("users").select("*").eq("is_premium", True).eq("is_active", True).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting premium users: {e}")
            return []

    async def count_users(self) -> int:
        """Count total users."""
        if not self.is_connected():
            return 0

        try:
            response = self._client.table("users").select("id", count="exact").execute()
            return response.count if response.count else 0
        except APIError as e:
            logger.error(f"Error counting users: {e}")
            return 0

    # ============ SIGNAL OPERATIONS ============

    async def create_signal(self, signal_data: Dict) -> Optional[Dict]:
        """Create a new signal."""
        if not self.is_connected():
            return None

        try:
            # Convert JSON fields
            if "indicators" in signal_data and isinstance(signal_data["indicators"], dict):
                signal_data["indicators"] = json.dumps(signal_data["indicators"])
            if "patterns" in signal_data and isinstance(signal_data["patterns"], list):
                signal_data["patterns"] = json.dumps(signal_data["patterns"])

            response = self._client.table("signals").insert(signal_data).execute()
            return response.data[0] if response.data else None
        except APIError as e:
            logger.error(f"Error creating signal: {e}")
            return None

    async def get_signal(self, signal_id: int) -> Optional[Dict]:
        """Get signal by ID."""
        if not self.is_connected():
            return None

        try:
            response = self._client.table("signals").select("*").eq("id", signal_id).execute()
            return response.data[0] if response.data else None
        except APIError as e:
            logger.error(f"Error getting signal: {e}")
            return None

    async def get_active_signals(self) -> List[Dict]:
        """Get all active signals."""
        if not self.is_connected():
            return []

        try:
            response = self._client.table("signals").select("*").eq("is_active", True).eq("closed", False).order("created_at", desc=True).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting active signals: {e}")
            return []

    async def update_signal(self, signal_id: int, **kwargs) -> Optional[Dict]:
        """Update signal fields."""
        if not self.is_connected():
            return None

        kwargs["updated_at"] = datetime.utcnow().isoformat()

        try:
            response = self._client.table("signals").update(kwargs).eq("id", signal_id).execute()
            return response.data[0] if response.data else None
        except APIError as e:
            logger.error(f"Error updating signal: {e}")
            return None

    async def get_signal_performance(self, days: int = 30) -> Dict:
        """Get signal performance statistics."""
        if not self.is_connected():
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0}

        try:
            from datetime import timedelta
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            # Get all signals in date range
            response = self._client.table("signals").select("*").gte("created_at", start_date).execute()
            signals = response.data

            if not signals:
                return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0}

            total = len(signals)
            wins = sum(1 for s in signals if s.get("hit_target", 0) > 0)
            losses = total - wins

            return {
                "total": total,
                "wins": wins,
                "losses": losses,
                "win_rate": (wins / total * 100) if total > 0 else 0,
            }
        except APIError as e:
            logger.error(f"Error getting signal performance: {e}")
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
        if not self.is_connected():
            return None

        try:
            alert_data = {
                "user_id": user_id,
                "symbol": symbol,
                "alert_type": alert_type,
                "target_price": target_price,
                "condition_type": condition_type,
                "is_active": True,
                "is_triggered": False,
            }

            response = self._client.table("alerts").insert(alert_data).execute()
            return response.data[0] if response.data else None
        except APIError as e:
            logger.error(f"Error creating alert: {e}")
            return None

    async def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Get all alerts for a user."""
        if not self.is_connected():
            return []

        try:
            query = self._client.table("alerts").select("*").eq("user_id", user_id)
            if active_only:
                query = query.eq("is_active", True).eq("is_triggered", False)

            response = query.order("created_at", desc=True).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting user alerts: {e}")
            return []

    async def get_all_active_alerts(self) -> List[Dict]:
        """Get all active alerts."""
        if not self.is_connected():
            return []

        try:
            response = self._client.table("alerts").select("*").eq("is_active", True).eq("is_triggered", False).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting all active alerts: {e}")
            return []

    async def trigger_alert(self, alert_id: int) -> bool:
        """Mark alert as triggered."""
        if not self.is_connected():
            return False

        try:
            self._client.table("alerts").update({
                "is_triggered": True,
                "triggered_at": datetime.utcnow().isoformat()
            }).eq("id", alert_id).execute()
            return True
        except APIError as e:
            logger.error(f"Error triggering alert: {e}")
            return False

    async def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert."""
        if not self.is_connected():
            return False

        try:
            self._client.table("alerts").delete().eq("id", alert_id).execute()
            return True
        except APIError as e:
            logger.error(f"Error deleting alert: {e}")
            return False

    # ============ STATISTICS OPERATIONS ============

    async def increment_stat(self, stat_name: str, value: int = 1, date: str = None):
        """Increment a daily statistic."""
        if not self.is_connected():
            return

        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            # Try to get existing record
            response = self._client.table("statistics").select("*").eq("date", date).execute()

            if response.data:
                # Update existing
                current_value = response.data[0].get(stat_name, 0) or 0
                self._client.table("statistics").update({
                    stat_name: current_value + value
                }).eq("date", date).execute()
            else:
                # Create new
                self._client.table("statistics").insert({
                    "date": date,
                    stat_name: value
                }).execute()
        except APIError as e:
            logger.error(f"Error incrementing stat: {e}")

    async def get_statistics(self, days: int = 7) -> List[Dict]:
        """Get statistics for the past N days."""
        if not self.is_connected():
            return []

        try:
            from datetime import timedelta
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

            response = self._client.table("statistics").select("*").gte("date", start_date).order("date", desc=True).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error getting statistics: {e}")
            return []

    # ============ SETTINGS OPERATIONS ============

    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value."""
        if not self.is_connected():
            return None

        try:
            response = self._client.table("bot_settings").select("value").eq("key", key).execute()
            return response.data[0]["value"] if response.data else None
        except APIError as e:
            logger.error(f"Error getting setting: {e}")
            return None

    async def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        if not self.is_connected():
            return False

        try:
            self._client.table("bot_settings").upsert({
                "key": key,
                "value": value,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            return True
        except APIError as e:
            logger.error(f"Error setting setting: {e}")
            return False

    async def get_all_settings(self) -> Dict[str, str]:
        """Get all settings."""
        if not self.is_connected():
            return {}

        try:
            response = self._client.table("bot_settings").select("key, value").execute()
            return {row["key"]: row["value"] for row in response.data}
        except APIError as e:
            logger.error(f"Error getting all settings: {e}")
            return {}


# Create singleton instance
supabase_manager = SupabaseManager()
