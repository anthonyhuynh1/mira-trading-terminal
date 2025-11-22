# 🔍 Drag-and-Drop System Analysis

## Current Architecture Overview

Your widget placement system has **4 main components** working together:

```
┌─────────────────────────────────────────────────────────────┐
│                   DRAG-AND-DROP FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. DraggableTabBar  →  2. DropZoneOverlay  →              │
│     (Start drag)        (Visual feedback)                   │
│                                                             │
│  3. WorkspaceDock    →  4. TradingTerminal                 │
│     (Detect drop)        (Execute placement)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Component Breakdown

### **1. DraggableTabBar** (`docking/draggable_tab_bar.py`)

**Purpose:** Handles tab dragging initiation

**What it does:**
```python
# When user clicks and drags a tab:
mousePressEvent()
  → Detects if click is ON a tab (vs empty space)
  → Stores drag starting position

mouseMoveEvent()
  → Tracks mouse movement
  → If moved >10px → Emits drag_started signal
  → Signal contains: tab index + position
```

**Key Logic:**
- Line 27-35: Distinguishes tab clicks from empty space clicks
- Line 42-48: Drag threshold detection (10px Manhattan distance)
- Line 45: Emits `drag_started` signal

**Problems:**
- ✅ **This part works fine** - cleanly detects drag start

---

### **2. DropZoneOverlay** (`docking/drop_overlay.py`)

**Purpose:** Visual feedback showing where tab will be placed

**What it does:**
```python
# Divides dock into zones:
┌─────────────────────────┐
│   ← 30% = 'top'         │
├─────────────────────────┤
│← 30%│   'merge'   │30%→│
│'left'│   (center)  │'rgt│
├─────────────────────────┤
│   ← 30% = 'bottom'      │
└─────────────────────────┘
```

**Key Logic:**
- Line 25: `edge_threshold = 0.30` (30% edge zones)
- Line 35-52: `_detect_zone()` - calculates which zone cursor is in
- Line 54-117: `paintEvent()` - draws visual feedback
  - Edge zones: Show thin line
  - Center: Show border highlight

**Problems:**
- ✅ **Visual feedback works** - zones are detected correctly
- ⚠️ **30% threshold might be too large** - hard to hit center

---

### **3. WorkspaceDock** (`docking/workspace_dock.py`)

**Purpose:** Receives drops and delegates to main window

**What it does:**
```python
# Drop handling flow:
dragEnterEvent() (Line 376)
  → Shows drop overlay
  → Accepts drag if format is "application/x-mira-tab"

dragMoveEvent() (Line 394)
  → Updates overlay cursor position
  → Highlights different zones as cursor moves

dropEvent() (Line 422)
  → Checks if drop is on title/tab area vs body
  → If title area: Calls _handle_tab_drop() (merge tabs)
  → If body: Calls _handle_zone_drop() (split dock)
```

**Key Methods:**
- `_handle_tab_drop()` (Line 601): Merges tab into existing dock
- `_handle_zone_drop()` (Line 466): Calls main window's `handle_zone_drop_on_dock()`
- Passes: source_dock_id, tab_key, target_dock_id, zone

**Problems:**
- ⚠️ **Delegates to main window** - doesn't know about grid structure
- ⚠️ **No validation** - doesn't check if split makes sense

---

### **4. TradingTerminal** (`trading_app.py`)

**Purpose:** Executes the actual placement logic

**What it does:**
```python
handle_zone_drop_on_dock() (Line 307-374)
  1. Takes tab from source dock
  2. If zone == 'merge':
       → Adds tab to target dock
  3. If zone in ['left', 'right', 'top', 'bottom']:
       → Creates NEW dock with the tab
       → Calls split_dock_grid_aware()
       → Balances sizes
```

**Split Logic (Line 459-508):**
```python
split_dock_grid_aware(target, new_dock, zone, orientation):
  1. Determine neighbor direction
  2. Find neighbors using get_dock_neighbors()
  3. If neighbors exist:
       → "Use grid-aware split" (TODO: not actually implemented!)
  4. Else:
       → Just call splitDockWidget()
  5. Return success
```

**Problems - THIS IS WHERE IT BREAKS:**

❌ **Line 502-509: Grid-aware logic is a stub!**
```python
if neighbors:
    # For now, just do the simple split on the target dock
    # A more sophisticated approach would split all neighbors together
    # TODO: Implement multi-dock splitting for perfect grid alignment
    if zone in ['left', 'top']:
        self.splitDockWidget(target_dock, new_dock, orientation)
```

**It says it's grid-aware but actually just calls the same `splitDockWidget()` regardless!**

---

## 🚨 THE MAIN PROBLEMS

### **Problem 1: Grid-Aware Splitting is Not Implemented**

**Current Code (Line 502-515):**
```python
if neighbors:
    # Comment says "split all neighbors together"
    # But code just splits target dock!
    self.splitDockWidget(target_dock, new_dock, orientation)
else:
    # Same code for no neighbors case!
    self.splitDockWidget(target_dock, new_dock, orientation)
```

**Result:**
- Neighbors are detected ✅
- But then... ignored ❌
- Creates nested splits instead of grid alignment

**Example of what goes wrong:**
```
You have:          You drop right:       Should create:
┌────┬────┐        ┌────┬────┬───┐       ┌────┬────┬───┐
│ A  │ B  │   →    │ A  │ B │ C │  BUT  │ A  │ B  │ C │
│    │    │        │    │───────│  IT    │    │    │   │
│    │    │        │    │   C   │  DOES  │    │    │   │
└────┴────┘        └────┴───────┘  THIS  └────┴────┴───┘
                   (B split nested)      (Grid aligned!)
