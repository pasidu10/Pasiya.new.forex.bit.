"""
Portfolio and watchlist management for users.
"""
from datetime import datetime
from typing import Dict, List, Optional
import json

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioManager:
    """Manage user portfolios and watchlists."""

    def __init__(self, db):
        self.db = db

    async def add_to_watchlist(self, user_id: int, symbol: str) -> bool:
        """Add a symbol to user's watchlist."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            watchlist = settings_data.get("watchlist", [])

            if symbol not in watchlist:
                watchlist.append(symbol)
                settings_data["watchlist"] = watchlist
                await self.db.update_user_settings(user_id, settings_data)
                return True
            return False

        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False

    async def remove_from_watchlist(self, user_id: int, symbol: str) -> bool:
        """Remove a symbol from user's watchlist."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            watchlist = settings_data.get("watchlist", [])

            if symbol in watchlist:
                watchlist.remove(symbol)
                settings_data["watchlist"] = watchlist
                await self.db.update_user_settings(user_id, settings_data)
                return True
            return False

        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            return False

    async def get_watchlist(self, user_id: int) -> List[str]:
        """Get user's watchlist."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            return settings_data.get("watchlist", [])
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []

    async def clear_watchlist(self, user_id: int) -> bool:
        """Clear user's watchlist."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            settings_data["watchlist"] = []
            await self.db.update_user_settings(user_id, settings_data)
            return True
        except Exception as e:
            logger.error(f"Error clearing watchlist: {e}")
            return False

    async def add_portfolio_position(
        self,
        user_id: int,
        symbol: str,
        entry_price: float,
        size: float,
        position_type: str = "long",
        notes: str = None,
    ) -> Optional[Dict]:
        """Add a portfolio position."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            portfolio = settings_data.get("portfolio", [])

            position = {
                "id": len(portfolio) + 1,
                "symbol": symbol,
                "entry_price": entry_price,
                "current_price": entry_price,
                "size": size,
                "position_type": position_type,
                "notes": notes,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            portfolio.append(position)
            settings_data["portfolio"] = portfolio
            await self.db.update_user_settings(user_id, settings_data)

            return position

        except Exception as e:
            logger.error(f"Error adding portfolio position: {e}")
            return None

    async def update_portfolio_position(
        self,
        user_id: int,
        position_id: int,
        **kwargs
    ) -> bool:
        """Update a portfolio position."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            portfolio = settings_data.get("portfolio", [])

            for i, pos in enumerate(portfolio):
                if pos.get("id") == position_id:
                    portfolio[i].update(kwargs)
                    portfolio[i]["updated_at"] = datetime.utcnow().isoformat()
                    settings_data["portfolio"] = portfolio
                    await self.db.update_user_settings(user_id, settings_data)
                    return True

            return False

        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            return False

    async def close_portfolio_position(
        self,
        user_id: int,
        position_id: int,
        exit_price: float,
    ) -> Optional[Dict]:
        """Close a portfolio position."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            portfolio = settings_data.get("portfolio", [])
            trades = settings_data.get("trades", [])

            for i, pos in enumerate(portfolio):
                if pos.get("id") == position_id:
                    # Calculate P/L
                    if pos.get("position_type") == "long":
                        pnl = (exit_price - pos["entry_price"]) * pos["size"]
                        pnl_percent = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * 100
                    else:
                        pnl = (pos["entry_price"] - exit_price) * pos["size"]
                        pnl_percent = ((pos["entry_price"] - exit_price) / pos["entry_price"]) * 100

                    # Create trade record
                    trade = {
                        "id": len(trades) + 1,
                        "symbol": pos["symbol"],
                        "entry_price": pos["entry_price"],
                        "exit_price": exit_price,
                        "size": pos["size"],
                        "position_type": pos["position_type"],
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                        "opened_at": pos["created_at"],
                        "closed_at": datetime.utcnow().isoformat(),
                    }

                    trades.append(trade)
                    portfolio.pop(i)

                    settings_data["portfolio"] = portfolio
                    settings_data["trades"] = trades
                    await self.db.update_user_settings(user_id, settings_data)

                    return trade

            return None

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None

    async def get_portfolio(self, user_id: int) -> List[Dict]:
        """Get user's portfolio positions."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            return settings_data.get("portfolio", [])
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return []

    async def get_trade_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's trade history."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            trades = settings_data.get("trades", [])
            return trades[-limit:] if trades else []
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    async def calculate_portfolio_value(self, user_id: int, exchange_manager) -> Dict:
        """Calculate portfolio value with current prices."""
        try:
            portfolio = await self.get_portfolio(user_id)

            if not portfolio:
                return {"total_value": 0, "positions": [], "pnl": 0}

            total_entry_value = 0
            total_current_value = 0
            positions = []

            for pos in portfolio:
                symbol = pos["symbol"]
                entry_price = pos["entry_price"]
                size = pos["size"]
                position_type = pos.get("position_type", "long")

                # Get current price
                try:
                    exchange_type = "forex" if "/" in symbol and "USDT" not in symbol else "binance"
                    ticker = await exchange_manager.get_ticker(symbol, exchange_type)
                    current_price = ticker.get("last", entry_price) if ticker else entry_price
                except Exception:
                    current_price = entry_price

                # Calculate values
                entry_value = entry_price * size
                current_value = current_price * size

                if position_type == "long":
                    pnl = current_value - entry_value
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl = entry_value - current_value
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100

                total_entry_value += entry_value
                total_current_value += current_value if position_type == "long" else entry_value - pnl

                positions.append({
                    **pos,
                    "current_price": current_price,
                    "entry_value": entry_value,
                    "current_value": current_value,
                    "pnl": pnl,
                    "pnl_percent": pnl_percent,
                })

            total_pnl = total_current_value - total_entry_value

            return {
                "total_entry_value": total_entry_value,
                "total_current_value": total_current_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": (total_pnl / total_entry_value * 100) if total_entry_value > 0 else 0,
                "positions": positions,
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}")
            return {"total_value": 0, "positions": [], "pnl": 0, "error": str(e)}

    async def add_favorite_market(self, user_id: int, market: str) -> bool:
        """Add a favorite market."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            favorites = settings_data.get("favorite_markets", [])

            if market not in favorites:
                favorites.append(market)
                settings_data["favorite_markets"] = favorites
                await self.db.update_user_settings(user_id, settings_data)
                return True
            return False

        except Exception as e:
            logger.error(f"Error adding favorite market: {e}")
            return False

    async def get_favorite_markets(self, user_id: int) -> List[str]:
        """Get user's favorite markets."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            return settings_data.get("favorite_markets", ["crypto"])  # Default to crypto
        except Exception as e:
            logger.error(f"Error getting favorite markets: {e}")
            return ["crypto"]

    def format_watchlist(self, watchlist: List[str], prices: Dict = None) -> str:
        """Format watchlist for display."""
        if not watchlist:
            return "📋 **Watchlist**\n\nYour watchlist is empty.\nUse `/watchlist add SYMBOL` to add."

        lines = ["📋 **Your Watchlist**", ""]

        for i, symbol in enumerate(watchlist, 1):
            if prices and symbol in prices:
                price = prices[symbol]
                lines.append(f"{i}. `{symbol}` - `{price:,.8f}`")
            else:
                lines.append(f"{i}. `{symbol}`")

        return "\n".join(lines)

    def format_portfolio(self, portfolio_data: Dict) -> str:
        """Format portfolio for display."""
        if not portfolio_data.get("positions"):
            return "💼 **Portfolio**\n\nNo open positions.\nUse `/portfolio add` to track a trade."

        lines = [
            "💼 **Your Portfolio**",
            "",
            f"📊 **Summary:**",
            f"  Entry Value: `${portfolio_data['total_entry_value']:,.2f}`",
            f"  Current Value: `${portfolio_data['total_current_value']:,.2f}`",
            f"  P/L: `${portfolio_data['total_pnl']:,.2f}` ({portfolio_data['total_pnl_percent']:+.2f}%)",
            "",
            "**Positions:**",
        ]

        for pos in portfolio_data["positions"]:
            emoji = "🟢" if pos["pnl"] >= 0 else "🔴"
            lines.append(
                f"{emoji} **{pos['symbol']}** ({pos['position_type'].upper()})"
            )
            lines.append(f"   Entry: `{pos['entry_price']:,.8f}`")
            lines.append(f"   Current: `{pos['current_price']:,.8f}`")
            lines.append(f"   P/L: `${pos['pnl']:,.2f}` ({pos['pnl_percent']:+.2f}%)")

        return "\n".join(lines)

    def format_trade_history(self, trades: List[Dict], limit: int = 10) -> str:
        """Format trade history."""
        if not trades:
            return "📜 **Trade History**\n\nNo trades recorded yet."

        lines = ["📜 **Recent Trades**", ""]

        for trade in trades[-limit:]:
            emoji = "✅" if trade["pnl"] >= 0 else "❌"
            lines.append(f"{emoji} **{trade['symbol']}**")
            lines.append(f"   Entry: `{trade['entry_price']:,.8f}` → Exit: `{trade['exit_price']:,.8f}`")
            lines.append(f"   P/L: `${trade['pnl']:,.2f}` ({trade['pnl_percent']:+.2f}%)")
            lines.append("")

        # Calculate totals
        total_pnl = sum(t["pnl"] for t in trades)
        win_rate = (sum(1 for t in trades if t["pnl"] > 0) / len(trades) * 100) if trades else 0

        lines.extend([
            "**Summary:**",
            f"  Total Trades: `{len(trades)}`",
            f"  Win Rate: `{win_rate:.1f}%`",
            f"  Total P/L: `${total_pnl:,.2f}`",
        ])

        return "\n".join(lines)


