"""
Screener widget for searching and filtering stocks.
Provides watchlist management and quick access to different market setups.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QListWidget, QSizePolicy
)

from core.themes import BASE_SPACING, TOUCH_TARGET
from core.config import DEFAULT_TICKERS


class ScreenerWidget(QWidget):
    """Left sidebar: Stock screener and search."""

    def __init__(self, ticker_callback):
        super().__init__()
        self.ticker_callback = ticker_callback  # Callback when ticker selected
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(BASE_SPACING)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("Market Scanner")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Search, filter, and monitor breakout-ready names.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search ticker...")
        self.search_input.returnPressed.connect(self.search_ticker)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_ticker)
        self.search_btn.setMinimumHeight(TOUCH_TARGET)
        self.search_input.setMinimumHeight(TOUCH_TARGET)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # Quick filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filters = [
            ("Breakouts", "breakout"),
            ("False breaks", "false"),
            ("Tight ranges", "consolidation"),
            ("Volume spikes", "volume"),
        ]
        for label, key in filters:
            btn = QPushButton(label)
            btn.setObjectName("SegmentButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, l=label, k=key: self.apply_filter(l, k))
            filter_row.addWidget(btn)
        layout.addLayout(filter_row)

        self.filter_summary = QLabel("Focus: All setups")
        self.filter_summary.setObjectName("SectionHint")
        layout.addWidget(self.filter_summary)

        # Quick scan button
        scan_btn = QPushButton("Scan Universe")
        scan_btn.clicked.connect(self.scan_universe)
        scan_btn.setMinimumHeight(TOUCH_TARGET)
        scan_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(scan_btn)

        # Ticker list
        self.ticker_list = QListWidget()
        self.ticker_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ticker_list.itemClicked.connect(self.on_ticker_selected)
        watchlist_label = QLabel("Watchlist")
        watchlist_label.setObjectName("SectionTitle")
        layout.addWidget(watchlist_label)
        layout.addWidget(self.ticker_list)

        # Load default tickers
        for ticker in DEFAULT_TICKERS:
            self.ticker_list.addItem(ticker)

        self.setLayout(layout)
        self.active_filter = "all"

    def search_ticker(self):
        """Search and add ticker."""
        ticker = self.search_input.text().strip().upper()
        if ticker and ticker not in [self.ticker_list.item(i).text() for i in range(self.ticker_list.count())]:
            self.ticker_list.addItem(ticker)
            self.ticker_list.setCurrentRow(self.ticker_list.count() - 1)
            self.ticker_callback(ticker)
        self.search_input.clear()

    def scan_universe(self):
        """Run scanner on universe."""
        # This would trigger scanner - for now just show message
        self.ticker_list.addItem("Scanning...")
        self.filter_summary.setText("Focus: Running scan...")

    def apply_filter(self, label: str, key: str):
        """Update selected filter badge."""
        self.active_filter = key
        self.filter_summary.setText(f"Focus: {label}")

    def on_ticker_selected(self, item):
        """Handle ticker selection."""
        text = item.text().strip()
        if text.lower().startswith("scanning"):
            return
        self.ticker_callback(text)

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)
