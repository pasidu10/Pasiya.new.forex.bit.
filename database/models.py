"""
Database models and initialization for the Telegram AI Trading Assistant.
"""
import aiosqlite
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

from config import settings


class DatabaseManager:
    """Manages database operations for the trading bot."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Establish database connection and create tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        return self

    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()

    async def _create_tables(self):
        """Create all necessary tables."""
        await self._create_users_table()
        await self._create_premium_table()
        await self._create_signals_table()
        await self._create_alerts_table()
        await self._create_statistics_table()
        await self._create_referrals_table()
        await self._create_settings_table()
        await self._create_signal_performance_table()

    async def _create_users_table(self):
        """Create users table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'en',
                is_active BOOLEAN DEFAULT TRUE,
                is_banned BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referral_code TEXT,
                referred_by INTEGER,
                free_signals_used INTEGER DEFAULT 0,
                settings TEXT DEFAULT '{}'
            )
        """)
        await self._connection.commit()

    async def _create_premium_table(self):
        """Create premium subscriptions table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS premium_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_type TEXT NOT NULL,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                payment_amount REAL,
                payment_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await self._connection.commit()

    async def _create_signals_table(self):
        """Create signals table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                market_type TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                take_profit_3 REAL,
                risk_reward_ratio REAL,
                confidence_score REAL,
                indicators TEXT DEFAULT '{}',
                patterns TEXT DEFAULT '[]',
                analysis_notes TEXT,
                created_by INTEGER,
                is_auto BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                expired_at TIMESTAMP,
                hit_target INTEGER DEFAULT 0,
                closed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        await self._connection.commit()

    async def _create_alerts_table(self):
        """Create price alerts table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                target_price REAL NOT NULL,
                condition_type TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_triggered BOOLEAN DEFAULT FALSE,
                triggered_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await self._connection.commit()

    async def _create_statistics_table(self):
        """Create statistics tracking table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                signals_generated INTEGER DEFAULT 0,
                signals_hit INTEGER DEFAULT 0,
                signals_missed INTEGER DEFAULT 0,
                total_users INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                premium_users INTEGER DEFAULT 0,
                premium_revenue REAL DEFAULT 0,
                messages_sent INTEGER DEFAULT 0,
                broadcasts_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._connection.commit()

    async def _create_referrals_table(self):
        """Create referrals tracking table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referral_code TEXT NOT NULL,
                referred_user_id INTEGER NOT NULL,
                reward_given BOOLEAN DEFAULT FALSE,
                reward_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users(id),
                FOREIGN KEY (referred_user_id) REFERENCES users(id)
            )
        """)
        await self._connection.commit()

    async def _create_settings_table(self):
        """Create bot settings table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._connection.commit()

    async def _create_signal_performance_table(self):
        """Create signal performance tracking table."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS signal_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                status TEXT,
                notes TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            )
        """)
        await self._connection.commit()

    async def execute(self, query: str, params: tuple = None):
        """Execute a SQL query."""
        if params:
            return await self._connection.execute(query, params)
        return await self._connection.execute(query)

    async def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch a single row."""
        async with self._connection.execute(query, params) if params else self._connection.execute(query) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows."""
        async with self._connection.execute(query, params) if params else self._connection.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def commit(self):
        """Commit transaction."""
        await self._connection.commit()
