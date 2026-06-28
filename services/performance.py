"""
Performance tracking service for trading statistics and reports.
Handles daily, weekly, monthly reports and signal accuracy.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from config import settings
from utils.logger import get_logger
from utils.helpers import format_percentage

logger = get_logger(__name__)


class PerformanceTracker:
    """Tracks and reports trading performance."""

    def __init__(self, db):
        self.db = db

    async def get_daily_report(self, date: str = None) -> Dict:
        """Get daily performance report."""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            stats = await self.db.get_statistics(1)
            signals = await self.db.get_active_signals()

            # Get today's closed signals
            if hasattr(self.db, "_is_supabase") and self.db._is_supabase:
                # Use Supabase query
                all_signals = await self._get_daily_signals_supabase(date)
            else:
                # Use SQLite query
                all_signals = await self._get_daily_signals_sqlite(date)

            total_signals = len(all_signals)
            wins = sum(1 for s in all_signals if s.get("hit_target", 0) > 0)
            losses = sum(1 for s in all_signals if s.get("closed", False) and s.get("hit_target", 0) == 0)

            win_rate = (wins / total_signals * 100) if total_signals > 0 else 0

            return {
                "date": date,
                "total_signals": total_signals,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "active_signals": len(signals),
            }

        except Exception as e:
            logger.error(f"Error getting daily report: {e}")
            return {
                "date": date,
                "total_signals": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "active_signals": 0,
            }

    async def _get_daily_signals_supabase(self, date: str) -> List[Dict]:
        """Get daily signals from Supabase."""
        try:
            if hasattr(self.db, "_backend") and hasattr(self.db._backend, "_client"):
                client = self.db._backend._client
                response = client.table("signals").select("*").gte("created_at", f"{date}T00:00:00").lt("created_at", f"{date}T23:59:59").execute()
                return response.data
        except Exception as e:
            logger.error(f"Error getting Supabase signals: {e}")
        return []

    async def _get_daily_signals_sqlite(self, date: str) -> List[Dict]:
        """Get daily signals from SQLite."""
        try:
            query = """
                SELECT * FROM signals
                WHERE DATE(created_at) = ?
            """
            return await self.db.fetchall(query, (date,))
        except Exception as e:
            logger.error(f"Error getting SQLite signals: {e}")
        return []

    async def get_weekly_report(self, weeks_back: int = 0) -> Dict:
        """Get weekly performance report."""
        end_date = datetime.utcnow() - timedelta(weeks=weeks_back)
        start_date = end_date - timedelta(days=7)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        try:
            # Aggregate daily stats
            if hasattr(self.db, "_is_supabase") and self.db._is_supabase:
                weekly_stats = await self._get_range_stats_supabase(start_str, end_str)
            else:
                weekly_stats = await self._get_range_stats_sqlite(start_str, end_str)

            return {
                "start_date": start_str,
                "end_date": end_str,
                **weekly_stats,
            }

        except Exception as e:
            logger.error(f"Error getting weekly report: {e}")
            return {
                "start_date": start_str,
                "end_date": end_str,
                "total_signals": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
            }

    async def get_monthly_report(self, months_back: int = 0) -> Dict:
        """Get monthly performance report."""
        now = datetime.utcnow()
        if months_back > 0:
            # Go back months
            target_date = now - timedelta(days=months_back * 30)
        else:
            target_date = now

        year = target_date.year
        month = target_date.month

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        try:
            if hasattr(self.db, "_is_supabase") and self.db._is_supabase:
                monthly_stats = await self._get_range_stats_supabase(
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
            else:
                monthly_stats = await self._get_range_stats_sqlite(
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )

            return {
                "month": target_date.strftime("%B %Y"),
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                **monthly_stats,
            }

        except Exception as e:
            logger.error(f"Error getting monthly report: {e}")
            return {
                "month": target_date.strftime("%B %Y"),
                "total_signals": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
            }

    async def _get_range_stats_supabase(self, start_date: str, end_date: str) -> Dict:
        """Get statistics for date range from Supabase."""
        try:
            if hasattr(self.db, "_backend") and hasattr(self.db._backend, "_client"):
                client = self.db._backend._client
                response = client.table("signals").select("*").gte("created_at", f"{start_date}T00:00:00").lte("created_at", f"{end_date}T23:59:59").execute()
                signals = response.data

                total = len(signals)
                closed = [s for s in signals if s.get("closed")]
                wins = sum(1 for s in closed if s.get("hit_target", 0) > 0)
                losses = len(closed) - wins

                # Calculate average R:R
                rr_ratios = [s.get("risk_reward_ratio", 0) for s in signals if s.get("risk_reward_ratio")]
                avg_rr = sum(rr_ratios) / len(rr_ratios) if rr_ratios else 0

                # Calculate average confidence
                confidences = [s.get("confidence_score", 0) for s in signals if s.get("confidence_score")]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                return {
                    "total_signals": total,
                    "closed_signals": len(closed),
                    "wins": wins,
                    "losses": losses,
                    "win_rate": (wins / len(closed) * 100) if closed else 0,
                    "avg_risk_reward": round(avg_rr, 2),
                    "avg_confidence": round(avg_confidence, 1),
                }

        except Exception as e:
            logger.error(f"Error getting Supabase range stats: {e}")

        return {
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_risk_reward": 0,
            "avg_confidence": 0,
        }

    async def _get_range_stats_sqlite(self, start_date: str, end_date: str) -> Dict:
        """Get statistics for date range from SQLite."""
        try:
            query = """
                SELECT * FROM signals
                WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?
            """
            signals = await self.db.fetchall(query, (start_date, end_date))

            total = len(signals)
            closed = [s for s in signals if s.get("closed")]
            wins = sum(1 for s in closed if s.get("hit_target", 0) > 0)
            losses = len(closed) - wins

            rr_values = [float(s.get("risk_reward_ratio", 0)) for s in signals if s.get("risk_reward_ratio")]
            avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0

            return {
                "total_signals": total,
                "closed_signals": len(closed),
                "wins": wins,
                "losses": losses,
                "win_rate": (wins / len(closed) * 100) if closed else 0,
                "avg_risk_reward": round(avg_rr, 2),
            }

        except Exception as e:
            logger.error(f"Error getting SQLite range stats: {e}")

        return {
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_risk_reward": 0,
        }

    async def get_signal_accuracy(self, days: int = 30) -> Dict:
        """Calculate signal accuracy metrics."""
        try:
            stats = await self.db.get_signal_performance(days)

            total = stats.get("total", 0)
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)

            # Additional accuracy metrics
            accuracy = {
                "period_days": days,
                "total_signals": total,
                "winning_signals": wins,
                "losing_signals": losses,
                "win_rate": stats.get("win_rate", 0),
                "loss_rate": (losses / total * 100) if total > 0 else 0,
                "signal_frequency": round(total / days, 1) if days > 0 else 0,
                "performance_grade": self._calculate_grade(wins, total),
            }

            return accuracy

        except Exception as e:
            logger.error(f"Error calculating signal accuracy: {e}")
            return {
                "period_days": days,
                "total_signals": 0,
                "winning_signals": 0,
                "losing_signals": 0,
                "win_rate": 0,
                "loss_rate": 0,
                "signal_frequency": 0,
                "performance_grade": "N/A",
            }

    def _calculate_grade(self, wins: int, total: int) -> str:
        """Calculate performance grade."""
        if total == 0:
            return "N/A"

        win_rate = wins / total * 100

        if win_rate >= 80:
            return "A+ (Excellent)"
        elif win_rate >= 70:
            return "A (Very Good)"
        elif win_rate >= 60:
            return "B (Good)"
        elif win_rate >= 50:
            return "C (Average)"
        elif win_rate >= 40:
            return "D (Below Average)"
        else:
            return "F (Needs Improvement)"

    def format_daily_report(self, report: Dict, language: str = "en") -> str:
        """Format daily report for display."""
        date = report.get("date", "")

        if language == "si":
            return "\n".join([
                f"📊 **දිනපතා වාර්තාව** - {date}",
                "",
                f"📈 මුළු Signals: `{report['total_signals']}`",
                f"✅ ජයග්‍රහණ: `{report['wins']}`",
                f"❌ පරාජ: `{report['losses']}`",
                f"📊 ජයග්‍රහණ අනුපාතය: `{report['win_rate']:.1f}%`",
                "",
                f"🔄 සක්‍රීය Signals: `{report['active_signals']}`",
            ])

        return "\n".join([
            f"📊 **Daily Performance Report** - {date}",
            "",
            f"📈 Total Signals: `{report['total_signals']}`",
            f"✅ Wins: `{report['wins']}`",
            f"❌ Losses: `{report['losses']}`",
            f"📊 Win Rate: `{report['win_rate']:.1f}%`",
            "",
            f"🔄 Active Signals: `{report['active_signals']}`",
        ])

    def format_weekly_report(self, report: Dict, language: str = "en") -> str:
        """Format weekly report for display."""
        start = report.get("start_date", "")
        end = report.get("end_date", "")

        if language == "si":
            return "\n".join([
                f"📊 **සතිපතා වාර්තාව**",
                f"📅 {start} සිට {end} දක්වා",
                "",
                f"📈 මුළු Signals: `{report['total_signals']}`",
                f"✅ ජයග්‍රහණ: `{report['wins']}`",
                f"❌ පරාජ: `{report['losses']}`",
                f"📊 ජයග්‍රහණ අනුපාතය: `{report.get('win_rate', 0):.1f}%`",
                f"📉 සාමාන්‍ය R:R: `{report.get('avg_risk_reward', 0):.2f}`",
            ])

        return "\n".join([
            "📊 **Weekly Performance Report**",
            f"📅 {start} to {end}",
            "",
            f"📈 Total Signals: `{report['total_signals']}`",
            f"✅ Wins: `{report['wins']}`",
            f"❌ Losses: `{report['losses']}`",
            f"📊 Win Rate: `{report.get('win_rate', 0):.1f}%`",
            f"📉 Avg R:R: `{report.get('avg_risk_reward', 0):.2f}`",
        ])

    def format_monthly_report(self, report: Dict, language: str = "en") -> str:
        """Format monthly report for display."""
        month = report.get("month", "")

        if language == "si":
            return "\n".join([
                f"📊 **මාසික වාර්තාව** - {month}",
                "",
                f"📈 මුළු Signals: `{report['total_signals']}`",
                f"✅ ජයග්‍රහණ: `{report['wins']}`",
                f"❌ පරාජ: `{report['losses']}`",
                f"📊 ජයග්‍රහණ අනුපාතය: `{report.get('win_rate', 0):.1f}%`",
                f"📈 ග්‍රේඩ්: `{report.get('avg_risk_reward', 0):.2f}`",
            ])

        return "\n".join([
            f"📊 **Monthly Performance Report** - {month}",
            "",
            f"📈 Total Signals: `{report['total_signals']}`",
            f"✅ Wins: `{report['wins']}`",
            f"❌ Losses: `{report['losses']}`",
            f"📊 Win Rate: `{report.get('win_rate', 0):.1f}%`",
            f"📉 Avg R:R: `{report.get('avg_risk_reward', 0):.2f}`",
            f"🎯 Grade: `{report.get('performance_grade', 'N/A')}`",
        ])

    async def get_admin_dashboard_data(self) -> Dict:
        """Get comprehensive admin dashboard data."""
        try:
            daily = await self.get_daily_report()
            weekly = await self.get_weekly_report()
            monthly = await self.get_monthly_report()
            accuracy = await self.get_signal_accuracy(30)

            total_users = await self.db.count_users()
            premium_users = len(await self.db.get_premium_users())

            return {
                "daily_performance": daily,
                "weekly_performance": weekly,
                "monthly_performance": monthly,
                "signal_accuracy": accuracy,
                "total_users": total_users,
                "premium_users": premium_users,
                "bot_status": "Online",
                "auto_signals_enabled": settings.ENABLE_AUTO_SIGNALS,
                "price_alerts_enabled": settings.ENABLE_PRICE_ALERTS,
            }

        except Exception as e:
            logger.error(f"Error getting admin dashboard data: {e}")
            return {
                "error": str(e),
                "bot_status": "Error",
            }
