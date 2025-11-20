# Mira Trading Terminal

A beautiful, fast desktop trading terminal built with PyQt6.

## Features

- **Live Market Data**: Real-time quotes, charts, and market status
- **TradingView Integration**: Professional-grade charts with multiple timeframes
- **Customizable Layout**: Drag-and-drop docking system with floating windows
- **Link Groups**: Synchronize multiple widgets to the same ticker
- **Dark/Light Themes**: Pure black/white aesthetic with brand color accents
- **Multiple Widgets**:
  - Quote card with live prices
  - Interactive TradingView charts
  - Watchlist/Screener
  - Fundamentals (P/E, market cap, etc.)
  - Latest news headlines
  - AI-powered chatbot copilot
  - Multi-timezone market clock

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run

```bash
python trading_app.py
```

Or use the run script:
```bash
./run.sh
```

## Requirements

- Python 3.10+
- PyQt6
- PyQt6-WebEngine
- yfinance
- numpy
- websockets

See `requirements.txt` for complete list.

## Architecture

The app is built with a modular widget system:

- **TradingTerminal**: Main window with docking manager
- **WorkspaceDock**: Custom dock widgets with inline tabs
- **TickerDataProvider**: Centralized caching layer for market data
- **SnapshotWorker**: Background threads for non-blocking data fetching

All widgets support:
- Theme switching (dark/light)
- Link groups for ticker synchronization
- Drag-and-drop repositioning
- Minimize/expand/float controls

See `ARCHITECTURE.md` for detailed technical overview.

## Usage

1. **Search for a ticker**: Use the Screener widget to find stocks
2. **Click to select**: Selected ticker updates all linked widgets
3. **Customize layout**: Drag docks to reposition, float windows
4. **Link groups**: Right-click dock → Link Group → Choose 1-6
5. **Theme toggle**: Click sun/moon icon in header

## Project Structure

```
trading-terminal/
├── trading_app.py          # Main application (2,436 lines)
├── strategy.py             # Consolidation/breakout detection
├── requirements.txt        # Python dependencies
├── run.sh                  # Launch script
├── docs/                   # Documentation
├── legacy/                 # Old versions (archived)
└── venv/                   # Python virtual environment
```

## Development

The app uses PyQt6's signal/slot mechanism for communication between widgets. Key patterns:

- **Data fetching**: Always use background QThreads to avoid UI freezing
- **Theming**: Check `self.window().current_theme` and apply styles dynamically
- **Link groups**: Emit signals through main window's link group manager

## Known Issues

- Some stocks may not have complete fundamental data (yfinance limitation)
- TradingView charts require internet connection
- Market status updates every 60 seconds

## License

Personal project - use freely.