```

---

### **Problem 2: Size Balancing Doesn't Work Properly**

**Current Code (Line 384-390):**
```python
# Balance sizes after splitting
visible_docks = [d for d in self.dock_by_id.values()
                 if not d.isFloating() and not d.isHidden()]
if len(visible_docks) > 1:
    self.balance_dock_sizes(visible_docks, orientation)
```

**Why it fails:**
- Tries to balance ALL visible docks equally
- Doesn't understand grid structure
- Doesn't know which docks are in the same row/column
- Result: Weird sizes

**Example:**
```
You have 3 docks:          After split + balance:
┌────────┬─────┐          ┌────┬────┬────┐
│   A    │  B  │    →     │ A  │ B  │ C  │
│        │     │          │ 33%│ 33%│ 33%│
└────────┴─────┘          └────┴────┴────┘
 (70%      30%)           (All equal - wrong!)
```

---

### **Problem 3: Qt's splitDockWidget() is Naive**

**What `splitDockWidget(A, B, Horizontal)` does:**
1. Takes dock A
2. Splits it in half
3. Puts B next to A

**What it DOESN'T do:**
- Doesn't know about other docks
- Doesn't maintain grid alignment
- Doesn't consider existing structure
- Creates nested splits (bad!)

**Qt's limitation:**
```python
self.splitDockWidget(target, new_dock, orientation)
```
This is designed for simple 2-dock splits, not complex grids!

---

### **Problem 4: No Grid State Management**

**Current system tracks:**
- ✅ `dock_by_id` - maps ID → dock widget
- ✅ `dock_widgets` - maps widget key → dock

**Current system DOESN'T track:**
- ❌ Which row/column each dock is in
- ❌ Grid structure (2x2, 3x1, etc.)
- ❌ Sibling relationships
- ❌ Parent splitters

**Result:** Can't make intelligent placement decisions

---

## 🎯 Why It's Not Working

### **The Core Issue:**

You're trying to build a **grid-based layout** using **Qt's naive docking system**.

Qt's QMainWindow docking is designed for:
- Free-form dock placement
- Nested splitters
- No grid awareness

But you want:
- Structured grid (like Webull)
- Aligned rows/columns
- Predictable placement

**These are fundamentally incompatible!**

---

## 📊 What Actually Happens When You Drag

Let's trace a real scenario:

**Starting state:**
```
┌─────────┬──────────┐
│Screener │  Chart   │
└─────────┴──────────┘
```

**You drag "News" tab and drop it "to the right" of Chart:**

1. ✅ `DraggableTabBar` detects drag
2. ✅ `DropZoneOverlay` shows right edge zone
3. ✅ `WorkspaceDock.dropEvent()` detects zone = 'right'
4. ✅ Calls `handle_zone_drop_on_dock(..., 'right')`
5. ✅ Creates new dock for News
6. ⚠️ Calls `split_dock_grid_aware()`
7. ❌ **Grid-aware logic is stub** - just calls `splitDockWidget()`
8. ❌ Qt splits Chart dock: `Chart | News`
9. ❌ Balance tries to make ALL docks equal size
10. ❌ Result: Screener gets squished, Chart/News unaligned

**What you get:**
```
┌────┬──────┬────┐
│Scr │Chart │News│  ← Not aligned!
│    │──────────│  ← Nested mess!
└────┴──────────┘
```

---

## 💡 What Needs to Happen

### **Short-term fixes (Band-aids):**

1. **Disable grid-aware splitting** - just use simple splits
2. **Remove auto-balancing** - let Qt handle sizes
3. **Use Webull preset only** - don't allow dragging

### **Long-term solutions (Proper fix):**

**Option A: Constrained Docking**
- Limit where docks can be dropped
- Enforce 3-column structure (Webull-style)
- Don't allow arbitrary splits

**Option B: Custom Grid Manager**
- Replace Qt docking with custom layout
- Track grid structure (rows/columns)
- Implement smart placement logic

**Option C: Hybrid Approach**
- Keep Qt docking for flexibility
- Add "snap to grid" feature
- Smart presets that work well

---

## 🔧 Code Locations

**Files involved:**
- `docking/draggable_tab_bar.py` - 91 lines ✅ Works
- `docking/drop_overlay.py` - 118 lines ✅ Works
- `docking/workspace_dock.py` - 642 lines ⚠️ Delegates
- `trading_app.py` - Lines 307-548 ❌ **BROKEN LOGIC HERE**

**The problematic methods:**
- `handle_zone_drop_on_dock()` - Line 307
- `split_dock_grid_aware()` - Line 459 (stub!)
- `get_dock_neighbors()` - Line 422 (unused!)
- `balance_dock_sizes()` - Line 525 (wrong!)

---

## 🎬 Next Steps

I recommend we:

1. **Decide on approach:** Constrained, Custom, or Hybrid?
2. **Remove broken code** - the grid-aware stubs
3. **Implement proper solution** based on decision
4. **Test thoroughly** with multiple scenarios

**What do you think?** Should we:
- Go simple (constrained Webull-only)?
- Go complex (custom grid manager)?
- Go hybrid (smart presets + free dragging)?

Let me know and I'll implement the proper solution! 🚀
