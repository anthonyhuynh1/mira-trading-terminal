from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QMouseEvent, QFont
from typing import Optional

from core.stock_page_manager import StockPageManager, StockPage
from core.data_provider import TickerDataProvider
from core.themes import THEMES


class PageTabBar(QWidget):
    """Sophisticated tab bar matching the Mira design language."""
    tab_changed = pyqtSignal(str)
    add_tab_requested = pyqtSignal()
    close_tab_requested = pyqtSignal(str)

    def __init__(self, page_manager: StockPageManager, data_provider: TickerDataProvider, parent=None):
        super().__init__(parent)
        self.page_manager = page_manager
        self.data_provider = data_provider
        self.current_theme = "dark"
        self._tabs = {}

        self.setObjectName("PageTabBar")
        self.setFixedHeight(40)  # Reduced height to be more compact

        # Main layout with no margins
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Tab container
        self.tab_container = QWidget()
        self.tab_container.setObjectName("TabContainer")
        self.tab_layout = QHBoxLayout(self.tab_container)
        self.tab_layout.setContentsMargins(12, 0, 0, 0)  # Left padding only
        self.tab_layout.setSpacing(0)

        self.main_layout.addWidget(self.tab_container, 1)

        # Add button - minimal and elegant
        self.add_button = QPushButton("+")
        self.add_button.setObjectName("AddTabButton")
        self.add_button.setFixedSize(40, 40)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.add_tab_requested.emit)
        self.main_layout.addWidget(self.add_button)

        # Connect signals
        self.page_manager.page_added.connect(self.add_tab)
        self.page_manager.page_removed.connect(self.remove_tab)
        self.page_manager.active_page_changed.connect(self.update_active_tab)

        self.apply_theme(self.current_theme)
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        """Clears and rebuilds all tabs."""
        while self.tab_layout.count():
            child = self.tab_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._tabs.clear()

        for page in self.page_manager.pages:
            self.add_tab(page)

        if self.page_manager.active_page:
            self.update_active_tab(self.page_manager.active_page.page_id)

    def add_tab(self, page: StockPage):
        """Adds a new tab."""
        tab = TabWidget(page, self)
        tab.clicked.connect(lambda p=page.page_id: self.tab_changed.emit(p))
        tab.close_requested.connect(lambda p=page.page_id: self.close_tab_requested.emit(p))
        self.tab_layout.addWidget(tab)
        self._tabs[page.page_id] = tab

    def remove_tab(self, page_id: str):
        """Removes a tab."""
        tab = self._tabs.pop(page_id, None)
        if tab:
            tab.deleteLater()

    def update_active_tab(self, active_page_id: str):
        """Sets the active tab."""
        for page_id, tab in self._tabs.items():
            tab.set_active(page_id == active_page_id)

    def update_page_name(self, page_id: str, new_name: str):
        """Updates tab name."""
        tab = self._tabs.get(page_id)
        if tab:
            tab.update_name(new_name)

    def apply_theme(self, theme_name: str):
        """Applies theme matching the Mira design language."""
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        # Use theme colors directly for consistency
        bg = theme['window_bg']  # #0a0a0a
        divider = theme['divider']  # #2a2a2a
        muted = theme['muted']  # #9ca3af
        text = theme['text']  # #ffffff
        accent_hover = theme['accent_hover']  # #1f1f1f

        self.setStyleSheet(f"""
            QWidget#PageTabBar {{
                background-color: transparent;
                border: none;
            }}
            QWidget#TabContainer {{
                background-color: transparent;
            }}
            QPushButton#AddTabButton {{
                background-color: transparent;
                border: none;
                border-left: 1px solid {divider};
                color: {muted};
                font-size: 18px;
                font-weight: 300;
            }}
            QPushButton#AddTabButton:hover {{
                background-color: {accent_hover};
                color: {text};
            }}
        """)

        for tab in self._tabs.values():
            tab.apply_theme(theme_name)


class TabWidget(QWidget):
    """Individual tab matching Mira's sophisticated aesthetic."""
    clicked = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, page: StockPage, parent=None):
        super().__init__(parent)
        self.page = page
        self.is_active = False
        self.current_theme = "dark"

        self.setObjectName("TabWidget")
        self.setFixedHeight(40)  # Match tab bar height
        self.setMinimumWidth(120)
        self.setMaximumWidth(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout with generous padding
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(12)

        # Label with sophisticated typography
        self.label = QLabel(page.page_name.upper())  # Uppercase for elegance
        self.label.setObjectName("TabLabel")
        font = QFont()
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 105)  # Subtle letter spacing
        self.label.setFont(font)
        layout.addWidget(self.label, 1)

        # Close button - minimal design
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(14, 14)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close_requested.emit)

        # Start with close button hidden
        self.close_btn.setVisible(False)
        layout.addWidget(self.close_btn)

    def enterEvent(self, event):
        """Show close button on hover."""
        self.close_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide close button when not hovering (unless active)."""
        if not self.is_active:
            self.close_btn.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def set_active(self, active: bool):
        self.is_active = active
        self.setProperty("active", active)
        # Keep close button visible on active tab
        self.close_btn.setVisible(active)
        self.style().unpolish(self)
        self.style().polish(self)

    def update_name(self, new_name: str):
        self.page.page_name = new_name
        self.label.setText(new_name.upper())

    def apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        # Direct theme colors for perfect consistency
        bg = theme['window_bg']  # #0a0a0a
        surface_alt = theme['surface_alt']  # #141414
        divider = theme['divider']  # #2a2a2a
        muted = theme['muted']  # #9ca3af
        text = theme['text']  # #ffffff
        accent_hover = theme['accent_hover']  # #1f1f1f

        self.setStyleSheet(f"""
            QWidget#TabWidget {{
                background-color: transparent;
                border: none;
                border-right: 1px solid {divider};
            }}
            QWidget#TabWidget:hover {{
                background-color: {surface_alt};
            }}
            QWidget#TabWidget[active=true] {{
                background-color: {surface_alt};
                border-bottom: 2px solid {text};
                border-right: 1px solid {divider};
            }}

            QLabel#TabLabel {{
                color: {muted};
                font-size: 11px;
                font-weight: 500;
                background: transparent;
                letter-spacing: 0.12em;
            }}
            QWidget#TabWidget:hover QLabel#TabLabel {{
                color: {text};
            }}
            QWidget#TabWidget[active=true] QLabel#TabLabel {{
                color: {text};
                font-weight: 600;
            }}

            QPushButton#CloseButton {{
                background-color: transparent;
                border: none;
                color: {muted};
                font-size: 14px;
                font-weight: 300;
                padding: 0px;
                opacity: 0.6;
            }}
            QPushButton#CloseButton:hover {{
                color: {text};
                opacity: 1.0;
            }}
        """)