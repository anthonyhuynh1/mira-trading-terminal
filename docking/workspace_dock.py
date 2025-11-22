"""
Custom dock widget with inline tabs and elegant drag-and-drop support.
Provides the core docking functionality for the trading terminal.
"""

from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QMimeData, QSize
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout,
    QLabel, QToolButton, QFrame, QStackedWidget, QMenu,
    QSizePolicy, QStyle, QApplication
)

from .drop_overlay import DropZoneOverlay
from .draggable_tab_bar import DraggableTabBar
from .ticker_sync_header import TickerSyncHeader
from core.themes import BASE_SPACING


class WorkspaceDock(QDockWidget):
    """Dock widget with Mira header, inline tabs, and stacked content."""

    closed = pyqtSignal(object)
    collapsed_changed = pyqtSignal(object, bool)
    tab_removed = pyqtSignal(str)
    tab_added = pyqtSignal(str)
    active_tab_changed = pyqtSignal(str)

    def __init__(self, dock_id: str, initial_key: str, widget: QWidget, parent: QMainWindow,
                 link_callback: Callable[[str, int | None], None] | None = None,
                 widget_menu_callback: Callable[[object, QWidget | None], None] | None = None):
        super().__init__(initial_key, parent)
        self.dock_id = dock_id
        self.initial_widget_key = initial_key  # Store for use in title bar setup
        self.setObjectName(dock_id)
        self.setContentsMargins(0, 0, 0, 0)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |  # Qt's simple title bar dragging
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.collapsed = False
        self._collapsed_height = 48
        self.link_callback = link_callback
        self.widget_menu_callback = widget_menu_callback
        self._link_group: int | None = None
        self._options_menu: QMenu | None = None
        self.tab_widgets: dict[str, QWidget] = {}
        self.tab_order: list[str] = []

        # Initialize drag-and-drop state variables
        self._drop_overlay: DropZoneOverlay | None = None
        self._drop_highlight_active: bool = False
        self._dragging_tab_index: int = -1

        self._init_title_bar()
        self._init_body()
        self.add_tab(initial_key, widget, initial_key)

    def _init_title_bar(self):
        title_bar = QWidget()
        title_bar.setObjectName("DockTitleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        self.title_label = QLabel("")
        self.title_label.setObjectName("DockTitleLabel")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title_label)

        # Add ticker sync header (shows ticker with chain/pin icon)
        self.ticker_sync_header = TickerSyncHeader(self.initial_widget_key)
        self.ticker_sync_header.ticker_changed.connect(self._on_ticker_changed_from_header)
        self.ticker_sync_header.sync_toggled.connect(self._on_sync_toggled_from_header)
        layout.addWidget(self.ticker_sync_header)

        self.tab_bar = DraggableTabBar()
        self.tab_bar.setObjectName("DockTabBar")
        self.tab_bar.setExpanding(False)  # Don't expand - keep natural size for tabs
        self.tab_bar.setMovable(False)  # Disable Qt's built-in tab moving - we handle it
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabMoved.connect(self._on_tab_moved)
        self.tab_bar.tabBarDoubleClicked.connect(self._on_tab_double_clicked)
        # Removed custom drag handling - using Qt's built-in system

        layout.addWidget(self.tab_bar, stretch=1)

        self.menu_btn = self._create_options_button()
        layout.addWidget(self.menu_btn)

        self.min_btn = self._create_icon_button("icons/minimize.svg", self.toggle_collapsed, "Minimize")
        self.expand_btn = self._create_icon_button("icons/expand.svg", self.expand_to_fill, "Expand to fit space")
        self.float_btn = self._create_icon_button("icons/float.svg", self._toggle_floating, "Float / Dock")
        self.close_btn = self._create_icon_button("icons/close.svg", self._handle_close_clicked, "Close")

        for btn in (self.min_btn, self.expand_btn, self.float_btn, self.close_btn):
            layout.addWidget(btn)

        self.setTitleBarWidget(title_bar)
        # Removed event filter - Qt handles all dragging now
        title_bar.installEventFilter(self)  # Keep for context menu only
        self._rebuild_options_menu()

    def _init_body(self):
        body = QFrame()
        body.setObjectName("DockBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.setWidget(body)

    def _create_button(self, text: str, handler: Callable, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(handler)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(26, 22))
        btn.setObjectName("DockButton")
        return btn

    def _create_icon_button(self, icon_name: str, handler: Callable, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setToolTip(tooltip)
        btn.clicked.connect(handler)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(24, 24))
        btn.setObjectName("DockIconButton")
        btn.setIconSize(QSize(12, 12))
        btn.setProperty("icon_name", icon_name)
        icon_map = {
            "icons/minimize.svg": QStyle.StandardPixmap.SP_TitleBarMinButton,
            "icons/expand.svg": QStyle.StandardPixmap.SP_TitleBarMaxButton,
            "icons/float.svg": QStyle.StandardPixmap.SP_TitleBarNormalButton,
            "icons/close.svg": QStyle.StandardPixmap.SP_TitleBarCloseButton,
        }
        btn.setIcon(self.style().standardIcon(icon_map.get(icon_name, QStyle.StandardPixmap.SP_TitleBarMenuButton)))
        btn.setText("")
        return btn

    def _create_options_button(self) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("DockIconButton")
        btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
        btn.setToolTip("Widget options")
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(24, 24))
        return btn

    def _rebuild_options_menu(self):
        if self._options_menu:
            self._options_menu.deleteLater()
        menu = QMenu(self)

        # Webull-style menu structure
        current_tab = self.current_tab_key() or "Widget"

        # Add Widget submenu
        add_action = menu.addAction("Add a Widget")
        add_action.triggered.connect(self._handle_add_widget)

        # Copy Widget
        copy_action = menu.addAction(f"Copy {current_tab}")
        copy_action.triggered.connect(self._handle_copy_widget)
        copy_action.setEnabled(False)  # TODO: implement copy functionality

        menu.addSeparator()

        # Minimize
        minimize_action = menu.addAction("Minimize")
        minimize_action.triggered.connect(self.toggle_collapsed)

        # Maximize
        maximize_action = menu.addAction("Maximize")
        maximize_action.triggered.connect(self.expand_to_fill)

        # Detach/Float
        if self.isFloating():
            detach_action = menu.addAction("Dock")
        else:
            detach_action = menu.addAction("Detach")
        detach_action.triggered.connect(self._toggle_floating)

        menu.addSeparator()

        # Link Group submenu
        link_menu = menu.addMenu("Link Group")
        none_action = link_menu.addAction("No Link")
        none_action.setCheckable(True)
        none_action.setChecked(self._link_group is None)
        none_action.triggered.connect(lambda: self._set_link_group(None))
        for group in range(1, 7):
            action = link_menu.addAction(f"Group {group}")
            action.setCheckable(True)
            action.setChecked(self._link_group == group)
            action.triggered.connect(lambda checked=False, g=group: self._set_link_group(g))

        menu.addSeparator()

        # Remove Widget
        remove_action = menu.addAction(f"Remove {current_tab}")
        remove_action.triggered.connect(self._handle_close_clicked)

        self.menu_btn.setMenu(menu)
        self._options_menu = menu

    def _handle_copy_widget(self):
        """Copy current widget to a new dock (TODO: implement)"""
        pass

    def _handle_add_widget(self):
        if self.widget_menu_callback:
            anchor = self.titleBarWidget() or self
            self.widget_menu_callback(self, anchor)

    def _set_link_group(self, group: int | None):
        current_key = self.current_tab_key()
        if current_key and self.link_callback:
            self.link_callback(current_key, group)
        self._link_group = group
        self._rebuild_options_menu()
        # Update ticker sync header
        if hasattr(self, 'ticker_sync_header'):
            self.ticker_sync_header.set_link_group(group)

    def _on_ticker_changed_from_header(self, ticker: str):
        """Handle ticker change from ticker sync header."""
        # Get the current tab's widget and update it
        current_key = self.current_tab_key()
        if current_key:
            widget = self.tab_widgets.get(current_key)
            if widget and hasattr(widget, 'load_ticker'):
                widget.load_ticker(ticker)

    def _on_sync_toggled_from_header(self, group: int | None):
        """Handle sync toggle from ticker sync header."""
        self._set_link_group(group)

    def add_tab(self, key: str, widget: QWidget, title: str):
        if key in self.tab_widgets:
            self.focus_tab(key)
            return
        widget.setParent(self.stack)
        self.stack.addWidget(widget)
        tab_index = self.tab_bar.addTab(title)
        self.tab_bar.setTabData(tab_index, key)
        self.tab_widgets[key] = widget
        self.tab_order.insert(tab_index, key)
        self.tab_bar.setCurrentIndex(tab_index)
        self.tab_added.emit(key)
        self._update_title_label()

    def take_tab(self, key: str) -> QWidget | None:
        idx = self._index_for_key(key)
        if idx is None:
            return None
        return self._remove_tab_at(idx, delete=False, emit_signal=False)

    def focus_tab(self, key: str):
        idx = self._index_for_key(key)
        if idx is None:
            return
        self.tab_bar.setCurrentIndex(idx)

    def current_tab_key(self) -> str | None:
        idx = self.tab_bar.currentIndex()
        if idx < 0 or idx >= len(self.tab_order):
            return None
        return self.tab_order[idx]

    def list_tab_keys(self) -> list[str]:
        return list(self.tab_order)

    def is_empty(self) -> bool:
        return not self.tab_order

    def _index_for_key(self, key: str) -> int | None:
        try:
            return self.tab_order.index(key)
        except ValueError:
            return None

    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        self._update_title_label()
        key = self.current_tab_key()
        if key:
            self.active_tab_changed.emit(key)

    def _on_tab_moved(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        key = self.tab_order.pop(from_index)
        self.tab_order.insert(to_index, key)
        widget = self.stack.widget(from_index)
        self.stack.removeWidget(widget)
        self.stack.insertWidget(to_index, widget)

    def _on_tab_double_clicked(self, index: int):
        """Handle double-click on a tab to float/dock the widget"""
        if index >= 0:  # Valid tab clicked
            self._toggle_floating()

    def _on_drag_started(self, tab_index: int, pos):
        """Handle drag started from custom tab bar"""
        self._dragging_tab_index = tab_index
        self._start_tab_drag()

    def _remove_tab_at(self, index: int, delete: bool = True, emit_signal: bool = True) -> QWidget | None:
        if index < 0 or index >= len(self.tab_order):
            return None
        key = self.tab_order.pop(index)
        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        self.tab_bar.blockSignals(True)
        self.tab_bar.removeTab(index)
        self.tab_bar.blockSignals(False)
        self.tab_widgets.pop(key, None)
        if emit_signal:
            self.tab_removed.emit(key)
        if delete:
            widget.deleteLater()
        else:
            widget.setParent(None)
        if self.tab_bar.count():
            next_index = min(index, self.tab_bar.count() - 1)
            self.tab_bar.setCurrentIndex(next_index)
        else:
            QTimer.singleShot(0, self.close)
        self._update_title_label()
        return widget

    def _handle_close_clicked(self):
        idx = self.tab_bar.currentIndex()
        self._remove_tab_at(idx, delete=True, emit_signal=True)

    def toggle_collapsed(self):
        self.set_collapsed(not self.collapsed)

    def set_collapsed(self, collapsed: bool):
        if self.collapsed == collapsed:
            return
        self.collapsed = collapsed
        if self.widget():
            self.widget().setVisible(not self.collapsed)
        self.setVisible(not self.collapsed)
        if not self.collapsed:
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(0)
        self.collapsed_changed.emit(self, self.collapsed)

    def _toggle_floating(self):
        self.setFloating(not self.isFloating())

    def expand_to_fill(self):
        mw = self.parent()
        while mw and not isinstance(mw, QMainWindow):
            mw = mw.parent()
        if not mw:
            return
        mw.resizeDocks([self], [mw.width()], Qt.Orientation.Horizontal)
        mw.resizeDocks([self], [mw.height()], Qt.Orientation.Vertical)

    def closeEvent(self, event):
        # Always allow close - emit signal so parent can clean up
        self.closed.emit(self)
        super().closeEvent(event)

    def resizeEvent(self, event):
        """Handle resize - update overlay geometry"""
        super().resizeEvent(event)
        if self._drop_overlay and self.widget():
            # Update overlay to match body size (not whole dock)
            self._drop_overlay.setGeometry(self.widget().rect())

    def dragEnterEvent(self, event):
        """Handle drag entering the dock - show elegant drop zone overlay"""
        if not event.mimeData().hasFormat("application/x-mira-tab"):
            event.ignore()
            return

        pos = event.position().toPoint()

        # Check if the drag is over the title bar or tab bar
        if self._is_over_title_area(pos):
            # Over title/tab area - accept for merging (simple highlight, no overlay)
            event.acceptProposedAction()
            self._set_drop_highlight(True)
        else:
            # Over body/content area - show elegant drop zone overlay
            self._show_drop_overlay()
            event.acceptProposedAction()  # Accept to show overlay

    def dragMoveEvent(self, event):
        """Handle drag moving over the dock - update overlay position"""
        if not event.mimeData().hasFormat("application/x-mira-tab"):
            event.ignore()
            return

        pos = event.position().toPoint()

        if self._is_over_title_area(pos):
            # Over title area - hide overlay, show simple highlight
            self._hide_drop_overlay()
            self._set_drop_highlight(True)
            event.acceptProposedAction()
        else:
            # Over body - update overlay with cursor position
            self._set_drop_highlight(False)
            if self._drop_overlay and self.widget():
                # Convert position to overlay coordinates (overlay is parented to widget)
                widget_pos = self.widget().mapFrom(self, pos)
                self._drop_overlay.update_cursor_position(widget_pos)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Handle drag leaving the dock - hide overlay"""
        self._set_drop_highlight(False)
        self._hide_drop_overlay()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """Handle drop on the dock - merge or split based on zone"""
        if not event.mimeData().hasFormat("application/x-mira-tab"):
            event.ignore()
            return

        pos = event.position().toPoint()

        if self._is_over_title_area(pos):
            # Drop on title/tab area - merge tabs (existing behavior)
            self._set_drop_highlight(False)
            self._hide_drop_overlay()
            self._handle_tab_drop(event)
            event.acceptProposedAction()
        else:
            # Drop on body - handle split based on overlay zone
            zone = self._drop_overlay.current_zone if self._drop_overlay else None
            self._hide_drop_overlay()

            if zone:
                # Forward to main window with zone information for smart splitting
                self._handle_zone_drop(event, zone)
                event.acceptProposedAction()
            else:
                event.ignore()

    def _show_drop_overlay(self):
        """Create and show the elegant drop zone overlay"""
        if not self._drop_overlay:
            # Create overlay lazily - parent it to the dock's content widget, not the dock itself
            self._drop_overlay = DropZoneOverlay(self.widget())  # Widget = body, not whole dock

        # Position overlay to cover only the body (not title bar)
        if self.widget():
            self._drop_overlay.setGeometry(self.widget().rect())
            self._drop_overlay.show()
            self._drop_overlay.raise_()  # Ensure it's on top

    def _hide_drop_overlay(self):
        """Hide the drop zone overlay"""
        if self._drop_overlay:
            self._drop_overlay.hide()
            self._drop_overlay.current_zone = None

    def _handle_zone_drop(self, event, zone):
        """Handle drop in a specific zone - split or merge based on zone"""
        mime_data = event.mimeData()

        if not mime_data.hasFormat("application/x-mira-tab"):
            event.ignore()
            return

        # Parse the dropped tab data
        data = mime_data.data("application/x-mira-tab").data().decode()
        source_dock_id, tab_key = data.split("|", 1)

        # Find the main window
        main_window = self.window()
        if not hasattr(main_window, "handle_zone_drop_on_dock"):
            event.ignore()
            return

        # Let main window handle the zone-based split/merge
        main_window.handle_zone_drop_on_dock(source_dock_id, tab_key, self.dock_id, zone)
        event.acceptProposedAction()

    def _is_over_title_area(self, pos):
        """Check if position is over the title bar or tab bar area"""
        title_bar = self.titleBarWidget()
        if not title_bar:
            return False

        # Convert position to title bar coordinates
        title_pos = title_bar.mapFrom(self, pos)
        return title_bar.rect().contains(title_pos)

    def eventFilter(self, obj, event):
        if obj is self.titleBarWidget():
            # Right-click to show context menu
            if event.type() == QEvent.Type.ContextMenu:
                self._show_context_menu(event.globalPos())
                return True
            # Accept drag-and-drop on title bar (for tab merging)
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasFormat("application/x-mira-tab"):
                    event.acceptProposedAction()
                    self._set_drop_highlight(True)
                    return True
            elif event.type() == QEvent.Type.DragLeave:
                self._set_drop_highlight(False)
                return True
            elif event.type() == QEvent.Type.DragMove:
                if event.mimeData().hasFormat("application/x-mira-tab"):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasFormat("application/x-mira-tab"):
                    self._set_drop_highlight(False)
                    self._handle_tab_drop(event)
                    return True
            # Don't intercept other mouse events - let Qt handle dock dragging
            return False

        # Handle tab bar events
        if obj is self.tab_bar:
            # Drag detection is now handled by custom DraggableTabBar
            # Only handle drop events here
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasFormat("application/x-mira-tab"):
                    event.acceptProposedAction()
                    self._set_drop_highlight(True)
                    return True
            elif event.type() == QEvent.Type.DragLeave:
                self._set_drop_highlight(False)
                return True
            elif event.type() == QEvent.Type.DragMove:
                if event.mimeData().hasFormat("application/x-mira-tab"):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasFormat("application/x-mira-tab"):
                    self._set_drop_highlight(False)
                    self._handle_tab_drop(event)
                    return True

        return super().eventFilter(obj, event)

    def _show_context_menu(self, global_pos):
        """Show Webull-style context menu on right-click"""
        if self._options_menu:
            self._rebuild_options_menu()  # Refresh menu state
            self._options_menu.exec(global_pos)

    def _set_drop_highlight(self, active: bool):
        """Toggle visual highlight for valid drop zones"""
        if self._drop_highlight_active == active:
            return

        self._drop_highlight_active = active
        title_bar = self.titleBarWidget()

        if title_bar:
            title_bar.setProperty("drop_active", active)
            title_bar.style().unpolish(title_bar)
            title_bar.style().polish(title_bar)

        if hasattr(self, "tab_bar"):
            self.tab_bar.setProperty("drop_active", active)
            self.tab_bar.style().unpolish(self.tab_bar)
            self.tab_bar.style().polish(self.tab_bar)

    def _start_tab_drag(self):
        """Start dragging a tab to another dock"""
        if self._dragging_tab_index < 0 or self._dragging_tab_index >= len(self.tab_order):
            return

        drag = QDrag(self.tab_bar)
        mime_data = QMimeData()

        # Store the source dock ID and tab key
        tab_key = self.tab_order[self._dragging_tab_index]
        data = f"{self.dock_id}|{tab_key}"
        mime_data.setData("application/x-mira-tab", data.encode())
        mime_data.setText(tab_key)

        drag.setMimeData(mime_data)

        # Change cursor during drag
        QApplication.setOverrideCursor(Qt.CursorShape.DragMoveCursor)

        # Start the drag operation
        result = drag.exec(Qt.DropAction.MoveAction)

        # Restore cursor
        QApplication.restoreOverrideCursor()

        # Reset drag state
        self._dragging_tab_index = -1

    def _handle_tab_drop(self, event):
        """Handle a tab being dropped onto this dock (merge as new tab)"""
        mime_data = event.mimeData()

        if not mime_data.hasFormat("application/x-mira-tab"):
            return

        data = mime_data.data("application/x-mira-tab").data().decode()
        source_dock_id, tab_key = data.split("|", 1)

        # Don't merge with self
        if source_dock_id == self.dock_id:
            return

        # Find the main window and merge the tab
        main_window = self.window()
        if hasattr(main_window, "merge_dock_tabs"):
            main_window.merge_dock_tabs(source_dock_id, tab_key, self.dock_id)
            event.acceptProposedAction()

    def set_link_group_display(self, group: int | None):
        self._link_group = group
        self._update_title_label()
        self._rebuild_options_menu()
        # Update ticker sync header
        if hasattr(self, 'ticker_sync_header'):
            self.ticker_sync_header.set_link_group(group)

    def _update_title_label(self):
        if not hasattr(self, "title_label"):
            return
        # Check if widget is still valid (not deleted)
        try:
            if self.title_label:
                # Always hide title label - tabs show the widget names
                self.title_label.setVisible(False)
        except RuntimeError:
            # Widget was deleted, ignore
            return
        # Update window title for Qt's dock system
        text = self.current_tab_key() or ""
        if self._link_group:
            text = f"{text} · #{self._link_group}"
        display = text.upper()
        super().setWindowTitle(display)
