from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QMouseEvent
from typing import Optional

from core.stock_page_manager import StockPageManager, StockPage
from core.data_provider import TickerDataProvider, SnapshotWorker
from core.themes import THEMES, BASE_RADIUS

class PageTabBar(QWidget):
    """The main bar that holds all the page tabs."""
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
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(24, 8, 24, 0)
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)

        self.tab_container = QWidget()
        self.tab_container.setObjectName("TabContainer")
        self.tab_container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.tab_layout = QHBoxLayout(self.tab_container)
        self.tab_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_layout.setSpacing(6)
        self.tab_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.tab_container, 0)
        self.main_layout.addStretch(1)

        self.add_button = QPushButton("+")
        self.add_button.setObjectName("AddTabButton")
        self.add_button.setFixedSize(32, 32)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.add_tab_requested.emit)
        self.main_layout.addWidget(self.add_button)

        # Connect signals from the page manager
        self.page_manager.page_added.connect(self.add_tab)
        self.page_manager.page_removed.connect(self.remove_tab)
        self.page_manager.active_page_changed.connect(self.update_active_tab)

        self.apply_theme(self.current_theme)
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        """Clears and rebuilds all tabs from the page manager."""
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
        """Adds a new tab widget to the bar."""
        tab = TabWidget(page, self.data_provider, self)
        tab.clicked.connect(lambda p=page.page_id: self.tab_changed.emit(p))
        tab.close_requested.connect(lambda p=page.page_id: self.close_tab_requested.emit(p))
        self.tab_layout.addWidget(tab)
        self._tabs[page.page_id] = tab
        self.apply_theme(self.current_theme)

    def remove_tab(self, page_id: str):
        """Removes a tab widget from the bar and cleans it up."""
        tab = self._tabs.pop(page_id, None)
        if tab:
            tab.cleanup()
            tab.deleteLater()

    def update_active_tab(self, active_page_id: str):
        """Sets the visual active state for the corresponding tab."""
        for page_id, tab in self._tabs.items():
            is_active = (page_id == active_page_id)
            tab.set_active(is_active)
            if is_active:
                tab.raise_()

    def update_page_name(self, page_id: str, new_name: str):
        """Updates the name displayed on a specific tab."""
        tab = self._tabs.get(page_id)
        if tab:
            tab.update_name(new_name)

    def apply_theme(self, theme_name: str):
        """Applies the current theme to the tab bar and all child tabs."""
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        # Theme-specific colors from GEMINI_PROMPT.md spec
        if theme_name == "dark":
            tab_bar_bg = "#1e1e1e"
            active_tab_bg = "#3a3a3a"
            inactive_tab_bg = "#2a2a2a"
            hover_tab_bg = "#333333"
            active_text = "#ffffff"
            inactive_text = "#aaaaaa"
            underline_color = "#ffffff"
        else:  # light mode
            tab_bar_bg = "#f0f0f0"
            active_tab_bg = "#e8e8e8"
            inactive_tab_bg = "#f5f5f5"
            hover_tab_bg = "#eeeeee"
            active_text = "#000000"
            inactive_text = "#666666"
            underline_color = "#2196F3"

        self.setStyleSheet(f"""
            QWidget#PageTabBar {{
                background-color: {tab_bar_bg};
                border: none;
                padding: 0px 0px 0px 0px;
                min-height: 48px;
            }}
            QWidget#TabContainer {{
                background-color: transparent;
            }}
            QPushButton#AddTabButton {{
                background-color: {inactive_tab_bg};
                border: 1px solid {inactive_text};
                color: {active_text};
                border-radius: 4px;
                font-weight: 600;
                font-size: 18px;
                padding: 8px 16px;
                min-width: 32px;
                min-height: 32px;
            }}
            QPushButton#AddTabButton:hover {{
                background-color: {hover_tab_bg};
                color: {active_text};
                border-color: {active_text};
            }}
        """)
        for tab in self._tabs.values():
            tab.apply_theme(theme_name)


