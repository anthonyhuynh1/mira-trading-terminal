# Trading Terminal Refactoring Plan
**Date:** November 21, 2025
**Status:** Ready to start - Refactor first, then fix grid layout

---

## Current State

**File:** `trading_app.py` (~3000 lines)
- Everything in one massive file
- Hard to maintain and navigate
- Works well, just needs organization

**What's Working:**
- Drop zone overlay with edge detection (left/right/top/bottom) and merge
- Visual feedback: thin lines for edges, border for merge
- Tab dragging from multi-tab docks
- Workspace presets (Bloomberg, Trading, Research)
- Theme system (dark/light)

**What Needs Fixing (After Refactor):**
1. **Grid layout awareness** - splits don't consider grid context (rows/columns)
2. **Smart splitting** - when dropping "to the right", should maintain grid structure
3. **Size management** - docks get weirdly sized after multiple splits
4. **Ecosystem thinking** - changes should consider the entire layout, not just one dock

---

## Phase 1: Refactor (Do This First)

**Goal:** Split `trading_app.py` into organized modules WITHOUT changing functionality

**Estimated Time:** 2-3 hours

### New File Structure:
```
trading-terminal/
├── trading_app.py (main entry, ~500 lines)
│   └── Main application, window setup, entry point
│
├── widgets/
│   ├── __init__.py
│   ├── chart.py          # ChartWidget
│   ├── quotes.py         # QuoteWidget
│   ├── screener.py       # ScreenerWidget
│   ├── fundamentals.py   # FundamentalsWidget
│   ├── news.py           # NewsWidget
│   ├── chatbot.py        # ChatbotWidget
│   └── market_clock.py   # MarketClockWidget
│
├── docking/
│   ├── __init__.py
│   ├── workspace_dock.py      # WorkspaceDock class
│   ├── drop_overlay.py        # DropZoneOverlay class
│   └── draggable_tab_bar.py  # DraggableTabBar class
│
├── layout/
│   ├── __init__.py
│   └── workspace_manager.py   # WorkspaceManager class + presets
│
├── core/
│   ├── __init__.py
│   ├── themes.py             # THEMES dict + theme-related code
│   └── data_provider.py      # TickerDataProvider + SnapshotWorker
│
└── strategy.py (already separate)
```

### Step-by-Step Refactoring Plan:

**Step 1: Create Directory Structure**
```bash
mkdir -p widgets docking layout core
touch widgets/__init__.py docking/__init__.py layout/__init__.py core/__init__.py
```

**Step 2: Extract in This Order** (to minimize import issues):

1. **core/themes.py** (no dependencies)
   - Extract: THEMES dict, BASE_RADIUS, BASE_SPACING, TOUCH_TARGET constants

2. **core/data_provider.py** (minimal dependencies)
   - Extract: TickerDataProvider class, SnapshotWorker class

3. **docking/drop_overlay.py** (only Qt dependencies)
   - Extract: DropZoneOverlay class (~150 lines, starts around line 612)

4. **docking/draggable_tab_bar.py** (only Qt dependencies)
   - Extract: DraggableTabBar class (~80 lines)

5. **docking/workspace_dock.py** (depends on drop_overlay, draggable_tab_bar)
   - Extract: WorkspaceDock class (~600 lines, starts around line 695)

6. **layout/workspace_manager.py** (depends on workspace_dock)
   - Extract: WorkspaceManager class + all preset layout functions (~250 lines, starts around line 341)

7. **widgets/*.py** (extract each widget class)
   - QuoteWidget (~160 lines, starts around line 935)
   - MarketClockWidget (~80 lines, starts around line 1095)
   - ChartWidget (~110 lines, starts around line 1173)
   - FundamentalsWidget (~85 lines, starts around line 1285)
   - NewsWidget (~80 lines, starts around line 1371)
   - ChatbotWidget (~215 lines, starts around line 1453)
   - ScreenerWidget (~115 lines, starts around line 1670)

8. **trading_app.py** (keep only TradingTerminal class + main entry)
   - Update imports to reference new modules
   - Keep: TradingTerminal class, main() function, if __name__ == '__main__'

**Step 3: Update Imports**
- Each file imports what it needs from PyQt6
- Files import from each other as needed
- trading_app.py imports everything and wires it together

**Step 4: Test**
- Run the app after refactoring
- Ensure everything still works
- No functionality changes, just organization

---

## Phase 2: Fix Grid Layout (Do This After Refactor)

**Goal:** Make dock splitting aware of grid layout context

**Estimated Time:** 4-6 hours

### Problems to Solve:

1. **Grid Context Detection**
   - When dropping "to the right of Chart", detect if there are other docks in that column
   - Determine if we should split just that dock or the entire column

2. **Smart Splitting Logic**
   - If dropping between columns → create new column, shift everything
   - If dropping within a dock → split just that dock
   - Maintain grid structure (aligned rows/columns)

3. **Size Management**
   - Set size policies so docks don't get weirdly sized
   - Maintain proportional sizing after splits
   - Use Qt's size hints effectively

### Implementation Approach:

**In `docking/workspace_dock.py`:**
- Add method to detect neighboring docks (above/below, left/right)
- Add grid context to drop zone detection

**In `trading_app.py` (TradingTerminal):**
- Modify `handle_zone_drop_on_dock()` to be grid-aware
- Add helper methods:
  - `get_dock_neighbors(dock)` - returns docks in same row/column
  - `split_dock_grid_aware(target, new_widget, zone)` - smart splitting
  - `balance_dock_sizes(affected_docks)` - maintain reasonable sizing

**Key Insight:**
- Don't just call `splitDockWidget(A, B)`
- Check grid context first
- Split all docks in the same row/column if needed
- Keep things aligned

---

## Current Issues (To Fix in Phase 2)

1. **Drop zones show but placement is wrong** - overlay was covering title bar (FIXED)
2. **App crashes when dragging** - added error handling (PARTIALLY FIXED)
3. **Splits don't consider grid** - needs Phase 2 fix
4. **Sizes get weird** - needs Phase 2 fix

---

## Notes for Next Session

**Don't forget:**
- The design is good, just needs refinement
- User loves the current visual style (subtle brilliance, minimal)
- Drop zones: edges show line, center shows border (DONE)
- Webull-style system but with our aesthetic (cleaner, more minimal)
- 30% edge threshold for drop zones (DONE)

**Testing Checklist (After Each Phase):**
- [ ] App launches without errors
- [ ] Can drag tabs between docks
- [ ] Drop zones appear correctly (edges = line, center = border)
- [ ] Drops work without crashing
- [ ] Workspace presets load correctly
- [ ] Theme switching works
- [ ] All widgets display properly

---

## Quick Start Commands (Next Session)

```bash
# Navigate to project
cd "/Users/anthony/Trading /Python Financials/trading-terminal"

# Create directory structure
mkdir -p widgets docking layout core
touch widgets/__init__.py docking/__init__.py layout/__init__.py core/__init__.py

# Start refactoring with themes (easiest first)
# Extract THEMES, BASE_RADIUS, BASE_SPACING, TOUCH_TARGET to core/themes.py
```

**First File to Create:** `core/themes.py`
**Last File to Update:** `trading_app.py` (update all imports)

---

## Estimated Timeline

- **Phase 1 (Refactor):** 2-3 hours
- **Phase 2 (Grid Layout):** 4-6 hours
- **Total:** 6-9 hours

**Let's start with Phase 1 next session!** 🚀