class TradingJournal:
    """Trading journal for user notes and analysis."""

    def __init__(self, db):
        self.db = db

    async def add_entry(
        self,
        user_id: int,
        symbol: str,
        entry_type: str,
        content: str,
        signal_id: int = None,
    ) -> Optional[Dict]:
        """Add a journal entry."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            journal = settings_data.get("trading_journal", [])

            entry = {
                "id": len(journal) + 1,
                "symbol": symbol,
                "entry_type": entry_type,
                "content": content,
                "signal_id": signal_id,
                "created_at": datetime.utcnow().isoformat(),
            }

            journal.append(entry)
            settings_data["trading_journal"] = journal
            await self.db.update_user_settings(user_id, settings_data)

            return entry

        except Exception as e:
            logger.error(f"Error adding journal entry: {e}")
            return None

    async def get_entries(
        self,
        user_id: int,
        symbol: str = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Get journal entries."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            journal = settings_data.get("trading_journal", [])

            if symbol:
                journal = [e for e in journal if e.get("symbol") == symbol]

            return journal[-limit:] if journal else []

        except Exception as e:
            logger.error(f"Error getting journal entries: {e}")
            return []

    async def delete_entry(self, user_id: int, entry_id: int) -> bool:
        """Delete a journal entry."""
        try:
            settings_data = await self.db.get_user_settings(user_id)
            journal = settings_data.get("trading_journal", [])

            journal = [e for e in journal if e.get("id") != entry_id]

            settings_data["trading_journal"] = journal
            await self.db.update_user_settings(user_id, settings_data)

            return True

        except Exception as e:
            logger.error(f"Error deleting journal entry: {e}")
            return False
