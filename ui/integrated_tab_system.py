"""
Integrated tab system that properly connects tabs to content.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.stock_page_manager import StockPageManager, StockPage
from core.data_provider import TickerDataProvider
from core.themes import THEMES


class IntegratedTabSystem(QWidget):
    """Tab system that contains the entire workspace."""
    tab_changed = pyqtSignal(str)
    add_tab_requested = pyqtSignal()
    close_tab_requested = pyqtSignal(str)

    def __init__(self, page_manager: StockPageManager, data_provider: TickerDataProvider, parent=None):
        super().__init__(parent)
        self.page_manager = page_manager
        self.data_provider = data_provider
        self.current_theme = "dark"
        self.workspace_widgets = {}  # Store workspace per tab

        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar at the top
        self.tab_bar = CustomTabBar(self)
        self.tab_bar.setObjectName("MainTabBar")
        layout.addWidget(self.tab_bar)

        # Content area directly below tabs
        self.content_stack = QWidget()
        self.content_stack.setObjectName("TabContent")
        self.content_layout = QVBoxLayout(self.content_stack)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_stack, 1)

        self.apply_theme(self.current_theme)

    def apply_theme(self, theme_name: str):
        """Apply cohesive theme."""
        theme = THEMES[theme_name]

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme['window_bg']};
            }}

            CustomTabBar {{
                background-color: {theme['surface']};
                border-bottom: 1px solid {theme['divider']};
                min-height: 40px;
                max-height: 40px;
            }}

            QWidget#TabContent {{
                background-color: {theme['window_bg']};
                border: none;
            }}
        """)


class CustomTabBar(QWidget):
    """Custom tab bar that sits flush with content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        # Tab container
        self.tab_container = QWidget()
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(1)  # 1px gap between tabs

        layout.addWidget(self.tab_container)
        layout.addStretch()

        # Add button
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(32, 40)
        layout.addWidget(self.add_btn)

    def add_tab(self, text: str):
        """Add a tab that connects to content below."""
        tab = TabButton(text)
        self.tab_container.layout().addWidget(tab)
        return tab


class TabButton(QPushButton):
    """Individual tab that visually connects to content."""

    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName("TabButton")
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setMinimumWidth(100)

        font = QFont()
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 105)
        self.setFont(font)

        self.setCursor(Qt.CursorShape.PointingHandCursor)