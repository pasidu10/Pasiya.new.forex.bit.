"""
Exchange client implementations for market data fetching.
"""
import asyncio
import aiohttp
from typing import Optional, Dict, List, Any
from datetime import datetime
import ccxt.async_support as ccxt
import json

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class BinanceClient:
    """Binance exchange client for crypto market data."""

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or settings.BINANCE_API_KEY
        self.api_secret = api_secret or settings.BINANCE_API_SECRET
        self.exchange = None

    async def initialize(self):
        """Initialize the exchange connection."""
        self.exchange = ccxt.binance({
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
            },
        })
        logger.info("Binance client initialized")

    async def close(self):
        """Close the exchange connection."""
        if self.exchange:
            await self.exchange.close()

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker for a symbol."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": ticker["symbol"],
                "last": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "high": ticker["high"],
                "low": ticker["low"],
                "volume": ticker["baseVolume"],
                "change_percent": ticker["percentage"],
                "timestamp": ticker["timestamp"],
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            return None

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[List]:
        """Get OHLCV data for a symbol."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return []

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Get order book for a symbol."""
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return {
                "bids": orderbook["bids"][:limit],
                "asks": orderbook["asks"][:limit],
                "timestamp": orderbook["timestamp"],
            }
        except Exception as e:
            logger.error(f"Failed to fetch order book for {symbol}: {e}")
            return None

    async def get_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades for a symbol."""
        try:
            trades = await self.exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            logger.error(f"Failed to fetch trades for {symbol}: {e}")
            return []


class BybitClient:
    """Bybit exchange client for crypto market data."""

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or settings.BYBIT_API_KEY
        self.api_secret = api_secret or settings.BYBIT_API_SECRET
        self.exchange = None

    async def initialize(self):
        """Initialize the exchange connection."""
        self.exchange = ccxt.bybit({
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "enableRateLimit": True,
        })
        logger.info("Bybit client initialized")

    async def close(self):
        """Close the exchange connection."""
        if self.exchange:
            await self.exchange.close()

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker for a symbol."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": ticker["symbol"],
                "last": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "high": ticker["high"],
                "low": ticker["low"],
                "volume": ticker["baseVolume"],
                "change_percent": ticker["percentage"],
                "timestamp": ticker["timestamp"],
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            return None

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[List]:
        """Get OHLCV data for a symbol."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return []


class ForexClient:
    """Forex market data client using free APIs."""

    BASE_URL = "https://api.exchangerate.host"
    YAHOO_FINANCE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
        logger.info("Forex client initialized")

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def get_ticker(self, pair: str) -> Optional[Dict]:
        """Get current rate for a forex pair."""
        try:
            base, quote = pair.split("/")
            url = f"{self.BASE_URL}/latest"
            params = {"base": base, "symbols": quote}

            async with self.session.get(url, params=params) as response:
                data = await response.json()

            if data.get("success"):
                rate = data["rates"].get(quote)
                return {
                    "symbol": pair,
                    "last": rate,
                    "bid": rate,
                    "ask": rate,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }

        except Exception as e:
            logger.error(f"Failed to fetch forex rate for {pair}: {e}")

        return None

    async def get_ohlcv(
        self,
        pair: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[List]:
        """Get OHLCV data for a forex pair using Yahoo Finance."""
        try:
            symbol = f"{pair.replace('/', '')}=X"
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "1h": "1h",
                "4h": "1d",
                "1d": "1d",
            }

            interval = interval_map.get(timeframe, "1h")
            range_period = "1mo" if interval == "1m" else "3mo"

            url = f"{self.YAHOO_FINANCE_URL}/{symbol}"
            params = {"interval": interval, "range": range_period}

            async with self.session.get(url, params=params) as response:
                data = await response.json()

            result = data.get("chart", {}).get("result", [])
            if result:
                timestamps = result[0]["timestamp"]
                opens = result[0]["indicators"]["quote"][0]["open"]
                highs = result[0]["indicators"]["quote"][0]["high"]
                lows = result[0]["indicators"]["quote"][0]["low"]
                closes = result[0]["indicators"]["quote"][0]["close"]
                volumes = result[0]["indicators"]["quote"][0].get("volume", [0] * len(timestamps))

                ohlcv = []
                for i in range(len(timestamps)):
                    ohlcv.append([
                        timestamps[i] * 1000,
                        opens[i],
                        highs[i],
                        lows[i],
                        closes[i],
                        volumes[i],
                    ])

                return ohlcv[-limit:]

        except Exception as e:
            logger.error(f"Failed to fetch forex OHLCV for {pair}: {e}")

        return []


class ExchangeManager:
    """Manager for multiple exchange clients."""

    def __init__(self):
        self.binance = None
        self.bybit = None
        self.forex = None
        self._initialized = False

    async def initialize(self):
        """Initialize all exchange clients."""
        self.binance = BinanceClient()
        await self.binance.initialize()

        self.bybit = BybitClient()
        await self.bybit.initialize()

        self.forex = ForexClient()
        await self.forex.initialize()

        self._initialized = True
        logger.info("Exchange manager initialized")

    async def close(self):
        """Close all exchange connections."""
        if self.binance:
            await self.binance.close()
        if self.bybit:
            await self.bybit.close()
        if self.forex:
            await self.forex.close()

    async def get_ticker(self, symbol: str, exchange: str = "binance") -> Optional[Dict]:
        """Get ticker from specified exchange."""
        if exchange == "binance":
            return await self.binance.get_ticker(symbol)
        elif exchange == "bybit":
            return await self.bybit.get_ticker(symbol)
        elif exchange == "forex":
            return await self.forex.get_ticker(symbol)
        return None

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        exchange: str = "binance",
        limit: int = 100
    ) -> List[List]:
        """Get OHLCV data from specified exchange."""
        if exchange == "binance":
            return await self.binance.get_ohlcv(symbol, timeframe, limit)
        elif exchange == "bybit":
            return await self.bybit.get_ohlcv(symbol, timeframe, limit)
        elif exchange == "forex":
            return await self.forex.get_ohlcv(symbol, timeframe, limit)
        return []

    def is_crypto(self, symbol: str) -> bool:
        """Check if symbol is a crypto pair."""
        return "USDT" in symbol or "BUSD" in symbol or "/" not in symbol

    def is_forex(self, symbol: str) -> bool:
        """Check if symbol is a forex pair."""
        return "/" in symbol and not self.is_crypto(symbol)
