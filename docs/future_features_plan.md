# Mira – Future Feature Roadmap & Brainstorm

## Near-Term Goals
1. **SEC Filings Console**
   - Aggregate 8-K/10-Q/10-K and proxy updates per ticker via EDGAR API.
   - Inline summarization akin to Perplexity’s “key takeaways”.
   - Alert hooks: notify when a watched ticker files within last N hours.

2. **Macro & Economic Calendar**
   - ForexFactory-style feed (NFP, CPI, FOMC, PMI) with timezone localization.
   - Impact tagging (low/med/high) and countdown timers.
   - Ability to link events to affected tickers or sectors for proactive watchlists.

3. **Intelligent Alerts Layer**
   - Blend filings, earnings, price/volume triggers, and macro releases into a unified alert timeline.
   - Allow natural-language queries (“Ping me if TSLA files an 8-K mentioning production”).

## Medium-Term Ideas
- **Perplexity-inspired Research Threads**
  - Multi-source summaries (filings, press releases, transcripts, news) with citations inside the Copilot chat.
  - Save/share “research cards” tied to link groups.
- **Strategy Backtesting UI**
  - Visual overlay of consolidation/breakout signals on the TradingView pane with trade stats.
  - Scenario builder for custom ticker baskets.
- **Portfolio/Watch Buckets**
  - Group tickers by intent (swing, earnings, macro sensitive) with dedicated layout presets.

## Exploration Topics
- Vendor evaluation for SEC + macro feeds (EDGAR, Polygon, Finnhub, ForexFactory scraping vs API).
- Offline/queued data handling so filings/macro events preload even when widgets are closed.
- User personalization: accent colors by portfolio, saved workspace states, cross-device sync.

> This document is living—add new concepts or move items across sections as priorities firm up.

