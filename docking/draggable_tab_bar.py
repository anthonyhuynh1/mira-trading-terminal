"""
Custom tab bar with smart event handling for dock widgets.
Supports tab dragging while allowing dock widget dragging from empty space.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTabBar, QDockWidget


class DraggableTabBar(QTabBar):
    """
    Custom tab bar with smart event handling:
    - Clicks ON a tab: handle tab selection and dragging
    - Clicks on EMPTY space: ignore event to allow dock widget dragging
    """

    drag_started = pyqtSignal(int, object)  # Emitted when user starts dragging a tab

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_start_pos = None  # Starting position for tab drag detection
        self._drag_tab_index = -1    # Index of tab being dragged (-1 = no drag)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is directly on a tab
            index = self.tabAt(event.pos())
            if index >= 0:
                # Click is on a tab - handle tab selection and prepare for tab dragging
                self._drag_start_pos = event.pos()
                self._drag_tab_index = index
                super().mousePressEvent(event)  # Let QTabBar handle tab selection
            else:
                # Click is on empty tab bar space - ignore so dock widget can handle dragging
                event.ignore()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_start_pos:
            # User is dragging and started on a tab
            dist = (event.pos() - self._drag_start_pos).manhattanLength()
            if dist > 10 and self._drag_tab_index >= 0:
                # Drag threshold exceeded - start tab drag operation
                self.drag_started.emit(self._drag_tab_index, self._drag_start_pos)
                self._drag_start_pos = None
                self._drag_tab_index = -1
                return

        # Only propagate move events if we're tracking a tab drag
        if self._drag_start_pos is not None:
            super().mouseMoveEvent(event)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        # Reset drag tracking state
        was_tracking = self._drag_start_pos is not None
        self._drag_start_pos = None
        self._drag_tab_index = -1

        # Only propagate if we were tracking a tab interaction
        if was_tracking:
            super().mouseReleaseEvent(event)
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if double-click is on a tab or empty space
            index = self.tabAt(event.pos())
            if index >= 0:
                # Double-click on tab - let QTabBar handle it (emits tabBarDoubleClicked)
                super().mouseDoubleClickEvent(event)
            else:
                # Double-click on empty tab bar space - toggle dock floating state
                # Find parent WorkspaceDock and toggle its floating state
                try:
                    dock = self.parent()
                    while dock and not isinstance(dock, QDockWidget):
                        dock = dock.parent()
                    # Safety check: ensure dock still exists and is valid
                    if dock and not dock.isHidden():
                        dock.setFloating(not dock.isFloating())
                    event.accept()
                except RuntimeError:
                    # Dock was deleted - ignore the event
                    event.ignore()
        else:
            super().mouseDoubleClickEvent(event)
