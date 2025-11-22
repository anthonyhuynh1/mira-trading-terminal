"""Debug script to test tab rendering"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from ui.page_tab_bar import PageTabBar
from core.stock_page_manager import StockPageManager
from core.data_provider import TickerDataProvider

app = QApplication(sys.argv)

# Create a simple window
window = QMainWindow()
window.setWindowTitle("Tab Debug")
window.resize(800, 200)

# Create central widget
central = QWidget()
layout = QVBoxLayout(central)
window.setCentralWidget(central)

# Create page manager and tab bar
data_provider = TickerDataProvider()
page_manager = StockPageManager(window)
tab_bar = PageTabBar(page_manager, data_provider, window)

layout.addWidget(tab_bar)

# Create a test page
page = page_manager.create_page(name="SPY", ticker="SPY", activate=True)

print(f"Tab bar height: {tab_bar.height()}")
print(f"Tab bar stylesheet: {tab_bar.styleSheet()[:200]}...")
print(f"Number of tabs: {len(tab_bar._tabs)}")
print(f"Add button text: '{tab_bar.add_button.text()}'")
print(f"Add button size: {tab_bar.add_button.size()}")
print(f"Add button visible: {tab_bar.add_button.isVisible()}")

if tab_bar._tabs:
    first_tab = list(tab_bar._tabs.values())[0]
    print(f"\nFirst tab ticker: {first_tab.page.page_name}")
    print(f"First tab size: {first_tab.size()}")
    print(f"First tab visible: {first_tab.isVisible()}")
    print(f"First tab label text: '{first_tab.name_label.text()}'")

window.show()
print("\nWindow displayed. Close to exit.")
sys.exit(app.exec())