class TabWidget(QWidget):
    """An individual tab with live price updates."""
    clicked = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, page: StockPage, data_provider: TickerDataProvider, parent=None):
        super().__init__(parent)
        self.page = page
        self.data_provider = data_provider
        self.is_active = False
        self.current_theme = "dark"
        self.worker: Optional[SnapshotWorker] = None

        self.setObjectName("TabWidget")
        self.setFixedHeight(40)
        self.setMinimumWidth(120)
        self.setMaximumWidth(200)

        # --- Layouts and Widgets ---
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(16, 8, 16, 8)
        self.main_layout.setSpacing(12)

        self.name_label = QLabel(page.page_name)
        self.name_label.setObjectName("TabLabel")

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("TabCloseButton")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.hide()
        self.close_button.clicked.connect(self.close_requested.emit)

        self.main_layout.addWidget(self.name_label)
        self.main_layout.addWidget(self.close_button)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Force initial size
        self.setMinimumSize(120, 40)
        self.updateGeometry()

        # Simplified - no price updates for now

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton: self.clicked.emit()
        elif event.button() == Qt.MouseButton.MiddleButton: self.close_requested.emit()
    
    def enterEvent(self, event):
        self.close_button.show()
        if not self.is_active: self.setProperty("hover", "true")
        self._update_style()
        
    def leaveEvent(self, event):
        self.close_button.hide()
        self.setProperty("hover", "false")
        self._update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.setProperty("active", "true" if active else "false")

        # Directly set background using palette for reliability
        from PyQt6.QtGui import QPalette, QColor
        from core.themes import THEMES
        theme = THEMES[self.current_theme]

        palette = self.palette()
        if active:
            if self.current_theme == "dark":
                palette.setColor(QPalette.ColorRole.Window, QColor("#3a3a3a"))
            else:
                palette.setColor(QPalette.ColorRole.Window, QColor("#e8e8e8"))
        else:
            if self.current_theme == "dark":
                palette.setColor(QPalette.ColorRole.Window, QColor("#2a2a2a"))
            else:
                palette.setColor(QPalette.ColorRole.Window, QColor("#f5f5f5"))

        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self._update_style()
        
    def _update_style(self):
        """Forces a QSS re-evaluation for the widget."""
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        self.repaint()

    def apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        # Theme-specific colors from GEMINI_PROMPT.md spec
        if theme_name == "dark":
            active_tab_bg = "#3a3a3a"
            inactive_tab_bg = "#2a2a2a"
            hover_tab_bg = "#333333"
            active_text = "#ffffff"
            inactive_text = "#aaaaaa"
            underline_color = "#ffffff"
        else:  # light mode
            active_tab_bg = "#e8e8e8"
            inactive_tab_bg = "#f5f5f5"
            hover_tab_bg = "#eeeeee"
            active_text = "#000000"
            inactive_text = "#666666"
            underline_color = "#2196F3"

        self.setStyleSheet(f"""
            QWidget#TabWidget {{
                background-color: {inactive_tab_bg};
                border: none;
                border-bottom: 3px solid transparent;
                border-radius: 0px;
                padding-bottom: 0px;
            }}
            QWidget#TabWidget[active='true'] {{
                background-color: {active_tab_bg};
                border-bottom: 3px solid {underline_color};
            }}
            QWidget#TabWidget[hover='true'] {{
                background-color: {hover_tab_bg};
            }}

            QWidget#PriceContainer {{
                background-color: transparent;
            }}

            QLabel#TabLabel {{
                color: {inactive_text};
                font-weight: 500;
                font-size: 13px;
                background-color: transparent;
            }}
            QWidget#TabWidget[active='true'] QLabel#TabLabel {{
                color: {active_text};
                font-weight: 700;
            }}

            QLabel#PriceLabel {{
                font-size: 11px;
                font-weight: 600;
                color: {active_text};
                background-color: transparent;
            }}
            QLabel#ChangeLabel {{
                font-size: 10px;
                font-weight: 500;
                color: {inactive_text};
                background-color: transparent;
            }}
            QLabel#ChangeLabel[trend='positive'] {{ color: #4ade80; }}
            QLabel#ChangeLabel[trend='negative'] {{ color: #f43f5e; }}

            QPushButton#TabCloseButton {{
                background-color: transparent;
                color: {inactive_text};
                border: none;
                border-radius: 0px;
                font-weight: 400;
                font-size: 18px;
            }}
            QPushButton#TabCloseButton:hover {{
                background-color: {hover_tab_bg};
                color: {active_text};
            }}
        """)
        self._update_style()
        
    def update_name(self, new_name: str):
        """Updates the tab's name."""
        self.page.page_name = new_name
        self.page.primary_ticker = new_name
        self.name_label.setText(new_name)

    def cleanup(self):
        """Cleanup before deletion."""
        pass