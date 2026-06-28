"""
Chart generation using matplotlib and mplfinance.
"""
import os
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import mplfinance as mpf

from market.indicators import TechnicalIndicators
from market.patterns import SupportResistance
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ChartGenerator:
    """Generate professional trading charts."""

    def __init__(self):
        self.style = "seaborn-v0_8"
        plt.style.use("seaborn-v0_8-whitegrid")
        self.colors = {
            "bullish": "#26a69a",
            "bearish": "#ef5350",
            "volume_high": "#4caf50",
            "volume_low": "#9e9e9e",
            "support": "#2196f3",
            "resistance": "#f44336",
            "ema": ["#ff9800", "#9c27b0", "#00bcd4"],
            "bb_upper": "#90caf9",
            "bb_lower": "#ffcc80",
            "pivot": "#9c27b0",
        }
        os.makedirs("charts", exist_ok=True)

    def generate_candlestick_chart(
        self,
        ohlcv: List[List],
        symbol: str,
        timeframe: str = "1h",
        indicators: Dict = None,
        levels: Dict = None,
        signal: Dict = None,
        width: int = 1200,
        height: int = 800,
    ) -> str:
        """Generate candlestick chart with indicators and levels."""
        if not ohlcv or len(ohlcv) < 20:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])

        # Calculate additional indicators if not provided
        if indicators is None:
            indicators = TechnicalIndicators.get_all_indicators(ohlcv)

        # Create mplfinance style
        mc = mpf.make_marketcolors(
            up=self.colors["bullish"],
            down=self.colors["bearish"],
            edge={"up": self.colors["bullish"], "down": self.colors["bearish"]},
            wick={"up": self.colors["bullish"], "down": self.colors["bearish"]},
            volume={"up": self.colors["volume_high"], "down": self.colors["volume_low"]},
        )

        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle="-",
            gridcolor="#e0e0e0",
            y_on_right=False,
        )

        # Add moving averages
        addplots = []

        # EMAs
        ema_periods = [9, 21, 50]
        for i, period in enumerate(ema_periods):
            ema = TechnicalIndicators.calculate_ema(df, period)
            addplots.append(mpf.make_addplot(
                ema,
                color=self.colors["ema"][i % len(self.colors["ema"])],
                width=1.5,
                label=f"EMA {period}"
            ))

        # Bollinger Bands
        middle, upper, lower = TechnicalIndicators.calculate_bollinger_bands(df)
        addplots.append(mpf.make_addplot(upper, color=self.colors["bb_upper"], width=1, linestyle="--"))
        addplots.append(mpf.make_addplot(lower, color=self.colors["bb_lower"], width=1, linestyle="--"))

        # Volume plot
        addplots.append(mpf.make_addplot(
            df["volume"],
            type="bar",
            color=self.colors["volume_low"],
            alpha=0.3,
            panel=1,
            ylabel="Volume"
        ))

        # Save chart
        filename = f"charts/{symbol.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        fig, axes = mpf.plot(
            df,
            type="candle",
            style=style,
            title=f"{symbol} - {timeframe}",
            ylabel="Price",
            volume=True,
            addplot=addplots,
            figsize=(width / 100, height / 100),
            savefig=dict(fname=filename, dpi=100, bbox_inches="tight"),
            returnfig=True,
        )

        # Add support/resistance levels if provided
        if levels:
            ax = axes[0]
            for r in levels.get("resistance", [])[:3]:
                ax.axhline(y=r, color=self.colors["resistance"], linestyle="--", alpha=0.7)
                ax.text(0.02, r, f"R: {r:.4f}", transform=ax.get_yaxis_transform(),
                       color=self.colors["resistance"])

            for s in levels.get("support", [])[:3]:
                ax.axhline(y=s, color=self.colors["support"], linestyle="--", alpha=0.7)
                ax.text(0.02, s, f"S: {s:.4f}", transform=ax.get_yaxis_transform(),
                       color=self.colors["support"])

        # Add signal entry/SL/TP lines if provided
        if signal:
            ax = axes[0]
            entry = signal.get("entry")
            sl = signal.get("stop_loss")
            tp = signal.get("take_profit")

            if entry:
                ax.axhline(y=entry, color="white", linestyle="-", alpha=0.8, linewidth=2)
                ax.text(0.98, entry, f"Entry: {entry:.4f}", transform=ax.get_yaxis_transform(),
                       color="white", fontweight="bold")

            if sl:
                ax.axhline(y=sl, color=self.colors["resistance"], linestyle=":", alpha=0.8, linewidth=2)
                ax.text(0.98, sl, f"SL: {sl:.4f}", transform=ax.get_yaxis_transform(),
                       color=self.colors["resistance"])

            if tp:
                ax.axhline(y=tp, color=self.colors["resistance"], linestyle=":", alpha=0.8, linewidth=2)
                ax.text(0.98, tp, f"TP: {tp:.4f}", transform=ax.get_yaxis_transform(),
                       color=self.colors["support"])

        plt.close()

        return filename

    def generate_analysis_chart(
        self,
        ohlcv: List[List],
        symbol: str,
        timeframe: str = "1h",
        indicators: Dict = None,
        patterns: List = None,
        levels: Dict = None,
    ) -> str:
        """Generate comprehensive analysis chart with multiple panels."""
        if not ohlcv or len(ohlcv) < 50:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])

        # Calculate indicators
        if indicators is None:
            indicators = TechnicalIndicators.get_all_indicators(ohlcv)

        # Create figure with subplots
        fig, axes = plt.subplots(4, 1, figsize=(14, 12), gridspec_kw={"height_ratios": [3, 1, 1, 1]})
        fig.suptitle(f"{symbol} - {timeframe} Analysis", fontsize=14, fontweight="bold")

        # Candlestick chart (main panel)
        ax1 = axes[0]
        self._plot_candlesticks(ax1, df)
        self._plot_moving_averages(ax1, df)
        self._plot_bollinger_bands(ax1, df)

        if levels:
            self._plot_levels(ax1, levels)

        ax1.set_ylabel("Price")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)

        # Volume chart
        ax2 = axes[1]
        self._plot_volume(ax2, df)
        ax2.set_ylabel("Volume")
        ax2.grid(True, alpha=0.3)

        # RSI chart
        ax3 = axes[2]
        self._plot_rsi(ax3, df)
        ax3.set_ylabel("RSI")
        ax3.grid(True, alpha=0.3)

        # MACD chart
        ax4 = axes[3]
        self._plot_macd(ax4, df)
        ax4.set_ylabel("MACD")
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save chart
        filename = f"charts/{symbol.replace('/', '_')}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        fig.savefig(filename, dpi=100, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        return filename

    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot candlesticks on axis."""
        width = 0.8
        width2 = 0.1

        for idx, row in enumerate(df.itertuples()):
            open_price = row.open
            close_price = row.close
            high_price = row.high
            low_price = row.low

            if close_price >= open_price:
                color = self.colors["bullish"]
            else:
                color = self.colors["bearish"]

            # Plot the wick
            ax.plot([idx, idx], [low_price, high_price], color=color, linewidth=0.6)

            # Plot the body
            body_bottom = min(open_price, close_price)
            body_height = abs(close_price - open_price)
            rect = Rectangle(
                (idx - width2, body_bottom),
                width,
                body_height,
                facecolor=color,
                edgecolor=color
            )
            ax.add_patch(rect)

        ax.set_xlim(-0.5, len(df) - 0.5)

    def _plot_moving_averages(self, ax, df: pd.DataFrame):
        """Plot moving averages."""
        ema_periods = [9, 21, 50]
        indices = range(len(df))

        for i, period in enumerate(ema_periods):
            ema = TechnicalIndicators.calculate_ema(df, period)
            ax.plot(indices, ema.values,
                   color=self.colors["ema"][i % len(self.colors["ema"])],
                   linewidth=1.5,
                   label=f"EMA {period}")

    def _plot_bollinger_bands(self, ax, df: pd.DataFrame):
        """Plot Bollinger Bands."""
        middle, upper, lower = TechnicalIndicators.calculate_bollinger_bands(df)
        indices = range(len(df))

        ax.fill_between(indices, upper, lower, alpha=0.1, color="gray")
        ax.plot(indices, upper, color=self.colors["bb_upper"], linewidth=0.8, alpha=0.7)
        ax.plot(indices, lower, color=self.colors["bb_lower"], linewidth=0.8, alpha=0.7)

    def _plot_volume(self, ax, df: pd.DataFrame):
        """Plot volume bars."""
        indices = range(len(df))
        colors = [self.colors["bullish"] if c >= o else self.colors["bearish"]
                  for c, o in zip(df["close"], df["open"])]

        ax.bar(indices, df["volume"], color=colors, alpha=0.6, width=0.8)

        # Volume moving average
        vol_ma = df["volume"].rolling(window=20).mean()
        ax.plot(indices, vol_ma, color="orange", linewidth=1, label="Volume MA(20)")
        ax.legend(loc="upper left")

    def _plot_rsi(self, ax, df: pd.DataFrame):
        """Plot RSI indicator."""
        rsi = TechnicalIndicators.calculate_rsi(df)
        indices = range(len(rsi))

        ax.plot(indices, rsi.values, color="purple", linewidth=1.2)
        ax.axhline(y=70, color="red", linestyle="--", alpha=0.5)
        ax.axhline(y=30, color="green", linestyle="--", alpha=0.5)
        ax.axhline(y=50, color="gray", linestyle="-", alpha=0.3)

        # Fill overbought/oversold zones
        ax.fill_between(indices, 70, rsi.values, where=rsi.values >= 70,
                       color="red", alpha=0.3)
        ax.fill_between(indices, 30, rsi.values, where=rsi.values <= 30,
                       color="green", alpha=0.3)

        ax.set_ylim(0, 100)

    def _plot_macd(self, ax, df: pd.DataFrame):
        """Plot MACD indicator."""
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(df)
        indices = range(len(macd_line))

        ax.plot(indices, macd_line.values, color="blue", linewidth=1.2, label="MACD")
        ax.plot(indices, signal_line.values, color="orange", linewidth=1, label="Signal")

        # Histogram
        colors = ["green" if h >= 0 else "red" for h in histogram.values]
        ax.bar(indices, histogram.values, color=colors, alpha=0.4, width=0.8)

        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.5)
        ax.legend(loc="upper left")

    def _plot_levels(self, ax, levels: Dict):
        """Plot support/resistance levels."""
        if levels.get("current_price"):
            ax.axhline(y=levels["current_price"], color="white", linestyle=":",
                      alpha=0.8, linewidth=1.5)

        for r in levels.get("resistance", [])[:3]:
            ax.axhline(y=r, color="red", linestyle="--", alpha=0.5)

        for s in levels.get("support", [])[:3]:
            ax.axhline(y=s, color="green", linestyle="--", alpha=0.5)

    def generate_signal_chart(
        self,
        ohlcv: List[List],
        signal: Dict,
        symbol: str,
        timeframe: str = "1h",
    ) -> str:
        """Generate a chart showing entry, stop loss, and take profit levels."""
        levels = {
            "support": [signal.get("stop_loss")] if signal.get("stop_loss") else [],
            "resistance": signal.get("take_profits", [])[:3] if signal.get("take_profits") else [signal.get("take_profit")] if signal.get("take_profit") else [],
            "current_price": signal.get("entry_price"),
        }

        chart_signal = {
            "entry": signal.get("entry_price"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
        }

        return self.generate_candlestick_chart(
            ohlcv=ohlcv,
            symbol=symbol,
            timeframe=timeframe,
            levels=levels,
            signal=chart_signal,
        )

    def cleanup_old_charts(self, max_age_hours: int = 24):
        """Remove old chart files to save disk space."""
        charts_dir = "charts"
        if not os.path.exists(charts_dir):
            return

        now = datetime.now()
        for filename in os.listdir(charts_dir):
            filepath = os.path.join(charts_dir, filename)
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if (now - file_time).total_seconds() > max_age_hours * 3600:
                    os.remove(filepath)
                    logger.debug(f"Removed old chart: {filename}")
