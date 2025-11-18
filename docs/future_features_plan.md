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

## SEC Filings – Implementation Notes
- **Data Ingestion**
  - Use SEC “company facts” + “submissions” endpoints (`https://data.sec.gov/submissions/CIK########.json`).
  - Cache responses per ticker (CIK lookup table) with 5-minute TTL, respect 10 req/sec rate limit + custom UA header.
  - Normalize filings into dataclass: `Filing(id, type, filed_at, title, summary, link, risk_flags)`.
- **Processing**
  - Generate TL;DR via lightweight heuristic (first paragraph + bullet extraction) before piping to Copilot for refinement.
  - Tag filings with categories (Guidance, M&A, Product, Risk) using keyword map for quick filtering.
- **UI Integration**
  - Dock widget layout: left list (type/date), right detail pane with highlight + “Open in browser”.
  - Hero row “Latest Filing” card pulls next upcoming/most recent entry for active ticker.
  - Link group support so changing ticker refreshes filings automatically.
- **Alerts**
  - Hook into future alert tray; simple MVP = modal toast when watched ticker files within last hour.

## Economic Calendar – Implementation Notes
- **Data Source Options**
  - Scrape ForexFactory HTML (requires schedule + caching) or leverage APIs (EconDB, TradingEconomics, Finnhub). Evaluate licensing.
  - Normalize events: `Event(id, datetime_utc, currency, impact, title, actual, forecast, previous, notes)`.
- **UI**
  - Widget header with date selector + timezone dropdown.  
  - Table rows: impact dot, time (local + user zone), event name, actual/forecast/previous columns, affected tickers badge (optional).  
  - Provide “Today / Week / Custom” filters and search bar.
- **Hero Integration**
  - “Next Up” mini-card highlighting highest-impact event within next 4 hours.
- **Alerting**
  - Countdown pill per event; allow adding alert (“Notify 15m before release”).
- **Copilot Hooks**
  - Copilot can answer “How might today’s CPI affect NVDA?” using calendar data + strategy heuristics.

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


