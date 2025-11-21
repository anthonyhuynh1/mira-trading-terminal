"""
Drop zone overlay for visual feedback during dock widget dragging.
Provides elegant, minimal visual cues showing where widgets can be placed.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget


class DropZoneOverlay(QWidget):
    """
    Elegant overlay showing drop zones with subtle visual feedback.
    Appears when dragging a tab over a dock, showing where it can be placed.
    Design: Subtle brilliance - minimal, thoughtful, sophisticated.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.current_zone = None  # Which zone cursor is in: 'left', 'right', 'top', 'bottom', or None (center = merge)
        self.edge_threshold = 0.30  # 30% of width/height for edge zones (slightly larger for easier targeting)

    def update_cursor_position(self, pos):
        """Update which zone the cursor is in and trigger repaint"""
        old_zone = self.current_zone
        self.current_zone = self._detect_zone(pos)

        if old_zone != self.current_zone:
            self.update()  # Repaint to show new zone

    def _detect_zone(self, pos):
        """Detect which edge zone the cursor is in (or None for center merge)"""
        rect = self.rect()
        x_ratio = pos.x() / rect.width() if rect.width() > 0 else 0
        y_ratio = pos.y() / rect.height() if rect.height() > 0 else 0

        # Check edge zones only
        if x_ratio < self.edge_threshold:
            return 'left'
        elif x_ratio > (1 - self.edge_threshold):
            return 'right'
        elif y_ratio < self.edge_threshold:
            return 'top'
        elif y_ratio > (1 - self.edge_threshold):
            return 'bottom'

        # Center area (not an edge) = merge into dock
        return 'merge'

    def paintEvent(self, event):
        """Paint the drop zones with refined, minimal feedback"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Determine if we're in dark or light mode
        is_dark_mode = True  # Default to dark, could detect from parent

        if self.current_zone:
            # Colors: Subtle and elegant
            if is_dark_mode:
                line_color = QColor(255, 255, 255, 204)  # 80% white - clear but soft
                glow_color = QColor(255, 255, 255, 51)   # 20% white - soft glow
                border_color = QColor(255, 255, 255, 102)  # 40% white - subtle border
            else:
                line_color = QColor(0, 0, 0, 153)
                glow_color = QColor(0, 0, 0, 51)
                border_color = QColor(0, 0, 0, 102)

            if self.current_zone in ['left', 'right', 'top', 'bottom']:
                # Edge zone - show thin line only
                pen = QPen(line_color)
                pen.setWidth(2)
                painter.setPen(pen)

                if self.current_zone == 'left':
                    x = int(rect.width() * self.edge_threshold)
                    painter.drawLine(x, 0, x, rect.height())
                    # Subtle glow
                    painter.setPen(QPen(glow_color, 4))
                    painter.drawLine(x, 0, x, rect.height())

                elif self.current_zone == 'right':
                    x = int(rect.width() * (1 - self.edge_threshold))
                    painter.setPen(QPen(line_color, 2))
                    painter.drawLine(x, 0, x, rect.height())
                    # Subtle glow
                    painter.setPen(QPen(glow_color, 4))
                    painter.drawLine(x, 0, x, rect.height())

                elif self.current_zone == 'top':
                    y = int(rect.height() * self.edge_threshold)
                    painter.setPen(QPen(line_color, 2))
                    painter.drawLine(0, y, rect.width(), y)
                    # Subtle glow
                    painter.setPen(QPen(glow_color, 4))
                    painter.drawLine(0, y, rect.width(), y)

                elif self.current_zone == 'bottom':
                    y = int(rect.height() * (1 - self.edge_threshold))
                    painter.setPen(QPen(line_color, 2))
                    painter.drawLine(0, y, rect.width(), y)
                    # Subtle glow
                    painter.setPen(QPen(glow_color, 4))
                    painter.drawLine(0, y, rect.width(), y)

            elif self.current_zone == 'merge':
                # Center area - highlight entire dock border
                pen = QPen(border_color)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.drawRect(rect.adjusted(1, 1, -1, -1))
