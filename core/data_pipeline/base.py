"""
Base data pipeline abstraction for Mira Trading Terminal.
Provides unified interface for multiple data providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import asyncio
from decimal import Decimal


class DataType(Enum):
    """Types of data available in the system."""
    QUOTE = "quote"
    TRADE = "trade"
    BAR = "bar"
    FUNDAMENTALS = "fundamentals"
    NEWS = "news"
    FILING = "filing"
    ECONOMIC = "economic"


@dataclass
class Quote:
    """Real-time quote data."""
    symbol: str
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    last: Decimal
    volume: int
    timestamp: datetime
    exchange: Optional[str] = None


@dataclass
class Bar:
    """OHLCV bar data."""
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    timestamp: datetime
    vwap: Optional[Decimal] = None
    trade_count: Optional[int] = None


@dataclass
class Fundamental:
    """Company fundamental data."""
    symbol: str
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    revenue_growth: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    timestamp: datetime = None
    period: Optional[str] = None  # Q1, Q2, Q3, Q4, FY


class DataProvider(ABC):
    """Abstract base class for all data providers."""

    def __init__(self, name: str):
        self.name = name
        self._callbacks: Dict[str, List[Callable]] = {}
        self._subscriptions: Dict[str, set] = {}

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data provider."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to data provider."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for symbol."""
        pass

    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D"
    ) -> List[Bar]:
        """Get historical bars for symbol."""
        pass

    @abstractmethod
    async def subscribe_quotes(self, symbols: List[str], callback: Callable) -> None:
        """Subscribe to real-time quotes."""
        pass

    @abstractmethod
    async def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Unsubscribe from real-time quotes."""
        pass

    def supports(self, data_type: DataType) -> bool:
        """Check if provider supports data type."""
        return data_type in self.supported_types()

    @abstractmethod
    def supported_types(self) -> List[DataType]:
        """Return list of supported data types."""
        pass


class DataManager:
    """
    Central data management system.
    Routes requests to appropriate providers and manages caching.
    """

    def __init__(self):
        self.providers: Dict[str, DataProvider] = {}
        self.primary_provider: Optional[str] = None
        self.cache = None  # Will implement caching layer

    def register_provider(self, provider: DataProvider, primary: bool = False) -> None:
        """Register a data provider."""
        self.providers[provider.name] = provider
        if primary or not self.primary_provider:
            self.primary_provider = provider.name

    async def get_quote(self, symbol: str, provider: Optional[str] = None) -> Optional[Quote]:
        """Get quote from specified or primary provider."""
        provider_name = provider or self.primary_provider
        if not provider_name or provider_name not in self.providers:
            return None

        provider = self.providers[provider_name]

        # Check cache first (implement later)
        # if self.cache:
        #     cached = await self.cache.get_quote(symbol)
        #     if cached and not cached.is_stale():
        #         return cached

        # Fetch from provider
        quote = await provider.get_quote(symbol)

        # Update cache (implement later)
        # if self.cache and quote:
        #     await self.cache.store_quote(quote)

        return quote

    async def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D",
        provider: Optional[str] = None
    ) -> List[Bar]:
        """Get historical bars from specified or primary provider."""
        provider_name = provider or self.primary_provider
        if not provider_name or provider_name not in self.providers:
            return []

        provider = self.providers[provider_name]
        return await provider.get_bars(symbol, start, end, timeframe)

    async def subscribe_quotes(
        self,
        symbols: List[str],
        callback: Callable,
        provider: Optional[str] = None
    ) -> None:
        """Subscribe to real-time quotes."""
        provider_name = provider or self.primary_provider
        if not provider_name or provider_name not in self.providers:
            return

        provider = self.providers[provider_name]
        await provider.subscribe_quotes(symbols, callback)

    def get_provider_for_type(self, data_type: DataType) -> Optional[DataProvider]:
        """Find best provider for data type."""
        # First check primary
        if self.primary_provider:
            primary = self.providers[self.primary_provider]
            if primary.supports(data_type):
                return primary

        # Check other providers
        for provider in self.providers.values():
            if provider.supports(data_type):
                return provider

        return None


# Global data manager instance
data_manager = DataManager()