# Mira Trading Terminal – Current System Overview

## Shell & Layout
- `TradingTerminal` (PyQt6 `QMainWindow`) with nested/tabbed docks, hero “Quote” card, market clock, and header controls for refresh/widget spawning/theme.
- Custom `WorkspaceDock` title bars with inline tab strip, expand/minimize/float controls, stow bar for collapsed widgets, and link groups (1-6) for synchronized tickers.
- Dock bodies keep a padded `QFrame` shell with a `QStackedWidget`, so each module shares the same spacing/border treatment while tab swaps stay instant.
- Qt’s native dock tabbing is disabled; instead, Mira’s header hosts its own lightweight tab strip so multiple widgets can stack without spawning extra title bars.
- Double-clicking a dock title toggles float/dock, while the adjacent options menu now exposes link groups plus an “Add Widget…” shortcut so users can spawn modules directly from any existing dock.
- Inline tab pills (custom `QTabBar`) live in the same header, so adding a widget from a dock simply stacks it into the dock’s own `QStackedWidget`; switching tabs is instantaneous and keeps the single-header aesthetic.

## Live Data & Background Work
- `SnapshotWorker` (QThread) fetches hero quote snapshots from `yfinance` (fast_info + info fallback). Results hydrate hero stats, apply dynamic brand accent, and drive status badges.
- TradingView `QWebEngineView` embed caches last (ticker, interval, theme) signature to avoid redundant reloads; theme refresh resets the cache.
- Strategy helpers (`strategy.py`) provide ticker universe, consolidation/breakout analytics leveraged by Screener and Copilot context.
- `TickerDataProvider` centralizes all `yfinance` calls with coarse TTL caches (snapshots, fundamentals, news) so widgets reuse payloads instead of hammering the network/UI thread.

## Core Widgets
- **QuoteWidget**: hero stats (price/change/volume/range) plus market status badge and interval awareness.
- **ChartWidget**: TradingView advanced chart embed with interval switching, theme-aware backgrounds.
- **ScreenerWidget**: search, quick filters, “Scan Universe” stub, watchlist list, broadcasts selections through link system.
- **FundamentalsWidget**: tabular metrics (market cap, P/E, EPS, div yield, 52-week stats, volume, beta) fetched via `yfinance`.
- **NewsWidget**: latest headlines/time stamps per ticker (fallback message when empty or error).
- **ChatbotWidget (Copilot)**: context-aware assistant using strategy data, handles breakout explanations, risk framing, etc.
- **MarketClockWidget**: timezone selector (NYSE/LSE/TSE), per-market open/pre/after status, continuous timer.

## Theming & UX Principles
- Pure black/white palette with theme dictionary (dark & light) controlling surfaces, borders, tab invert colors, inputs, and hero gradients.
- Header buttons use monochrome glyphs (`↻`, `+`, `☀/☾`) aligned with market clock; utility and toggle buttons share square outlines.
- Widgets hide internal headers when tabified, showing only the shared dock tab strip; selections broadcast to linked docks, ensuring quotes/charts/fundamentals stay in sync.

## Known Assets & Tech Stack
- Python 3, PyQt6 (Widgets + WebEngine), `yfinance`, TradingView JS embed, strategy analytics module, minimal requirements in `requirements.txt`.
- Global env tweaks (`QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu`, `AA_ShareOpenGLContexts`) ensure macOS reliability with WebEngine.

