#!/usr/bin/env python3
"""Test script to verify tab bar alignment and styling."""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit
from PyQt6.QtCore import Qt

# Add parent directory to path to import modules
sys.path.insert(0, '/Users/anthony/Trading /Python Financials/trading-terminal')

from ui.page_tab_bar import PageTabBar
from core.stock_page_manager import StockPageManager
from core.data_provider import TickerDataProvider

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab Bar Alignment Test")
        self.setGeometry(100, 100, 1200, 800)

        # Set dark theme for the window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0a;
            }
        """)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create managers and providers
        self.page_manager = StockPageManager()
        self.data_provider = TickerDataProvider()

        # Create tab bar
        self.tab_bar = PageTabBar(self.page_manager, self.data_provider)
        layout.addWidget(self.tab_bar)

        # Add some test pages
        self.page_manager.create_page("SPY", "SPY")
        self.page_manager.create_page("QQQ", "QQQ")
        self.page_manager.create_page("AAPL", "AAPL")
        self.page_manager.create_page("MSFT", "MSFT")

        # Set first page as active
        if self.page_manager.pages:
            self.page_manager.set_active_page(self.page_manager.pages[0].page_id)

        # Add content area
        content = QTextEdit()
        content.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: none;
                font-size: 14px;
                padding: 20px;
            }
        """)
        content.setPlainText("""
Tab Bar Alignment Test
======================

This test window verifies the following:

1. Close button (×) vertical alignment
   - Should be perfectly centered with tab text
   - Should maintain alignment when tab is active/inactive

2. Visual separation between tabs
   - Each tab should have visible borders
   - Clear distinction between active and inactive tabs
   - Proper spacing between tabs

3. Professional appearance
   - Clean, minimal design
   - Smooth hover effects
   - Consistent styling across all elements

4. Tab height and proportions
   - Tab bar is 44px tall
   - Individual tabs fit within container
   - Proper padding and margins

Try the following:
- Click on different tabs to test active state
- Hover over tabs to see hover effects
- Click close buttons to test alignment
- Add new tabs with the + button
        """)
        layout.addWidget(content)

        # Connect signals
        self.tab_bar.tab_changed.connect(lambda page_id: print(f"Tab changed to: {page_id}"))
        self.tab_bar.close_tab_requested.connect(self.handle_close_tab)
        self.tab_bar.add_tab_requested.connect(self.handle_add_tab)

    def handle_close_tab(self, page_id):
        print(f"Closing tab: {page_id}")
        self.page_manager.remove_page(page_id)

    def handle_add_tab(self):
        import random
        tickers = ["NVDA", "TSLA", "AMZN", "GOOGL", "META", "NFLX", "AMD", "INTC"]
        new_ticker = random.choice(tickers)
        print(f"Adding new tab: {new_ticker}")
        self.page_manager.create_page(new_ticker, new_ticker)
        # Set the new page as active
        if self.page_manager.pages:
            self.page_manager.set_active_page(self.page_manager.pages[-1].page_id)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())