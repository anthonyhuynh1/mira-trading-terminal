"""
Trading Terminal Application - Modular Architecture
Left: Stock Screener | Main: Charts/Fundamentals/News | Right: Context-Aware Chatbot
"""

import sys
import warnings
import traceback
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict

warnings.filterwarnings("ignore")

import os
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDockWidget, QSizePolicy, QFrame, QToolButton, QMenu,
    QToolBar, QTabWidget, QStyle, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QIcon, QCursor

# Import our custom modules
from core.themes import (
    THEMES, BASE_RADIUS, BASE_SPACING, TOUCH_TARGET, BRAND_COLORS,
    ticker_hash_color, soften_color, mix_colors
)
from core.data_provider import TickerDataProvider, SnapshotWorker
from core.stock_page_manager import StockPageManager
from docking.workspace_dock import WorkspaceDock
from layout.workspace_manager import WorkspaceManager
from ui.page_tab_bar import PageTabBar
from widgets.quotes import QuoteWidget
from widgets.market_clock import MarketClockWidget
from widgets.chart import ChartWidget
from widgets.screener import ScreenerWidget
from widgets.fundamentals import FundamentalsWidget
from widgets.news import NewsWidget
from widgets.chatbot import ChatbotWidget

# Import configuration
from core.config import DEFAULT_TICKERS


