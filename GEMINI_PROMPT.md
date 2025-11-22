# Task: Implement Multi-Page Tab System for Trading Terminal

## Current State
- Working PyQt6 trading terminal application (`trading_app.py`)
- Has header with "Mira" branding, market clock, and control buttons
- Uses QMainWindow with dock widgets for layout (Quotes, Chart, Screener, Fundamentals, News, Copilot)
- Single-page application currently

## Objective
Add a Chrome-style tab bar system to enable multiple pages, where each page can have different:
- Primary ticker being viewed
- Widget configurations/layouts

## Requirements

### Visual Design
1. **Header**: Keep existing header exactly as-is (white card in light mode, dark card in dark mode with "Mira", clock, buttons)
2. **Tab Bar**: Add horizontal tab bar immediately below header with:
   - Individual tabs showing page ticker(s) (e.g., "SPY" or "TSLA, SPX" if using link groups)
   - Active tab has subtle underline indicator
   - Inactive tabs have slightly muted background
   - Hover effect on tabs
   - Small "×" close button appears on hover (right side of each tab)
   - "+" button on far right to create new tabs
   - Clean, minimal design matching existing aesthetic

### Theme Compatibility
- **Light mode colors**:
  - Tab bar background: `#f0f0f0`
  - Active tab: `#e8e8e8` with `#2196F3` (blue) underline
  - Inactive tab: `#f5f5f5`, hover: `#eeeeee`
  - Text: `#000000` active, `#666666` inactive

- **Dark mode colors**:
  - Tab bar background: `#1e1e1e`
  - Active tab: `#3a3a3a` with `#ffffff` underline
  - Inactive tab: `#2a2a2a`, hover: `#333333`
  - Text: `#ffffff` active, `#aaaaaa` inactive

### Functional Requirements
1. **Tab Management**:
   - Each tab represents a separate "page" with its own state
   - Clicking tab switches to that page
   - Clicking "+" creates new page
   - Clicking "×" closes tab (prevent closing last tab)
   - Support drag-to-reorder tabs (optional but nice)

2. **Page State**:
   - Each page tracks:
     - `page_id`: Unique identifier
     - `page_name`: Display name (defaults to primary ticker or "Untitled")
     - `primary_ticker`: Main ticker being viewed
     - `widget_states`: Which widgets are open/visible
   - Pages managed by `StockPageManager` class

3. **Integration Points**:
   - Create `core/stock_page.py` - StockPage data class
   - Create `core/stock_page_manager.py` - Manager for page lifecycle
   - Create `ui/page_tab_bar.py` - Tab bar UI component
   - Modify `trading_app.py` to integrate tab system

### Technical Constraints
- Must work with existing QMainWindow + dock widget architecture
- Docks should remain functional and not be blocked by new layout
- Tab bar must render properly (full widget rendering, not just text labels)
- Use standard PyQt6 layouts (QVBoxLayout, QHBoxLayout)
- Header must stay at top, tab bar below it, docks in remaining space

### Existing Code Context
- `trading_app.py` uses `create_header()` to build header (line ~909)
- Currently sets header via `setMenuWidget()`
- Uses `WorkspaceDock` subclass for all dock widgets
- Has ticker synchronization system with link groups (groups 1-6)
- Theme system in `core/themes.py` with `THEMES` dict

## Deliverables
1. Three new Python files with complete implementations
2. Modifications to `trading_app.py` __init__ method to integrate tab system
3. Ensure tabs render visually with proper styling (not just text labels)
4. Test that "+" button works to create new tabs without crashing

## Key Success Criteria
- ✅ Tabs are VISIBLE with proper backgrounds, borders, and styling
- ✅ "+" button appears and creates new tabs
- ✅ "×" close button appears on hover
- ✅ Active tab has visible underline indicator
- ✅ Header remains at top, unchanged
- ✅ Docks continue to work normally
