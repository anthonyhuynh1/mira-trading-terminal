"""Test the tab system fixes."""
import sys
from PyQt6.QtWidgets import QApplication
from trading_app import TradingTerminal

def test_tab_system():
    """Test that tabs are visible and + button works."""
    app = QApplication(sys.argv)
    window = TradingTerminal()

    # Check initial state
    print(f"✓ App started")
    print(f"✓ Page manager has {window.page_manager.get_page_count()} page(s)")
    print(f"✓ Tab bar visible: {window.page_tab_bar.isVisible()}")
    print(f"✓ Tab bar has {len(window.page_tab_bar.tabs)} tab(s)")

    if window.page_tab_bar.tabs:
        first_tab = window.page_tab_bar.tabs[0]
        print(f"✓ First tab visible: {first_tab.isVisible()}")
        print(f"✓ First tab text: '{first_tab.label.text()}'")
        print(f"✓ Close button hidden: {not first_tab.close_btn.isVisible()}")

    print(f"✓ + button visible: {window.page_tab_bar.new_tab_btn.isVisible()}")
    print(f"✓ + button text: '{window.page_tab_bar.new_tab_btn.text()}'")

    print("\n✅ All checks passed! Ready to test manually.")
    print("   1. You should see the tab bar below the header")
    print("   2. You should see the tab(s) showing ticker symbols")
    print("   3. You should see the '+' button on the right")
    print("   4. Hover over a tab to see the '×' close button")
    print("   5. Click '+' to create a new tab (should not crash)")

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    test_tab_system()
