"""Debug script to diagnose tab visibility issues."""
import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

# Set OpenGL context sharing BEFORE creating QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

app = QApplication(sys.argv)

# Import after QApplication
from trading_app import TradingTerminal

window = TradingTerminal()
window.show()

def debug_info():
    """Print detailed debug information."""
    print("\n" + "="*60)
    print("TAB BAR DEBUG INFORMATION")
    print("="*60)

    # Main window info
    print(f"\n1. Main Window:")
    print(f"   - Visible: {window.isVisible()}")
    print(f"   - Size: {window.size().width()}x{window.size().height()}")

    # Menu widget (header container)
    menu_widget = window.menuWidget()
    print(f"\n2. Menu Widget (Header Container):")
    if menu_widget:
        print(f"   - Exists: Yes")
        print(f"   - Visible: {menu_widget.isVisible()}")
        print(f"   - Size: {menu_widget.size().width()}x{menu_widget.size().height()}")
        print(f"   - Geometry: {menu_widget.geometry()}")
        print(f"   - StyleSheet: {menu_widget.styleSheet()[:100] if menu_widget.styleSheet() else 'None'}...")
    else:
        print(f"   - Exists: No")

    # Page tab bar
    print(f"\n3. Page Tab Bar:")
    print(f"   - Visible: {window.page_tab_bar.isVisible()}")
    print(f"   - Size: {window.page_tab_bar.size().width()}x{window.page_tab_bar.size().height()}")
    print(f"   - Fixed Height: {window.page_tab_bar.height()}")
    print(f"   - Geometry: {window.page_tab_bar.geometry()}")
    print(f"   - Parent: {window.page_tab_bar.parent()}")
    print(f"   - Number of tabs: {len(window.page_tab_bar.tabs)}")

    # Tab container
    print(f"\n4. Tab Container:")
    print(f"   - Visible: {window.page_tab_bar.tab_container.isVisible()}")
    print(f"   - Size: {window.page_tab_bar.tab_container.size().width()}x{window.page_tab_bar.tab_container.size().height()}")
    print(f"   - Geometry: {window.page_tab_bar.tab_container.geometry()}")

    # Individual tabs
    print(f"\n5. Individual Tabs:")
    for i, tab in enumerate(window.page_tab_bar.tabs):
        print(f"   Tab {i+1}:")
        print(f"     - Label: '{tab.label.text()}'")
        print(f"     - Visible: {tab.isVisible()}")
        print(f"     - Size: {tab.size().width()}x{tab.size().height()}")
        print(f"     - Geometry: {tab.geometry()}")
        print(f"     - Parent visible: {tab.parent().isVisible() if tab.parent() else 'No parent'}")
        print(f"     - Active: {tab.is_active}")

    # New tab button
    print(f"\n6. New Tab Button:")
    print(f"   - Visible: {window.page_tab_bar.new_tab_btn.isVisible()}")
    print(f"   - Text: '{window.page_tab_bar.new_tab_btn.text()}'")
    print(f"   - Size: {window.page_tab_bar.new_tab_btn.size().width()}x{window.page_tab_bar.new_tab_btn.size().height()}")
    print(f"   - Geometry: {window.page_tab_bar.new_tab_btn.geometry()}")

    # Check if the tab bar has zero height/width
    if window.page_tab_bar.height() == 0 or window.page_tab_bar.width() == 0:
        print(f"\n⚠️  WARNING: Tab bar has zero dimensions!")

    if not window.page_tab_bar.isVisible():
        print(f"\n⚠️  WARNING: Tab bar is NOT visible!")

    print("\n" + "="*60)
    print("If tabs aren't visible, check:")
    print("1. Tab bar visibility = True")
    print("2. Tab bar height > 0")
    print("3. Tab bar width > 0")
    print("4. Individual tabs visible = True")
    print("5. Tab container visible = True")
    print("="*60 + "\n")

# Run debug after 1.5 seconds
QTimer.singleShot(1500, debug_info)

sys.exit(app.exec())
