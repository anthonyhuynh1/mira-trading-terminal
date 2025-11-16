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

### Run

```bash
python trading_app.py
```

## 📐 Architecture

- **Left Sidebar**: Stock screener and watchlist
- **Main Panel**: Interactive charts with tabs (Chart | Fundamentals | News)
- **Right Sidebar**: Context-aware AI chatbot

## 🎨 UI Components

### Chart Features
- Candlestick visualization
- Consolidation bands (support/resistance)
- True breakout signals (high volume)
- False breakout signals (low volume)
- Dynamic volume thresholds
- Multiple timeframes (1h, 4h, 1d)

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
- **Matplotlib**: Chart rendering
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

