# Mira Trading Terminal – UI/UX Overhaul Blueprint

## 1. Guiding Principles
- **Think like Perplexity for markets**: fast answers, compressed signal, citations.
- **One mental model per surface**: hero (context), workspace (analysis), copilot (explanations), utility (shortcuts).
- **Clear hierarchy via tone-on-tone layers** (charcoal/graphite for dark, cloud/ink for light); reserve accent color for alerts/selections.
- **Deterministic spacing**: 8 px grid, 32 px gutters, 48 px minimum tap targets.
- **Linked-context clarity**: every widget that reflects a shared ticker shows its link state (badge or underline) so traders trust synchronization.

## 2. Current Flow Audit
| Area | Current Behavior | Pain Points |
| --- | --- | --- |
| Header | Clock, theme toggle, refresh/add buttons loosely aligned | Buttons float, inconsistent padding, “market status” badge drifts |
| Hero Snapshot | Quote stats + market badge atop main workspace | Needs better delineation from dock stack, colors sometimes clash |
| Dock Workspace | Custom `WorkspaceDock` title bars with inline tabs, link menu on double-click | Title text can truncate, tab density high, no persistent nav |
| Left Stack | Screener/watchlist list widget | Needs better empty state and quick filter chips |
| Right Stack | Copilot chat full height | Works but header could host conversation controls |

## 3. Proposed Flow
1. **Top App Bar (64 px)**  
   - Left: brand wordmark + workspace selector (future).  
   - Center: market status capsule (Pre / Open / Post) + session clock (NY + selectable).  
   - Right: icon-only buttons (`↻`, `＋`, `☀/☾`), notifications bell (future alerts), user avatar stub.
   - Use glass panel styling (tab_bg color, 1 px divider).

2. **Hero Context Row (96 px)**  
   - Quote snapshot (price/change/volume) + quick actions (set alert, add to list).  
   - Adjacent micro-panels: “Next Events” (economic calendar glance) and “Latest Filing” summary.

3. **Workspace Grid** (draggable docks remain, but default layout = 3-column)  
   - **Column A (320 px, fixed)**: Screener/Search + Watch buckets.  
   - **Column B (flex)**: Chart (top), Fundamentals/News (tabs).  
   - **Column C (360 px)**: Copilot + Alert feed.

4. **Tab Strip Behavior**  
   - Maintain inline tab buttons within each dock header.  
   - Active tab uses accent underline; inactive tabs adopt muted text color.  
   - Link badge sits before title (e.g., `·#2 Chart`).

5. **Selection Feedback**  
   - Replace full-row white highlight with accent border + slight surface lift.  
   - Text color adapts using `ideal_text_color` to avoid white-on-white.

## 4. Component Updates
### Header Controls
- Consolidate into `HeaderButtonGroup` QWidget managing spacing + hover states.
- Add tooltip conventions (“Refresh data”, “Spawn widget”, “Toggle theme”).
- Consider `QAction` shortcuts (⌘R refresh, ⌘⇧N add widget).

### Market Clock & Status
- Combine into single `MarketPulse` widget (pill: `PRE · NYSE · 09:22:15 EDT`).
- Poll timer every second (existing) but animate color when session switches.

### Screener / Watch Buckets
- Add filter chips (Momentum, Earnings, AI, Custom).  
- Provide empty-state card with CTA to add tickers.  
- Ensure row highlight uses accent border + text inversion fix.

### Copilot Pane
- Introduce conversation header (ticker context, temperature, clear chat).  
- Show “research threads” list when idle (Perplexity inspiration).

### Dock Title Bars
- Rebalance padding to 8 px vertical / 12 px horizontal.  
- Tab buttons become `QToolButton` with uppercase label + underline animation.

## 5. Implementation Phases
1. **Phase 1 – Structural Refactor (UI polish)**  
   - Build `HeaderButtonGroup`, `MarketPulse`, hero micro-panels.  
   - Update screener list selection visuals + filter chips.  
   - Tighten dock header styles and link badge display.  
   - Validate both light/dark themes.

2. **Phase 2 – SEC Filings Surface**  
   - Create `SecFilingsWidget` dock: ticker selector, filings list, detail preview.  
   - Data layer using SEC EDGAR RSS/JSON; cache per ticker; summary view with TL;DR.  
   - Hook into link groups + hero “Latest Filing”.

3. **Phase 3 – Economic Calendar (Forex Factory inspired)**  
   - `MacroCalendarWidget`: date navigator, event rows (time, currency, impact, actual/forecast).  
   - Global timeline card for next high-impact events in hero row.  
   - Option to trigger alerts + color-coded impact dots.

4. **Phase 4 – Alerts & Research Threads (stretch)**  
   - Unified alert tray, Copilot research cards referencing filings/macro events.

## 6. Fast Execution Checklist
- [ ] Extract reusable header widgets (`MarketPulse`, `HeaderButtonGroup`).  
- [ ] Redesign hero row layout (quote + filings/macro slots).  
- [ ] Update selection/highlight styles in screener/watchlist.  
- [ ] Scaffold `SecFilingsWidget` + `MacroCalendarWidget` (UI + placeholder data).  
- [ ] Wire both widgets into dock registration + link groups.  
- [ ] Add placeholder data providers + TODO hooks for live APIs.

Deliverable: apply structural/UI changes first, then slot in data-driven widgets leveraging the new layout without major rewrites later.



