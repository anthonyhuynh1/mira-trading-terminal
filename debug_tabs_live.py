"""Debug script to inspect live tab rendering"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from trading_app import TradingTerminal

app = QApplication(sys.argv)
window = TradingTerminal()

def inspect_tabs():
    print("\n=== TAB BAR INSPECTION ===")
    tab_bar = window.page_tab_bar

    print(f"Tab bar visible: {tab_bar.isVisible()}")
    print(f"Tab bar size: {tab_bar.size()}")
    print(f"Tab bar position: {tab_bar.pos()}")
    print(f"Tab bar geometry: {tab_bar.geometry()}")
    print(f"Tab bar background: {tab_bar.palette().color(tab_bar.backgroundRole()).name()}")
    print(f"Number of tabs: {len(tab_bar._tabs)}")

    for i, (page_id, tab) in enumerate(tab_bar._tabs.items()):
        print(f"\n--- Tab {i} (ID: {page_id[:8]}) ---")
        print(f"  Visible: {tab.isVisible()}")
        print(f"  Size: {tab.size()}")
        print(f"  Width: {tab.width()}, Height: {tab.height()}")
        print(f"  Minimum size: {tab.minimumSize()}")
        print(f"  Maximum size: {tab.maximumSize()}")
        print(f"  Position: {tab.pos()}")
        print(f"  Background: {tab.palette().color(tab.backgroundRole()).name()}")
        print(f"  AutoFillBackground: {tab.autoFillBackground()}")
        print(f"  StyleSheet length: {len(tab.styleSheet())}")
        print(f"  Label text: '{tab.name_label.text()}'")
        print(f"  Label visible: {tab.name_label.isVisible()}")
        print(f"  Is active: {tab.is_active}")
        print(f"  Active property: {tab.property('active')}")

    print(f"\n+ Button visible: {tab_bar.add_button.isVisible()}")
    print(f"+ Button size: {tab_bar.add_button.size()}")
    print(f"+ Button text: '{tab_bar.add_button.text()}'")

    app.quit()

# Inspect after window is shown
QTimer.singleShot(1000, inspect_tabs)

window.show()
sys.exit(app.exec())
