"""
Simplified validation-only manager for business rules.
Primary purpose: Enforce screener locking (screener stays leftmost).
Layout management is delegated to Qt's native dock system.
"""
from typing import Optional, Tuple
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QDockWidget


class DockValidator:
    """
    Validates dock operations based on business rules.

    Key principle: Trust Qt for layout, only validate business constraints.
    The only custom business rule: screener must remain in leftmost position.
    """

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.screener_dock_id: Optional[str] = None
        self._dock_registry: dict[str, QDockWidget] = {}  # dock_id → dock widget

    def register_dock(self, dock_id: str, dock: QDockWidget):
        """Register a dock for validation (minimal tracking)"""
        self._dock_registry[dock_id] = dock

    def unregister_dock(self, dock_id: str):
        """Unregister a dock"""
        self._dock_registry.pop(dock_id, None)

    def set_screener_dock(self, dock_id: str):
        """Mark a dock as the screener (leftmost, immovable)"""
        self.screener_dock_id = dock_id

    def is_screener_dock(self, dock_id: str) -> bool:
        """Check if a dock is the screener"""
        return dock_id == self.screener_dock_id

    def validate_drop(self, source_dock_id: str, target_dock_id: str, zone: str) -> Tuple[bool, str]:
        """
        Validate if a drop operation is allowed based on business rules.

        Args:
            source_dock_id: The dock being dragged
            target_dock_id: The dock being dropped onto
            zone: The drop zone ('merge', 'top', 'bottom', 'left', 'right')

        Returns:
            (is_valid, error_message)
        """
        # Business Rule 1: Cannot move the screener
        if self.is_screener_dock(source_dock_id):
            return False, "Cannot move screener widget"

        # Business Rule 2: Cannot drop to the left of screener
        if zone == 'left' and self.is_screener_dock(target_dock_id):
            return False, "Cannot place widgets left of screener"

        # All other operations are allowed - Qt handles the layout
        return True, ""

    def can_move_dock(self, dock_id: str) -> bool:
        """Check if a dock can be moved (screener cannot)"""
        return not self.is_screener_dock(dock_id)

    def get_dock(self, dock_id: str) -> Optional[QDockWidget]:
        """Get a registered dock by ID"""
        return self._dock_registry.get(dock_id)

    def print_layout(self):
        """Debug: Print current dock layout (query Qt directly)"""
        print("\n=== Dock Layout (Qt State) ===")

        # Get all dock widgets from main window
        docks = self.main_window.findChildren(QDockWidget)

        # Group by dock area
        areas = {
            Qt.DockWidgetArea.LeftDockWidgetArea: "Left",
            Qt.DockWidgetArea.RightDockWidgetArea: "Right",
            Qt.DockWidgetArea.TopDockWidgetArea: "Top",
            Qt.DockWidgetArea.BottomDockWidgetArea: "Bottom",
        }

        for area_enum, area_name in areas.items():
            area_docks = [d for d in docks if self.main_window.dockWidgetArea(d) == area_enum]
            if area_docks:
                print(f"{area_name} Area:")
                for dock in area_docks:
                    screener_tag = " [SCREENER]" if dock.objectName() == self.screener_dock_id else ""
                    print(f"  - {dock.objectName()}{screener_tag}")

        print("=" * 30 + "\n")