class TradingTerminal(QMainWindow):
    """Main application window - Cursor-like interface."""
    
    def __init__(self):
        super().__init__()
        self.current_ticker = None
        self.current_theme_name = "dark"
        self.theme_button = None
        self.refresh_button = None
        self.status_badge = None
        self.widget_button = None
        self.quote_widget = None
        self.chart_widget = None
        self.chatbot = None
        self.screener = None
        self.fundamentals_widget = None
        self.news_widget = None
        self.stowed_actions: dict[str, QAction] = {}
        self.widget_link_groups: dict[str, int | None] = {}
        self.link_groups: defaultdict[int, set[str]] = defaultdict(set)
        self.link_group_tickers: dict[int, str] = {}
        self.snapshot_worker: SnapshotWorker | None = None
        self.snapshot_workers: list[SnapshotWorker] = []
        self.widget_factories: Dict[str, Callable[[], QWidget]] = {}
        self.dock_widgets: Dict[str, WorkspaceDock] = {}
        self.dock_by_id: Dict[str, WorkspaceDock] = {}
        self.pending_widget_target_dock: WorkspaceDock | None = None
        self.data_provider = TickerDataProvider()
        self.page_manager = StockPageManager(self)
        self.page_tab_bar = PageTabBar(self.page_manager, self.data_provider, self)

        # Workspace management - save/load layouts
        # Directory will be user-specific once authentication is added
        app_data_dir = Path.home() / ".mira_terminal"
        self.workspace_manager = WorkspaceManager(app_data_dir)

        # Auto-refresh timer for live quotes (every 15 seconds)
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_quotes)
        self.auto_refresh_timer.start(15000)  # 15 seconds

        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        self.setWindowTitle("Mira - Trading Terminal")
        self.resize(1600, 940)
        
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.GroupedDragging |
            QMainWindow.DockOption.AllowTabbedDocks
        )
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)

        # Use a minimal central widget to avoid blocking dock operations
        # Set it to a very small size so docks can occupy most of the space
        central = QWidget()
        central.setObjectName("Workspace")
        central.setMaximumSize(1, 1)  # Minimal size
        central.setVisible(False)  # Hide it entirely - docks will fill the space
        self.setCentralWidget(central)

        # Enable drag-and-drop for tabs onto the main window (empty space drops)
        self.setAcceptDrops(True)

        # Unified header+tabs in menu area
        unified_header = self.create_integrated_header()
        self.setMenuWidget(unified_header)
        self.setup_stow_bar()

        # Connect tab bar signals
        self.page_tab_bar.add_tab_requested.connect(self._on_add_tab_requested)
        self.page_tab_bar.close_tab_requested.connect(self._on_close_tab_requested)
        self.page_tab_bar.tab_changed.connect(self._on_tab_changed)
        self.page_manager.active_page_changed.connect(self._on_active_page_changed)

        self.widget_factories = {
            "Quotes": lambda: QuoteWidget(self.handle_interval_change),
            "Chart": lambda: ChartWidget(self.get_current_theme),
            "Screener": lambda: ScreenerWidget(self.on_ticker_selected),
            "Fundamentals": lambda: FundamentalsWidget(self.data_provider),
            "News": lambda: NewsWidget(self.data_provider),
            "Copilot": lambda: ChatbotWidget(self.get_context),
        }

        self.create_widget_menu()
        self.create_default_layout()

        if DEFAULT_TICKERS:
            self.on_ticker_selected(DEFAULT_TICKERS[0])

    def create_widget_menu(self):
        """Create add-widget menu for re-spawning docks."""
        self.widget_menu = QMenu(self)
        for key in self.widget_factories.keys():
            action = self.widget_menu.addAction(key)
            action.triggered.connect(lambda checked=False, n=key: self.handle_widget_menu_selection(n))
        if self.widget_button:
            self.widget_button.setMenu(self.widget_menu)
            self.widget_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def create_workspace_menu(self):
        """Create workspace management menu with presets, save, and load options."""
        self.workspace_menu = QMenu(self)

        # Section: Load Preset Layouts
        presets_menu = self.workspace_menu.addMenu("Load Preset")
        for preset_name in WorkspaceManager.get_default_presets().keys():
            action = presets_menu.addAction(preset_name)
            action.triggered.connect(lambda checked=False, name=preset_name: self.load_preset_workspace(name))

        self.workspace_menu.addSeparator()

        # Section: Saved Workspaces
        self.saved_workspaces_menu = self.workspace_menu.addMenu("My Workspaces")
        self.refresh_saved_workspaces_menu()

        self.workspace_menu.addSeparator()

        # Save Current Workspace
        save_action = self.workspace_menu.addAction("Save Current Layout...")
        save_action.triggered.connect(self.save_current_workspace)

        # Set menu on button
        if hasattr(self, 'workspace_button'):
            self.workspace_button.setMenu(self.workspace_menu)

    def refresh_saved_workspaces_menu(self):
        """Refresh the list of saved workspaces in the menu."""
        if not hasattr(self, 'saved_workspaces_menu'):
            return

        self.saved_workspaces_menu.clear()

        saved_workspaces = self.workspace_manager.list_workspaces()
        if not saved_workspaces:
            no_workspaces_action = self.saved_workspaces_menu.addAction("(No saved workspaces)")
            no_workspaces_action.setEnabled(False)
        else:
            for workspace_name in saved_workspaces:
                # Skip preset names to avoid confusion
                if workspace_name in WorkspaceManager.get_default_presets().keys():
                    continue

                action = self.saved_workspaces_menu.addAction(workspace_name)
                action.triggered.connect(lambda checked=False, name=workspace_name: self.load_saved_workspace(name))

    def load_preset_workspace(self, preset_name: str):
        """Load a preset workspace layout."""
        # Safely close all existing docks (deferred to avoid crashes during drag operations)
        docks_to_close = list(self.dock_by_id.values())
        self.dock_widgets.clear()
        self.dock_by_id.clear()

        # Close docks after clearing references (prevents accessing deleted objects)
        for dock in docks_to_close:
            dock.blockSignals(True)  # Prevent signals during cleanup
            dock.deleteLater()  # Safe deferred deletion

        # Get and apply the preset layout
        presets = WorkspaceManager.get_default_presets()
        if preset_name in presets:
            layout_func = presets[preset_name]
            layout_func(self)
            self.workspace_manager.current_workspace_name = f"Preset: {preset_name}"

            # Force style refresh for all docks to show tab titles properly
            QTimer.singleShot(0, self._refresh_all_dock_styles)

    def load_saved_workspace(self, workspace_name: str):
        """Load a user-saved workspace."""
        success = self.workspace_manager.load_workspace(workspace_name, self)
        if success:
            # Force style refresh for all docks to show tab titles properly
            QTimer.singleShot(0, self._refresh_all_dock_styles)
        else:
            print(f"Failed to load workspace: {workspace_name}")

    def _refresh_all_dock_styles(self):
        """Force Qt to refresh styling on all dock widgets and their components."""
        for dock in self.dock_by_id.values():
            # Refresh the dock widget itself
            dock.style().unpolish(dock)
            dock.style().polish(dock)

            # Refresh the title bar
            if dock.titleBarWidget():
                dock.titleBarWidget().style().unpolish(dock.titleBarWidget())
                dock.titleBarWidget().style().polish(dock.titleBarWidget())

            # Refresh the tab bar (critical for showing tab titles)
            if hasattr(dock, 'tab_bar'):
                dock.tab_bar.style().unpolish(dock.tab_bar)
                dock.tab_bar.style().polish(dock.tab_bar)
                # Force tab bar to update its size
                dock.tab_bar.updateGeometry()

    def save_current_workspace(self):
        """Prompt user for workspace name and save current layout."""
        from PyQt6.QtWidgets import QInputDialog

        # Get workspace name from user
        name, ok = QInputDialog.getText(
            self,
            "Save Workspace",
            "Enter a name for this workspace layout:",
            text=self.workspace_manager.current_workspace_name or ""
        )

        if ok and name.strip():
            success = self.workspace_manager.save_workspace(name.strip(), self)
            if success:
                print(f"Workspace '{name}' saved successfully")
                self.refresh_saved_workspaces_menu()
            else:
                print(f"Failed to save workspace '{name}'")

    def create_default_layout(self):
        """Create a simple, flexible starting layout"""

        # Screener on the left side.
        screener_dock = self.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)

        # Main content dock on the right, starting with the Chart.
        main_dock = self.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)

        # Add other important widgets as tabs to the main dock.
        if main_dock:
            self.add_widget_tab(main_dock, "Quotes")
            self.add_widget_tab(main_dock, "Fundamentals")
            self.add_widget_tab(main_dock, "News")
            self.add_widget_tab(main_dock, "Copilot")

        # Split the screener and the main content area.
        if screener_dock and main_dock:
            self.splitDockWidget(screener_dock, main_dock, Qt.Orientation.Horizontal)
            # Give more space to the main content
            self.resizeDocks([screener_dock, main_dock], [350, 1250], Qt.Orientation.Horizontal)

    def show_widget_menu_at(self, dock: WorkspaceDock | None, anchor: QWidget | None):
        if not hasattr(self, "widget_menu") or not self.widget_menu:
            return
        self.pending_widget_target_dock = dock
        if anchor:
            pos = anchor.mapToGlobal(anchor.rect().bottomRight())
        else:
            pos = QCursor.pos()
        self.widget_menu.popup(pos)

    def handle_widget_menu_selection(self, key: str):
        target = self.pending_widget_target_dock
        self.pending_widget_target_dock = None
        if target and isinstance(target, WorkspaceDock):
            self.add_widget_tab(target, key)
        else:
            self.ensure_widget(key)

    def merge_dock_tabs(self, source_dock_id: str, tab_key: str, target_dock_id: str):
        """Merge a tab from source dock into target dock via drag-and-drop"""
        source_dock = self.dock_by_id.get(source_dock_id)
        target_dock = self.dock_by_id.get(target_dock_id)

        if not source_dock or not target_dock or source_dock is target_dock:
            return

        # Move the tab from source to target
        widget = source_dock.take_tab(tab_key)
        if not widget:
            return

        # Add to target dock
        target_dock.add_tab(tab_key, widget, tab_key)

        # Update the mapping
        self.dock_widgets[tab_key] = target_dock

        # Close source dock if it's now empty
        if source_dock.is_empty():
            source_dock.close()

        # Refresh link group display
        target_dock.set_link_group_display(self.widget_link_groups.get(tab_key))

    def handle_zone_drop_on_dock(self, source_dock_id: str, tab_key: str, target_dock_id: str, zone: str):
        """Handle tab dropped on a specific zone of a dock - split or merge"""
        try:
            source_dock = self.dock_by_id.get(source_dock_id)
            target_dock = self.dock_by_id.get(target_dock_id)

            # Safety checks
            if not source_dock or not target_dock:
                print(f"Error: Invalid docks - source: {source_dock}, target: {target_dock}")
                return

            if source_dock.isHidden() or target_dock.isHidden():
                print(f"Error: Hidden dock detected")
                return

            # Take the tab from source dock
            widget = source_dock.take_tab(tab_key)
            if not widget:
                print(f"Error: Could not take tab '{tab_key}' from source dock")
                return

            if zone == 'merge':
                # Center area - merge into target dock as a new tab
                target_dock.add_tab(tab_key, widget, tab_key)
                self.dock_widgets[tab_key] = target_dock
            elif zone in ['left', 'right', 'top', 'bottom']:
                # Edge zone - split the target dock and create new dock at that position
                # Create new dock with the tab
                new_dock_id = f"dock_{len(self.dock_by_id)}"
                new_dock = WorkspaceDock(
                    new_dock_id, tab_key, widget, self,
                    link_callback=self.update_widget_link_group,
                    widget_menu_callback=self.show_widget_menu_at
                )
                new_dock.closed.connect(lambda d=new_dock: self.on_dock_closed(d))
                new_dock.collapsed_changed.connect(lambda d, c: self.on_dock_collapsed(d, c))
                new_dock.tab_removed.connect(lambda k, d=new_dock: self.on_dock_tab_removed(d, k))
                new_dock.active_tab_changed.connect(lambda k: self.on_active_tab_changed(k))

                # Determine split orientation based on zone
                if zone in ['left', 'right']:
                    orientation = Qt.Orientation.Horizontal
                else:  # 'top' or 'bottom'
                    orientation = Qt.Orientation.Vertical

                # Add the new dock next to the target
                if zone == 'left' or zone == 'top':
                    # Add new dock before target
                    self.splitDockWidget(target_dock, new_dock, orientation)
                else:  # 'right' or 'bottom'
                    # Add new dock after target
                    self.splitDockWidget(new_dock, target_dock, orientation)

                # Register the new dock
                self.dock_by_id[new_dock_id] = new_dock
                self.dock_widgets[tab_key] = new_dock
                new_dock.set_link_group_display(self.widget_link_groups.get(tab_key))

            # Close source dock if it's now empty
            if source_dock.is_empty():
                source_dock.close()

            # Refresh link group display
            if zone == 'merge':
                target_dock.set_link_group_display(self.widget_link_groups.get(tab_key))

        except Exception as e:
            print(f"Error in handle_zone_drop_on_dock: {e}")
            import traceback
            traceback.print_exc()

    def dragEnterEvent(self, event):
        """Handle drag entering main window for tab drops in empty space"""
        if event.mimeData().hasFormat("application/x-mira-tab"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag moving over main window"""
        if event.mimeData().hasFormat("application/x-mira-tab"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle tab dropped in empty space - create new dock at drop position"""
        mime_data = event.mimeData()
        if not mime_data.hasFormat("application/x-mira-tab"):
            event.ignore()
            return

        try:
            # Parse the dropped tab data
            data = mime_data.data("application/x-mira-tab").data().decode()
            source_dock_id, tab_key = data.split("|", 1)

            source_dock = self.dock_by_id.get(source_dock_id)
            if not source_dock or source_dock.isHidden():
                event.ignore()
                return

            # Safety check: ensure source dock is still valid
            if source_dock.tab_bar.count() == 0:
                event.ignore()
                return

            # Check if this is the last tab in the source dock
            if source_dock.tab_bar.count() == 1:
                # Last tab - move the whole dock instead of creating a new one
                # Determine which dock area the drop position is closest to
                drop_pos = event.position().toPoint()
                area = self._get_dock_area_for_position(drop_pos)

                # If dock is already floating, just move it
                if source_dock.isFloating():
                    source_dock.move(drop_pos)
                else:
                    # Make it float at the drop position
                    source_dock.setFloating(True)
                    # Position it at the drop location
                    global_pos = self.mapToGlobal(drop_pos)
                    source_dock.move(global_pos)
            else:
                # Not the last tab - create a new dock with this tab
                # Take the tab from source dock
                widget = source_dock.take_tab(tab_key)
                if not widget:
                    event.ignore()
                    return

                # Create new dock with the tab
                drop_pos = event.position().toPoint()
                area = self._get_dock_area_for_position(drop_pos)

                # Create the new dock
                new_dock = self.ensure_widget_in_area(tab_key, widget, area)

                if new_dock:
                    # Update tracking
                    self.dock_widgets[tab_key] = new_dock
                    new_dock.set_link_group_display(self.widget_link_groups.get(tab_key))

            event.acceptProposedAction()

        except Exception as e:
            # Catch any errors during drop to prevent crashes
            print(f"Error handling tab drop: {e}")
            event.ignore()

    def _get_dock_area_for_position(self, pos):
        """Determine which dock area a position is closest to"""
        rect = self.rect()
        center_x = rect.width() / 2
        center_y = rect.height() / 2

        # Simple quadrant-based detection
        if pos.x() < center_x / 2:
            return Qt.DockWidgetArea.LeftDockWidgetArea
        elif pos.x() > rect.width() - center_x / 2:
            return Qt.DockWidgetArea.RightDockWidgetArea
        elif pos.y() < center_y / 2:
            return Qt.DockWidgetArea.TopDockWidgetArea
        elif pos.y() > rect.height() - center_y / 2:
            return Qt.DockWidgetArea.BottomDockWidgetArea
        else:
            # Center - default to right
            return Qt.DockWidgetArea.RightDockWidgetArea

    def ensure_widget_in_area(self, key: str, widget: QWidget, area: Qt.DockWidgetArea) -> WorkspaceDock | None:
        """Create a dock with the given widget in the specified area"""
        dock_id = f"dock_{len(self.dock_by_id)}"
        dock = WorkspaceDock(
            dock_id, key, widget, self,
            link_callback=self.update_widget_link_group,
            widget_menu_callback=self.show_widget_menu_at
        )
        dock.closed.connect(lambda d=dock: self.on_dock_closed(d))
        dock.collapsed_changed.connect(lambda d, c: self.on_dock_collapsed(d, c))
        dock.tab_removed.connect(lambda k, d=dock: self.on_dock_tab_removed(d, k))
        dock.active_tab_changed.connect(lambda k: self.on_active_tab_changed(k))

        self.addDockWidget(area, dock)
        self.dock_by_id[dock_id] = dock
        self.dock_widgets[key] = dock

        return dock

    def add_widget_tab(self, target_dock: WorkspaceDock, key: str):
        if not target_dock:
            return
        # Find if widget already exists in another dock
        existing_dock = self.find_dock_for_widget(key)
        widget = None
        if existing_dock:
            if existing_dock is target_dock:
                target_dock.focus_tab(key)
                return
            # Move widget from existing dock to target dock
            widget = existing_dock.take_tab(key)
            if existing_dock.is_empty():
                existing_dock.close()
        else:
            # Create new widget instance
            factory = self.widget_factories.get(key)
            if not factory:
                return
            widget = factory()
            self.register_widget_instance(key, widget)
        target_dock.add_tab(key, widget, key)
        # Update the mapping to point to the new dock
        self.dock_widgets[key] = target_dock
        target_dock.set_link_group_display(self.widget_link_groups.get(key))
        if hasattr(widget, "load_ticker") and self.current_ticker:
            widget.load_ticker(self.current_ticker)
    
    def ensure_widget(self, key: str, area: Qt.DockWidgetArea | None = None):
        """Make sure a widget dock exists and is visible."""
        # Find the dock that actually contains this widget
        dock = self.find_dock_for_widget(key)
        if dock:
            dock.show()
            dock.raise_()
            dock.focus_tab(key)
            return dock
        factory = self.widget_factories.get(key)
        if not factory:
            return None
        widget = factory()
        dock_id = f"Dock_{key}_{len(self.dock_by_id) + 1}"
        dock = WorkspaceDock(
            dock_id,
            key,
            widget,
            self,
            link_callback=self.set_widget_link,
            widget_menu_callback=self.show_widget_menu_at
        )
        dock.closed.connect(self.on_dock_closed)
        dock.collapsed_changed.connect(self.on_dock_collapsed)
        dock.tab_removed.connect(lambda removed_key, d=dock: self.on_dock_tab_removed(d, removed_key))
        dock.active_tab_changed.connect(self.on_dock_active_tab_changed)
        dock.setMinimumSize(QSize(150, 120))
        dock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addDockWidget(area or Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.dock_by_id[dock.dock_id] = dock
        self.dock_widgets[key] = dock
        self.register_widget_instance(key, widget)
        dock.set_link_group_display(self.widget_link_groups.get(key))
        if hasattr(widget, "load_ticker") and self.current_ticker:
            widget.load_ticker(self.current_ticker)
        return dock
    
    def on_dock_closed(self, dock: WorkspaceDock):
        for key in dock.list_tab_keys():
            self._untrack_widget(key)
        self.remove_stowed_tab(dock.dock_id)
        self.dock_by_id.pop(dock.dock_id, None)

    def on_dock_tab_removed(self, dock: WorkspaceDock, key: str):
        self._untrack_widget(key)
    
    def on_dock_active_tab_changed(self, key: str):
        # Update the dock_widgets mapping to reflect the active tab's dock
        dock = self.find_dock_for_widget(key)
        if dock:
            self.dock_widgets[key] = dock
            dock.set_link_group_display(self.widget_link_groups.get(key))

    def register_widget_instance(self, key: str, widget: QWidget):
        if key == "Chart":
            self.chart_widget = widget
        elif key == "Quotes":
            self.quote_widget = widget
        elif key == "Fundamentals":
            self.fundamentals_widget = widget
        elif key == "News":
            self.news_widget = widget
        elif key == "Copilot":
            self.chatbot = widget
        elif key == "Screener":
            self.screener = widget
        self.widget_link_groups.setdefault(key, None)

    def unregister_widget_instance(self, key: str):
        if key == "Chart":
            self.chart_widget = None
        elif key == "Quotes":
            self.quote_widget = None
        elif key == "Fundamentals":
            self.fundamentals_widget = None
        elif key == "News":
            self.news_widget = None
        elif key == "Copilot":
            self.chatbot = None
        elif key == "Screener":
            self.screener = None

    def _untrack_widget(self, key: str):
        # Remove from dock_widgets mapping
        self.dock_widgets.pop(key, None)
        group = self.widget_link_groups.pop(key, None)
        if group and key in self.link_groups[group]:
            self.link_groups[group].remove(key)
        self.unregister_widget_instance(key)
    
    def find_dock_for_widget(self, key: str) -> WorkspaceDock | None:
        """Find which dock currently hosts a widget key."""
        for dock in self.dock_by_id.values():
            if key in dock.tab_widgets:
                return dock
        return None
    
    def get_widget_instance(self, key: str) -> QWidget | None:
        """Get the actual widget instance for a key, regardless of which dock it's in."""
        dock = self.find_dock_for_widget(key)
        if dock:
            return dock.tab_widgets.get(key)
        return None

    def set_widget_link(self, key: str, group: int | None):
        prev = self.widget_link_groups.get(key)
        if prev == group:
            return
        if prev and key in self.link_groups[prev]:
            self.link_groups[prev].remove(key)
        self.widget_link_groups[key] = group
        # Find the actual dock hosting this widget
        dock = self.find_dock_for_widget(key)
        if dock and dock.current_tab_key() == key:
            dock.set_link_group_display(group)
        if group:
            self.link_groups[group].add(key)
            if self.current_ticker:
                ticker = self.current_ticker
            else:
                ticker = self.link_group_tickers.get(group)
            if ticker:
                self.link_group_tickers[group] = ticker
                self.load_widget_ticker(key, ticker, propagate=False)
        else:
            # revert to main ticker feed
            if key in ("Chart", "Fundamentals", "News"):
                self.load_widget_ticker(key, self.current_ticker, propagate=False)

    def on_dock_collapsed(self, dock: WorkspaceDock, collapsed: bool):
        if not dock:
            return
        if collapsed:
            self.add_stowed_tab(dock)
        else:
            self.remove_stowed_tab(dock.dock_id)

    def add_stowed_tab(self, dock: WorkspaceDock):
        dock_id = dock.dock_id
        if dock_id in self.stowed_actions:
            return
        action = self.stow_bar.addAction(dock.windowTitle())
        action.triggered.connect(lambda checked=False, d_id=dock_id: self.restore_stowed(d_id))
        self.stowed_actions[dock_id] = action
        self.stow_bar.show()

    def remove_stowed_tab(self, dock_id: str):
        action = self.stowed_actions.pop(dock_id, None)
        if action:
            self.stow_bar.removeAction(action)
        if not self.stowed_actions and hasattr(self, "stow_bar"):
            self.stow_bar.hide()

    def restore_stowed(self, dock_id: str):
        dock = self.dock_by_id.get(dock_id)
        if not dock:
            return
        if dock.collapsed:
            dock.toggle_collapsed()

        self.remove_stowed_tab(dock_id)

    def load_widget_ticker(self, key: str, ticker: str, propagate: bool = False):
        loaded = False
        if key == "Chart" and self.chart_widget:
            self.chart_widget.load_ticker(ticker)
            loaded = True
        elif key == "Fundamentals" and self.fundamentals_widget:
            self.fundamentals_widget.load_ticker(ticker)
            loaded = True
        elif key == "News" and self.news_widget:
            self.news_widget.load_ticker(ticker)
            loaded = True
        elif key == "Quotes" and self.quote_widget:
            self.quote_widget.show_loading(ticker)
            self.update_brand_accent(ticker)
            self.request_snapshot(ticker)
            loaded = True
        if propagate:
            self.broadcast_link_update(key, ticker)

    def broadcast_link_update(self, source_key: str, ticker: str):
        group = self.widget_link_groups.get(source_key)
        if not group:
            return
        self.link_group_tickers[group] = ticker
        for key in self.link_groups[group]:
            if key == source_key:
                continue
            self.load_widget_ticker(key, ticker, propagate=False)

    def handle_interval_change(self, interval: str):
        """Update chart interval from hero buttons."""
        if not self.current_ticker:
            return
        self.chart_widget.update_chart(self.current_ticker, interval)
        if self.quote_widget:
            self.quote_widget.set_active_interval(interval)

    def refresh_snapshot(self):
        """Manually refresh ticker snapshot data."""
        self.request_snapshot()

    def auto_refresh_quotes(self):
        """Auto-refresh quotes for the current ticker."""
        if self.current_ticker and self.quote_widget:
            self.request_snapshot()

    def request_snapshot(self, ticker: str | None = None):
        """Spawn/refresh background worker for ticker quotes."""
        target = (ticker or self.current_ticker or "").strip()
        if not target:
            return
        symbol = target.upper()
        worker = SnapshotWorker(lambda: self.fetch_ticker_snapshot(symbol))
        worker.result_ready.connect(lambda snapshot, w=worker, expected=symbol: self.on_snapshot_ready(snapshot, w, expected))
        worker.finished.connect(lambda w=worker: self.cleanup_worker(w))
        self.snapshot_worker = worker
        self.snapshot_workers.append(worker)
        worker.start()

    def on_snapshot_ready(self, snapshot: dict, worker: SnapshotWorker | None = None,
                          expected_symbol: str | None = None):
        current_symbol = (self.current_ticker or "").upper()
        if expected_symbol and expected_symbol != current_symbol:
            return
        target_symbol = expected_symbol or current_symbol
        snapshot_symbol = snapshot.get("symbol", "").upper()
        if target_symbol and snapshot_symbol and snapshot_symbol != target_symbol:
            return
        self.update_snapshot_ui(snapshot)
        if worker is self.snapshot_worker:
            self.snapshot_worker = None

    def cleanup_worker(self, worker: SnapshotWorker):
        if worker in self.snapshot_workers:
            self.snapshot_workers.remove(worker)
        worker.deleteLater()

    def fetch_ticker_snapshot(self, ticker: str) -> dict:
        """Lightweight ticker overview used by the hero section."""
        return self.data_provider.fetch_snapshot_payload(ticker)

    def update_snapshot_ui(self, snapshot: dict):
        if self.quote_widget:
            self.quote_widget.update_snapshot(snapshot)

    def update_brand_accent(self, ticker: str):
        if not self.quote_widget:
            return
        ticker = (ticker or "").strip().upper()
        accent = None
        if ticker:
            brand_color = BRAND_COLORS.get(ticker) or ticker_hash_color(ticker)
            if self.current_theme_name == "dark":
                pastel = soften_color(brand_color, 0.85)
                accent = mix_colors("#101013", pastel, 0.55)
            else:
                pastel = soften_color(brand_color, 0.45)
                accent = mix_colors("#ffffff", pastel, 0.25)
        self.quote_widget.apply_brand_color(accent)
    
    def _build_header_button(self, glyph: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("UtilityIconButton")
        btn.setText(glyph)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(False)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setCheckable(False)
        btn.setIcon(QIcon())
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setFixedSize(QSize(36, 36))
        return btn
    
    def create_integrated_header(self):
        """Create unified header+tab component."""
        container = QWidget()
        container.setObjectName("HeaderContainer")

        # Single frame for both header and tabs
        unified = QFrame()
        unified.setObjectName("UnifiedHeader")

        layout = QVBoxLayout(unified)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header content
        header_content = self.create_header_content()
        layout.addWidget(header_content)

        # Tabs integrated at bottom
        layout.addWidget(self.page_tab_bar)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(unified)

        return container

    def create_header_content(self):
        """Create header content without wrapper."""
        widget = QWidget()
        widget.setObjectName("HeaderContent")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Mira")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Adaptive Trading Workspace")
        subtitle.setObjectName("HeaderSubtitle")
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)

        layout.addSpacing(24)

        self.market_clock = MarketClockWidget()
        self.market_clock.setFixedWidth(220)
        layout.addWidget(self.market_clock)

        layout.addStretch()

        controls_container = QWidget()
        controls_container.setObjectName("HeaderControls")
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        # Simple placeholder buttons for now
        for icon in ["↻", "+", "⋮", "⚙"]:
            btn = QToolButton()
            btn.setText(icon)
            btn.setFixedSize(36, 36)
            btn.setObjectName("DockIconButton")
            controls_layout.addWidget(btn)

        layout.addWidget(controls_container)
        return widget

    def create_header(self):
        header = QFrame()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("Mira")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Adaptive Trading Workspace")
        subtitle.setObjectName("HeaderSubtitle")
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)

        layout.addSpacing(24)

        self.market_clock = MarketClockWidget()
        self.market_clock.setFixedWidth(220)
        layout.addWidget(self.market_clock)

        layout.addStretch()
        
        controls_container = QWidget()
        controls_container.setObjectName("HeaderControls")
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        self.refresh_button = self._build_header_button("↻", "Refresh market data")
        self.refresh_button.clicked.connect(self.refresh_snapshot)
        controls_layout.addWidget(self.refresh_button)

        self.widget_button = self._build_header_button("+", "Add widget")
        self.widget_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.widget_button.pressed.connect(lambda: setattr(self, 'pending_widget_target_dock', None))
        controls_layout.addWidget(self.widget_button)

        # Workspace switcher button
        self.workspace_button = self._build_header_button("⊞", "Workspaces")
        self.workspace_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.create_workspace_menu()
        controls_layout.addWidget(self.workspace_button)

        self.theme_button = self._build_header_button("", "Toggle theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        controls_layout.addWidget(self.theme_button)

        controls_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(controls_container)
        return header

    def setup_stow_bar(self):
        self.stow_bar = QToolBar("Stowed")
        self.stow_bar.setObjectName("StowBar")
        self.stow_bar.setMovable(False)
        self.stow_bar.setFloatable(False)
        self.stow_bar.setAllowedAreas(Qt.ToolBarArea.BottomToolBarArea)
        self.stow_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.stow_bar)
        self.stow_bar.hide()

    def get_current_theme(self):
        return THEMES[self.current_theme_name]
    
    def apply_theme(self):
        theme = self.get_current_theme()
        radius = BASE_RADIUS
        spacing = BASE_SPACING
        touch = TOUCH_TARGET
        quote_gradient = theme['surface']
        card_radius = 8

        # Prominent borders for high contrast
        if self.current_theme_name == "dark":
            strong_border = "#404040"  # Visible separator
            subtle_border = "#2a2a2a"  # Gentle division
            accent_color = "#00d4ff"  # Mira cyan
        else:
            strong_border = "#c0c0c0"
            subtle_border = "#e0e0e0"
            accent_color = "#0066ff"

        stylesheet = f"""
        QMainWindow {{
            background-color: {theme['window_bg']};
            color: {theme['text']};
            font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
        }}
        QWidget#Workspace {{
            background-color: {theme['window_bg']};
        }}
        QWidget#MenuContainer {{
            background-color: {theme['window_bg']};
            padding: 0px;
            margin: 0px;
        }}
        QWidget {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
        }}
        QLabel {{
            color: {theme['text']};
            background-color: transparent;
        }}
        QLabel#SectionHint {{
            color: {theme['muted']};
            font-size: 13px;
            font-weight: 500;
        }}
        QFrame#UnifiedHeader {{
            background-color: {theme['surface']};
            border: none;
            border-bottom: 1px solid {strong_border};
        }}
        QWidget#HeaderContent {{
            background-color: transparent;
        }}
        QFrame#Header {{
            background-color: {theme['surface']};
            border: none;
            border-radius: 0px;
            padding: 16px 24px;
            margin: 0px;
        }}
        QLabel#HeaderTitle {{
            color: {theme['text']};
            font-size: 20px;
            font-weight: 700;
        }}
        QLabel#HeaderSubtitle {{
            color: {theme['muted']};
            font-size: 13px;
        }}
        QLabel#QuoteTicker {{
            color: {theme['text']};
            font-size: 28px;
            font-weight: 700;
        }}
        QLabel#QuoteSubtitle {{
            color: {theme['muted']};
            font-size: 14px;
        }}
        QFrame#QuoteCard {{
            background: {quote_gradient};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QFrame#ClockCard {{
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            background-color: {theme['panel_bg']};
        }}
        QLabel#SectionTitle {{
            color: {theme['text']};
            font-size: 16px;
            font-weight: 600;
        }}
        QLabel#ClockTime {{
            font-size: 14px;
            font-weight: 600;
        }}
        QLabel#ClockStatus {{
            font-size: 11px;
            color: {theme['muted']};
        }}
        QComboBox#ClockSelector {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
            border: 1px solid {theme['divider']};
            padding: 4px 8px;
        }}
        QComboBox {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            padding: 4px 8px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QLabel#StatusBadge {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
            border-radius: 0px;
            padding: 6px 14px;
            font-size: 12px;
            letter-spacing: 0.08em;
            border: 1px solid {theme['divider']};
        }}
        QListWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            padding: {spacing - 4}px;
            border-radius: 0px;
        }}
        QListWidget::item {{
            padding: 6px;
            margin-bottom: 2px;
            border-radius: 0;
            background-color: transparent;
            color: {theme['text']};
        }}
        QListWidget::item:selected {{
            background-color: {theme['tab_bg']};
            color: {theme['tab_text']};
            border: 1px solid {theme['tab_text']};
        }}
        QFrame#StatPill {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            border-radius: 0px;
        }}
        QLabel#StatLabel {{
            color: {theme['muted']};
            font-size: 11px;
            letter-spacing: 0.12em;
        }}
        QLabel#StatValue {{
            color: {theme['text']};
            font-size: 20px;
            font-weight: 700;
        }}
        QLabel#StatSubtext {{
            color: {theme['muted']};
            font-size: 12px;
        }}
        QFrame#StatPill[trend="positive"] QLabel#StatValue {{
            color: #4ade80;
        }}
        QFrame#StatPill[trend="negative"] QLabel#StatValue {{
            color: #f43f5e;
        }}
        QDockWidget {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['divider']};
            border-radius: 0px;
        }}
        QWidget#DockTitleBar {{
            background-color: {theme['tab_bg']};
            border-bottom: 1px solid {theme['divider']};
        }}
        QWidget#DockTitleBar[tabbed="true"] {{
            border-bottom: none;
        }}
        QWidget#DockTitleBar[drop_active="true"] {{
            border-bottom: 2px solid {theme['accent']};
        }}
        QLabel#DockTitleLabel {{
            color: {theme['text']};
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
        QTabBar::tab {{
            background: {theme['tab_bg']};
            color: {theme['tab_text']};
            padding: 6px 14px;
            margin-right: 4px;
            border: 1px solid {theme['divider']};
            border-bottom: none;
            border-top-left-radius: {radius}px;
            border-top-right-radius: {radius}px;
        }}
        QTabBar::tab:selected {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
        }}
        QTabBar::tab:!selected {{
            opacity: 0.7;
        }}
        QTabBar::tab:hover {{
            color: {theme['accent']};
        }}
        QTabWidget::pane {{
            border: 1px solid {theme['divider']};
            top: -1px;
        }}
        QDockWidget::title {{
            padding: 0;
            margin: 0;
            color: {theme['tab_text']};
            background-color: {theme['tab_bg']};
        }}
        QFrame#DockBody {{
            border: 1px solid {theme['divider']};
            border-radius: 0px;
            background-color: {theme['panel_bg']};
        }}
        QToolButton#DockButton, QToolButton#DockIconButton {{
            background-color: transparent;
            border: 1px solid {theme['divider']};
            border-radius: 4px;
            color: {theme['text']};
            padding: 0;
        }}
        QToolButton#DockButton:hover, QToolButton#DockIconButton:hover {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
        }}
        QTabBar#DockTabBar {{
            background: transparent;
        }}
        QTabBar#DockTabBar[drop_active="true"] {{
            /* No visual change - title bar line is enough */
        }}
        QTabBar#DockTabBar::tab {{
            background-color: transparent;
            color: {theme['muted']};
            padding: 4px 12px;
            margin-left: 6px;
            border: 1px solid {theme['divider']};
            border-radius: 4px;
        }}
        QTabBar#DockTabBar::tab:selected {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
            border-color: {theme['accent']};
            font-weight: 600;
        }}
        QTabBar#DockTabBar::tab:hover:!selected {{
            background-color: {theme['accent_hover']};
            color: {theme['text']};
            border-color: {theme['divider']};
        }}
        QToolBar#StowBar {{
            background-color: {theme['panel_bg']};
            border-top: 1px solid {theme['divider']};
            spacing: 6px;
        }}
        QToolBar#StowBar QToolButton {{
            background-color: transparent;
            border: 1px dashed {theme['divider']};
            color: {theme['muted']};
            padding: 6px 12px;
            border-radius: {card_radius}px;
        }}
        QToolBar#StowBar QToolButton:hover {{
            background-color: {theme['accent']};
            color: {theme['text']};
        }}
        QLineEdit {{
            background-color: {theme['input_bg']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            padding: 0 {spacing}px;
            border-radius: {radius}px;
            min-height: {touch}px;
        }}
        QLineEdit::placeholder {{
            color: {theme['muted']};
        }}
        QPushButton {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
            border: 1px solid {theme['accent']};
            border-radius: {radius}px;
            padding: 0 {spacing + 4}px;
            font-weight: 600;
            min-height: {touch}px;
        }}
        QPushButton:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QPushButton#SegmentButton {{
            background-color: transparent;
            color: {theme['text']};
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            padding: 6px 12px;
            min-height: auto;
        }}
        QPushButton#SegmentButton:hover {{
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QPushButton#TimeframeButton {{
            background-color: transparent;
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            padding: 6px 16px;
            color: {theme['muted']};
            font-weight: 600;
            min-height: auto;
        }}
        QPushButton#TimeframeButton:checked {{
            background-color: {theme['accent']};
            color: {theme['text']};
            border-color: {theme['accent_hover']};
        }}
        QPushButton#UtilityButton, QToolButton#UtilityButton {{
            background-color: transparent;
            color: {theme['text']};
            border: 1px solid {theme['text']};
            border-radius: 0px;
            padding: 0 {spacing + 6}px;
            font-weight: 600;
        }}
        QPushButton#UtilityButton:hover, QToolButton#UtilityButton:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QToolButton#UtilityIconButton {{
            background-color: transparent;
            border: 2px solid {strong_border};
            border-radius: 8px;
            padding: 0;
            color: {theme['text']};
        }}
        QToolButton#UtilityIconButton:hover {{
            background-color: {theme['surface_alt']};
            color: {theme['text']};
            border-color: {strong_border};
        }}
        QToolButton#UtilityIconButton:pressed {{
            background-color: {theme['accent_hover']};
            border-color: {accent_color};
        }}
        QPushButton#ToggleButton {{
            background-color: transparent;
            border: 1px solid {theme['text']};
            border-radius: 0px;
            padding: 0 {spacing + 6}px;
            color: {theme['text']};
        }}
        QPushButton#ToggleButton:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QTextEdit {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            border-radius: {card_radius}px;
            padding: {spacing}px;
        }}
        QTextEdit#ChatDisplay {{
            background-color: {theme['surface']};
            border-radius: {card_radius}px;
        }}
        QTableWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            gridline-color: {theme['border']};
            border-radius: {card_radius}px;
        }}
        QTableWidget::item {{
            padding: {spacing - 4}px;
            background-color: transparent;
        }}
        QHeaderView::section {{
            background-color: {theme['surface_alt']};
            color: {theme['muted']};
            padding: 6px;
            border: none;
        }}
        QToolBar {{
            background: {theme['surface_alt']};
            border: none;
            padding: {spacing - 6}px {spacing}px;
        }}
        QMainWindow::separator {{
            background: {strong_border};
            width: 2px;
            height: 2px;
        }}
        QMainWindow::separator:hover {{
            background: {accent_color};
            width: 3px;
            height: 3px;
        }}
        """
        self.setStyleSheet(stylesheet)
        if self.theme_button:
            if self.current_theme_name == "dark":
                self.theme_button.setText("☀")
                self.theme_button.setToolTip("Switch to light mode")
            else:
                self.theme_button.setText("☾")
                self.theme_button.setToolTip("Switch to dark mode")
        if self.current_ticker and self.chart_widget:
            self.chart_widget.refresh_theme()
            if self.quote_widget:
                self.quote_widget.set_active_interval(self.chart_widget.current_interval)
        self.page_tab_bar.apply_theme(self.current_theme_name)
    
    def toggle_theme(self):
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self.apply_theme()
    
    def on_ticker_selected(self, ticker: str):
        """Handle ticker selection."""
        self.current_ticker = ticker

        active_page = self.page_manager.active_page
        if active_page:
            active_page.primary_ticker = ticker
            active_page.page_name = ticker
            self.page_tab_bar.update_page_name(active_page.page_id, ticker)

        self.update_brand_accent(ticker)
        self.load_widget_ticker("Quotes", ticker, propagate=True)
        # Ensure critical widgets exist (will show existing or create new)
        if not self.find_dock_for_widget("Chart"):
            self.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)
        if not self.find_dock_for_widget("Quotes"):
            self.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)
        if not self.find_dock_for_widget("Fundamentals"):
            self.ensure_widget("Fundamentals", Qt.DockWidgetArea.BottomDockWidgetArea)
        if not self.find_dock_for_widget("News"):
            self.ensure_widget("News", Qt.DockWidgetArea.BottomDockWidgetArea)
        if self.chart_widget:
            self.chart_widget.load_ticker(ticker)
        if self.fundamentals_widget:
            self.fundamentals_widget.load_ticker(ticker)
        if self.news_widget:
            self.news_widget.load_ticker(ticker)
        self.request_snapshot()
        if self.quote_widget and self.chart_widget:
            self.quote_widget.set_active_interval(self.chart_widget.current_interval)
        self.broadcast_link_update("Screener", ticker)
        if self.refresh_button:
            self.refresh_button.setEnabled(True)
        if self.chatbot:
            self.chatbot.add_bot_message(f"Loaded {ticker}. Ask me about the terminal features or market data!")
    
    def get_context(self) -> dict:
        """Get current context for chatbot - enhanced with more details."""
        return {
            "ticker": self.current_ticker or "N/A",
            "timeframe": getattr(self.chart_widget, 'current_interval', self.chart_widget.default_interval),
            "timestamp": datetime.now().isoformat(),
            "chart_type": "tradingview_widget",
            "view": "main_chart",
            "theme": self.current_theme_name
        }

    # --- Tab Management ---
    def _on_add_tab_requested(self):
        ticker = self.current_ticker or "SPY"
        page = self.page_manager.create_page(name=ticker, ticker=ticker, activate=True)
        self.page_tab_bar.update_page_name(page.page_id, ticker)

    def _on_close_tab_requested(self, page_id: str):
        self.page_manager.remove_page(page_id)

    def _on_tab_changed(self, page_id: str):
        self.page_manager.set_active_page(page_id)

    def _on_active_page_changed(self, page_id: str):
        """Switch to a different page - save current state and restore new page state"""
        if not page_id:
            return

        # Save current page state before switching
        if hasattr(self, '_last_active_page_id') and self._last_active_page_id:
            self._save_page_state(self._last_active_page_id)

        # Get the new page
        page = self.page_manager.get_page_by_id(page_id)
        if not page:
            return

        # Restore the new page's state
        self._restore_page_state(page_id)

        # Update ticker
        self.on_ticker_selected(page.primary_ticker)
        self.page_tab_bar.update_page_name(page.page_id, page.primary_ticker)

        # Remember this as the last active page
        self._last_active_page_id = page_id

    def _save_page_state(self, page_id: str):
        """Save current dock layout and widget visibility to a page"""
        page = self.page_manager.get_page_by_id(page_id)
        if not page:
            return

        # Save QMainWindow state (dock positions, sizes, etc.)
        page.layout_state = self.saveState()

        # Save which widgets are currently visible
        page.visible_widgets = set()
        for widget_key, dock in self.dock_widgets.items():
            if dock and not dock.isHidden():
                page.visible_widgets.add(widget_key)

        # Save dock geometry
        page.dock_geometry = {}
        for dock_id, dock in self.dock_by_id.items():
            if dock:
                page.dock_geometry[dock_id] = dock.saveGeometry()

    def _restore_page_state(self, page_id: str):
        """Restore dock layout and widget visibility from a page"""
        page = self.page_manager.get_page_by_id(page_id)
        if not page:
            return

        # Subtle fade effect for page transitions
        self._animate_page_transition()

        # If this page has a saved layout, restore it
        if False and page.layout_state: # Temporarily disable loading saved state
            self.restoreState(page.layout_state)

            # Restore dock geometries
            for dock_id, geometry in page.dock_geometry.items():
                dock = self.dock_by_id.get(dock_id)
                if dock:
                    dock.restoreGeometry(geometry)
        else:
            # First time viewing this page - create default layout
            # Hide all current docks
            for dock in self.dock_by_id.values():
                dock.hide()

            # Create a clean default layout for this page
            self.create_default_layout()

            # Save this as the initial state
            page.layout_state = self.saveState()
            page.visible_widgets = set(self.dock_widgets.keys())
    def _animate_page_transition(self):
        """Subtle fade animation when switching pages"""
        # Create opacity effect if it doesn't exist
        if not hasattr(self, '_page_opacity_effect'):
            self._page_opacity_effect = QGraphicsOpacityEffect(self)
            self.centralWidget().setGraphicsEffect(self._page_opacity_effect)

        # Quick fade out and in
        if hasattr(self, '_page_anim'):
            self._page_anim.stop()

        self._page_anim = QPropertyAnimation(self._page_opacity_effect, b"opacity")
        self._page_anim.setDuration(150)  # 150ms - very subtle
        self._page_anim.setStartValue(1.0)
        self._page_anim.setKeyValueAt(0.5, 0.85)  # Slight fade
        self._page_anim.setEndValue(1.0)
        self._page_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._page_anim.start()


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    window = TradingTerminal()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

