"""
WatchlistSidebar - TradingView-style watchlist with collapsible groups.

Features:
- Collapsible watchlist groups (like TradingView)
- Drag-drop reordering of tickers
- Right-click context menu (add/remove, create groups)
- Clicking ticker → sets as Group 1 (main ticker) for page
- Sidebar collapsible to left edge
- Per-page watchlist (each StockPage has own watchlist)
"""

from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QDrag, QCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QMenu, QInputDialog,
    QSizePolicy
)

from core.stock_page import StockPage, WatchlistGroup


class TickerItem(QWidget):
    """
    Single ticker item in the watchlist.
    Clickable, draggable, right-click menu.
    """

    clicked = pyqtSignal(str)  # ticker
    context_menu_requested = pyqtSignal(str, object)  # ticker, QPoint

    def __init__(self, ticker: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ticker = ticker
        self.is_hovered = False

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Ticker label
        self.label = QLabel(ticker)
        self.label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: #e0e0e0;
                background: transparent;
            }
        """)

        layout.addWidget(self.label)
        layout.addStretch()

        # Style
        self.setFixedHeight(32)
        self._update_style()

        # Enable drag
        self.setAcceptDrops(True)

    def _update_style(self):
        """Update styling based on hover state."""
        if self.is_hovered:
            self.setStyleSheet("""
                TickerItem {
                    background: rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                TickerItem {
                    background: transparent;
                    border-radius: 4px;
                }
                TickerItem:hover {
                    background: rgba(255, 255, 255, 0.05);
                }
            """)

    def enterEvent(self, event):
        """Mouse enter - show hover state."""
        self.is_hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse leave - remove hover state."""
        self.is_hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press - click to select ticker."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.ticker)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(self.ticker, event.globalPosition().toPoint())
        super().mousePressEvent(event)


class WatchlistGroupWidget(QWidget):
    """
    Collapsible group of tickers (TradingView-style).
    """

    ticker_clicked = pyqtSignal(str)  # ticker
    ticker_context_menu = pyqtSignal(str, object)  # ticker, QPoint
    group_context_menu = pyqtSignal(str, object)  # group_name, QPoint

    def __init__(self, group: WatchlistGroup, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.group = group
        self.ticker_items: List[TickerItem] = []

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header (collapsible)
        header = QWidget()
        header.setFixedHeight(36)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_context_menu)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)

        # Collapse/expand arrow
        self.arrow_label = QLabel("▼" if not group.is_collapsed else "▶")
        self.arrow_label.setFixedWidth(16)
        self.arrow_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #888888;
            }
        """)

        # Group name
        self.name_label = QLabel(group.name)
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #a0a0a0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """)

        header_layout.addWidget(self.arrow_label)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()

        header.mousePressEvent = lambda e: self.toggle_collapse()

        header.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QWidget:hover {
                background: rgba(255, 255, 255, 0.03);
            }
        """)

        main_layout.addWidget(header)

        # Ticker list container
        self.ticker_container = QWidget()
        self.ticker_layout = QVBoxLayout(self.ticker_container)
        self.ticker_layout.setContentsMargins(0, 0, 0, 0)
        self.ticker_layout.setSpacing(0)

        main_layout.addWidget(self.ticker_container)

        # Initial population
        self._populate_tickers()

        # Apply collapse state
        self.ticker_container.setVisible(not group.is_collapsed)

    def _populate_tickers(self):
        """Populate ticker items from group data."""
        # Clear existing
        for item in self.ticker_items:
            item.deleteLater()
        self.ticker_items.clear()

        # Add tickers
        for ticker in self.group.tickers:
            item = TickerItem(ticker, self.ticker_container)
            item.clicked.connect(self.ticker_clicked.emit)
            item.context_menu_requested.connect(self.ticker_context_menu.emit)
            self.ticker_layout.addWidget(item)
            self.ticker_items.append(item)

    def toggle_collapse(self):
        """Toggle group collapse state."""
        self.group.is_collapsed = not self.group.is_collapsed
        self.ticker_container.setVisible(not self.group.is_collapsed)
        self.arrow_label.setText("▶" if self.group.is_collapsed else "▼")

    def add_ticker(self, ticker: str):
        """Add a ticker to this group."""
        if ticker not in self.group.tickers:
            self.group.tickers.append(ticker)
            self._populate_tickers()

    def remove_ticker(self, ticker: str):
        """Remove a ticker from this group."""
        if ticker in self.group.tickers:
            self.group.tickers.remove(ticker)
            self._populate_tickers()

    def _on_header_context_menu(self, pos: QPoint):
        """Handle right-click on group header."""
        self.group_context_menu.emit(self.group.name, self.mapToGlobal(pos))


class WatchlistSidebar(QWidget):
    """
    TradingView-style watchlist sidebar.

    Features:
    - Collapsible groups
    - Drag-drop reordering
    - Right-click context menus
    - Ticker selection updates page
    """

    ticker_selected = pyqtSignal(str)  # ticker selected as main
    watchlist_updated = pyqtSignal()  # watchlist changed

    def __init__(self, page: StockPage, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.page = page
        self.group_widgets: List[WatchlistGroupWidget] = []
        self.is_collapsed = False

        self._setup_ui()
        self._populate_groups()

        # Connect to page signals
        self.page.watchlist_updated.connect(self._populate_groups)

    def _setup_ui(self):
        """Initialize UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with collapse button
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet("""
            QWidget {
                background: #1e1e1e;
                border-bottom: 1px solid #333333;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        # Title
        title = QLabel("Watchlist")
        title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #ffffff;
            }
        """)

        # Add button
        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setFlat(True)
        add_btn.setToolTip("Add ticker")
        add_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                color: #888888;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        add_btn.clicked.connect(self._add_ticker_dialog)

        # Collapse button
        self.collapse_btn = QPushButton("◀")
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.setFlat(True)
        self.collapse_btn.setToolTip("Collapse sidebar")
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                color: #888888;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        header_layout.addWidget(self.collapse_btn)

        main_layout.addWidget(header)

        # Scroll area for watchlist groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #1a1a1a;
                border: none;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
        """)

        # Container for groups
        self.groups_container = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 8, 0, 8)
        self.groups_layout.setSpacing(12)
        self.groups_layout.addStretch()

        scroll.setWidget(self.groups_container)
        main_layout.addWidget(scroll)

        # Style the sidebar
        self.setStyleSheet("""
            WatchlistSidebar {
                background: #1a1a1a;
                border-right: 1px solid #333333;
            }
        """)
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

    def _populate_groups(self):
        """Populate watchlist groups from page data."""
        # Clear existing
        for widget in self.group_widgets:
            widget.deleteLater()
        self.group_widgets.clear()

        # Add groups
        for group in self.page.watchlist_groups:
            widget = WatchlistGroupWidget(group, self.groups_container)
            widget.ticker_clicked.connect(self._on_ticker_selected)
            widget.ticker_context_menu.connect(self._show_ticker_menu)
            widget.group_context_menu.connect(self._show_group_menu)

            # Insert before stretch
            self.groups_layout.insertWidget(len(self.group_widgets), widget)
            self.group_widgets.append(widget)

    def _on_ticker_selected(self, ticker: str):
        """Handle ticker selection - set as Group 1 (main ticker)."""
        self.page.primary_ticker = ticker
        self.ticker_selected.emit(ticker)

    def _add_ticker_dialog(self):
        """Show dialog to add a ticker."""
        ticker, ok = QInputDialog.getText(
            self,
            "Add Ticker",
            "Enter ticker symbol:",
        )

        if ok and ticker.strip():
            ticker = ticker.strip().upper()
            # Add to first group (Favorites) by default
            if self.page.watchlist_groups:
                self.page.add_to_watchlist(ticker, self.page.watchlist_groups[0].name)

    def _show_ticker_menu(self, ticker: str, pos: QPoint):
        """Show context menu for ticker."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)

        # Set as main ticker
        set_main_action = menu.addAction(f"Set {ticker} as main ticker")
        set_main_action.triggered.connect(lambda: self._on_ticker_selected(ticker))

        menu.addSeparator()

        # Remove from watchlist
        remove_action = menu.addAction("Remove from watchlist")
        remove_action.triggered.connect(lambda: self._remove_ticker(ticker))

        menu.exec(pos)

    def _show_group_menu(self, group_name: str, pos: QPoint):
        """Show context menu for group."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)

        # Rename group
        rename_action = menu.addAction(f"Rename '{group_name}'")
        rename_action.triggered.connect(lambda: self._rename_group(group_name))

        # Delete group
        delete_action = menu.addAction(f"Delete '{group_name}'")
        delete_action.triggered.connect(lambda: self._delete_group(group_name))

        menu.addSeparator()

        # Create new group
        new_group_action = menu.addAction("Create new group")
        new_group_action.triggered.connect(self._create_group_dialog)

        menu.exec(pos)

    def _remove_ticker(self, ticker: str):
        """Remove ticker from watchlist."""
        self.page.remove_from_watchlist(ticker)

    def _rename_group(self, old_name: str):
        """Rename a watchlist group."""
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Group",
            f"Enter new name for '{old_name}':",
            text=old_name
        )

        if ok and new_name.strip():
            # Find and rename group
            for group in self.page.watchlist_groups:
                if group.name == old_name:
                    group.name = new_name.strip()
                    self.page.watchlist_updated.emit()
                    break

    def _delete_group(self, group_name: str):
        """Delete a watchlist group."""
        self.page.remove_watchlist_group(group_name)

    def _create_group_dialog(self):
        """Show dialog to create a new group."""
        name, ok = QInputDialog.getText(
            self,
            "Create Group",
            "Enter name for new watchlist group:",
        )

        if ok and name.strip():
            self.page.create_watchlist_group(name.strip())

    def toggle_collapse(self):
        """Toggle sidebar collapse state."""
        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self.setMaximumWidth(48)
            self.collapse_btn.setText("▶")
            # Hide everything except header
            for widget in self.group_widgets:
                widget.hide()
        else:
            self.setMaximumWidth(300)
            self.collapse_btn.setText("◀")
            # Show groups
            for widget in self.group_widgets:
                widget.show()
