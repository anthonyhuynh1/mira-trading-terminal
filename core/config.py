"""
Application configuration and default settings.
"""

# Default watchlist for screener and initial ticker selection
DEFAULT_TICKERS = [
    "SPY",   # S&P 500 ETF
    "QQQ",   # NASDAQ-100 ETF
    "AAPL",  # Apple
    "MSFT",  # Microsoft
    "NVDA",  # NVIDIA
    "AMD",   # AMD
    "TSLA",  # Tesla
    "META",  # Meta
    "GOOGL", # Google
    "AMZN",  # Amazon
]

# Chart default settings
DEFAULT_CHART_INTERVAL = "60"  # 1 hour (TradingView interval code)

# Data refresh intervals (milliseconds)
QUOTE_REFRESH_INTERVAL = 15000  # 15 seconds
NEWS_REFRESH_INTERVAL = 300000  # 5 minutes

# Market data settings
DEFAULT_PERIOD_DAYS = 30  # Default historical data period
