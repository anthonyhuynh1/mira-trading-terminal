"""
Alpaca data provider implementation.
Handles real-time and historical market data from Alpaca.
"""

import os
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Callable
import logging

from ..base import DataProvider, DataType, Quote, Bar

# Try to import Alpaca SDK
try:
    from alpaca.data import StockHistoricalDataClient, StockDataStream
    from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    from alpaca.data.models import Quote as AlpacaQuote, Bar as AlpacaBar
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logging.warning("Alpaca SDK not installed. Install with: pip install alpaca-py")


class AlpacaProvider(DataProvider):
    """Alpaca data provider for real-time and historical market data."""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        super().__init__("alpaca")

        # Get credentials from env if not provided
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")

        self.historical_client = None
        self.stream_client = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to Alpaca services."""
        if not ALPACA_AVAILABLE:
            logging.error("Alpaca SDK not available")
            return False

        if not self.api_key or not self.secret_key:
            logging.error("Alpaca credentials not provided")
            return False

        try:
            # Initialize historical data client
            self.historical_client = StockHistoricalDataClient(
                self.api_key,
                self.secret_key
            )

            # Initialize streaming client for real-time data
            self.stream_client = StockDataStream(
                self.api_key,
                self.secret_key
            )

            self.is_connected = True
            logging.info("Connected to Alpaca")
            return True

        except Exception as e:
            logging.error(f"Failed to connect to Alpaca: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Alpaca services."""
        if self.stream_client:
            try:
                await self.stream_client.close()
            except:
                pass
        self.is_connected = False
        logging.info("Disconnected from Alpaca")

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for symbol."""
        if not self.is_connected or not self.historical_client:
            return None

        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            response = self.historical_client.get_stock_latest_quote(request)

            alpaca_quote = response[symbol]

            return Quote(
                symbol=symbol,
                bid=Decimal(str(alpaca_quote.bid_price)) if alpaca_quote.bid_price else Decimal(0),
                ask=Decimal(str(alpaca_quote.ask_price)) if alpaca_quote.ask_price else Decimal(0),
                bid_size=alpaca_quote.bid_size or 0,
                ask_size=alpaca_quote.ask_size or 0,
                last=Decimal(str(alpaca_quote.bid_price)) if alpaca_quote.bid_price else Decimal(0),
                volume=0,  # Not available in latest quote
                timestamp=alpaca_quote.timestamp,
                exchange=alpaca_quote.exchange
            )

        except Exception as e:
            logging.error(f"Error getting quote for {symbol}: {e}")
            return None

    async def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D"
    ) -> List[Bar]:
        """Get historical bars for symbol."""
        if not self.is_connected or not self.historical_client:
            return []

        try:
            # Map timeframe string to Alpaca TimeFrame
            tf_map = {
                "1Min": TimeFrame(1, TimeFrameUnit.Minute),
                "5Min": TimeFrame(5, TimeFrameUnit.Minute),
                "15Min": TimeFrame(15, TimeFrameUnit.Minute),
                "30Min": TimeFrame(30, TimeFrameUnit.Minute),
                "1H": TimeFrame(1, TimeFrameUnit.Hour),
                "1D": TimeFrame(1, TimeFrameUnit.Day),
                "1W": TimeFrame(1, TimeFrameUnit.Week),
            }

            alpaca_timeframe = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=alpaca_timeframe,
                start=start,
                end=end
            )

            response = self.historical_client.get_stock_bars(request)

            bars = []
            for alpaca_bar in response[symbol]:
                bars.append(Bar(
                    symbol=symbol,
                    open=Decimal(str(alpaca_bar.open)),
                    high=Decimal(str(alpaca_bar.high)),
                    low=Decimal(str(alpaca_bar.low)),
                    close=Decimal(str(alpaca_bar.close)),
                    volume=alpaca_bar.volume,
                    timestamp=alpaca_bar.timestamp,
                    vwap=Decimal(str(alpaca_bar.vwap)) if alpaca_bar.vwap else None,
                    trade_count=alpaca_bar.trade_count
                ))

            return bars

        except Exception as e:
            logging.error(f"Error getting bars for {symbol}: {e}")
            return []

    async def subscribe_quotes(self, symbols: List[str], callback: Callable) -> None:
        """Subscribe to real-time quotes."""
        if not self.is_connected or not self.stream_client:
            return

        async def handle_quote(data):
            """Convert Alpaca quote to our format and call callback."""
            quote = Quote(
                symbol=data.symbol,
                bid=Decimal(str(data.bid_price)) if data.bid_price else Decimal(0),
                ask=Decimal(str(data.ask_price)) if data.ask_price else Decimal(0),
                bid_size=data.bid_size or 0,
                ask_size=data.ask_size or 0,
                last=Decimal(str(data.bid_price)) if data.bid_price else Decimal(0),
                volume=0,
                timestamp=data.timestamp,
                exchange=data.exchange
            )
            await callback(quote)

        try:
            for symbol in symbols:
                self.stream_client.subscribe_quotes(handle_quote, symbol)

            # Store subscription info
            if "quotes" not in self._subscriptions:
                self._subscriptions["quotes"] = set()
            self._subscriptions["quotes"].update(symbols)

        except Exception as e:
            logging.error(f"Error subscribing to quotes: {e}")

    async def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Unsubscribe from real-time quotes."""
        if not self.is_connected or not self.stream_client:
            return

        try:
            for symbol in symbols:
                self.stream_client.unsubscribe_quotes(symbol)

            # Update subscription info
            if "quotes" in self._subscriptions:
                self._subscriptions["quotes"].difference_update(symbols)

        except Exception as e:
            logging.error(f"Error unsubscribing from quotes: {e}")

    def supported_types(self) -> List[DataType]:
        """Return list of supported data types."""
        return [DataType.QUOTE, DataType.TRADE, DataType.BAR]


