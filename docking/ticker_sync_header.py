"""
Ticker Sync Header component with visual sync indicators.

Displays ticker with chain/pin icon showing sync state.
Provides intuitive controls for changing sync state and ticker.
"""
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QInputDialog, QSizePolicy
)
from PyQt6.QtGui import QDrag, QCursor


class TickerSyncHeader(QWidget):
    """
    Header showing ticker with sync/pin control.

    Displays:
    - Chain icon (🔗) when synced to a link group
    - Pin icon (📌) when independent
    - Ticker symbol (clickable to change)
    - Color coding: blue=synced, orange=pinned, gray=no ticker

    Signals:
        ticker_changed: Emitted when user manually changes ticker (ticker: str)
        sync_toggled: Emitted when user toggles sync state (group: int | None)
        group_selected: Emitted when user selects a specific group (group: int)
    """

    ticker_changed = pyqtSignal(str)  # New ticker selected
    sync_toggled = pyqtSignal(object)  # Group number or None
    group_selected = pyqtSignal(int)  # Specific group selected

    def __init__(self, widget_key: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.widget_key = widget_key
        self.current_ticker: str = ""
        self.link_group: Optional[int] = None
        self._setup_ui()

    def _setup_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Link/Pin toggle button
        self.link_btn = QPushButton()
        self.link_btn.setFixedSize(24, 20)
        self.link_btn.setFlat(True)
        self.link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.link_btn.clicked.connect(self._on_link_button_clicked)
        self.link_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.link_btn.customContextMenuRequested.connect(self._show_group_menu)

        # Ticker label (clickable)
        self.ticker_label = QLabel("---")
        self.ticker_label.setMinimumWidth(40)
        self.ticker_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.ticker_label.mousePressEvent = self._on_ticker_click
        self.ticker_label.setObjectName("TickerSyncLabel")

        layout.addWidget(self.link_btn)
        layout.addWidget(self.ticker_label)
        layout.addStretch()

        # Enable drag-drop for ticker assignment
        self.setAcceptDrops(True)

        # Update initial appearance
        self._update_appearance()

    def _update_appearance(self):
        """Update icon and colors based on current sync state."""
        if self.link_group is not None:
            # Synced to a group - show the header
            self.setVisible(True)
            self.link_btn.setText(f"🔗{self.link_group}")
            self.link_btn.setToolTip(f"Synced to Group {self.link_group} (click to unlink, right-click for options)")
            self.link_btn.setVisible(True)
            self.ticker_label.setVisible(True)
            color = "#2196F3"  # Blue for synced

            # Style the ticker label
            if not self.current_ticker:
                ticker_color = "#888888"  # Gray for no ticker
            else:
                ticker_color = color

            self.ticker_label.setStyleSheet(f"""
                QLabel#TickerSyncLabel {{
                    font-weight: bold;
                    font-size: 11px;
                    color: {ticker_color};
                    padding: 2px 6px;
                    border-radius: 3px;
                    background: transparent;
                }}
                QLabel#TickerSyncLabel:hover {{
                    background: rgba(255, 255, 255, 0.1);
                }}
            """)

            self.link_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 12px;
                    color: {color};
                    border: none;
                    background: transparent;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 3px;
                }}
            """)
        else:
            # Not in a group - hide the entire header widget
            self.setVisible(False)

    def _on_link_button_clicked(self):
        """Unlink from current group."""
        if self.link_group is not None:
            # Currently synced → unlink (widget follows global ticker)
            self.sync_toggled.emit(None)

    def _show_group_menu(self, pos):
        """Show menu to select specific link group."""
        from PyQt6.QtWidgets import QMenu

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

        # Add "No Link" option
        none_action = menu.addAction("No Link (Independent)")
        none_action.setCheckable(True)
        none_action.setChecked(self.link_group is None)
        none_action.triggered.connect(lambda: self.sync_toggled.emit(None))

        menu.addSeparator()

        # Add group options (1-6)
        for group in range(1, 7):
            action = menu.addAction(f"Link Group {group}")
            action.setCheckable(True)
            action.setChecked(self.link_group == group)
            action.triggered.connect(lambda checked=False, g=group: self.sync_toggled.emit(g))

        # Show menu at button position
        menu.exec(self.link_btn.mapToGlobal(pos))

    def _on_ticker_click(self, event):
        """Show ticker input dialog when clicking ticker."""
        new_ticker, ok = QInputDialog.getText(
            self,
            "Change Ticker",
            f"Enter ticker symbol for {self.widget_key}:",
            text=self.current_ticker
        )

        if ok and new_ticker.strip():
            ticker = new_ticker.strip().upper()
            self.set_ticker(ticker)
            self.ticker_changed.emit(ticker)

    def set_ticker(self, ticker: str):
        """
        Update the displayed ticker.

        Args:
            ticker: Ticker symbol to display
        """
        self.current_ticker = ticker
        self.ticker_label.setText(ticker if ticker else "---")
        self._update_appearance()

    def set_link_group(self, group: Optional[int]):
        """
        Update the link group.

        Args:
            group: Link group number (1-6) or None for independent
        """
        self.link_group = group
        self._update_appearance()

    def dragEnterEvent(self, event):
        """Accept ticker drops from screener."""
        if event.mimeData().hasText():
            # Check if it looks like a ticker (simple validation)
            text = event.mimeData().text().strip().upper()
            if text and len(text) <= 5:  # Typical ticker length
                event.acceptProposedAction()
                # Highlight to show drop is valid
                self.ticker_label.setStyleSheet(self.ticker_label.styleSheet() + """
                    QLabel#TickerSyncLabel {
                        background: rgba(33, 150, 243, 0.2) !important;
                    }
                """)
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Remove highlight when drag leaves."""
        self._update_appearance()  # Reset styling

    def dropEvent(self, event):
        """Handle ticker drop - just change ticker (stays in same group)."""
        ticker = event.mimeData().text().strip().upper()

        if ticker:
            # Set ticker (keeps current link group state)
            self.set_ticker(ticker)

            # Notify that ticker changed
            self.ticker_changed.emit(ticker)

            event.acceptProposedAction()

        # Reset styling
        self._update_appearance()
