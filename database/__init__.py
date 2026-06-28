"""
Database module for Telegram AI Trading Assistant.
Supports both Supabase (PostgreSQL) and SQLite (local fallback).
"""
from config import settings

# Import both database implementations
from .models import DatabaseManager as SQLiteDatabaseManager
from .supabase_db import SupabaseManager, supabase_manager

__all__ = [
    "get_database",
    "SQLiteDatabaseManager",
    "SupabaseManager",
    "supabase_manager",
]


async def get_database():
    """
    Get the appropriate database manager based on configuration.
    Returns SupabaseManager if Supabase is configured, else SQLiteDatabaseManager.
    """
    if settings.use_supabase:
        # Try to connect to Supabase
        connected = await supabase_manager.connect()
        if connected:
            return supabase_manager

    # Fall back to SQLite
    db = SQLiteDatabaseManager(settings.DATABASE_PATH)
    await db.connect()
    return db