class MockAlpacaProvider(DataProvider):
    """Mock Alpaca provider for testing without API keys."""

    def __init__(self):
        super().__init__("mock_alpaca")
        self.is_connected = False

    async def connect(self) -> bool:
        """Simulate connection."""
        self.is_connected = True
        logging.info("Connected to Mock Alpaca")
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.is_connected = False

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Return mock quote data."""
        import random
        base_price = {"SPY": 450, "AAPL": 190, "NVDA": 500}.get(symbol, 100)
        spread = base_price * 0.0002

        return Quote(
            symbol=symbol,
            bid=Decimal(str(base_price - spread)),
            ask=Decimal(str(base_price + spread)),
            bid_size=random.randint(100, 1000),
            ask_size=random.randint(100, 1000),
            last=Decimal(str(base_price)),
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now()
        )

    async def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D"
    ) -> List[Bar]:
        """Return mock bar data."""
        bars = []
        current = start
        base_price = {"SPY": 450, "AAPL": 190, "NVDA": 500}.get(symbol, 100)

        while current <= end:
            import random
            volatility = base_price * 0.02

            open_price = base_price + random.uniform(-volatility, volatility)
            close_price = base_price + random.uniform(-volatility, volatility)
            high_price = max(open_price, close_price) + random.uniform(0, volatility/2)
            low_price = min(open_price, close_price) - random.uniform(0, volatility/2)

            bars.append(Bar(
                symbol=symbol,
                open=Decimal(str(open_price)),
                high=Decimal(str(high_price)),
                low=Decimal(str(low_price)),
                close=Decimal(str(close_price)),
                volume=random.randint(1000000, 10000000),
                timestamp=current,
                vwap=Decimal(str((high_price + low_price + close_price) / 3))
            ))

            # Move to next period
            if "Min" in timeframe:
                minutes = int(timeframe.replace("Min", ""))
                current += timedelta(minutes=minutes)
            elif "H" in timeframe:
                hours = int(timeframe.replace("H", ""))
                current += timedelta(hours=hours)
            else:  # Daily
                current += timedelta(days=1)

        return bars

    async def subscribe_quotes(self, symbols: List[str], callback: Callable) -> None:
        """Simulate quote subscription."""
        # Could implement periodic mock updates
        pass

    async def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Simulate quote unsubscription."""
        pass

    def supported_types(self) -> List[DataType]:
        """Return list of supported data types."""
        return [DataType.QUOTE, DataType.BAR]