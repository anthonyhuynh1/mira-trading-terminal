from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QTabBar, QStylePainter, QStyleOptionTab, QStyle
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize
from PyQt6.QtGui import QPainter, QFontMetrics
from typing import Optional

from core.stock_page_manager import StockPageManager, StockPage
from core.data_provider import TickerDataProvider
from core.themes import THEMES


class PageTabBar(QWidget):
    """Tab bar using Qt's native QTabBar for proper rendering."""
    tab_changed = pyqtSignal(str)
    add_tab_requested = pyqtSignal()
    close_tab_requested = pyqtSignal(str)

    def __init__(self, page_manager: StockPageManager, data_provider: TickerDataProvider, parent=None):
        super().__init__(parent)
        self.page_manager = page_manager
        self.data_provider = data_provider
        self.current_theme = "dark"
        self._page_id_map = {}  # Maps tab index to page_id

        self.setObjectName("PageTabBar")
        self.setFixedHeight(44)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # Use Qt's native tab bar
        self.tab_bar = QTabBar(self)
        self.tab_bar.setObjectName("NativeTabBar")
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideRight)

        # Connect signals
        self.tab_bar.currentChanged.connect(self._on_tab_index_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)

        layout.addWidget(self.tab_bar, 1)

        # Add button
        self.add_button = QPushButton("+")
        self.add_button.setObjectName("AddTabButton")
        self.add_button.setFixedSize(32, 32)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.add_tab_requested.emit)
        layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)

        # Connect to page manager
        self.page_manager.page_added.connect(self.add_tab)
        self.page_manager.page_removed.connect(self.remove_tab)
        self.page_manager.active_page_changed.connect(self.update_active_tab)

        self.apply_theme(self.current_theme)
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        """Clears and rebuilds all tabs from the page manager."""
        # Clear existing tabs
        while self.tab_bar.count() > 0:
            self.tab_bar.removeTab(0)
        self._page_id_map.clear()

        for idx, page in enumerate(self.page_manager.pages):
            self.tab_bar.addTab(page.page_name)
            self._page_id_map[idx] = page.page_id

        if self.page_manager.active_page:
            self.update_active_tab(self.page_manager.active_page.page_id)

    def add_tab(self, page: StockPage):
        """Adds a new tab to the bar."""
        idx = self.tab_bar.addTab(page.page_name)
        self._page_id_map[idx] = page.page_id

    def remove_tab(self, page_id: str):
        """Removes a tab from the bar."""
        for idx, pid in self._page_id_map.items():
            if pid == page_id:
                self.tab_bar.removeTab(idx)
                # Rebuild the map
                self._page_id_map = {i: self._page_id_map[i+1 if i >= idx else i]
                                     for i in range(self.tab_bar.count())}
                break

    def update_active_tab(self, active_page_id: str):
        """Sets the active tab."""
        for idx, pid in self._page_id_map.items():
            if pid == active_page_id:
                self.tab_bar.setCurrentIndex(idx)
                break

    def update_page_name(self, page_id: str, new_name: str):
        """Updates the name displayed on a specific tab."""
        for idx, pid in self._page_id_map.items():
            if pid == page_id:
                self.tab_bar.setTabText(idx, new_name)
                break

    def _on_tab_index_changed(self, index: int):
        """Handle tab selection."""
        if index >= 0 and index in self._page_id_map:
            page_id = self._page_id_map[index]
            self.tab_changed.emit(page_id)

    def _on_tab_close_requested(self, index: int):
        """Handle tab close request."""
        if index in self._page_id_map:
            page_id = self._page_id_map[index]
            self.close_tab_requested.emit(page_id)

    def apply_theme(self, theme_name: str):
        """Applies the current theme to the tab bar."""
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        if theme_name == "dark":
            tab_bar_bg = "#0a0a0a"
            tab_bg = "#1e1e1e"
            tab_selected_bg = "#0a0a0a"
            text_color = "#969696"
            text_selected = "#ffffff"
            border_color = "#3c3c3c"
            accent_color = "#007acc"
            hover_bg = "#2d2d30"
        else:
            tab_bar_bg = "#fafafa"
            tab_bg = "#ececec"
            tab_selected_bg = "#ffffff"
            text_color = "#6e6e6e"
            text_selected = "#333333"
            border_color = "#d3d3d3"
            accent_color = "#0078d4"
            hover_bg = "#e1e1e1"

        self.setStyleSheet(f"""
            QWidget#PageTabBar {{
                background-color: {tab_bar_bg};
                border: none;
                border-bottom: 1px solid {border_color};
            }}

            QTabBar#NativeTabBar {{
                background-color: transparent;
                border: none;
            }}

            QTabBar#NativeTabBar::tab {{
                background-color: {tab_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 14px 8px 14px;
                margin-right: 2px;
                min-width: 100px;
                max-width: 180px;
                font-weight: 500;
                font-size: 13px;
            }}

            QTabBar#NativeTabBar::tab:selected {{
                background-color: {tab_selected_bg};
                color: {text_selected};
                border-bottom: 3px solid {accent_color};
                font-weight: 600;
            }}

            QTabBar#NativeTabBar::tab:hover {{
                background-color: {hover_bg};
                color: {text_selected};
            }}

            QTabBar#NativeTabBar::tab:selected:hover {{
                background-color: {tab_selected_bg};
            }}

            QTabBar#NativeTabBar::close-button {{
                image: none;
                subcontrol-position: right;
                width: 16px;
                height: 16px;
                margin: 0px 2px 0px 6px;
                border-radius: 3px;
                background-color: transparent;
            }}

            QTabBar#NativeTabBar::close-button:hover {{
                background-color: rgba(255, 67, 67, 0.2);
            }}

            QPushButton#AddTabButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                color: {text_color};
                border-radius: 6px;
                font-size: 16px;
            }}

            QPushButton#AddTabButton:hover {{
                background-color: {hover_bg};
                border-color: {accent_color};
                color: {text_selected};
            }}
        """)
