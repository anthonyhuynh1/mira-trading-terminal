"""Simple test to verify tab system works."""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

from ui.page_tab_bar import PageTabBar
from core.stock_page_manager import StockPageManager

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab System Test")
        self.resize(800, 600)

        # Central widget
        central = QWidget()
        layout = QVBoxLayout(central)

        # Page manager
        self.page_manager = StockPageManager(self)
        self.page_manager.page_created.connect(self._on_page_created)

        # Tab bar
        self.tab_bar = PageTabBar()
        self.tab_bar.tab_clicked.connect(lambda page: self.page_manager.switch_to_page(page))
        self.tab_bar.new_tab_requested.connect(self._create_page)
        layout.addWidget(self.tab_bar)

        # Test button
        test_btn = QPushButton("Create Test Page")
        test_btn.clicked.connect(self._create_page)
        layout.addWidget(test_btn)

        self.setCentralWidget(central)

        # Create initial page
        self._create_page()

    def _create_page(self):
        count = self.page_manager.get_page_count()
        page = self.page_manager.create_page(
            page_name=f"Page {count + 1}",
            initial_ticker="SPY" if count == 0 else None,
            activate=True
        )
        print(f"Created page: {page.page_name} (ID: {page.page_id})")

    def _on_page_created(self, page):
        print(f"Page created signal: {page.page_name}")
        self.tab_bar.add_page(page)
        print(f"Tab bar now has {len(self.tab_bar.tabs)} tabs")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
