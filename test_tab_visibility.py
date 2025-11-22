"""Quick test to verify tab visibility fix."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

def test_tabs():
    """Test tab visibility in the main app."""
    app = QApplication(sys.argv)

    # Import after QApplication is created
    from trading_app import TradingTerminal

    window = TradingTerminal()
    window.show()

    # Check visibility after a short delay (let UI settle)
    def check_visibility():
        print("\n=== Tab Visibility Test ===")
        print(f"✓ Window visible: {window.isVisible()}")
        print(f"✓ Menu widget visible: {window.menuWidget().isVisible() if window.menuWidget() else 'No menu widget'}")
        print(f"✓ Tab bar visible: {window.page_tab_bar.isVisible()}")
        print(f"✓ Tab bar has {len(window.page_tab_bar.tabs)} tab(s)")

        if window.page_tab_bar.tabs:
            for i, tab in enumerate(window.page_tab_bar.tabs):
                print(f"  Tab {i+1}: '{tab.label.text()}' - Visible: {tab.isVisible()}")

        print(f"✓ + button visible: {window.page_tab_bar.new_tab_btn.isVisible()}")
        print(f"✓ Tab bar height: {window.page_tab_bar.height()}px")
        print(f"✓ Tab bar geometry: {window.page_tab_bar.geometry()}")

        print("\n✅ If tabs are visible in the UI, the fix worked!")
        print("   Close the window to end the test.")

    # Schedule check after 1 second
    QTimer.singleShot(1000, check_visibility)

    sys.exit(app.exec())

if __name__ == "__main__":
    test_tabs()
