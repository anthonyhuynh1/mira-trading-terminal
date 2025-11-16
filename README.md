# Trading Terminal - AI-Powered Trading Analysis Platform

A professional desktop trading application with context-aware AI assistant, inspired by TradingView's UI and Cursor's AI capabilities.

## 🎯 Features

- **TradingView-like Dark Theme**: Professional, easy-on-the-eyes interface
- **Candlestick Charts**: Full OHLCV visualization with breakout signals
- **Multiple Timeframes**: Switch between 1h, 4h, and daily charts
- **Context-Aware AI**: Chatbot understands what you're viewing and provides relevant analysis
- **Signal Detection**: True/false breakout detection with dynamic volume thresholds
- **Fundamentals & News**: Integrated company data and news feed
- **No Auto-Trading**: Analysis and education only - you make the decisions

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

**Note:** PyQt6-WebEngine is required for TradingView charts. If you encounter issues, install it separately:
```bash
pip install PyQt6-WebEngine
```

### Run

**Option 1: Using the run script (easiest)**
```bash
./run.sh
```

**Option 2: Manual activation**
```bash
# From parent directory
source .venv/bin/activate
cd trading-terminal
python trading_app.py
```

## 📐 Architecture

- **Left Sidebar**: Stock screener and watchlist
- **Main Panel**: Interactive charts with tabs (Chart | Fundamentals | News)
- **Right Sidebar**: Context-aware AI chatbot

## 🎨 UI Components

### Chart Features
- **TradingView Advanced Chart Widget** - official charting experience
- Candlestick visualization with the full TradingView toolbar
- Consolidation bands (support/resistance)
- True breakout signals (high volume) - marked on chart
- False breakout signals (low volume) - marked on chart
- Multiple timeframes (1h, 4h, 1d)
- Zoom, pan, and crosshair functionality
- Light/Dark theme toggle with curated palettes
- Dockable panels (watchlist, assistant) you can move/rescale

### AI Assistant
- Explains signals and patterns
- Provides trade setup analysis
- Answers strategy questions
- Context-aware responses based on current ticker/timeframe

## 📊 Strategy

**Consolidation + Breakout + Volume Strategy**

1. Identifies tight consolidations (≤ 2% range)
2. Detects breakouts above consolidation high
3. Confirms with volume:
   - High volume (≥ 75th percentile) = True breakout (long)
   - Low volume (< 25th percentile) = False breakout (short opportunity)
4. Risk management: Stop at consolidation low, target at 2R

## 🔧 Tech Stack

- **PyQt6**: Desktop GUI framework
- **PyQt6-WebEngine**: Web view for TradingView charts
- **TradingView Lightweight Charts**: Free, open-source professional charting library
- **yfinance**: Market data (free)
- **Pandas/NumPy**: Data processing

## 📝 Project Structure

```
trading-terminal/
├── trading_app.py      # Main application
├── strategy.py         # Strategy logic and signal generation
├── requirements.txt    # Dependencies
└── README.md          # This file
```

## 🗺️ Roadmap

- [x] Basic UI with dark theme
- [x] Candlestick charts
- [x] Timeframe selector
- [x] Context-aware AI
- [ ] Pattern recognition
- [ ] Drawing tools
- [ ] More indicators
- [ ] Alpaca API integration (when ready)

## ⚠️ Disclaimer

This platform is for **analysis and education only**. It does not execute trades. All trading decisions are your own responsibility. Past performance does not guarantee future results.

## 📄 License

MIT License - Feel free to use and modify.

