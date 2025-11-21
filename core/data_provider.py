"""
Data provider for fetching and caching market data from Alpaca.
Centralizes all market data access with intelligent caching.
"""

import os
from datetime import datetime, timedelta
from threading import Lock
from typing import Callable

from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

# Load environment variables
load_dotenv()

# Try to import Alpaca, fall back to yfinance if not available
try:
    from alpaca.data.historical import StockHistoricalDataClient, NewsClient
    from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest, NewsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("Warning: Alpaca SDK not installed. Install with: pip install alpaca-py")

# Fallback to yfinance for fundamentals
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class TickerDataProvider:
    """Centralized, cache-aware access layer for market data using Alpaca API."""

    SNAPSHOT_TTL = timedelta(seconds=15)
    FUNDAMENTALS_TTL = timedelta(minutes=8)
    NEWS_TTL = timedelta(minutes=2)

    def __init__(self):
        self._lock = Lock()
        self._snapshot_cache: dict[str, tuple[datetime, dict]] = {}
        self._fundamentals_cache: dict[str, tuple[datetime, dict]] = {}
        self._news_cache: dict[str, tuple[datetime, dict]] = {}

        # Initialize Alpaca clients
        if ALPACA_AVAILABLE:
            api_key = os.getenv('APCA_API_KEY_ID')
            secret_key = os.getenv('APCA_API_SECRET_KEY')

            if api_key and secret_key:
                self.alpaca_client = StockHistoricalDataClient(api_key, secret_key)
                self.news_client = NewsClient(api_key, secret_key)
                self.data_source = "alpaca"
            else:
                print("Warning: Alpaca credentials not found in environment")
                self.alpaca_client = None
                self.news_client = None
                self.data_source = "yfinance"
        else:
            self.alpaca_client = None
            self.news_client = None
            self.data_source = "yfinance"

        # yfinance ticker handles (for fundamentals fallback)
        self._yf_ticker_handles: dict[str, yf.Ticker] = {} if YFINANCE_AVAILABLE else {}

    def fetch_snapshot_payload(self, ticker: str) -> dict:
        """Fetch latest quote snapshot for a ticker."""
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return {"symbol": "", "status": "No symbol"}

        cached = self._get_cached(self._snapshot_cache, symbol, self.SNAPSHOT_TTL)
        if cached:
            return cached

        payload = self._build_snapshot(symbol)
        self._store_cached(self._snapshot_cache, symbol, payload)
        return payload

    def fetch_fundamentals_payload(self, ticker: str) -> dict:
        """Fetch fundamental data for a ticker."""
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return {"ticker": "", "error": "No ticker provided"}

        cached = self._get_cached(self._fundamentals_cache, symbol, self.FUNDAMENTALS_TTL)
        if cached:
            return cached

        payload = self._build_fundamentals(symbol)
        self._store_cached(self._fundamentals_cache, symbol, payload)
        return payload

    def fetch_news_payload(self, ticker: str) -> dict:
        """Fetch news for a ticker."""
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return {"ticker": "", "items": []}

        cached = self._get_cached(self._news_cache, symbol, self.NEWS_TTL)
        if cached:
            return cached

        payload = self._build_news(symbol)
        self._store_cached(self._news_cache, symbol, payload)
        return payload

    def _get_cached(self, cache: dict, symbol: str, ttl: timedelta) -> dict | None:
        """Get cached data if not expired."""
        with self._lock:
            entry = cache.get(symbol)
            if not entry:
                return None
            ts, payload = entry
            if datetime.utcnow() - ts > ttl:
                cache.pop(symbol, None)
                return None
            return payload

    def _store_cached(self, cache: dict, symbol: str, payload: dict):
        """Store data in cache with timestamp."""
        with self._lock:
            cache[symbol] = (datetime.utcnow(), payload)

    def _build_snapshot(self, symbol: str) -> dict:
        """Build snapshot using Alpaca or yfinance fallback."""
        if self.alpaca_client and ALPACA_AVAILABLE:
            return self._build_snapshot_alpaca(symbol)
        elif YFINANCE_AVAILABLE:
            return self._build_snapshot_yfinance(symbol)
        else:
            return {"symbol": symbol, "status": "No data source available", "error": "Install alpaca-py or yfinance"}

    def _build_snapshot_alpaca(self, symbol: str) -> dict:
        """Build snapshot from Alpaca API."""
        snapshot = {"symbol": symbol}
        try:
            # Get latest quote
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote_data = self.alpaca_client.get_stock_latest_quote(request)

            if symbol not in quote_data:
                return {"symbol": symbol, "status": "No data", "error": "Symbol not found"}

            quote = quote_data[symbol]

            # Calculate current price (mid-point of bid/ask)
            bid_price = float(quote.bid_price) if quote.bid_price else 0
            ask_price = float(quote.ask_price) if quote.ask_price else 0
            current_price = (bid_price + ask_price) / 2 if bid_price and ask_price else bid_price or ask_price

            # Get previous close from bars
            bars_request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                limit=2
            )
            bars = self.alpaca_client.get_stock_bars(bars_request)

            prev_close = None
            if symbol in bars and len(bars[symbol]) >= 2:
                prev_close = float(bars[symbol][-2].close)

            # Calculate change
            if current_price and prev_close:
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = None
                change_pct = None

            snapshot.update({
                "name": symbol,  # Alpaca doesn't provide company names in quotes
                "price": current_price,
                "change": change,
                "change_pct": change_pct,
                "volume": int(quote.bid_size + quote.ask_size) if quote.bid_size and quote.ask_size else None,
                "volume_label": "Latest volume",
                "time": datetime.now().strftime("%b %d - %H:%M"),
                "status": "Live data",
                "range": None,  # Would need additional API call
                "range_label": None,
            })

        except Exception as exc:
            snapshot["status"] = "Data issue"
            snapshot["error"] = str(exc)
            print(f"Alpaca API error for {symbol}: {exc}")

        return snapshot

    def _build_snapshot_yfinance(self, symbol: str) -> dict:
        """Build snapshot from yfinance (fallback)."""
        snapshot = {"symbol": symbol}
        try:
            handle = self._get_yf_ticker(symbol)
            fast_info = dict(getattr(handle, "fast_info", {}) or {})
            try:
                info = handle.info
            except Exception:
                info = {}

            price = (fast_info.get("last_price") or fast_info.get("lastPrice") or
                     fast_info.get("lastSalePrice") or info.get("regularMarketPrice") or
                     info.get("currentPrice"))
            prev_close = (fast_info.get("previous_close") or fast_info.get("previousClose") or
                          info.get("previousClose"))

            if price is not None and prev_close:
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close else None
            else:
                change = None
                change_pct = None

            volume = (fast_info.get("volume") or info.get("volume") or
                      info.get("averageVolume"))
            high_52 = fast_info.get("yearHigh") or info.get("fiftyTwoWeekHigh")
            low_52 = fast_info.get("yearLow") or info.get("fiftyTwoWeekLow")

            snapshot.update({
                "name": info.get("shortName") or info.get("longName") or symbol,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "volume_label": "Session volume" if fast_info.get("volume") else "Avg volume",
                "time": datetime.now().strftime("%b %d - %H:%M"),
                "status": self._market_status_text(fast_info, info),
            })

            if high_52 and low_52:
                snapshot["range"] = f"${low_52:,.0f} - ${high_52:,.0f}"
                snapshot["range_label"] = "52W range"
            else:
                snapshot["range"] = None
        except Exception as exc:
            snapshot["status"] = "Data issue"
            snapshot["range"] = None
            snapshot["error"] = str(exc)
        return snapshot

    def _build_fundamentals(self, symbol: str) -> dict:
        """Build fundamentals - use yfinance as Alpaca doesn't provide this."""
        if not YFINANCE_AVAILABLE:
            return {"ticker": symbol, "error": "yfinance not available for fundamentals"}

        try:
            handle = self._get_yf_ticker(symbol)
            info = handle.info
            metrics = [
                ("Market Cap", info.get("marketCap", "N/A")),
                ("P/E Ratio", info.get("trailingPE", "N/A")),
                ("Forward P/E", info.get("forwardPE", "N/A")),
                ("EPS", info.get("trailingEps", "N/A")),
                ("Dividend Yield", f"{info.get('dividendYield', 0) * 100:.2f}%"
                 if info.get('dividendYield') else "N/A"),
                ("52 Week High", f"${info.get('fiftyTwoWeekHigh', 'N/A')}"),
                ("52 Week Low", f"${info.get('fiftyTwoWeekLow', 'N/A')}"),
                ("Volume (Avg)", info.get("averageVolume", "N/A")),
                ("Beta", info.get("beta", "N/A")),
            ]
            return {"ticker": symbol, "metrics": metrics}
        except Exception as exc:
            return {"ticker": symbol, "error": str(exc)}

    def _build_news(self, symbol: str) -> dict:
        """Build news from Alpaca or yfinance fallback."""
        if self.news_client and ALPACA_AVAILABLE:
            return self._build_news_alpaca(symbol)
        elif YFINANCE_AVAILABLE:
            return self._build_news_yfinance(symbol)
        else:
            return {"ticker": symbol, "items": [], "error": "No data source available"}

    def _build_news_alpaca(self, symbol: str) -> dict:
        """Fetch news from Alpaca."""
        try:
            request = NewsRequest(symbols=symbol, limit=12)
            news = self.news_client.get_news(request)

            items = []
            for article in news.data:
                date_str = article.created_at.strftime("%b %d") if article.created_at else "--"
                items.append(f"[{date_str}] {article.headline}")

            return {"ticker": symbol, "items": items}
        except Exception as exc:
            print(f"Alpaca news error for {symbol}: {exc}")
            return {"ticker": symbol, "items": [], "error": str(exc)}

    def _build_news_yfinance(self, symbol: str) -> dict:
        """Fetch news from yfinance (fallback)."""
        try:
            handle = self._get_yf_ticker(symbol)
            news_items = getattr(handle, "news", None) or []
            items = []
            for item in news_items[:12]:
                title = item.get("title", "No title")
                timestamp = item.get("providerPublishTime", 0) or 0
                date_str = datetime.fromtimestamp(timestamp).strftime("%b %d") if timestamp else "--"
                items.append(f"[{date_str}] {title}")
            return {"ticker": symbol, "items": items}
        except Exception as exc:
            return {"ticker": symbol, "error": str(exc)}

    def _get_yf_ticker(self, symbol: str):
        """Get or create yfinance ticker handle."""
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance not available")

        with self._lock:
            handle = self._yf_ticker_handles.get(symbol)
            if handle is None:
                handle = yf.Ticker(symbol)
                self._yf_ticker_handles[symbol] = handle
            return handle

    @staticmethod
    def _market_status_text(fast_info: dict, info: dict) -> str:
        """Get market status text from yfinance data."""
        state = (fast_info.get("market_state") or fast_info.get("marketState") or
                 info.get("marketState") or "Live data")
        state = str(state).replace("_", " ")
        return state.title()


class SnapshotWorker(QThread):
    """Background worker to fetch ticker snapshots off the UI thread."""

    result_ready = pyqtSignal(dict)

    def __init__(self, fetch_callable: Callable[[], dict]):
        super().__init__()
        self.fetch_callable = fetch_callable

    def run(self):
        try:
            snapshot = self.fetch_callable()
        except Exception as exc:
            snapshot = {"status": "Data issue", "error": str(exc)}
        self.result_ready.emit(snapshot)
