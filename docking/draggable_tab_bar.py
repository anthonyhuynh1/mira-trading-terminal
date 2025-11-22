"""
Custom tab bar with drag-and-drop support for moving tabs between docks.
"""

from PyQt6.QtCore import Qt, QPoint, QMimeData
from PyQt6.QtGui import QDrag, QCursor
from PyQt6.QtWidgets import QTabBar, QDockWidget, QApplication


class DraggableTabBar(QTabBar):
    """
    Tab bar that supports dragging tabs to other docks or positions.

    Features:
    - Click on tab text to drag it
    - Drag to another dock to merge as tab
    - Drag to edges to split
    - Double-click empty space to float dock
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_start_pos = None
        self._dragging_index = -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is on a tab
            index = self.tabAt(event.pos())
            if index >= 0:
                # Store drag start position and index
                self._drag_start_pos = event.pos()
                self._dragging_index = index
                # Let QTabBar handle tab selection
                super().mousePressEvent(event)
            else:
                # Click on empty space - ignore to allow dock dragging
                event.ignore()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Check if we should start a drag
        if (self._drag_start_pos is not None and
            self._dragging_index >= 0 and
            (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance()):

            # Start drag operation
            self._start_drag()
            return

        # Otherwise, let QTabBar handle it
        if self.tabAt(event.pos()) >= 0:
            super().mouseMoveEvent(event)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        # Reset drag state
        self._drag_start_pos = None
        self._dragging_index = -1

        # Let QTabBar handle release
        if self.tabAt(event.pos()) >= 0:
            super().mouseReleaseEvent(event)
        else:
            event.ignore()

    def _start_drag(self):
        """Initiate drag operation for the tab."""
        if self._dragging_index < 0:
            return

        # Find parent WorkspaceDock
        dock = self._find_parent_dock()
        if not dock:
            return

        # Get tab key from tab data
        tab_key = self.tabData(self._dragging_index)
        if not tab_key:
            # Fallback to tab text
            tab_key = self.tabText(self._dragging_index)

        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()

        # Store dock ID and tab key
        data = f"{dock.dock_id}|{tab_key}"
        mime_data.setData("application/x-mira-tab", data.encode())
        mime_data.setText(tab_key)

        drag.setMimeData(mime_data)

        # Change cursor during drag
        QApplication.setOverrideCursor(Qt.CursorShape.DragMoveCursor)

        # Execute drag
        result = drag.exec(Qt.DropAction.MoveAction)

        # Restore cursor
        QApplication.restoreOverrideCursor()

        # Reset drag state
        self._drag_start_pos = None
        self._dragging_index = -1

    def _find_parent_dock(self):
        """Find the parent WorkspaceDock."""
        parent = self.parent()
        while parent:
            if isinstance(parent, QDockWidget):
                return parent
            parent = parent.parent()
        return None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.tabAt(event.pos())
            if index >= 0:
                # Double-click on tab - emit signal
                super().mouseDoubleClickEvent(event)
            else:
                # Double-click on empty space - toggle dock floating
                try:
                    dock = self._find_parent_dock()
                    if dock and not dock.isHidden():
                        dock.setFloating(not dock.isFloating())
                    event.accept()
                except RuntimeError:
                    event.ignore()
        else:
            super().mouseDoubleClickEvent(event)
