# 🧪 Drag-Drop Testing Guide

## Fixes Applied

### 1. ✅ Drop Zone Visual Positioning
**Fixed:** Drop zones now appear AT the edges (borders) instead of 30% inside the widget

**Before:**
```
┌────────────────────────┐
│       │                │  ← Line 30% from left
│       │                │
└────────────────────────┘
```

**After:**
```
│──────────────────────┐
│                      │  ← Line AT left edge
│                      │
└──────────────────────┘
```

### 2. ✅ Widget Disappearing Fix
**Fixed:** Added error recovery - if drop fails, widget is restored to source dock

**Error handling:**
- ❌ Validation fails → Widget stays in source
- 💥 Exception during drop → Widget restored to source
- 🔧 Auto-recovery with console messages

### 3. ✅ Auto-Registration
**Fixed:** Docks not registered in ColumnManager are auto-registered on first drop

## Test Scenarios

### Basic Tab Dragging
1. **Drag Chart tab to News dock center**
   - Expected: Tabs merge, Chart becomes tab in News dock
   - Console: "=== Column Layout ===" output

2. **Drag Chart tab to News dock RIGHT edge**
   - Expected: White line appears AT right edge (not inside)
   - Result: New column created to the right
   - Console: Shows new column added

3. **Drag Chart tab to News dock BOTTOM edge**
   - Expected: White line appears AT bottom edge
   - Result: Chart stacked below News in same column
   - Console: Shows dock added to column stack

### Validation Tests

4. **Try to drag Screener widget**
   - Expected: 🚫 Console message: "Drop blocked: Cannot move screener widget"
   - Result: Screener stays in place

5. **Try to drop LEFT of Screener**
   - Expected: 🚫 Console message: "Drop blocked: Cannot add column left of screener"
   - Result: Drop rejected

### Error Recovery

6. **Simulate drop failure** (intentional error)
   - Expected: 🔧 Console message: "Restoring widget back to source dock"
   - Result: Widget appears back where it started

### Visual Feedback

7. **Hover over dock edges**
   - LEFT edge: Line should appear at x=2 pixels (far left)
   - RIGHT edge: Line should appear at x=width-2 pixels (far right)
   - TOP edge: Line should appear at y=2 pixels (top)
   - BOTTOM edge: Line should appear at y=height-2 pixels (bottom)
   - CENTER: Border highlight around entire dock

8. **Hover over title bar**
   - Expected: Simple highlight (no drop zones)
   - Result: Can merge tabs by dropping on title

## Expected Console Output

When dragging Chart to right of News:
```
=== Column Layout ===
Column 0 [SCREENER]:
  [0] dock_0
Column 1:
  [0] dock_1
Column 2:
  [0] dock_2
Column 3:
  [0] dock_3
====================
```

When validation blocks screener drag:
```
🚫 Drop blocked: Cannot move screener widget
```

When error occurs:
```
💥 Error in handle_zone_drop_on_dock: <error message>
🔧 Restoring widget 'Chart' back to source dock
```

## Known Limitations (To Implement)

### Tab vs Dock Drag (User Request)
**Not yet implemented:**
- Drag TAB (from tab bar) = Move single widget ✅ *Already works*
- Drag DOCK (from title bar) = Move all tabs ❌ *Need to implement*

This would require:
1. Enable drag from title bar area (not just tabs)
2. Package all tab keys in drag data
3. Detect multi-tab drag on drop
4. Merge all tabs at once

**Current behavior:**
- Can only drag individual tabs from tab bar
- Qt's built-in dock dragging repositions the whole dock (doesn't merge tabs)

## How to Test

1. **Run the app:**
   ```bash
   cd "/Users/anthony/Trading /Python Financials/trading-terminal"
   python trading_app.py
   ```

2. **Watch console output** for debugging messages

3. **Test each scenario** from the list above

4. **Look for:**
   - ✅ Drop zones AT edges (not inside)
   - ✅ Widgets don't disappear
   - ✅ Column layout updates
   - ✅ Screener stays locked
   - ✅ Error messages are helpful

## If Issues Persist

Report:
1. Which test scenario failed
2. What you expected vs what happened
3. Console output
4. Whether widget disappeared or stayed

## Next Phase: Tab vs Dock Drag

If current fixes work well, we'll implement:
- **Drag handle area** in title bar (empty space next to tabs)
- **Multi-tab drag data** packaging
- **Bulk tab merge** on drop
- **Visual distinction** (cursor changes based on drag type)
